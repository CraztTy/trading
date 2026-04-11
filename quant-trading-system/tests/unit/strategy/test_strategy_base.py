"""
策略基类与框架测试

测试内容：
- StrategyContext 数据接口
- StrategyBase 生命周期
- StrategyManager 管理功能
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from src.strategy.base import (
    StrategyBase, StrategyContext, BarData, TickData,
    Signal, SignalType, StrategyState, Position, AccountInfo
)
from src.strategy.manager import StrategyManager


class MockStrategy(StrategyBase):
    """测试用的模拟策略"""

    def __init__(self, strategy_id, name, symbols, params=None):
        super().__init__(strategy_id, name, symbols, params)
        self.init_called = False
        self.bar_count = 0
        self.tick_count = 0
        self.last_bar = None
        self.last_tick = None

    def on_init(self, context):
        self.init_called = True

    def on_bar(self, bar):
        self.bar_count += 1
        self.last_bar = bar

    def on_tick(self, tick):
        self.tick_count += 1
        self.last_tick = tick


@pytest.fixture
def strategy_manager():
    """创建新的策略管理器实例"""
    manager = StrategyManager()
    # 清空已有策略
    for sid in list(manager.list_strategies()):
        manager.remove_strategy(sid)
    return manager


class TestStrategyContext:
    """测试策略上下文"""

    def test_context_initialization(self):
        """测试上下文初始化"""
        ctx = StrategyContext("test_strategy", initial_capital=Decimal("100000"))

        assert ctx.strategy_id == "test_strategy"
        assert ctx.initial_capital == Decimal("100000")
        assert ctx.current_capital == Decimal("100000")

    def test_update_and_get_bars(self):
        """测试K线更新和获取"""
        ctx = StrategyContext("test")

        # 添加K线数据
        for i in range(10):
            bar = BarData(
                symbol="000001.SZ",
                timestamp=datetime.now() + timedelta(minutes=i),
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10.5"),
                volume=1000,
                amount=Decimal("10500")
            )
            ctx._update_bar(bar)

        # 获取数据
        bars = ctx.get_bars("000001.SZ", n=5)
        assert len(bars) == 5

        latest = ctx.get_latest_bar("000001.SZ")
        assert latest is not None
        assert latest.close == Decimal("10.5")

    def test_update_and_get_tick(self):
        """测试Tick更新和获取"""
        ctx = StrategyContext("test")

        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.5"),
            volume=100,
            bid_price=Decimal("10.4"),
            ask_price=Decimal("10.6")
        )
        ctx._update_tick(tick)

        latest = ctx.get_latest_tick("000001.SZ")
        assert latest is not None
        assert latest.price == Decimal("10.5")

    def test_position_management(self):
        """测试持仓管理"""
        ctx = StrategyContext("test")

        # 更新账户信息
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            avg_price=Decimal("10"),
            current_price=Decimal("10.5"),
            market_value=Decimal("10500"),
            unrealized_pnl=Decimal("500")
        )

        account = AccountInfo(
            total_equity=Decimal("100000"),
            available_cash=Decimal("89500"),
            frozen_cash=Decimal("0"),
            margin_used=Decimal("0"),
            positions={"000001.SZ": position}
        )
        ctx._update_account(account)

        # 查询持仓
        assert ctx.has_position("000001.SZ") is True
        assert ctx.has_position("000002.SZ") is False
        assert ctx.get_position_quantity("000001.SZ") == 1000
        assert ctx.get_position_quantity("000002.SZ") == 0


class TestStrategyBase:
    """测试策略基类"""

    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = MockStrategy(
            strategy_id="test_001",
            name="测试策略",
            symbols=["000001.SZ"],
            params={"param1": 10}
        )

        assert strategy.strategy_id == "test_001"
        assert strategy.name == "测试策略"
        assert strategy.symbols == ["000001.SZ"]
        assert strategy.params == {"param1": 10}
        assert strategy.state == StrategyState.INITIALIZING

    def test_strategy_lifecycle(self):
        """测试策略生命周期"""
        strategy = MockStrategy("test", "测试", ["000001.SZ"])
        context = StrategyContext("test")

        # 初始化
        strategy.initialize(context)
        assert strategy.init_called is True
        assert strategy.state == StrategyState.READY
        assert strategy.context is context

        # 启动
        strategy.start()
        assert strategy.state == StrategyState.RUNNING

        # 暂停
        strategy.pause()
        assert strategy.state == StrategyState.PAUSED

        # 恢复
        strategy.resume()
        assert strategy.state == StrategyState.RUNNING

        # 停止
        strategy.stop()
        assert strategy.state == StrategyState.STOPPED

    def test_signal_emission(self):
        """测试信号发出"""
        strategy = MockStrategy("test", "测试", ["000001.SZ"])

        signals_received = []

        def on_signal(signal):
            signals_received.append(signal)

        strategy.on_signal(on_signal)

        # 发出信号
        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.5"),
            volume=100,
            reason="测试信号"
        )
        strategy.emit_signal(signal)

        assert len(signals_received) == 1
        assert signals_received[0].type == SignalType.BUY
        assert len(strategy.signals) == 1

    def test_stats(self):
        """测试统计信息"""
        strategy = MockStrategy("test", "测试", ["000001.SZ"])
        context = StrategyContext("test")

        strategy.initialize(context)
        strategy.start()

        stats = strategy.stats
        assert stats["strategy_id"] == "test"
        assert stats["name"] == "测试"
        assert stats["state"] == "running"
        assert "init_time" in stats


class TestStrategyManager:
    """测试策略管理器"""

    def test_singleton(self):
        """测试单例模式"""
        manager1 = StrategyManager()
        manager2 = StrategyManager()
        assert manager1 is manager2

    def test_register_strategy_class(self, strategy_manager):
        """测试注册策略类"""
        strategy_manager.register_strategy_class("MockStrategy", MockStrategy)

        assert "MockStrategy" in strategy_manager._strategy_classes

    def test_create_and_remove_strategy(self, strategy_manager):
        """测试创建和移除策略"""
        strategy_manager.register_strategy_class("MockStrategy", MockStrategy)

        # 创建策略
        strategy = strategy_manager.create_strategy(
            strategy_class_name="MockStrategy",
            strategy_id="test_001",
            name="测试策略",
            symbols=["000001.SZ"],
            params={"param": 10}
        )

        assert strategy.strategy_id == "test_001"
        assert "test_001" in strategy_manager.list_strategies()

        # 获取策略
        retrieved = strategy_manager.get_strategy("test_001")
        assert retrieved is strategy

        # 移除策略
        strategy_manager.remove_strategy("test_001")
        assert "test_001" not in strategy_manager.list_strategies()

    def test_strategy_lifecycle_control(self, strategy_manager):
        """测试策略生命周期控制"""
        strategy_manager.register_strategy_class("MockStrategy", MockStrategy)

        strategy = strategy_manager.create_strategy(
            strategy_class_name="MockStrategy",
            strategy_id="test_002",
            name="测试策略",
            symbols=["000001.SZ"]
        )

        # 启动
        strategy_manager.start_strategy("test_002")
        assert strategy.state == StrategyState.RUNNING

        # 暂停
        strategy_manager.pause_strategy("test_002")
        assert strategy.state == StrategyState.PAUSED

        # 恢复
        strategy_manager.resume_strategy("test_002")
        assert strategy.state == StrategyState.RUNNING

        # 停止
        strategy_manager.stop_strategy("test_002")
        assert strategy.state == StrategyState.STOPPED

    def test_get_stats(self, strategy_manager):
        """测试获取统计信息"""
        strategy_manager.register_strategy_class("MockStrategy", MockStrategy)

        strategy = strategy_manager.create_strategy(
            strategy_class_name="MockStrategy",
            strategy_id="test_003",
            name="测试策略",
            symbols=["000001.SZ"]
        )

        stats = strategy_manager.get_strategy_stats("test_003")
        assert stats is not None
        assert stats["strategy_id"] == "test_003"
        assert stats["name"] == "测试策略"

    def test_duplicate_strategy_id(self, strategy_manager):
        """测试重复策略ID"""
        strategy_manager.register_strategy_class("MockStrategy", MockStrategy)

        strategy_manager.create_strategy(
            strategy_class_name="MockStrategy",
            strategy_id="duplicate_test",
            name="策略1",
            symbols=["000001.SZ"]
        )

        with pytest.raises(ValueError, match="策略ID已存在"):
            strategy_manager.create_strategy(
                strategy_class_name="MockStrategy",
                strategy_id="duplicate_test",
                name="策略2",
                symbols=["000002.SZ"]
            )


class TestMACrossStrategy:
    """测试双均线策略"""

    @pytest.fixture
    def ma_strategy(self):
        """创建双均线策略实例"""
        from src.strategy.examples.ma_cross import MACrossStrategy

        return MACrossStrategy(
            strategy_id="ma_test",
            name="双均线测试",
            symbols=["000001.SZ"],
            params={"fast_period": 3, "slow_period": 5}
        )

    def test_initialization(self, ma_strategy):
        """测试初始化"""
        assert ma_strategy.fast_period == 3
        assert ma_strategy.slow_period == 5
        assert ma_strategy.symbols == ["000001.SZ"]

    def test_on_bar_with_mock_data(self, ma_strategy):
        """测试 on_bar 处理"""
        context = StrategyContext("ma_test")
        ma_strategy.initialize(context)
        ma_strategy.start()

        # 添加一些K线数据（创建金叉场景）
        base_time = datetime.now()

        # 前5根K线：价格平稳
        for i in range(5):
            bar = BarData(
                symbol="000001.SZ",
                timestamp=base_time + timedelta(minutes=i),
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10"),
                volume=1000,
                amount=Decimal("10000")
            )
            # 同时更新 context
            context._update_bar(bar)
            ma_strategy.on_bar(bar)

        # 第6、7、8根：价格快速上涨（金叉）
        for i, price in enumerate([10.5, 11, 12]):
            bar = BarData(
                symbol="000001.SZ",
                timestamp=base_time + timedelta(minutes=5+i),
                open=Decimal(str(price - 0.5)),
                high=Decimal(str(price + 0.5)),
                low=Decimal(str(price - 0.5)),
                close=Decimal(str(price)),
                volume=1000,
                amount=Decimal("10000")
            )
            context._update_bar(bar)
            ma_strategy.on_bar(bar)

        # 验证策略处理了数据
        assert len(ma_strategy._bars["000001.SZ"]) >= 8
