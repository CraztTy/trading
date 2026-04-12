"""
门下省 - 风控审核与拦截

职责：
- 对每一个信号做强制风控审核
- 一票否决机制
- 实时风险计算
- 熔断机制
- 信号/订单全流程风控

数据流向：
中书省(信号) → 门下省(风控审核) → 尚书省(执行)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import asyncio
import time

from src.strategy.base import Signal, SignalType
from src.common.logger import TradingLogger
from src.common.metrics import metrics
from src.risk.rules import (
    RiskRule, RiskLevel, RiskRuleType, RiskCheckResult,
    PositionLimitRule, StopLossCheckRule, DailyLossLimitRule,
    OrderFrequencyRule, ConsecutiveLossRule, PriceLimitRule, BlacklistRule,
    rule_registry
)

logger = TradingLogger(__name__)


@dataclass
class AuditResult:
    """审核结果"""
    approved: bool                    # 是否通过
    signal_id: Optional[str] = None   # 信号ID
    checks: List[RiskCheckResult] = field(default_factory=list)
    rejected_by: Optional[str] = None # 拒绝的规则
    reject_reason: Optional[str] = None
    audit_time: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0   # 处理耗时


class MenxiaSheng:
    """
    门下省 - 风控审核中心（单例）

    职责：
    - 审核所有交易信号
    - 执行风控规则链
    - 记录审核日志
    - 触发熔断机制
    - 支持动态规则配置
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # 风控规则链
        self._rules: List[RiskRule] = []

        # 审核日志
        self._audit_log: List[AuditResult] = []
        self._max_log_size = 10000

        # 熔断状态
        self._circuit_breaker_triggered = False
        self._circuit_breaker_reason: Optional[str] = None
        self._circuit_breaker_time: Optional[datetime] = None

        # 审核通过后的回调（发送到尚书省）
        self._approval_callbacks: List[Callable[[Signal, AuditResult], None]] = []

        # 统计
        self._stats = {
            "total_audits": 0,
            "approved": 0,
            "rejected": 0,
            "circuit_breaker_count": 0,
        }

        # 动态配置存储
        self._rule_configs: Dict[str, Dict[str, Any]] = {}

        # 初始化默认规则
        self._init_default_rules()

        logger.info("门下省初始化完成")

    def _init_default_rules(self):
        """初始化默认风控规则"""
        self.add_rule(PositionLimitRule())
        self.add_rule(StopLossCheckRule())
        self.add_rule(DailyLossLimitRule())
        self.add_rule(OrderFrequencyRule())
        self.add_rule(ConsecutiveLossRule())
        self.add_rule(PriceLimitRule())
        self.add_rule(BlacklistRule())

    def add_rule(self, rule: RiskRule):
        """添加风控规则"""
        self._rules.append(rule)
        logger.info(f"添加风控规则: {rule.code} - {rule.name}")

    def remove_rule(self, rule_code: str):
        """移除风控规则"""
        self._rules = [r for r in self._rules if r.code != rule_code]
        logger.info(f"移除风控规则: {rule_code}")

    def enable_rule(self, rule_code: str, enabled: bool = True):
        """启用/禁用规则"""
        for rule in self._rules:
            if rule.code == rule_code:
                rule.enabled = enabled
                logger.info(f"{'启用' if enabled else '禁用'}规则: {rule_code}")
                break

    def update_rule_config(self, rule_code: str, **kwargs) -> bool:
        """
        动态更新规则配置

        Args:
            rule_code: 规则代码（如 "R001", "R004" 等）
            **kwargs: 配置参数

        Returns:
            bool: 是否成功更新
        """
        for rule in self._rules:
            if rule.code == rule_code:
                try:
                    rule.update_config(**kwargs)
                    self._rule_configs[rule_code] = {
                        **self._rule_configs.get(rule_code, {}),
                        **kwargs
                    }
                    logger.info(f"更新规则 {rule_code} 配置: {kwargs}")
                    return True
                except Exception as e:
                    logger.error(f"更新规则 {rule_code} 配置失败: {e}")
                    return False
        logger.warning(f"未找到规则: {rule_code}")
        return False

    def get_rule_config(self, rule_code: str) -> Optional[Dict[str, Any]]:
        """获取规则当前配置"""
        for rule in self._rules:
            if rule.code == rule_code:
                config = {}
                for key in dir(rule):
                    if not key.startswith('_') and not callable(getattr(rule, key)):
                        config[key] = getattr(rule, key)
                return config
        return None

    def configure_rules(self, configs: Dict[str, Dict[str, Any]]):
        """
        批量配置多个规则

        Args:
            configs: {rule_code: {param: value, ...}, ...}
        """
        for rule_code, params in configs.items():
            self.update_rule_config(rule_code, **params)

    def add_to_blacklist(self, symbol: str, reason: str = ""):
        """添加标的到黑名单"""
        for rule in self._rules:
            if isinstance(rule, BlacklistRule):
                rule.add_to_blacklist(symbol, reason)
                return
        # 如果没有黑名单规则，创建一个
        blacklist_rule = BlacklistRule()
        blacklist_rule.add_to_blacklist(symbol, reason)
        self.add_rule(blacklist_rule)

    def remove_from_blacklist(self, symbol: str):
        """从黑名单移除标的"""
        for rule in self._rules:
            if isinstance(rule, BlacklistRule):
                rule.remove_from_blacklist(symbol)
                return

    def set_price_limit(self, symbol: str, limit_pct: Decimal):
        """设置股票涨跌幅限制"""
        for rule in self._rules:
            if isinstance(rule, PriceLimitRule):
                rule.set_symbol_limit(symbol, limit_pct)
                return

    def on_trade_result(self, pnl: Decimal):
        """交易结果回调（用于更新连续亏损等状态）"""
        for rule in self._rules:
            if isinstance(rule, ConsecutiveLossRule):
                rule.on_trade_result(pnl)
            elif isinstance(rule, DailyLossLimitRule):
                rule.update_daily_pnl(pnl)

    async def audit_signal(self, signal: Signal, context: Optional[Dict] = None) -> AuditResult:
        """
        审核交易信号

        Args:
            signal: 交易信号
            context: 上下文信息（持仓、账户等）

        Returns:
            AuditResult: 审核结果
        """
        start_time = time.time()
        context = context or {}

        self._stats["total_audits"] += 1

        # 检查熔断状态
        if self._circuit_breaker_triggered:
            result = AuditResult(
                approved=False,
                signal_id=getattr(signal, 'id', None),
                reject_reason=f"熔断中: {self._circuit_breaker_reason}",
                rejected_by="CIRCUIT_BREAKER"
            )
            self._log_audit(result)
            # 记录熔断拒绝指标
            metrics.increment("risk.rejected", tags={"reason": "circuit_breaker"})
            return result

        # 执行规则链检查
        checks = []
        for rule in self._rules:
            if not rule.enabled:
                continue

            try:
                check_result = rule.check(signal, context)
                checks.append(check_result)

                if not check_result.passed:
                    # 未通过，记录并返回
                    self._stats["rejected"] += 1
                    processing_time_ms = (time.time() - start_time) * 1000
                    audit_result = AuditResult(
                        approved=False,
                        signal_id=getattr(signal, 'id', None),
                        checks=checks,
                        rejected_by=check_result.rule_code,
                        reject_reason=check_result.message,
                        processing_time_ms=processing_time_ms
                    )
                    self._log_audit(audit_result)

                    # 记录风控拒绝指标
                    metrics.increment("risk.rejected", tags={
                        "rule": check_result.rule_code,
                        "symbol": signal.symbol
                    })
                    # 记录审核耗时
                    metrics.record("risk.audit_duration", processing_time_ms, "histogram",
                                   tags={"result": "rejected"})

                    # 如果是严重风险，触发熔断
                    if check_result.level == RiskLevel.CRITICAL:
                        self._trigger_circuit_breaker(check_result.message)

                    return audit_result

            except Exception as e:
                logger.error(f"风控规则执行失败 [{rule.code}]: {e}")
                checks.append(RiskCheckResult(
                    False, rule.code, rule.name,
                    f"规则执行异常: {e}", RiskLevel.CRITICAL
                ))

        # 所有规则通过
        self._stats["approved"] += 1
        processing_time_ms = (time.time() - start_time) * 1000
        audit_result = AuditResult(
            approved=True,
            signal_id=getattr(signal, 'id', None),
            checks=checks,
            processing_time_ms=processing_time_ms
        )
        self._log_audit(audit_result)

        # 记录风控通过指标
        metrics.increment("risk.approved", tags={"symbol": signal.symbol})
        # 记录审核耗时
        metrics.record("risk.audit_duration", processing_time_ms, "histogram",
                       tags={"result": "approved"})

        # 触发审核通过回调（等待完成）
        await self._notify_approval(signal, audit_result)

        return audit_result

    def _log_audit(self, result: AuditResult):
        """记录审核日志"""
        self._audit_log.append(result)

        # 限制日志大小
        if len(self._audit_log) > self._max_log_size:
            self._audit_log = self._audit_log[-self._max_log_size:]

    async def _notify_approval(self, signal: Signal, result: AuditResult):
        """通知审核通过（异步等待所有回调完成）"""
        import inspect
        for callback in self._approval_callbacks:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(signal, result)
                else:
                    callback(signal, result)
            except Exception as e:
                logger.error(f"审批回调执行失败: {e}")

    def on_approval(self, callback: Callable[[Signal, AuditResult], None]):
        """注册审核通过回调（发送到尚书省）"""
        self._approval_callbacks.append(callback)
        logger.info(f"注册审核通过回调: {callback.__name__}")

    def _trigger_circuit_breaker(self, reason: str):
        """触发熔断"""
        self._circuit_breaker_triggered = True
        self._circuit_breaker_reason = reason
        self._circuit_breaker_time = datetime.now()
        self._stats["circuit_breaker_count"] += 1
        logger.critical(f"风控熔断触发: {reason}")

    def reset_circuit_breaker(self):
        """重置熔断"""
        self._circuit_breaker_triggered = False
        self._circuit_breaker_reason = None
        self._circuit_breaker_time = None
        logger.info("风控熔断已重置")

    def is_circuit_breaker_active(self) -> bool:
        """检查是否处于熔断状态"""
        return self._circuit_breaker_triggered

    def get_audit_log(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        approved_only: Optional[bool] = None,
        limit: int = 100
    ) -> List[AuditResult]:
        """获取审核日志"""
        results = self._audit_log

        if start_time:
            results = [r for r in results if r.audit_time >= start_time]
        if end_time:
            results = [r for r in results if r.audit_time <= end_time]
        if approved_only is not None:
            results = [r for r in results if r.approved == approved_only]

        return results[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "circuit_breaker_active": self._circuit_breaker_triggered,
            "circuit_breaker_reason": self._circuit_breaker_reason,
            "rules": [
                {
                    "code": r.code,
                    "name": r.name,
                    "enabled": r.enabled,
                    "stats": r.get_stats()
                }
                for r in self._rules
            ]
        }

    def reset_stats(self):
        """重置统计"""
        self._stats = {
            "total_audits": 0,
            "approved": 0,
            "rejected": 0,
            "circuit_breaker_count": 0,
        }
        for rule in self._rules:
            rule.reset_stats()

    def get_rule_status(self) -> List[Dict[str, Any]]:
        """获取所有规则状态"""
        return [
            {
                "code": r.code,
                "name": r.name,
                "type": r.rule_type.value,
                "level": r.level.value,
                "enabled": r.enabled,
                "stats": r.get_stats()
            }
            for r in self._rules
        ]

    # 兼容旧版API
    async def review_signals(
        self,
        signals: List[Dict[str, Any]],
        portfolio_state: Dict[str, Any]
    ):
        """审核信号列表（兼容旧版API）"""
        passed = []
        rejected = []

        for sig_dict in signals:
            signal = Signal(
                type=SignalType(sig_dict.get("direction", "buy").lower()),
                symbol=sig_dict.get("code", ""),
                timestamp=datetime.now(),
                price=Decimal(str(sig_dict.get("price", 0))),
                volume=sig_dict.get("qty", 0)
            )

            result = await self.audit_signal(signal, portfolio_state)

            if result.approved:
                passed.append(sig_dict)
            else:
                rejected.append({
                    **sig_dict,
                    "reject_reason": result.reject_reason,
                    "reject_rule": result.rejected_by
                })

        return passed, rejected


# 全局门下省实例
menxia_sheng = MenxiaSheng()
