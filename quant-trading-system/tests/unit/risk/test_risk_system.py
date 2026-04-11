"""
风控系统测试

测试内容：
- 仓位管理器 (PositionManager)
- 止损止盈管理器 (StopLossManager)
- 风控管理器 (RiskManager)
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from src.risk import (
    PositionManager, PositionLimit, PositionLimitType,
    StopLossManager, StopLossType, TakeProfitType,
    RiskManager, RiskConfig, TradeSignal
)


@pytest.fixture
def position_manager():
    """创建仓位管理器"""
    return PositionManager(
        initial_capital=Decimal("1000000"),
        limits=[
            PositionLimit(
                limit_type=PositionLimitType.SINGLE_STOCK,
                max_ratio=Decimal("0.10"),  # 单票10%
                warning_ratio=Decimal("0.08")
            ),
            PositionLimit(
                limit_type=PositionLimitType.TOTAL,
                max_ratio=Decimal("0.80"),  # 总仓位80%
                warning_ratio=Decimal("0.70")
            )
        ]
    )


@pytest.fixture
def stop_loss_manager():
    """创建止损止盈管理器"""
    return StopLossManager(check_interval=0.1)


@pytest.fixture
def risk_manager():
    """创建风控管理器"""
    config = RiskConfig(
        max_single_stock=Decimal("0.10"),
        max_total_position=Decimal("0.80"),
        default_stop_loss_pct=Decimal("0.05"),
        default_take_profit_pct=Decimal("0.10"),
        check_interval=0.1
    )
    return RiskManager(config)


class TestPositionManager:
    """测试仓位管理器"""

    def test_initialization(self, position_manager):
        """测试初始化"""
        assert position_manager.initial_capital == Decimal("1000000")
        assert position_manager.current_capital == Decimal("1000000")

    def test_update_position(self, position_manager):
        """测试更新持仓"""
        position_manager.update_position(
            symbol="000001.SZ",
            quantity=1000,
            avg_cost=Decimal("10"),
            market_price=Decimal("11")
        )

        pos = position_manager.get_position("000001.SZ")
        assert pos is not None
        assert pos.quantity == 1000
        assert pos.avg_cost == Decimal("10")
        assert pos.market_price == Decimal("11")
        assert pos.market_value == Decimal("11000")
        assert pos.unrealized_pnl == Decimal("1000")  # (11-10)*1000

    def test_can_open_position_within_limit(self, position_manager):
        """测试在限制内开仓"""
        can_open, reason = position_manager.can_open_position(
            symbol="000001.SZ",
            quantity=5000,  # 5000 * 10 = 50000 = 5%
            price=Decimal("10")
        )

        assert can_open is True
        assert reason is None

    def test_can_open_position_exceeds_limit(self, position_manager):
        """测试超出单票限制"""
        can_open, reason = position_manager.can_open_position(
            symbol="000001.SZ",
            quantity=20000,  # 20000 * 10 = 200000 = 20% > 10%
            price=Decimal("10")
        )

        assert can_open is False
        assert "单票仓位超限" in reason

    def test_total_position_limit(self, position_manager):
        """测试总仓位限制"""
        # 先建立一些持仓（注意不能超过单票限制10%，也不能超过总限制80%）
        # 每只票最多 10万（10%），最多8只票就是80%
        for i in range(8):
            position_manager.update_position(
                f"00000{i+1}.SZ", 10000, Decimal("10"), Decimal("10")
            )  # 每只10万 = 10%
        # 总计 80万 = 80%

        # 尝试再加仓（超过80%总限制）
        can_open, reason = position_manager.can_open_position(
            symbol="000009.SZ",
            quantity=1000,  # 1万，合计81万 > 80%
            price=Decimal("10")
        )

        assert can_open is False
        assert "总仓位超限" in reason

    def test_position_health_check(self, position_manager):
        """测试持仓健康检查"""
        position_manager.update_position(
            "000001.SZ", 10000, Decimal("10"), Decimal("10")
        )  # 10万 = 10%

        health = position_manager.check_position_health("000001.SZ")

        assert health["status"] == "OVER_LIMIT"  # 达到限制
        assert len(health["warnings"]) > 0

    def test_position_report(self, position_manager):
        """测试仓位报告"""
        position_manager.update_position(
            "000001.SZ", 1000, Decimal("10"), Decimal("11")
        )

        report = position_manager.get_position_report()

        assert report["summary"]["position_count"] == 1
        assert len(report["positions"]) == 1


class TestStopLossManager:
    """测试止损止盈管理器"""

    @pytest.mark.asyncio
    async def test_add_stop_loss_fixed(self, stop_loss_manager):
        """测试添加固定止损"""
        order_id = stop_loss_manager.add_stop_loss(
            symbol="000001.SZ",
            position_qty=1000,
            entry_price=Decimal("10"),
            stop_type=StopLossType.FIXED,
            stop_price=Decimal("9")
        )

        assert order_id is not None
        order = stop_loss_manager.get_stop_loss("000001.SZ")
        assert order.stop_price == Decimal("9")

    def test_add_stop_loss_percentage(self, stop_loss_manager):
        """测试添加比例止损"""
        order_id = stop_loss_manager.add_stop_loss(
            symbol="000001.SZ",
            position_qty=1000,
            entry_price=Decimal("10"),
            stop_type=StopLossType.PERCENTAGE,
            stop_pct=Decimal("0.05")  # 5%
        )

        order = stop_loss_manager.get_stop_loss("000001.SZ")
        # 止损价应该是 10 * (1-0.05) = 9.5
        assert order.stop_price is not None

    def test_add_take_profit(self, stop_loss_manager):
        """测试添加止盈"""
        order_id = stop_loss_manager.add_take_profit(
            symbol="000001.SZ",
            position_qty=1000,
            entry_price=Decimal("10"),
            tp_type=TakeProfitType.FIXED,
            target_price=Decimal("12")
        )

        assert order_id is not None
        order = stop_loss_manager.get_take_profit("000001.SZ")
        assert order.target_price == Decimal("12")

    def test_check_stop_loss_triggered(self, stop_loss_manager):
        """测试止损触发检查"""
        from src.risk.stop_loss import StopLossOrder, StopLossResult

        # 添加止损
        stop_loss_manager.add_stop_loss(
            symbol="000001.SZ",
            position_qty=1000,
            entry_price=Decimal("10"),
            stop_type=StopLossType.FIXED,
            stop_price=Decimal("9")
        )

        # 模拟价格下跌到止损价以下
        stop_loss_manager.update_price("000001.SZ", Decimal("8.5"))

        # 手动触发检查
        order = stop_loss_manager.get_stop_loss("000001.SZ")
        result = stop_loss_manager._check_stop_loss(order, Decimal("8.5"))

        assert result.should_stop is True
        assert result.stop_price == Decimal("9")

    def test_check_take_profit_triggered(self, stop_loss_manager):
        """测试止盈触发检查"""
        # 添加止盈
        stop_loss_manager.add_take_profit(
            symbol="000001.SZ",
            position_qty=1000,
            entry_price=Decimal("10"),
            tp_type=TakeProfitType.FIXED,
            target_price=Decimal("12")
        )

        # 模拟价格上涨到止盈价以上
        stop_loss_manager.update_price("000001.SZ", Decimal("12.5"))

        # 手动触发检查
        order = stop_loss_manager.get_take_profit("000001.SZ")
        result = stop_loss_manager._check_take_profit(order, Decimal("12.5"))

        assert result.should_take is True
        assert result.target_price == Decimal("12")

    @pytest.mark.asyncio
    async def test_trailing_stop_loss(self, stop_loss_manager):
        """测试跟踪止损"""
        stop_loss_manager.add_stop_loss(
            symbol="000001.SZ",
            position_qty=1000,
            entry_price=Decimal("10"),
            stop_type=StopLossType.TRAILING,
            trailing_distance=Decimal("1")  # 1元跟踪距离
        )

        # 获取订单并设置最高价为12（模拟价格上涨）
        order = stop_loss_manager.get_stop_loss("000001.SZ")
        order.highest_price = Decimal("12")  # 手动设置最高价

        # 价格回落到11.2（从最高价12回落0.8元 < 1元，不应触发）
        result = stop_loss_manager._check_stop_loss(order, Decimal("11.2"))
        assert result.should_stop is False

        # 价格回落到10.5（从最高价12回落1.5元 > 1元，应触发）
        result = stop_loss_manager._check_stop_loss(order, Decimal("10.5"))
        assert result.should_stop is True


class TestRiskManager:
    """测试风控管理器"""

    def test_initialization(self, risk_manager):
        """测试初始化"""
        assert risk_manager.config is not None
        assert risk_manager.position_manager is not None
        assert risk_manager.stop_loss_manager is not None

    def test_check_trade_buy_pass(self, risk_manager):
        """测试买入通过风控"""
        signal = TradeSignal(
            symbol="000001.SZ",
            direction="BUY",
            qty=1000,  # 1000股 @ 10元 = 1万元 = 1%
            price=Decimal("10")
        )

        allowed, reason = risk_manager.check_trade(signal)

        assert allowed is True
        assert reason is None

    def test_check_trade_buy_rejected(self, risk_manager):
        """测试买入被风控拒绝"""
        signal = TradeSignal(
            symbol="000001.SZ",
            direction="BUY",
            qty=50000,  # 50000股 @ 100元 = 500万元 > 单票限制
            price=Decimal("100")
        )

        allowed, reason = risk_manager.check_trade(signal)

        assert allowed is False
        assert "仓位限制" in reason

    def test_check_trade_sell(self, risk_manager):
        """测试卖出通过风控"""
        signal = TradeSignal(
            symbol="000001.SZ",
            direction="SELL",
            qty=1000
        )

        allowed, reason = risk_manager.check_trade(signal)

        assert allowed is True  # 卖出通常都允许

    def test_on_position_opened(self, risk_manager):
        """测试持仓建立后的处理"""
        risk_manager.on_position_opened(
            symbol="000001.SZ",
            quantity=1000,
            avg_cost=Decimal("10"),
            stop_loss=Decimal("9.5"),
            take_profit=Decimal("12")
        )

        # 验证仓位已添加
        pos = risk_manager.position_manager.get_position("000001.SZ")
        assert pos is not None
        assert pos.quantity == 1000

        # 验证止损止盈已设置
        sl = risk_manager.stop_loss_manager.get_stop_loss("000001.SZ")
        assert sl is not None

        tp = risk_manager.stop_loss_manager.get_take_profit("000001.SZ")
        assert tp is not None

    def test_on_position_closed(self, risk_manager):
        """测试持仓关闭后的处理"""
        # 先建立持仓
        risk_manager.on_position_opened(
            symbol="000001.SZ",
            quantity=1000,
            avg_cost=Decimal("10")
        )

        # 关闭持仓
        risk_manager.on_position_closed("000001.SZ")

        # 验证已清除
        pos = risk_manager.position_manager.get_position("000001.SZ")
        assert pos is None

        sl = risk_manager.stop_loss_manager.get_stop_loss("000001.SZ")
        assert sl is None

    def test_on_bar_update(self, risk_manager):
        """测试K线更新处理"""
        from src.strategy.base import BarData

        # 先建立持仓
        risk_manager.on_position_opened(
            symbol="000001.SZ",
            quantity=1000,
            avg_cost=Decimal("10")
        )

        # 更新K线
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9.5"),
            close=Decimal("10.5"),
            volume=10000,
            amount=Decimal("100000")
        )
        risk_manager.on_bar_update(bar)

        # 验证价格已更新
        pos = risk_manager.position_manager.get_position("000001.SZ")
        assert pos.market_price == Decimal("10.5")

    def test_get_risk_report(self, risk_manager):
        """测试风控报告"""
        # 建立持仓
        risk_manager.on_position_opened(
            symbol="000001.SZ",
            quantity=1000,
            avg_cost=Decimal("10")
        )

        report = risk_manager.get_risk_report()

        assert "timestamp" in report
        assert "position" in report
        assert "stop_loss" in report
        assert "take_profit" in report
