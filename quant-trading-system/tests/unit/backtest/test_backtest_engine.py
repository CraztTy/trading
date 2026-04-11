"""
回测引擎测试

测试内容：
- 历史数据加载
- 回测执行循环
- 绩效计算
- 交易记录
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from src.backtest import (
    BacktestEngine, BacktestConfig, BacktestResult,
    HistoryDataLoader, HistoryDataRequest,
    MetricsCalculator, TradeRecord, DailyPortfolio
)
from src.strategy.base import StrategyBase, BarData, Signal, SignalType
from src.strategy.examples.ma_cross import MACrossStrategy


@pytest.fixture
def sample_config():
    """回测配置"""
    return BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 3, 31),
        initial_capital=Decimal("100000"),
        commission_rate=0.0003,
        min_commission=5.0,
        stamp_tax_rate=0.001
    )


@pytest.fixture
def simple_strategy():
    """简单测试策略"""
    return MACrossStrategy(
        strategy_id="test_ma",
        name="测试双均线策略",
        symbols=["000001.SZ"],
        params={"fast_period": 3, "slow_period": 5}
    )


class TestHistoryDataLoader:
    """测试历史数据加载"""

    @pytest.mark.asyncio
    async def test_load_mock_data(self):
        """测试加载模拟数据"""
        loader = HistoryDataLoader()

        request = HistoryDataRequest(
            symbol="000001.SZ",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 31),
            period="1d"
        )

        bars = await loader.load_bars(request)

        # 验证数据
        assert len(bars) > 0
        assert all(isinstance(b, BarData) for b in bars)

        # 验证字段
        bar = bars[0]
        assert bar.symbol == "000001.SZ"
        assert bar.open > 0
        assert bar.high >= bar.low
        assert bar.close > 0
        assert bar.volume > 0

    @pytest.mark.asyncio
    async def test_cache_functionality(self):
        """测试缓存功能"""
        loader = HistoryDataLoader()

        request = HistoryDataRequest(
            symbol="000001.SZ",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 10),
            period="1d"
        )

        # 第一次加载
        bars1 = await loader.load_bars(request)

        # 第二次加载（应从缓存获取）
        bars2 = await loader.load_bars(request)

        assert len(bars1) == len(bars2)

        # 清除缓存
        loader.clear_cache()
        assert len(loader._cache) == 0


class TestMetricsCalculator:
    """测试绩效计算"""

    def test_calc_total_return(self):
        """测试总收益率计算"""
        calculator = MetricsCalculator()

        portfolios = [
            DailyPortfolio(
                date=datetime(2023, 1, 1),
                cash=Decimal("50000"),
                market_value=Decimal("50000"),
                total_value=Decimal("100000")
            ),
            DailyPortfolio(
                date=datetime(2023, 12, 31),
                cash=Decimal("50000"),
                market_value=Decimal("60000"),
                total_value=Decimal("110000")
            ),
        ]

        metrics = calculator.calculate(portfolios, [])

        # 总收益率 = (110000 - 100000) / 100000 = 10%
        assert metrics.total_return == pytest.approx(0.10, abs=0.001)

    def test_calc_max_drawdown(self):
        """测试最大回撤计算"""
        calculator = MetricsCalculator()

        portfolios = [
            DailyPortfolio(date=datetime(2023, 1, 1), cash=Decimal("0"), market_value=Decimal("100000"), total_value=Decimal("100000")),
            DailyPortfolio(date=datetime(2023, 1, 2), cash=Decimal("0"), market_value=Decimal("110000"), total_value=Decimal("110000")),  # 峰值
            DailyPortfolio(date=datetime(2023, 1, 3), cash=Decimal("0"), market_value=Decimal("105000"), total_value=Decimal("105000")),
            DailyPortfolio(date=datetime(2023, 1, 4), cash=Decimal("0"), market_value=Decimal("95000"), total_value=Decimal("95000")),   # 谷底
            DailyPortfolio(date=datetime(2023, 1, 5), cash=Decimal("0"), market_value=Decimal("100000"), total_value=Decimal("100000")),
        ]

        metrics = calculator.calculate(portfolios, [])

        # 最大回撤 = (110000 - 95000) / 110000 = 13.64%
        assert metrics.max_drawdown == pytest.approx(0.1364, abs=0.001)
        assert metrics.max_drawdown_duration == 2  # 持续2天

    def test_calc_trade_stats(self):
        """测试交易统计"""
        calculator = MetricsCalculator()

        trades = [
            TradeRecord(
                timestamp=datetime.now(),
                symbol="000001.SZ",
                side="SELL",
                qty=100,
                price=Decimal("11"),
                amount=Decimal("1100"),
                pnl=Decimal("100")
            ),
            TradeRecord(
                timestamp=datetime.now(),
                symbol="000001.SZ",
                side="SELL",
                qty=100,
                price=Decimal("9"),
                amount=Decimal("900"),
                pnl=Decimal("-100")
            ),
        ]

        portfolios = [
            DailyPortfolio(date=datetime(2023, 1, 1), cash=Decimal("100000"), market_value=Decimal("0"), total_value=Decimal("100000")),
        ]

        metrics = calculator.calculate(portfolios, trades)

        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.win_rate == 0.5
        assert metrics.profit_factor == 1.0  # 盈亏比 = 100/100 = 1


class TestBacktestEngine:
    """测试回测引擎"""

    @pytest.mark.asyncio
    async def test_backtest_run(self, sample_config, simple_strategy):
        """测试完整回测流程"""
        engine = BacktestEngine()

        result = await engine.run(simple_strategy, sample_config)

        # 验证结果类型
        assert isinstance(result, BacktestResult)
        assert result.config == sample_config

        # 验证绩效指标
        assert result.metrics is not None
        assert result.metrics.total_return is not None
        assert result.metrics.sharpe_ratio is not None

        # 验证每日持仓记录
        assert len(result.daily_portfolios) > 0

        # 验证可以打印报告
        result.print_report()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_backtest_buy_sell(self, sample_config):
        """测试回测中的买卖逻辑"""
        from src.backtest.engine import BacktestContext

        context = BacktestContext(
            strategy_id="test",
            initial_capital=Decimal("100000")
        )

        # 添加一个 bar
        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime(2023, 1, 15),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
            volume=10000,
            amount=Decimal("100000")
        )
        context._update_bar(bar)

        # 买入
        order_id = context.buy("000001.SZ", 1000, Decimal("10"))
        assert order_id is not None
        assert len(context.trades) == 1
        assert context.trades[0].side == "BUY"

        # 检查资金减少
        assert context.current_capital < Decimal("100000")

        # 检查持仓
        position = context.get_position("000001.SZ")
        assert position is not None
        assert position.quantity == 1000

        # 卖出
        order_id = context.sell("000001.SZ", 500, Decimal("11"))
        assert order_id is not None
        assert len(context.trades) == 2
        assert context.trades[1].side == "SELL"

        # 检查部分持仓减少
        position = context.get_position("000001.SZ")
        assert position.quantity == 500

    @pytest.mark.asyncio
    async def test_insufficient_funds(self, sample_config):
        """测试资金不足情况"""
        from src.backtest.engine import BacktestContext

        context = BacktestContext(
            strategy_id="test",
            initial_capital=Decimal("1000")  # 很少的资金
        )

        bar = BarData(
            symbol="000001.SZ",
            timestamp=datetime(2023, 1, 15),
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("90"),
            close=Decimal("100"),
            volume=10000,
            amount=Decimal("1000000")
        )
        context._update_bar(bar)

        # 尝试买入超过资金能力的数量
        order_id = context.buy("000001.SZ", 1000)  # 需要 100000 + 佣金
        assert order_id is None  # 应该失败

    @pytest.mark.asyncio
    async def test_insufficient_position(self, sample_config):
        """测试持仓不足情况"""
        from src.backtest.engine import BacktestContext

        context = BacktestContext(
            strategy_id="test",
            initial_capital=Decimal("100000")
        )

        # 没有持仓时尝试卖出
        order_id = context.sell("000001.SZ", 100)
        assert order_id is None  # 应该失败


class TestBacktestWithIndicators:
    """测试回测与技术指标结合"""

    @pytest.mark.asyncio
    async def test_indicator_in_backtest(self, sample_config):
        """测试在回测中使用技术指标"""
        from src.strategy.indicators import IndicatorEngine
        import pandas as pd

        engine = IndicatorEngine()

        # 创建测试数据
        df = pd.DataFrame({
            'open': [10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
            'high': [11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
            'low': [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
            'close': [10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5],
            'volume': [1000] * 10,
        })

        # 计算指标
        result = engine.calculate_all(df, indicators=['ma', 'rsi'])

        assert 'ma5' in result.columns
        assert 'rsi6' in result.columns
