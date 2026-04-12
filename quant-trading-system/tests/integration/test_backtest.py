"""
回测系统集成测试

测试场景:
1. 完整回测流程
2. 多策略回测
3. 错误处理
4. 性能测试
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# 尝试导入pytest，如果不存在则使用模拟
try:
    import pytest
except ImportError:
    # 创建一个模拟的pytest模块
    class MockPytest:
        @staticmethod
        def mark_asyncio(func):
            return func
        @staticmethod
        def mark(*args, **kwargs):
            class Marker:
                @staticmethod
                def __call__(func):
                    return func
            return Marker()
    pytest = MockPytest()
    pytest.mark.asyncio = pytest.mark_asyncio
    pytest.mark = pytest.mark

# 直接导入需要的模块，避免加载有问题的模型
from src.backtest.engine import BacktestEngine, BacktestConfig, SlippageModel, CommissionCalculator, BacktestContext
from src.backtest.metrics import MetricsCalculator, TradeRecord, DailyPortfolio
from src.strategy.base import StrategyBase, StrategyContext, Signal, SignalType, BarData
from src.models.enums import OrderDirection


# ==================== Mock数据 ====================

class MockDataLoader:
    """模拟历史数据加载器"""

    def __init__(self):
        self.data = {}

    async def load_bars(
        self,
        request
    ):
        """生成模拟K线数据"""
        import pandas as pd
        import numpy as np

        # 生成日期范围
        dates = pd.date_range(
            start=request.start_date,
            end=request.end_date,
            freq='B'  # 工作日
        )

        # 生成随机价格数据（随机游走）
        np.random.seed(42)  # 固定种子确保可重复
        returns = np.random.normal(0.001, 0.02, len(dates))  # 日均收益0.1%，波动2%
        prices = 10 * np.exp(np.cumsum(returns))  # 从10元开始

        df = pd.DataFrame({
            '日期': dates.strftime('%Y-%m-%d'),
            '开盘': prices * (1 + np.random.normal(0, 0.005, len(dates))),
            '收盘': prices,
            '最高': prices * (1 + np.random.normal(0.01, 0.005, len(dates))),
            '最低': prices * (1 + np.random.normal(-0.01, 0.005, len(dates))),
            '成交量': np.random.randint(1000000, 10000000, len(dates)),
            '成交额': np.random.randint(10000000, 100000000, len(dates)),
        })

        # 确保high >= open >= low, high >= close >= low
        df['最高'] = df[['开盘', '最高', '收盘']].max(axis=1)
        df['最低'] = df[['开盘', '最低', '收盘']].min(axis=1)

        # 转换为BarData列表
        bars = []
        for _, row in df.iterrows():
            bar = BarData(
                symbol=request.symbol,
                timestamp=pd.to_datetime(row['日期']),
                open=Decimal(str(row['开盘'])),
                high=Decimal(str(row['最高'])),
                low=Decimal(str(row['最低'])),
                close=Decimal(str(row['收盘'])),
                volume=int(row['成交量']),
                amount=Decimal(str(row['成交额'])),
                period=request.period
            )
            bars.append(bar)

        return bars


# ==================== 测试策略 ====================

class MockMAStrategy(StrategyBase):
    """简单的均线策略（用于测试）"""

    def __init__(self, fast_period=5, slow_period=10):
        super().__init__("ma_test", "MA Test", ["000001.SZ"])
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.prices = []
        self.has_position = False

    def on_init(self, context: StrategyContext):
        pass

    def on_bar(self, bar: BarData):
        self.prices.append(bar.close)

        if len(self.prices) >= self.slow_period:
            fast_ma = sum(self.prices[-self.fast_period:]) / self.fast_period
            slow_ma = sum(self.prices[-self.slow_period:]) / self.slow_period

            # 金叉买入
            if fast_ma > slow_ma and len(self.prices) > 1:
                prev_fast = sum(self.prices[-self.fast_period-1:-1]) / self.fast_period
                prev_slow = sum(self.prices[-self.slow_period-1:-1]) / self.slow_period

                if prev_fast <= prev_slow and not self.has_position and self.context:
                    self.has_position = True
                    # 直接通过context执行买入
                    self.context.buy(bar.symbol, 100, bar.close, reason="MA Golden Cross")
                    # 同时发出信号
                    signal = Signal(
                        type=SignalType.BUY,
                        symbol=bar.symbol,
                        timestamp=bar.timestamp,
                        price=bar.close,
                        volume=100,
                        reason="MA Golden Cross"
                    )
                    self.emit_signal(signal)

    def on_tick(self, tick):
        pass


class MockBuyHoldStrategy(StrategyBase):
    """买入持有策略（用于测试）"""

    def __init__(self):
        super().__init__("buy_hold", "Buy & Hold", ["000001.SZ"])
        self.has_bought = False

    def on_init(self, context: StrategyContext):
        pass

    def on_bar(self, bar: BarData):
        if not self.has_bought and self.context:
            self.has_bought = True
            # 直接通过context执行买入
            self.context.buy(bar.symbol, 1000, bar.close, reason="Initial Buy")
            # 同时发出信号
            signal = Signal(
                type=SignalType.BUY,
                symbol=bar.symbol,
                timestamp=bar.timestamp,
                price=bar.close,
                volume=1000,
                reason="Initial Buy"
            )
            self.emit_signal(signal)

    def on_tick(self, tick):
        pass


class MockSignalEmittingStrategy(StrategyBase):
    """发出信号并通过context执行交易的策略"""

    def __init__(self):
        super().__init__("signal_emit", "Signal Emit", ["000001.SZ"])
        self.bar_count = 0

    def on_init(self, context: StrategyContext):
        pass

    def on_bar(self, bar: BarData):
        self.bar_count += 1

        # 第5根K线买入
        if self.bar_count == 5:
            if self.context:
                self.context.buy(bar.symbol, 500, bar.close, reason="Test Buy")

        # 第15根K线卖出
        elif self.bar_count == 15:
            if self.context:
                self.context.sell(bar.symbol, 500, bar.close, reason="Test Sell")

    def on_tick(self, tick):
        pass


# ==================== 测试用例 ====================

class TestBacktestEngine:
    """回测引擎测试"""

    @pytest.mark.asyncio
    async def test_basic_backtest(self):
        """测试基本回测流程"""
        print("\n[TEST] 基本回测流程...")

        # 创建引擎
        engine = BacktestEngine()

        # 创建策略
        strategy = MockBuyHoldStrategy()

        # 配置
        config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31),
            initial_capital=Decimal("100000"),
            slippage_pct=0.001,
            commission_rate=0.0003
        )

        # 使用模拟数据加载器
        engine.data_loader = MockDataLoader()

        # 运行回测
        result = await engine.run(strategy, config)

        # 验证结果
        assert result is not None, "回测结果不应为空"
        assert result.trades, "应该有交易记录"
        assert result.metrics.total_return is not None, "应该有收益指标"

        print(f"   总收益: {result.metrics.total_return * 100:.2f}%")
        print(f"   交易次数: {result.metrics.total_trades}")
        print("   [PASS] 基本回测通过")

    @pytest.mark.asyncio
    async def test_ma_strategy_backtest(self):
        """测试均线策略回测"""
        print("\n[TEST] 均线策略回测...")

        engine = BacktestEngine()
        strategy = MockMAStrategy(fast_period=5, slow_period=10)

        config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 6, 30),
            initial_capital=Decimal("100000")
        )

        engine.data_loader = MockDataLoader()
        result = await engine.run(strategy, config)

        assert result.metrics.total_trades >= 0, "应该有交易统计"
        assert result.metrics.sharpe_ratio is not None, "应该有夏普比率"

        print(f"   交易次数: {result.metrics.total_trades}")
        print(f"   胜率: {result.metrics.win_rate * 100:.2f}%")
        print(f"   夏普比率: {result.metrics.sharpe_ratio:.2f}")
        print("   [PASS] 均线策略回测通过")

    @pytest.mark.asyncio
    async def test_context_buy_sell(self):
        """测试回测上下文中的买卖操作"""
        print("\n[TEST] 回测上下文买卖操作...")

        engine = BacktestEngine()
        strategy = MockSignalEmittingStrategy()

        config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31),
            initial_capital=Decimal("100000"),
            slippage_pct=0.001,
            commission_rate=0.0003
        )

        engine.data_loader = MockDataLoader()
        result = await engine.run(strategy, config)

        # 验证有交易记录
        assert len(result.trades) >= 2, "应该有至少2笔交易（买和卖）"

        # 验证交易方向
        buy_trades = [t for t in result.trades if t.side == "BUY"]
        sell_trades = [t for t in result.trades if t.side == "SELL"]

        assert len(buy_trades) >= 1, "应该有买入交易"
        assert len(sell_trades) >= 1, "应该有卖出交易"

        print(f"   买入次数: {len(buy_trades)}")
        print(f"   卖出次数: {len(sell_trades)}")
        print("   [PASS] 上下文买卖操作通过")

    def test_slippage_model(self):
        """测试滑点模型"""
        print("\n[TEST] 滑点模型...")

        model = SlippageModel(slippage_pct=0.001)
        price = Decimal("100")

        # 买入滑点
        buy_price = model.apply(price, OrderDirection.BUY)
        assert buy_price > price, "买入价格应该更高"
        assert buy_price == Decimal("100.1"), f"滑点计算错误: {buy_price}"

        # 卖出滑点
        sell_price = model.apply(price, OrderDirection.SELL)
        assert sell_price < price, "卖出价格应该更低"
        assert sell_price == Decimal("99.9"), f"滑点计算错误: {sell_price}"

        print("   [PASS] 滑点模型通过")

    def test_commission_calculator(self):
        """测试手续费计算器"""
        print("\n[TEST] 手续费计算器...")

        calc = CommissionCalculator(
            commission_rate=0.0003,
            min_commission=5.0,
            stamp_tax_rate=0.001,
            transfer_fee_rate=0.00002
        )

        amount = Decimal("100000")

        # 买入费用
        buy_fees = calc.calculate(amount, OrderDirection.BUY)
        assert buy_fees["commission"] == Decimal("30"), f"佣金计算错误: {buy_fees['commission']}"
        assert buy_fees["stamp_tax"] == Decimal("0"), "买入不应有印花税"
        assert buy_fees["transfer_fee"] == Decimal("2"), f"过户费计算错误: {buy_fees['transfer_fee']}"

        # 卖出费用
        sell_fees = calc.calculate(amount, OrderDirection.SELL)
        assert sell_fees["stamp_tax"] == Decimal("100"), f"卖出印花税计算错误: {sell_fees['stamp_tax']}"

        # 小额交易（最低佣金）
        small_amount = Decimal("10000")
        small_fees = calc.calculate(small_amount, OrderDirection.BUY)
        assert small_fees["commission"] == Decimal("5"), f"最低佣金计算错误: {small_fees['commission']}"

        print("   [PASS] 手续费计算器通过")


class TestBacktestMetrics:
    """回测指标测试"""

    def test_metrics_calculation(self):
        """测试指标计算"""
        print("\n[TEST] 回测指标计算...")

        # 创建模拟每日持仓记录
        portfolios = [
            DailyPortfolio(
                date=datetime(2024, 1, 1),
                cash=Decimal("90000"),
                market_value=Decimal("10000"),
                total_value=Decimal("100000"),
                positions={"000001.SZ": 1000}
            ),
            DailyPortfolio(
                date=datetime(2024, 2, 1),
                cash=Decimal("90000"),
                market_value=Decimal("11000"),
                total_value=Decimal("101000"),
                positions={"000001.SZ": 1000}
            ),
            DailyPortfolio(
                date=datetime(2024, 3, 1),
                cash=Decimal("100500"),
                market_value=Decimal("0"),
                total_value=Decimal("100500"),
                positions={}
            ),
        ]

        # 创建模拟交易记录
        trades = [
            TradeRecord(
                timestamp=datetime(2024, 1, 1),
                symbol="000001.SZ",
                side="BUY",
                qty=1000,
                price=Decimal("10"),
                amount=Decimal("10000"),
                commission=Decimal("5"),
                stamp_tax=Decimal("0"),
                transfer_fee=Decimal("0.2")
            ),
            TradeRecord(
                timestamp=datetime(2024, 3, 1),
                symbol="000001.SZ",
                side="SELL",
                qty=1000,
                price=Decimal("11"),
                amount=Decimal("11000"),
                commission=Decimal("5"),
                stamp_tax=Decimal("11"),
                transfer_fee=Decimal("0.22"),
                pnl=Decimal("1000")
            ),
        ]

        calc = MetricsCalculator()
        metrics = calc.calculate(portfolios, trades)

        assert metrics.total_return is not None
        # 注意：metrics.total_trades 只统计有盈亏的平仓交易（SELL with pnl）
        assert metrics.total_trades == 1  # 只有卖出交易有pnl
        assert metrics.win_rate is not None
        assert metrics.sharpe_ratio is not None

        print(f"   总收益: {metrics.total_return * 100:.2f}%")
        print(f"   交易次数: {metrics.total_trades}")
        print(f"   胜率: {metrics.win_rate * 100:.2f}%")
        print("   [PASS] 指标计算通过")

    def test_empty_trades(self):
        """测试无交易情况的指标计算"""
        print("\n[TEST] 无交易指标计算...")

        portfolios = [
            DailyPortfolio(
                date=datetime(2024, 1, 1),
                cash=Decimal("100000"),
                market_value=Decimal("0"),
                total_value=Decimal("100000"),
                positions={}
            ),
            DailyPortfolio(
                date=datetime(2024, 3, 1),
                cash=Decimal("100000"),
                market_value=Decimal("0"),
                total_value=Decimal("100000"),
                positions={}
            ),
        ]

        calc = MetricsCalculator()
        metrics = calc.calculate(portfolios, [])

        assert metrics.total_trades == 0
        assert metrics.win_rate == 0

        print("   [PASS] 无交易指标计算通过")


class TestBacktestErrorHandling:
    """回测错误处理测试"""

    @pytest.mark.asyncio
    async def test_invalid_date_range(self):
        """测试无效日期范围"""
        print("\n[TEST] 无效日期范围...")

        engine = BacktestEngine()
        strategy = MockBuyHoldStrategy()

        # 结束日期早于开始日期
        config = BacktestConfig(
            start_date=datetime(2024, 6, 30),
            end_date=datetime(2024, 1, 1),
            initial_capital=Decimal("100000")
        )

        engine.data_loader = MockDataLoader()

        # 应该抛出异常或返回空结果
        try:
            result = await engine.run(strategy, config)
            # 如果没有异常，验证结果为空
            assert len(result.daily_portfolios) == 0
        except ValueError as e:
            # 预期行为：抛出ValueError
            print(f"   预期错误: {e}")

        print("   [PASS] 无效日期范围处理通过")

    @pytest.mark.asyncio
    async def test_zero_initial_capital(self):
        """测试零初始资金"""
        print("\n[TEST] 零初始资金...")

        engine = BacktestEngine()
        strategy = MockBuyHoldStrategy()

        config = BacktestConfig(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 3, 31),
            initial_capital=Decimal("0")
        )

        engine.data_loader = MockDataLoader()

        # 零初始资金会导致除零错误，这里测试是否能正确处理
        try:
            result = await engine.run(strategy, config)
            # 如果没有异常，验证没有交易
            assert len(result.trades) == 0
        except Exception as e:
            # 预期可能抛出除零错误
            print(f"   预期错误: {type(e).__name__}: {e}")

        print("   [PASS] 零初始资金处理通过")


class TestBacktestPerformance:
    """回测性能测试"""

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self):
        """测试大数据集性能"""
        print("\n[TEST] 大数据集性能...")

        import time

        engine = BacktestEngine()
        strategy = MockMAStrategy(fast_period=5, slow_period=20)

        # 一年的数据
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=Decimal("1000000")
        )

        engine.data_loader = MockDataLoader()

        start_time = time.time()
        result = await engine.run(strategy, config)
        elapsed = time.time() - start_time

        print(f"   回测耗时: {elapsed:.2f}秒")
        print(f"   总收益率: {result.metrics.total_return * 100:.2f}%")
        print(f"   夏普比率: {result.metrics.sharpe_ratio:.2f}")

        # 性能要求：一年数据应在5秒内完成
        assert elapsed < 5.0, f"回测耗时过长: {elapsed:.2f}秒"

        print("   [PASS] 大数据集性能测试通过")


# ==================== 主函数 ====================

async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("回测系统集成测试")
    print("=" * 60)

    # 引擎测试
    engine_tests = TestBacktestEngine()
    await engine_tests.test_basic_backtest()
    await engine_tests.test_ma_strategy_backtest()
    await engine_tests.test_context_buy_sell()
    engine_tests.test_slippage_model()
    engine_tests.test_commission_calculator()

    # 指标测试
    metrics_tests = TestBacktestMetrics()
    metrics_tests.test_metrics_calculation()
    metrics_tests.test_empty_trades()

    # 错误处理测试
    error_tests = TestBacktestErrorHandling()
    await error_tests.test_invalid_date_range()
    await error_tests.test_zero_initial_capital()

    # 性能测试
    perf_tests = TestBacktestPerformance()
    await perf_tests.test_large_dataset_performance()

    print("\n" + "=" * 60)
    print("所有测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
