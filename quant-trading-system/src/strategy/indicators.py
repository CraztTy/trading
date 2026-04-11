"""
技术指标计算引擎

提供常用技术分析指标的计算：
- 移动平均线 (MA, EMA)
- MACD (指数平滑异同移动平均线)
- RSI (相对强弱指标)
- 布林带 (Bollinger Bands)
- KDJ (随机指标)
- ATR (真实波幅)
- OBV (能量潮)

基于 NumPy/Pandas 实现，支持向量化计算，性能优化
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple, Union
from datetime import datetime

import numpy as np
import pandas as pd

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass(frozen=True)
class IndicatorValue:
    """指标值数据类"""
    timestamp: datetime
    value: float
    # 部分指标有多个值 (如 MACD 有 dif, dea, bar)
    sub_values: Optional[dict] = None


class MovingAverage:
    """移动平均线指标"""

    @staticmethod
    def sma(data: Union[List[float], pd.Series, np.ndarray], period: int) -> np.ndarray:
        """
        简单移动平均线 (SMA)

        Args:
            data: 价格数据
            period: 计算周期

        Returns:
            SMA 值数组，前 period-1 个为 nan
        """
        if len(data) < period:
            return np.full(len(data), np.nan)

        series = pd.Series(data)
        return series.rolling(window=period, min_periods=period).mean().values

    @staticmethod
    def ema(data: Union[List[float], pd.Series, np.ndarray], period: int) -> np.ndarray:
        """
        指数移动平均线 (EMA)

        Args:
            data: 价格数据
            period: 计算周期

        Returns:
            EMA 值数组
        """
        if len(data) < period:
            return np.full(len(data), np.nan)

        series = pd.Series(data)
        return series.ewm(span=period, adjust=False).mean().values

    @staticmethod
    def wma(data: Union[List[float], pd.Series, np.ndarray], period: int) -> np.ndarray:
        """
        加权移动平均线 (WMA)

        Args:
            data: 价格数据
            period: 计算周期

        Returns:
            WMA 值数组
        """
        if len(data) < period:
            return np.full(len(data), np.nan)

        weights = np.arange(1, period + 1)
        series = pd.Series(data)
        return series.rolling(window=period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        ).values


class MACD:
    """MACD 指标"""

    @staticmethod
    def calculate(
        data: Union[List[float], pd.Series, np.ndarray],
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算 MACD 指标

        Args:
            data: 收盘价数据
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期

        Returns:
            (dif, dea, bar) 三个数组
            - dif: DIF 线 (快线 - 慢线)
            - dea: DEA 线 (DIF 的 EMA)
            - bar: MACD 柱状图 (2 * (DIF - DEA))
        """
        series = pd.Series(data)

        # 计算快线和慢线的 EMA
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()

        # DIF 线
        dif = ema_fast - ema_slow

        # DEA 线 (DIF 的 EMA)
        dea = dif.ewm(span=signal, adjust=False).mean()

        # MACD 柱状图
        bar = 2 * (dif - dea)

        return dif.values, dea.values, bar.values

    @staticmethod
    def signal(dif: np.ndarray, dea: np.ndarray) -> np.ndarray:
        """
        生成 MACD 交易信号

        Returns:
            1: 金叉买入信号 (DIF 上穿 DEA)
            -1: 死叉卖出信号 (DIF 下穿 DEA)
            0: 无信号
        """
        # 计算差值
        diff = dif - dea

        # 找到穿越点
        signals = np.zeros(len(diff))

        for i in range(1, len(diff)):
            if diff[i-1] <= 0 and diff[i] > 0:
                # 金叉
                signals[i] = 1
            elif diff[i-1] >= 0 and diff[i] < 0:
                # 死叉
                signals[i] = -1

        return signals


class RSI:
    """RSI 相对强弱指标"""

    @staticmethod
    def calculate(data: Union[List[float], pd.Series, np.ndarray], period: int = 14) -> np.ndarray:
        """
        计算 RSI 指标

        Args:
            data: 收盘价数据
            period: 计算周期，默认 14

        Returns:
            RSI 值数组 (0-100)
        """
        series = pd.Series(data)

        # 计算价格变化
        delta = series.diff()

        # 分离上涨和下跌
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        # 使用 EMA 计算平均涨跌
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

        # 计算 RS 和 RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.values

    @staticmethod
    def signal(rsi: np.ndarray, overbought: float = 70, oversold: float = 30) -> np.ndarray:
        """
        生成 RSI 交易信号

        Args:
            rsi: RSI 值数组
            overbought: 超买阈值，默认 70
            oversold: 超卖阈值，默认 30

        Returns:
            1: 超卖区反弹 (买入)
            -1: 超买区回落 (卖出)
            0: 无信号
        """
        signals = np.zeros(len(rsi))

        for i in range(1, len(rsi)):
            # 从超卖区向上突破
            if rsi[i-1] <= oversold and rsi[i] > oversold:
                signals[i] = 1
            # 从超买区向下突破
            elif rsi[i-1] >= overbought and rsi[i] < overbought:
                signals[i] = -1

        return signals


class BollingerBands:
    """布林带指标"""

    @staticmethod
    def calculate(
        data: Union[List[float], pd.Series, np.ndarray],
        period: int = 20,
        num_std: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算布林带

        Args:
            data: 收盘价数据
            period: 计算周期，默认 20
            num_std: 标准差倍数，默认 2

        Returns:
            (upper, middle, lower) 三条线
            - upper: 上轨 (中轨 + 2倍标准差)
            - middle: 中轨 (SMA)
            - lower: 下轨 (中轨 - 2倍标准差)
        """
        series = pd.Series(data)

        # 中轨 (SMA)
        middle = series.rolling(window=period, min_periods=period).mean()

        # 标准差
        std = series.rolling(window=period, min_periods=period).std()

        # 上轨和下轨
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)

        return upper.values, middle.values, lower.values

    @staticmethod
    def signal(
        price: np.ndarray,
        upper: np.ndarray,
        lower: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        生成布林带交易信号和位置信息

        Returns:
            (signals, positions)
            - signals: 1 买入, -1 卖出, 0 无信号
            - positions: 价格相对于布林带的位置 (-1 到 1)
        """
        signals = np.zeros(len(price))
        positions = np.zeros(len(price))

        for i in range(1, len(price)):
            # 计算位置 (0 中轨, 1 上轨, -1 下轨)
            band_width = upper[i] - lower[i]
            if band_width > 0:
                positions[i] = 2 * (price[i] - lower[i]) / band_width - 1

            # 信号生成
            if price[i-1] <= lower[i-1] and price[i] > lower[i]:
                # 从下轨反弹
                signals[i] = 1
            elif price[i-1] >= upper[i-1] and price[i] < upper[i]:
                # 从上轨回落
                signals[i] = -1

        return signals, positions


class KDJ:
    """KDJ 随机指标"""

    @staticmethod
    def calculate(
        high: Union[List[float], pd.Series, np.ndarray],
        low: Union[List[float], pd.Series, np.ndarray],
        close: Union[List[float], pd.Series, np.ndarray],
        n: int = 9,
        m1: int = 3,
        m2: int = 3
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算 KDJ 指标

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            n: RSV 周期，默认 9
            m1: K 平滑因子，默认 3
            m2: D 平滑因子，默认 3

        Returns:
            (k, d, j) 三条线
        """
        high_series = pd.Series(high)
        low_series = pd.Series(low)
        close_series = pd.Series(close)

        # 计算 RSV
        lowest_low = low_series.rolling(window=n, min_periods=n).min()
        highest_high = high_series.rolling(window=n, min_periods=n).max()

        rsv = 100 * (close_series - lowest_low) / (highest_high - lowest_low)
        rsv = rsv.fillna(50)  # 填充缺失值

        # 计算 K 和 D
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()

        # 计算 J
        j = 3 * k - 2 * d

        return k.values, d.values, j.values

    @staticmethod
    def signal(k: np.ndarray, d: np.ndarray, j: np.ndarray) -> np.ndarray:
        """
        生成 KDJ 交易信号

        Returns:
            1: 金叉 (K 上穿 D 且 J < 20)
            -1: 死叉 (K 下穿 D 且 J > 80)
            0: 无信号
        """
        signals = np.zeros(len(k))

        for i in range(1, len(k)):
            if k[i-1] <= d[i-1] and k[i] > d[i] and j[i] < 20:
                # 低位金叉
                signals[i] = 1
            elif k[i-1] >= d[i-1] and k[i] < d[i] and j[i] > 80:
                # 高位死叉
                signals[i] = -1

        return signals


class ATR:
    """ATR 真实波幅指标"""

    @staticmethod
    def calculate(
        high: Union[List[float], pd.Series, np.ndarray],
        low: Union[List[float], pd.Series, np.ndarray],
        close: Union[List[float], pd.Series, np.ndarray],
        period: int = 14
    ) -> np.ndarray:
        """
        计算 ATR (Average True Range)

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            period: 计算周期，默认 14

        Returns:
            ATR 值数组
        """
        high_series = pd.Series(high)
        low_series = pd.Series(low)
        close_series = pd.Series(close)

        # 计算 True Range
        tr1 = high_series - low_series
        tr2 = abs(high_series - close_series.shift(1))
        tr3 = abs(low_series - close_series.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 计算 ATR
        atr = tr.rolling(window=period, min_periods=period).mean()

        return atr.values


class OBV:
    """OBV 能量潮指标"""

    @staticmethod
    def calculate(
        close: Union[List[float], pd.Series, np.ndarray],
        volume: Union[List[float], pd.Series, np.ndarray]
    ) -> np.ndarray:
        """
        计算 OBV (On Balance Volume)

        Args:
            close: 收盘价
            volume: 成交量

        Returns:
            OBV 值数组
        """
        close_series = pd.Series(close)
        volume_series = pd.Series(volume)

        # 计算价格变化方向
        price_change = close_series.diff()

        # 根据价格变化计算 OBV
        obv = pd.Series(index=close_series.index, dtype=float)
        obv.iloc[0] = volume_series.iloc[0]

        for i in range(1, len(close_series)):
            if price_change.iloc[i] > 0:
                obv.iloc[i] = obv.iloc[i-1] + volume_series.iloc[i]
            elif price_change.iloc[i] < 0:
                obv.iloc[i] = obv.iloc[i-1] - volume_series.iloc[i]
            else:
                obv.iloc[i] = obv.iloc[i-1]

        return obv.values


class IndicatorEngine:
    """指标计算引擎 - 批量计算多个指标"""

    def __init__(self):
        self.ma = MovingAverage()
        self.macd = MACD()
        self.rsi = RSI()
        self.boll = BollingerBands()
        self.kdj = KDJ()
        self.atr = ATR()
        self.obv = OBV()

    def calculate_all(
        self,
        df: pd.DataFrame,
        indicators: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        批量计算多个指标

        Args:
            df: 包含 open, high, low, close, volume 列的 DataFrame
            indicators: 要计算的指标列表，None 则计算全部

        Returns:
            添加了指标列的 DataFrame
        """
        if indicators is None:
            indicators = ['ma', 'ema', 'macd', 'rsi', 'boll', 'kdj', 'atr', 'obv']

        result = df.copy()
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values

        try:
            # 移动平均线
            if 'ma' in indicators:
                result['ma5'] = self.ma.sma(close, 5)
                result['ma10'] = self.ma.sma(close, 10)
                result['ma20'] = self.ma.sma(close, 20)
                result['ma60'] = self.ma.sma(close, 60)

            # 指数移动平均
            if 'ema' in indicators:
                result['ema12'] = self.ma.ema(close, 12)
                result['ema26'] = self.ma.ema(close, 26)

            # MACD
            if 'macd' in indicators:
                dif, dea, bar = self.macd.calculate(close)
                result['macd_dif'] = dif
                result['macd_dea'] = dea
                result['macd_bar'] = bar

            # RSI
            if 'rsi' in indicators:
                result['rsi6'] = self.rsi.calculate(close, 6)
                result['rsi12'] = self.rsi.calculate(close, 12)
                result['rsi24'] = self.rsi.calculate(close, 24)

            # 布林带
            if 'boll' in indicators:
                upper, middle, lower = self.boll.calculate(close)
                result['boll_upper'] = upper
                result['boll_middle'] = middle
                result['boll_lower'] = lower

            # KDJ
            if 'kdj' in indicators:
                k, d, j = self.kdj.calculate(high, low, close)
                result['kdj_k'] = k
                result['kdj_d'] = d
                result['kdj_j'] = j

            # ATR
            if 'atr' in indicators:
                result['atr14'] = self.atr.calculate(high, low, close, 14)

            # OBV
            if 'obv' in indicators:
                result['obv'] = self.obv.calculate(close, volume)

        except Exception as e:
            logger.error(f"指标计算失败: {e}")
            raise

        return result

    def get_signals(self, df: pd.DataFrame) -> dict:
        """
        获取所有指标的交易信号

        Returns:
            信号字典，包含各指标的最新信号
        """
        signals = {}

        # MACD 信号
        if 'macd_dif' in df.columns and 'macd_dea' in df.columns:
            macd_signals = self.macd.signal(
                df['macd_dif'].values,
                df['macd_dea'].values
            )
            signals['macd'] = int(macd_signals[-1])

        # RSI 信号
        if 'rsi6' in df.columns:
            rsi_signals = self.rsi.signal(df['rsi6'].values)
            signals['rsi'] = int(rsi_signals[-1])

        # 布林带信号
        if 'boll_upper' in df.columns:
            boll_signals, positions = self.boll.signal(
                df['close'].values,
                df['boll_upper'].values,
                df['boll_lower'].values
            )
            signals['boll'] = int(boll_signals[-1])
            signals['boll_position'] = float(positions[-1])

        # KDJ 信号
        if 'kdj_k' in df.columns:
            kdj_signals = self.kdj.signal(
                df['kdj_k'].values,
                df['kdj_d'].values,
                df['kdj_j'].values
            )
            signals['kdj'] = int(kdj_signals[-1])

        return signals
