"""
风控规则模块

包含所有风控规则实现：
- PositionLimitRule: 仓位限制规则
- StopLossCheckRule: 止损设置检查规则
- DailyLossLimitRule: 日亏损熔断规则
- OrderFrequencyRule: 委托频率限制规则
- ConsecutiveLossRule: 连续亏损熔断规则
- PriceLimitRule: 涨跌停价格限制规则
- BlacklistRule: 黑名单规则
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
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
    COMPLIANCE = "compliance"    # 合规相关
    PRICE = "price"              # 价格相关


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

    def update_config(self, **kwargs) -> None:
        """动态更新规则配置"""
        for key, value in kwargs.items():
            if hasattr(self, key) and not key.startswith('_'):
                setattr(self, key, value)
                logger.info(f"规则 {self.code} 配置更新: {key} = {value}")
            else:
                logger.warning(f"规则 {self.code} 不存在配置项: {key}")


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

    def reset_history(self):
        """重置历史记录"""
        self._order_history.clear()


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

    def reset_loss_count(self):
        """重置连续亏损计数"""
        self._consecutive_losses = 0


class PriceLimitRule(RiskRule):
    """涨跌停价格限制规则

    检查委托价格是否超出涨跌停限制，防止在极端行情下以不合理价格成交。
    支持A股市场的10%、20%涨跌幅限制，以及ST股票的5%限制。
    """

    def __init__(
        self,
        default_limit_pct: Decimal = Decimal("0.10"),  # 默认涨跌幅10%
        st_limit_pct: Decimal = Decimal("0.05"),       # ST股票涨跌幅5%
        chi_next_limit_pct: Decimal = Decimal("0.20"), # 创业板/科创板20%
    ):
        super().__init__(
            code="R006",
            name="涨跌停价格限制",
            rule_type=RiskRuleType.PRICE,
            level=RiskLevel.CRITICAL
        )
        self.default_limit_pct = default_limit_pct
        self.st_limit_pct = st_limit_pct
        self.chi_next_limit_pct = chi_next_limit_pct
        self._symbol_limits: Dict[str, Decimal] = {}  # 自定义股票涨跌幅

    def check(self, signal: Signal, context: Dict[str, Any]) -> RiskCheckResult:
        self._check_count += 1

        price = signal.price
        if price is None:
            return RiskCheckResult(True, self.code, self.name, "市价单跳过价格检查", RiskLevel.INFO)

        # 获取参考价格（昨收价或最新价）
        reference_price = context.get("reference_price") or context.get("last_close")
        if reference_price is None or reference_price <= 0:
            # 无法获取参考价格，跳过检查但记录警告
            return RiskCheckResult(
                True, self.code, self.name,
                "无法获取参考价格，跳过涨跌停检查",
                RiskLevel.LOW
            )

        # 获取该股票的涨跌幅限制
        limit_pct = self._get_limit_pct(signal.symbol, context)

        # 计算涨跌停价格
        upper_limit = reference_price * (Decimal("1") + limit_pct)
        lower_limit = reference_price * (Decimal("1") - limit_pct)

        # 检查价格是否在限制范围内
        if price > upper_limit:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"委托价格{price}超过涨停价{upper_limit:.2f}",
                RiskLevel.CRITICAL,
                {
                    "price": float(price),
                    "upper_limit": float(upper_limit),
                    "lower_limit": float(lower_limit),
                    "reference_price": float(reference_price),
                    "limit_pct": float(limit_pct)
                }
            )

        if price < lower_limit:
            self._fail_count += 1
            return RiskCheckResult(
                False, self.code, self.name,
                f"委托价格{price}低于跌停价{lower_limit:.2f}",
                RiskLevel.CRITICAL,
                {
                    "price": float(price),
                    "upper_limit": float(upper_limit),
                    "lower_limit": float(lower_limit),
                    "reference_price": float(reference_price),
                    "limit_pct": float(limit_pct)
                }
            )

        return RiskCheckResult(
            True, self.code, self.name,
            f"价格在合理范围内 [{lower_limit:.2f}, {upper_limit:.2f}]",
            RiskLevel.INFO
        )

    def _get_limit_pct(self, symbol: str, context: Dict[str, Any]) -> Decimal:
        """获取股票的涨跌幅限制"""
        # 优先使用自定义设置
        if symbol in self._symbol_limits:
            return self._symbol_limits[symbol]

        # 从上下文中获取股票类型
        symbol_type = context.get("symbol_types", {}).get(symbol)

        if symbol_type == "ST":
            return self.st_limit_pct
        elif symbol_type in ("创业板", "科创板", "chi_next", "kcb"):
            return self.chi_next_limit_pct

        # 默认使用10%限制
        return self.default_limit_pct

    def set_symbol_limit(self, symbol: str, limit_pct: Decimal):
        """为特定股票设置涨跌幅限制"""
        self._symbol_limits[symbol] = limit_pct
        logger.info(f"设置股票 {symbol} 涨跌幅限制: {limit_pct:.2%}")

    def remove_symbol_limit(self, symbol: str):
        """移除股票的自定义涨跌幅限制"""
        if symbol in self._symbol_limits:
            del self._symbol_limits[symbol]
            logger.info(f"移除股票 {symbol} 自定义涨跌幅限制")


class BlacklistRule(RiskRule):
    """黑名单规则

    禁止交易黑名单中的标的，用于：
    - 合规要求（如禁止交易某些股票）
    - 风险控制（如暂停交易异常波动股票）
    - 策略需要（如排除特定行业或个股）
    """

    def __init__(
        self,
        blacklisted_symbols: Optional[List[str]] = None,
        blacklist_reasons: Optional[Dict[str, str]] = None
    ):
        super().__init__(
            code="R007",
            name="黑名单",
            rule_type=RiskRuleType.COMPLIANCE,
            level=RiskLevel.CRITICAL
        )
        self.blacklist: Set[str] = set(blacklisted_symbols or [])
        self.blacklist_reasons: Dict[str, str] = blacklist_reasons or {}

    def check(self, signal: Signal, context: Dict[str, Any]) -> RiskCheckResult:
        self._check_count += 1

        symbol = signal.symbol

        if symbol in self.blacklist:
            self._fail_count += 1
            reason = self.blacklist_reasons.get(symbol, "该标的已被列入黑名单")
            return RiskCheckResult(
                False, self.code, self.name,
                f"黑名单限制: {reason}",
                RiskLevel.CRITICAL,
                {"symbol": symbol, "reason": reason}
            )

        return RiskCheckResult(True, self.code, self.name, "不在黑名单中", RiskLevel.INFO)

    def add_to_blacklist(self, symbol: str, reason: str = ""):
        """添加标的到黑名单"""
        self.blacklist.add(symbol)
        if reason:
            self.blacklist_reasons[symbol] = reason
        logger.info(f"添加 {symbol} 到黑名单: {reason or '无原因'}")

    def remove_from_blacklist(self, symbol: str):
        """从黑名单移除标的"""
        self.blacklist.discard(symbol)
        self.blacklist_reasons.pop(symbol, None)
        logger.info(f"从黑名单移除 {symbol}")

    def is_blacklisted(self, symbol: str) -> bool:
        """检查标的是否在黑名单中"""
        return symbol in self.blacklist

    def get_blacklist(self) -> List[str]:
        """获取黑名单列表"""
        return list(self.blacklist)

    def clear_blacklist(self):
        """清空黑名单"""
        self.blacklist.clear()
        self.blacklist_reasons.clear()
        logger.info("清空黑名单")


class RiskRuleRegistry:
    """风控规则注册表

    用于动态管理和配置风控规则。
    """

    def __init__(self):
        self._rules: Dict[str, RiskRule] = {}
        self._rule_classes: Dict[str, type] = {
            "position_limit": PositionLimitRule,
            "stop_loss_check": StopLossCheckRule,
            "daily_loss_limit": DailyLossLimitRule,
            "order_frequency": OrderFrequencyRule,
            "consecutive_loss": ConsecutiveLossRule,
            "price_limit": PriceLimitRule,
            "blacklist": BlacklistRule,
        }

    def register_rule_class(self, name: str, rule_class: type):
        """注册新的规则类"""
        self._rule_classes[name] = rule_class

    def create_rule(self, name: str, **kwargs) -> Optional[RiskRule]:
        """创建规则实例"""
        if name not in self._rule_classes:
            logger.error(f"未知的规则类型: {name}")
            return None

        try:
            rule = self._rule_classes[name](**kwargs)
            self._rules[rule.code] = rule
            return rule
        except Exception as e:
            logger.error(f"创建规则 {name} 失败: {e}")
            return None

    def get_rule(self, code: str) -> Optional[RiskRule]:
        """获取规则实例"""
        return self._rules.get(code)

    def get_all_rules(self) -> List[RiskRule]:
        """获取所有规则"""
        return list(self._rules.values())

    def remove_rule(self, code: str):
        """移除规则"""
        if code in self._rules:
            del self._rules[code]

    def clear(self):
        """清空所有规则"""
        self._rules.clear()


# 全局规则注册表实例
rule_registry = RiskRuleRegistry()
