"""
风控系统集成测试 (Risk Management Integration Tests)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from decimal import Decimal
from src.risk.risk_manager import RiskManager, RiskConfig, TradeSignal
from src.risk.rules import (
    RiskRuleRegistry, PositionLimitRule, StopLossCheckRule,
    DailyLossLimitRule, OrderFrequencyRule, ConsecutiveLossRule,
    PriceLimitRule, BlacklistRule, RiskLevel, RiskRuleType
)
from src.risk.position_manager import PositionManager, PositionLimit, PositionLimitType
from src.risk.stop_loss import StopLossManager, StopLossType, TakeProfitType
from src.strategy.base import Signal, SignalType


class TestRiskManagement:
    """风控系统测试"""

    def test_risk_manager_init(self):
        """测试风控管理器初始化"""
        print("\n[TEST] Risk Manager Initialization...")

        config = RiskConfig(
            max_single_stock=Decimal("0.15"),
            max_total_position=Decimal("0.75"),
            default_stop_loss_pct=Decimal("0.05"),
            default_take_profit_pct=Decimal("0.10")
        )

        manager = RiskManager(config)

        assert manager.position_manager is not None
        assert manager.stop_loss_manager is not None
        assert manager.config.max_single_stock == Decimal("0.15")

        print("   [OK] Risk manager initialized")

    def test_position_limit_rule(self):
        """测试仓位限制规则"""
        print("\n[TEST] Position Limit Rule...")

        rule = PositionLimitRule(
            max_single_position_pct=Decimal("0.10"),
            max_total_position_pct=Decimal("0.80")
        )

        # 模拟买入信号
        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=None,
            price=Decimal("10"),
            volume=100
        )

        # 测试通过场景
        context = {
            "positions": {},
            "total_value": Decimal("1000000")
        }
        result = rule.check(signal, context)

        assert result.passed is True
        print(f"   Pass result: {result.message}")

        # 测试超限场景
        context["positions"] = {
            "000001.SZ": {"market_value": Decimal("120000")}
        }
        result = rule.check(signal, context)

        assert result.passed is False
        assert result.level == RiskLevel.CRITICAL
        print(f"   Limit exceeded: {result.message}")

        print("   [OK] Position limit rule working")

    def test_stop_loss_rule(self):
        """测试止损设置规则"""
        print("\n[TEST] Stop Loss Check Rule...")

        rule = StopLossCheckRule(
            max_stop_loss_pct=Decimal("0.05"),
            require_stop_loss=True
        )

        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=None,
            price=Decimal("10")
        )

        # 测试无止损（必须设置）
        context = {"stop_loss": None}
        result = rule.check(signal, context)
        assert result.passed is False
        print(f"   No stop loss check: {result.message}")

        # 测试止损比例过大
        context["stop_loss"] = Decimal("8")  # 20% loss
        result = rule.check(signal, context)
        assert result.passed is False
        print(f"   Large stop loss check: {result.message}")

        # 测试正常止损
        context["stop_loss"] = Decimal("9.5")  # 5% loss
        result = rule.check(signal, context)
        assert result.passed is True
        print(f"   Normal stop loss: {result.message}")

        print("   [OK] Stop loss rule working")

    def test_price_limit_rule(self):
        """测试涨跌停价格限制规则"""
        print("\n[TEST] Price Limit Rule...")

        rule = PriceLimitRule(
            default_limit_pct=Decimal("0.10"),
            st_limit_pct=Decimal("0.05"),
            chi_next_limit_pct=Decimal("0.20")
        )

        # 测试涨停买入
        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=None,
            price=Decimal("11"),  # 涨停价
            volume=100
        )
        context = {
            "reference_price": Decimal("10"),
            "symbol_types": {"000001.SZ": "主板"}
        }
        result = rule.check(signal, context)
        assert result.passed is False
        print(f"   Upper limit check: {result.message}")

        # 测试跌停买入
        signal.price = Decimal("9")  # 跌停价
        result = rule.check(signal, context)
        assert result.passed is False
        print(f"   Lower limit check: {result.message}")

        # 测试正常价格
        signal.price = Decimal("10.5")
        result = rule.check(signal, context)
        assert result.passed is True
        print(f"   Normal price: {result.message}")

        # 测试创业板20%限制
        signal.symbol = "300001.SZ"
        signal.price = Decimal("15")  # 50%涨幅
        context["symbol_types"]["300001.SZ"] = "创业板"
        result = rule.check(signal, context)
        assert result.passed is False
        print(f   ChiNext limit check: {result.message}")

        print("   [OK] Price limit rule working")

    def test_blacklist_rule(self):
        """测试黑名单规则"""
        print("\n[TEST] Blacklist Rule...")

        rule = BlacklistRule(
            blacklisted_symbols=["000001.SZ", "600000.SH"],
            blacklist_reasons={"000001.SZ": "ST股票"}
        )

        # 测试黑名单股票
        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=None
        )
        result = rule.check(signal, {})
        assert result.passed is False
        assert result.level == RiskLevel.CRITICAL
        print(f"   Blacklist check: {result.message}")

        # 测试正常股票
        signal.symbol = "000002.SZ"
        result = rule.check(signal, {})
        assert result.passed is True
        print(f"   Normal stock: {result.message}")

        # 测试动态添加黑名单
        rule.add_to_blacklist("000002.SZ", "临时停牌")
        result = rule.check(signal, {})
        assert result.passed is False
        print(f"   Dynamic blacklist: {result.message}")

        print("   [OK] Blacklist rule working")

    def test_daily_loss_limit_rule(self):
        """测试日亏损熔断规则"""
        print("\n[TEST] Daily Loss Limit Rule...")

        rule = DailyLossLimitRule(max_daily_loss_pct=Decimal("0.02"))

        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=None
        )

        # 测试正常状态
        context = {"total_value": Decimal("1000000")}
        result = rule.check(signal, context)
        assert result.passed is True
        print(f"   Normal state: {result.message}")

        # 模拟日亏损
        rule.update_daily_pnl(Decimal("-30000"))  # -3%
        result = rule.check(signal, context)
        assert result.passed is False
        assert result.level == RiskLevel.CRITICAL
        print(f"   Circuit breaker: {result.message}")

        print("   [OK] Daily loss limit rule working")

    def test_order_frequency_rule(self):
        """测试委托频率限制规则"""
        print("\n[TEST] Order Frequency Rule...")

        rule = OrderFrequencyRule(
            max_orders_per_minute=3,
            max_orders_per_symbol_per_minute=2
        )

        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=None
        )

        # 前3次应该通过
        for i in range(3):
            result = rule.check(signal, {})
            assert result.passed is True
            print(f"   Order {i+1}: passed")

        # 第4次应该被限制
        result = rule.check(signal, {})
        assert result.passed is False
        print(f"   Order 4: blocked - {result.message}")

        # 重置后应该恢复
        rule.reset_history()
        result = rule.check(signal, {})
        assert result.passed is True
        print(f"   After reset: passed")

        print("   [OK] Order frequency rule working")

    def test_consecutive_loss_rule(self):
        """测试连续亏损限制规则"""
        print("\n[TEST] Consecutive Loss Rule...")

        rule = ConsecutiveLossRule(max_consecutive_losses=3)

        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=None
        )

        # 初始状态应该通过
        result = rule.check(signal, {})
        assert result.passed is True
        print(f"   Initial state: passed")

        # 模拟连续亏损
        for i in range(3):
            rule.on_trade_result(Decimal("-1000"))
            result = rule.check(signal, {})
            if i < 2:
                assert result.passed is True
                print(f"   Loss {i+1}: passed")

        # 第3次亏损后应该被限制
        assert result.passed is False
        print(f"   After 3 losses: blocked - {result.message}")

        # 盈利后应该恢复
        rule.on_trade_result(Decimal("1000"))
        result = rule.check(signal, {})
        assert result.passed is True
        print(f"   After profit: passed")

        print("   [OK] Consecutive loss rule working")

    def test_stop_loss_manager(self):
        """测试止损管理器"""
        print("\n[TEST] Stop Loss Manager...")

        manager = StopLossManager(check_interval=0.1)

        # 添加固定止损
        order_id = manager.add_stop_loss(
            symbol="000001.SZ",
            position_qty=100,
            entry_price=Decimal("10"),
            stop_type=StopLossType.FIXED,
            stop_price=Decimal("9")
        )
        print(f"   Fixed stop loss added: {order_id}")

        # 添加比例止损
        order_id2 = manager.add_stop_loss(
            symbol="000002.SZ",
            position_qty=100,
            entry_price=Decimal("20"),
            stop_type=StopLossType.PERCENTAGE,
            stop_pct=Decimal("0.05")
        )
        print(f"   Percentage stop loss added: {order_id2}")

        # 测试价格更新和触发
        triggered = []

        def on_stop_loss(result):
            if result.should_stop:
                triggered.append(result.symbol)

        manager.on_stop_loss(on_stop_loss)

        # 价格跌破止损
        manager.update_price("000001.SZ", Decimal("8.5"))
        result = manager._check_stop_loss(
            manager.get_stop_loss("000001.SZ"),
            Decimal("8.5")
        )
        assert result.should_stop is True
        print(f"   Stop loss triggered: {result.reason}")

        # 清理
        manager.remove_stop_loss("000001.SZ")
        manager.remove_stop_loss("000002.SZ")

        print("   [OK] Stop loss manager working")

    def test_position_manager(self):
        """测试仓位管理器"""
        print("\n[TEST] Position Manager...")

        manager = PositionManager(initial_capital=Decimal("1000000"))
        manager.set_default_limits(
            max_single_stock=Decimal("0.10"),
            max_total=Decimal("0.80")
        )

        # 添加持仓
        manager.update_position(
            symbol="000001.SZ",
            quantity=100,
            avg_cost=Decimal("10"),
            market_price=Decimal("12")
        )

        pos = manager.get_position("000001.SZ")
        assert pos is not None
        assert pos.quantity == 100
        assert pos.weight == Decimal("0.0012")  # 1200/1000000
        print(f"   Position added: {pos.symbol}, weight={pos.weight:.4%}")

        # 检查加仓限制
        can_open, reason = manager.can_open_position(
            "000001.SZ", 10000, Decimal("12")
        )
        assert can_open is False  # 会超限
        print(f   Large position check: {reason}")

        # 正常加仓
        can_open, reason = manager.can_open_position(
            "000002.SZ", 100, Decimal("10")
        )
        assert can_open is True
        print(f"   Normal position: allowed")

        # 获取报告
        report = manager.get_position_report()
        assert report["summary"]["position_count"] == 1
        print(f"   Position report: {report['summary']['position_count']} positions")

        print("   [OK] Position manager working")

    def test_risk_rule_registry(self):
        """测试规则注册表"""
        print("\n[TEST] Risk Rule Registry...")

        registry = RiskRuleRegistry()

        # 创建所有规则
        rules_to_create = [
            ("position_limit", {"max_single_position_pct": Decimal("0.10")}),
            ("stop_loss_check", {}),
            ("daily_loss_limit", {}),
            ("order_frequency", {}),
            ("consecutive_loss", {}),
            ("price_limit", {}),
            ("blacklist", {}),
        ]

        for name, kwargs in rules_to_create:
            rule = registry.create_rule(name, **kwargs)
            assert rule is not None, f"Failed to create {name}"
            print(f"   Rule created: {name}")

        # 获取所有规则
        all_rules = registry.get_all_rules()
        assert len(all_rules) == len(rules_to_create)
        print(f"   Total rules: {len(all_rules)}")

        # 禁用规则
        rule = registry.get_rule("R001")
        rule.enabled = False
        assert registry.get_rule("R001").enabled is False
        print("   Rule toggle: OK")

        print("   [OK] Rule registry working")


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Risk Management Integration Tests")
    print("=" * 60)

    tests = TestRiskManagement()

    tests.test_risk_manager_init()
    tests.test_position_limit_rule()
    tests.test_stop_loss_rule()
    tests.test_price_limit_rule()
    tests.test_blacklist_rule()
    tests.test_daily_loss_limit_rule()
    tests.test_order_frequency_rule()
    tests.test_consecutive_loss_rule()
    tests.test_stop_loss_manager()
    tests.test_position_manager()
    tests.test_risk_rule_registry()

    print("\n" + "=" * 60)
    print("All risk management tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
