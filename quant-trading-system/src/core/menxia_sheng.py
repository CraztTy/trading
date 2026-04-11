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

logger = TradingLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    CRITICAL = "critical"    # 严重 - 必须拦截
    HIGH = "high"            # 高风险 - 建议拦截
    MEDIUM = "medium"        # 中风险 - 警告但允许
    LOW = "low"              # 低风险 - 记录
    INFO = "info"            # 信息


class RiskRuleType(Enum):
    """风控规则类型"""
    POSITION = "position"        # 仓位相关
    STOP_LOSS = "stop_loss"      # 止损相关
    FREQUENCY = "frequency"      # 频率相关
    AMOUNT = "amount"            # 金额相关
    CIRCUIT_BREAKER = "circuit"  # 熔断相关
    TIME = "time"                # 时间相关


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    rule_code: str
    rule_name: str
    message: str
    level: RiskLevel
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


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


class RiskRule(ABC):
    """风控规则基类"""

    def __init__(
        self,
        code: str,
        name: str,
        rule_type: RiskRuleType,
        level: RiskLevel = RiskLevel.HIGH,
        enabled: bool = True
    ):
        self.code = code
        self.name = name
        self.rule_type = rule_type
        self.level = level
        self.enabled = enabled
        self._check_count = 0
        self._fail_count = 0

    @abstractmethod
    def check(self, signal: Signal, context: Dict[str, Any]) -> RiskCheckResult:
        """执行风控检查"""
        pass

    def get_stats(self) -> Dict[str, int]:
        """获取规则统计"""
        return {
            "total_checks": self._check_count,
            "failures": self._fail_count,
        }

    def reset_stats(self):
        """重置统计"""
        self._check_count = 0
        self._fail_count = 0


class PositionLimitRule(RiskRule):
    """仓位限制规则"""

    def __init__(
        self,
        max_single_position_pct: Decimal = Decimal("0.10"),  # 单票10%
        max_total_position_pct: Decimal = Decimal("0.80"),   # 总仓位80%
    ):
        super().__init__(
            code="R001",
            name="仓位限制",
            rule_type=RiskRuleType.POSITION,
            level=RiskLevel.CRITICAL
        )
        self.max_single_position_pct = max_single_position_pct
        self.max_total_position_pct = max_total_position_pct

    def check(self, signal: Signal, context: Dict[str, Any]) -> RiskCheckResult:
        self._check_count += 1

        if signal.type != SignalType.BUY:
            return RiskCheckResult(True, self.code, self.name, "", RiskLevel.INFO)

        # 获取当前持仓信息
        positions = context.get("positions", {})
        total_value = context.get("total_value", Decimal("0"))

        if total_value <= 0:
            return RiskCheckResult(True, self.code, self.name, "", RiskLevel.INFO)

        symbol = signal.symbol
        price = signal.price or Decimal("0")
        volume = signal.volume or 0

        # 计算新买入金额
        new_amount = price * volume

        # 检查单票仓位
        current_position = positions.get(symbol, {})
        current_value = current_position.get("market_value", Decimal("0"))
        new_single_pct = (current_value + new_amount) / total_value

        if new_single_pct > self.max_single_position_pct:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"单票仓位超限: {new_single_pct:.2%} > {self.max_single_position_pct:.2%}",
                RiskLevel.CRITICAL,
                {"current_pct": float(current_value / total_value), "new_pct": float(new_single_pct)}
            )

        # 检查总仓位
        total_position_value = sum(
            p.get("market_value", Decimal("0")) for p in positions.values()
        )
        new_total_pct = (total_position_value + new_amount) / total_value

        if new_total_pct > self.max_total_position_pct:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"总仓位超限: {new_total_pct:.2%} > {self.max_total_position_pct:.2%}",
                RiskLevel.CRITICAL,
                {"current_pct": float(total_position_value / total_value), "new_pct": float(new_total_pct)}
            )

        return RiskCheckResult(True, self.code, self.name, "仓位检查通过", RiskLevel.INFO)


class StopLossCheckRule(RiskRule):
    """止损设置检查规则"""

    def __init__(
        self,
        max_stop_loss_pct: Decimal = Decimal("0.05"),  # 最大止损5%
        require_stop_loss: bool = True,                  # 是否必须有止损
    ):
        super().__init__(
            code="R002",
            name="止损检查",
            rule_type=RiskRuleType.STOP_LOSS,
            level=RiskLevel.HIGH
        )
        self.max_stop_loss_pct = max_stop_loss_pct
        self.require_stop_loss = require_stop_loss

    def check(self, signal: Signal, context: Dict[str, Any]) -> RiskCheckResult:
        self._check_count += 1

        if signal.type != SignalType.BUY:
            return RiskCheckResult(True, self.code, self.name, "", RiskLevel.INFO)

        stop_loss = context.get("stop_loss")
        price = signal.price

        if stop_loss is None:
            if self.require_stop_loss:
                self._fail_count += 1
                return RiskCheckResult(
                    False, self.code, self.name,
                    "买入信号必须设置止损",
                    RiskLevel.HIGH
                )
            return RiskCheckResult(True, self.code, self.name, "无止损但允许", RiskLevel.LOW)

        # 检查止损比例
        loss_pct = abs(price - stop_loss) / price
        if loss_pct > self.max_stop_loss_pct:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"止损比例过大: {loss_pct:.2%} > {self.max_stop_loss_pct:.2%}",
                RiskLevel.HIGH,
                {"loss_pct": float(loss_pct)}
            )

        return RiskCheckResult(True, self.code, self.name, "止损设置合理", RiskLevel.INFO)


class DailyLossLimitRule(RiskRule):
    """日亏损熔断规则"""

    def __init__(self, max_daily_loss_pct: Decimal = Decimal("0.02")):  # 日亏2%熔断
        super().__init__(
            code="R003",
            name="日亏损熔断",
            rule_type=RiskRuleType.CIRCUIT_BREAKER,
            level=RiskLevel.CRITICAL
        )
        self.max_daily_loss_pct = max_daily_loss_pct
        self._daily_pnl: Dict[str, Decimal] = {}  # date -> pnl

    def check(self, signal: Signal, context: Dict[str, Any]) -> RiskCheckResult:
        self._check_count += 1

        today = datetime.now().date().isoformat()
        daily_pnl = self._daily_pnl.get(today, Decimal("0"))
        total_value = context.get("total_value", Decimal("1"))

        loss_pct = abs(daily_pnl) / total_value if total_value > 0 else Decimal("0")

        if loss_pct > self.max_daily_loss_pct:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"日亏损触发熔断: {loss_pct:.2%} > {self.max_daily_loss_pct:.2%}",
                RiskLevel.CRITICAL,
                {"daily_pnl": float(daily_pnl), "loss_pct": float(loss_pct)}
            )

        return RiskCheckResult(True, self.code, self.name, "日亏损正常", RiskLevel.INFO)

    def update_daily_pnl(self, pnl: Decimal):
        """更新日盈亏"""
        today = datetime.now().date().isoformat()
        self._daily_pnl[today] = self._daily_pnl.get(today, Decimal("0")) + pnl


class OrderFrequencyRule(RiskRule):
    """委托频率限制规则"""

    def __init__(
        self,
        max_orders_per_minute: int = 10,      # 每分钟最大委托数
        max_orders_per_symbol_per_minute: int = 2,  # 每票每分钟最大委托数
    ):
        super().__init__(
            code="R004",
            name="委托频率限制",
            rule_type=RiskRuleType.FREQUENCY,
            level=RiskLevel.MEDIUM
        )
        self.max_orders_per_minute = max_orders_per_minute
        self.max_orders_per_symbol_per_minute = max_orders_per_symbol_per_minute
        self._order_history: List[Dict[str, Any]] = []

    def check(self, signal: Signal, context: Dict[str, Any]) -> RiskCheckResult:
        self._check_count += 1

        now = time.time()
        one_minute_ago = now - 60

        # 清理1分钟前的记录
        self._order_history = [
            h for h in self._order_history
            if h["timestamp"] > one_minute_ago
        ]

        # 检查总频率
        if len(self._order_history) >= self.max_orders_per_minute:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"委托频率超限: {len(self._order_history)}/{self.max_orders_per_minute} 每分钟",
                RiskLevel.MEDIUM
            )

        # 检查单票频率
        symbol_orders = [
            h for h in self._order_history
            if h.get("symbol") == signal.symbol
        ]
        if len(symbol_orders) >= self.max_orders_per_symbol_per_minute:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"单票委托频率超限: {len(symbol_orders)}/{self.max_orders_per_symbol_per_minute} 每分钟",
                RiskLevel.MEDIUM
            )

        # 记录本次委托
        self._order_history.append({
            "timestamp": now,
            "symbol": signal.symbol,
            "type": signal.type.value
        })

        return RiskCheckResult(True, self.code, self.name, "频率检查通过", RiskLevel.INFO)


class ConsecutiveLossRule(RiskRule):
    """连续亏损限制规则"""

    def __init__(self, max_consecutive_losses: int = 3):
        super().__init__(
            code="R005",
            name="连续亏损限制",
            rule_type=RiskRuleType.CIRCUIT_BREAKER,
            level=RiskLevel.HIGH
        )
        self.max_consecutive_losses = max_consecutive_losses
        self._consecutive_losses = 0
        self._last_trade_pnl: Optional[Decimal] = None

    def check(self, signal: Signal, context: Dict[str, Any]) -> RiskCheckResult:
        self._check_count += 1

        if self._consecutive_losses >= self.max_consecutive_losses:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"连续亏损{self._consecutive_losses}次，暂停开仓",
                RiskLevel.HIGH,
                {"consecutive_losses": self._consecutive_losses}
            )

        return RiskCheckResult(
            True, self.code, self.name,
            f"连续亏损检查通过 ({self._consecutive_losses}/{self.max_consecutive_losses})",
            RiskLevel.INFO
        )

    def on_trade_result(self, pnl: Decimal):
        """交易结果回调"""
        if pnl < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0
        self._last_trade_pnl = pnl


class MenxiaSheng:
    """
    门下省 - 风控审核中心（单例）

    职责：
    - 审核所有交易信号
    - 执行风控规则链
    - 记录审核日志
    - 触发熔断机制
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
                    audit_result = AuditResult(
                        approved=False,
                        signal_id=getattr(signal, 'id', None),
                        checks=checks,
                        rejected_by=check_result.rule_code,
                        reject_reason=check_result.message,
                        processing_time_ms=(time.time() - start_time) * 1000
                    )
                    self._log_audit(audit_result)

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
        audit_result = AuditResult(
            approved=True,
            signal_id=getattr(signal, 'id', None),
            checks=checks,
            processing_time_ms=(time.time() - start_time) * 1000
        )
        self._log_audit(audit_result)

        # 触发审核通过回调
        self._notify_approval(signal, audit_result)

        return audit_result

    def _log_audit(self, result: AuditResult):
        """记录审核日志"""
        self._audit_log.append(result)

        # 限制日志大小
        if len(self._audit_log) > self._max_log_size:
            self._audit_log = self._audit_log[-self._max_log_size:]

    def _notify_approval(self, signal: Signal, result: AuditResult):
        """通知审核通过"""
        for callback in self._approval_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(signal, result))
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
