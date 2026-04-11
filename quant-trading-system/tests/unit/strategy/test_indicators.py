"""
技术指标计算引擎测试

测试内容：
- 移动平均线 (MA, EMA, WMA)
- MACD 指标
- RSI 指标
- 布林带
- KDJ 指标
- ATR 指标
- OBV 指标
- 批量计算引擎
"""
import numpy as np
import pandas as pd
import pytest

from src.strategy.indicators import (
    MovingAverage,
    MACD,
    RSI,
    BollingerBands,
    KDJ,
    ATR,
    OBV,
    IndicatorEngine,
)


class TestMovingAverage:
    """测试移动平均线"""

    def test_sma_basic(self):
        """测试 SMA 基本计算"""
        data = [1, 2, 3, 4, 5]
        result = MovingAverage.sma(data, period=3)

        # 前 2 个应为 nan
        assert np.isnan(result[0])
        assert np.isnan(result[1])
        # 第 3 个 = (1+2+3)/3 = 2
        assert result[2] == pytest.approx(2.0)
        # 第 4 个 = (2+3+4)/3 = 3
        assert result[3] == pytest.approx(3.0)
        # 第 5 个 = (3+4+5)/3 = 4
        assert result[4] == pytest.approx(4.0)

    def test_sma_insufficient_data(self):
        """测试数据不足时返回全 nan"""
        data = [1, 2]
        result = MovingAverage.sma(data, period=5)

        assert len(result) == 2
        assert all(np.isnan(result))

    def test_ema_basic(self):
        """测试 EMA 基本计算"""
        data = [10, 11, 12, 13, 14]
        result = MovingAverage.ema(data, period=3)

        # EMA 会计算所有值，但前几个可能不够准确
        assert len(result) == 5
        assert not np.isnan(result[-1])
        # EMA 应该是递增的
        assert result[-1] > result[0]

    def test_wma_basic(self):
        """测试 WMA 基本计算"""
        data = [1, 2, 3, 4, 5]
        result = MovingAverage.wma(data, period=3)

        # WMA: (1*1 + 2*2 + 3*3) / (1+2+3) = 14/6 = 2.33
        assert result[2] == pytest.approx(14/6, abs=0.01)


class TestMACD:
    """测试 MACD 指标"""

    def test_macd_calculation(self):
        """测试 MACD 计算"""
        # 模拟价格数据（上升趋势）
        data = list(range(50))

        dif, dea, bar = MACD.calculate(data, fast=12, slow=26, signal=9)

        assert len(dif) == len(data)
        assert len(dea) == len(data)
        assert len(bar) == len(data)

        # 在上升趋势中，DIF 应该大于 DEA
        assert dif[-1] > dea[-1]

        # MACD 柱状图 = 2 * (DIF - DEA)
        assert bar[-1] == pytest.approx(2 * (dif[-1] - dea[-1]))

    def test_macd_signal(self):
        """测试 MACD 信号生成"""
        # 构造一个金叉场景
        dif = np.array([0, -0.1, 0.1, 0.2, 0.3])
        dea = np.array([0, 0, 0, 0, 0])

        signals = MACD.signal(dif, dea)

        # 第 2 个位置应该是金叉信号
        assert signals[2] == 1

        # 构造一个死叉场景
        dif = np.array([0.3, 0.2, 0.1, -0.1, -0.2])
        dea = np.array([0, 0, 0, 0, 0])

        signals = MACD.signal(dif, dea)

        # 第 3 个位置应该是死叉信号
        assert signals[3] == -1


class TestRSI:
    """测试 RSI 指标"""

    def test_rsi_calculation(self):
        """测试 RSI 计算"""
        # 模拟价格数据
        np.random.seed(42)
        data = np.cumsum(np.random.randn(50)) + 100

        rsi = RSI.calculate(data, period=14)

        assert len(rsi) == len(data)
        # RSI 值应在 0-100 之间
        valid_rsi = rsi[~np.isnan(rsi)]
        assert all(valid_rsi >= 0)
        assert all(valid_rsi <= 100)

    def test_rsi_overbought_oversold(self):
        """测试 RSI 超买超卖判断"""
        # 构造超买场景
        rsi = np.array([30, 50, 70, 75, 65])
        signals = RSI.signal(rsi, overbought=70, oversold=30)

        # 从超买区回落应产生卖出信号
        assert signals[4] == -1

        # 构造超卖场景
        rsi = np.array([70, 50, 30, 25, 35])
        signals = RSI.signal(rsi, overbought=70, oversold=30)

        # 从超卖区反弹应产生买入信号
        assert signals[4] == 1


class TestBollingerBands:
    """测试布林带指标"""

    def test_bollinger_calculation(self):
        """测试布林带计算"""
        # 模拟价格波动数据
        np.random.seed(42)
        data = np.cumsum(np.random.randn(50) * 0.5) + 100

        upper, middle, lower = BollingerBands.calculate(data, period=20, num_std=2.0)

        assert len(upper) == len(data)
        assert len(middle) == len(data)
        assert len(lower) == len(data)

        # 上轨 > 中轨 > 下轨
        valid_idx = ~np.isnan(upper)
        assert all(upper[valid_idx] >= middle[valid_idx])
        assert all(middle[valid_idx] >= lower[valid_idx])

    def test_bollinger_signal(self):
        """测试布林带信号"""
        # 构造触及下轨反弹的场景
        price = np.array([100, 95, 90, 89, 91])
        upper = np.array([110, 110, 110, 110, 110])
        lower = np.array([90, 90, 90, 90, 90])

        signals, positions = BollingerBands.signal(price, upper, lower)

        # 从下轨反弹应产生买入信号
        assert signals[4] == 1


class TestKDJ:
    """测试 KDJ 指标"""

    def test_kdj_calculation(self):
        """测试 KDJ 计算"""
        np.random.seed(42)
        n = 50

        # 生成模拟的 K 线数据
        base = 100
        high = base + np.abs(np.random.randn(n) * 2)
        low = base - np.abs(np.random.randn(n) * 2)
        close = (high + low) / 2 + np.random.randn(n)

        k, d, j = KDJ.calculate(high, low, close, n=9, m1=3, m2=3)

        assert len(k) == n
        assert len(d) == n
        assert len(j) == n

        # K, D 值应在 0-100 之间
        valid_idx = ~np.isnan(k)
        assert all(k[valid_idx] >= 0)
        assert all(k[valid_idx] <= 100)

    def test_kdj_signal(self):
        """测试 KDJ 信号"""
        # 构造低位金叉: K 从低于 D 变为高于 D，且 J < 20
        k = np.array([10, 14])  # K 上升
        d = np.array([15, 13])  # K 从低于 D (10<15) 变为高于 D (14>13)
        j = np.array([0, 16])   # J < 20

        signals = KDJ.signal(k, d, j)

        # 低位金叉应产生买入信号
        assert signals[1] == 1


class TestATR:
    """测试 ATR 指标"""

    def test_atr_calculation(self):
        """测试 ATR 计算"""
        np.random.seed(42)
        n = 50

        base = 100
        high = base + np.abs(np.random.randn(n) * 2)
        low = base - np.abs(np.random.randn(n) * 2)
        close = (high + low) / 2

        atr = ATR.calculate(high, low, close, period=14)

        assert len(atr) == len(high)

        # ATR 应为正数
        valid_atr = atr[~np.isnan(atr)]
        assert all(valid_atr > 0)


class TestOBV:
    """测试 OBV 指标"""

    def test_obv_calculation(self):
        """测试 OBV 计算"""
        close = np.array([100, 102, 101, 103, 104])
        volume = np.array([1000, 1500, 1200, 1800, 2000])

        obv = OBV.calculate(close, volume)

        assert len(obv) == len(close)

        # 上涨时 OBV 增加
        assert obv[1] > obv[0]

        # 下跌时 OBV 减少
        assert obv[2] < obv[1]


class TestIndicatorEngine:
    """测试指标计算引擎"""

    @pytest.fixture
    def sample_data(self):
        """生成测试数据"""
        np.random.seed(42)
        n = 100

        base = 100
        data = {
            'open': base + np.cumsum(np.random.randn(n) * 0.3),
            'high': base + np.abs(np.random.randn(n) * 2) + np.cumsum(np.random.randn(n) * 0.3),
            'low': base - np.abs(np.random.randn(n) * 2) + np.cumsum(np.random.randn(n) * 0.3),
            'close': base + np.cumsum(np.random.randn(n) * 0.3),
            'volume': np.random.randint(1000, 10000, n),
        }

        # 确保 high >= close >= low
        for i in range(n):
            data['high'][i] = max(data['high'][i], data['close'][i], data['open'][i])
            data['low'][i] = min(data['low'][i], data['close'][i], data['open'][i])

        return pd.DataFrame(data)

    def test_calculate_all(self, sample_data):
        """测试批量计算所有指标"""
        engine = IndicatorEngine()

        result = engine.calculate_all(sample_data)

        # 检查是否添加了所有指标列
        expected_columns = [
            'ma5', 'ma10', 'ma20', 'ma60',
            'ema12', 'ema26',
            'macd_dif', 'macd_dea', 'macd_bar',
            'rsi6', 'rsi12', 'rsi24',
            'boll_upper', 'boll_middle', 'boll_lower',
            'kdj_k', 'kdj_d', 'kdj_j',
            'atr14', 'obv'
        ]

        for col in expected_columns:
            assert col in result.columns, f"缺少列: {col}"

    def test_calculate_selected_indicators(self, sample_data):
        """测试选择性计算指标"""
        engine = IndicatorEngine()

        result = engine.calculate_all(sample_data, indicators=['ma', 'rsi'])

        # 检查只添加了 MA 和 RSI 列
        assert 'ma5' in result.columns
        assert 'rsi6' in result.columns

        # 其他指标不应添加
        assert 'macd_dif' not in result.columns
        assert 'kdj_k' not in result.columns

    def test_get_signals(self, sample_data):
        """测试获取交易信号"""
        engine = IndicatorEngine()

        # 先计算指标
        df = engine.calculate_all(sample_data)

        # 获取信号
        signals = engine.get_signals(df)

        # 检查信号字典包含预期的键
        assert 'macd' in signals
        assert 'rsi' in signals
        assert 'boll' in signals
        assert 'kdj' in signals
        assert 'boll_position' in signals

        # 信号值应为 -1, 0, 或 1
        for key in ['macd', 'rsi', 'boll', 'kdj']:
            assert signals[key] in [-1, 0, 1]

    def test_get_signals_partial(self, sample_data):
        """测试部分指标的信号获取"""
        engine = IndicatorEngine()

        # 只计算 MACD
        df = engine.calculate_all(sample_data, indicators=['macd'])

        # 获取信号
        signals = engine.get_signals(df)

        # 只有 MACD 信号
        assert 'macd' in signals
        assert 'rsi' not in signals
