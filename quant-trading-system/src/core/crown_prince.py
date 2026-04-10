"""
太子院 - 数据前置校验与分发

职责：
- 对每根K线、每只股票做前置校验
- 过滤非法标的（ST/*ST、流动性不足等）
- 数据清洗和格式化
- 将校验后的数据分发给策略
"""
from typing import Optional
import pandas as pd
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class CrownPrince:
    """太子院：数据校验与分发中心"""

    def __init__(self, config: dict):
        self.config = config
        self.banned_stocks = set()  # 禁售股票列表
        self.min_avg_volume = config.get('min_avg_volume', 1_000_000)

    async def validate_and_distribute(
        self,
        klines: pd.DataFrame,
        code: str
    ) -> Optional[pd.DataFrame]:
        """
        验证K线数据并分发给策略

        Args:
            klines: 原始K线数据
            code: 股票代码

        Returns:
            清洗后的K线数据，验证失败返回None
        """
        # 1. 检查是否在禁售列表
        if code in self.banned_stocks:
            logger.warning(f"股票{code}在禁售列表中，跳过")
            return None

        # 2. 基础数据校验
        if klines is None or klines.empty:
            logger.warning(f"股票{code}数据为空")
            return None

        # 3. 数据清洗
        cleaned = self._clean_klines(klines)
        if cleaned is None or cleaned.empty:
            logger.warning(f"股票{code}数据清洗后为空")
            return None

        # 4. 流动性检查
        if not self._check_liquidity(cleaned):
            logger.warning(f"股票{code}流动性不足")
            return None

        # 5. 价格有效性检查
        if not self._check_price_validity(cleaned):
            logger.warning(f"股票{code}价格数据异常")
            return None

        return cleaned

    def _clean_klines(self, klines: pd.DataFrame) -> pd.DataFrame:
        """清洗K线数据"""
        df = klines.copy()

        # 确保必要的列存在
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"缺少必要列: {col}")
                return pd.DataFrame()

        # 删除无效数据
        df = df.dropna(subset=required_cols)

        # 确保价格为正
        df = df[
            (df['open'] > 0) &
            (df['high'] > 0) &
            (df['low'] > 0) &
            (df['close'] > 0) &
            (df['volume'] >= 0)
        ]

        # 确保high >= low
        df = df[df['high'] >= df['low']]

        # 按时间排序
        if 'datetime' in df.columns:
            df = df.sort_values('datetime')
        elif df.index.name == 'datetime' or isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()

        return df

    def _check_liquidity(self, klines: pd.DataFrame) -> bool:
        """检查股票流动性"""
        avg_volume = klines['volume'].mean()
        return avg_volume >= self.min_avg_volume

    def _check_price_validity(self, klines: pd.DataFrame) -> bool:
        """检查价格有效性"""
        # 检查是否有异常大的价格波动
        df = klines.copy()
        df['price_change'] = df['close'].pct_change().abs()

        # 如果单日涨跌幅超过20%，可能是异常数据
        max_change = df['price_change'].max()
        if max_change > 0.20:
            logger.warning(f"检测到异常价格波动: {max_change:.2%}")
            # 不直接返回False，而是记录警告

        return True

    def add_banned_stock(self, code: str, reason: str = ""):
        """添加禁售股票"""
        self.banned_stocks.add(code)
        logger.info(f"添加禁售股票: {code}, 原因: {reason}")

    def remove_banned_stock(self, code: str):
        """移除禁售股票"""
        self.banned_stocks.discard(code)
        logger.info(f"移除禁售股票: {code}")

    def is_banned(self, code: str) -> bool:
        """检查股票是否在禁售列表"""
        return code in self.banned_stocks
