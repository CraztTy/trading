"""
工部 - 数据清洗

职责：
- K线数据清洗
- 时序排序
- 缺失值处理
- 数据对齐
- 技术指标计算
"""
from typing import Optional
import pandas as pd
import numpy as np
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class GongBuWorks:
    """工部：数据清洗中心"""

    def __init__(self, config: dict):
        self.config = config

    def clean_klines(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清洗K线数据

        Args:
            df: 原始K线DataFrame

        Returns:
            清洗后的DataFrame
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 复制数据
        cleaned = df.copy()

        # 确保必要的列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in cleaned.columns:
                logger.error(f"缺少必要列: {col}")
                return pd.DataFrame()

        # 删除缺失值
        cleaned = cleaned.dropna(subset=required_cols)

        # 数据类型转换
        for col in ['open', 'high', 'low', 'close']:
            cleaned[col] = pd.to_numeric(cleaned[col], errors='coerce')

        cleaned['volume'] = pd.to_numeric(cleaned['volume'], errors='coerce')

        # 删除无效数据
        cleaned = cleaned[
            (cleaned['open'] > 0) &
            (cleaned['high'] > 0) &
            (cleaned['low'] > 0) &
            (cleaned['close'] > 0) &
            (cleaned['volume'] >= 0)
        ]

        # 修复OHLC关系
        cleaned = self._fix_ohlc(cleaned)

        # 按时间排序
        if 'datetime' in cleaned.columns:
            cleaned = cleaned.sort_values('datetime')
        elif isinstance(cleaned.index, pd.DatetimeIndex):
            cleaned = cleaned.sort_index()

        return cleaned

    def _fix_ohlc(self, df: pd.DataFrame) -> pd.DataFrame:
        """修复OHLC关系"""
        # 确保 high >= max(open, close) >= min(open, close) >= low
        df['high'] = df[['open', 'high', 'close']].max(axis=1)
        df['low'] = df[['open', 'low', 'close']].min(axis=1)
        return df

    def fill_missing_bars(
        self,
        df: pd.DataFrame,
        freq: str = '1min'
    ) -> pd.DataFrame:
        """
        填充缺失的K线

        Args:
            df: K线数据
            freq: 频率

        Returns:
            填充后的DataFrame
        """
        if df.empty:
            return df

        # 重新索引
        if isinstance(df.index, pd.DatetimeIndex):
            full_range = pd.date_range(
                start=df.index.min(),
                end=df.index.max(),
                freq=freq
            )
            df = df.reindex(full_range)

            # 前向填充
            df[['open', 'high', 'low', 'close']] = df[
                ['open', 'high', 'low', 'close']
            ].fillna(method='ffill')

            # 成交量填0
            df['volume'] = df['volume'].fillna(0)

        return df

    def align_data(
        self,
        data_dict: dict
    ) -> pd.DataFrame:
        """
        对齐多只股票数据

        Args:
            data_dict: {code: DataFrame}

        Returns:
            对齐后的DataFrame
        """
        # 简化的对齐实现
        aligned = []
        for code, df in data_dict.items():
            df_copy = df.copy()
            df_copy['code'] = code
            aligned.append(df_copy)

        if aligned:
            return pd.concat(aligned, ignore_index=True)
        return pd.DataFrame()

    def add_technical_indicators(
        self,
        df: pd.DataFrame,
        indicators: list = None
    ) -> pd.DataFrame:
        """
        添加技术指标

        Args:
            df: K线数据
            indicators: 指标列表

        Returns:
            添加指标后的DataFrame
        """
        if df.empty:
            return df

        indicators = indicators or ['sma', 'ema']

        if 'sma' in indicators:
            df['sma_5'] = df['close'].rolling(window=5).mean()
            df['sma_10'] = df['close'].rolling(window=10).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()

        if 'ema' in indicators:
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()

        if 'rsi' in indicators:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

        if 'macd' in indicators:
            ema_12 = df['close'].ewm(span=12).mean()
            ema_26 = df['close'].ewm(span=26).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']

        return df
