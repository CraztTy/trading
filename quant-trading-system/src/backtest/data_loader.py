"""
回测数据加载器

提供历史行情数据的加载和管理
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Union
import asyncio

import pandas as pd

from src.market_data.models import KLineData, TickData
from src.strategy.base import BarData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass
class HistoryDataRequest:
    """历史数据请求"""
    symbol: str
    start_date: datetime
    end_date: datetime
    period: str = "1d"  # 1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M
    adjusted: bool = True  # 是否复权


class HistoryDataLoader:
    """
    历史数据加载器

    支持：
    - 从 AKShare 加载历史数据
    - 从本地数据库加载
    - 数据缓存和合并
    """

    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}
        self._akshare_available = self._check_akshare()

    def _check_akshare(self) -> bool:
        """检查 AKShare 是否可用"""
        try:
            import akshare as ak
            return True
        except ImportError:
            logger.warning("AKShare 未安装，无法加载在线历史数据")
            return False

    async def load_bars(
        self,
        request: HistoryDataRequest
    ) -> List[BarData]:
        """
        加载历史 K 线数据

        Args:
            request: 数据请求参数

        Returns:
            BarData 列表
        """
        cache_key = f"{request.symbol}_{request.period}_{request.start_date.date()}_{request.end_date.date()}"

        # 检查缓存
        if cache_key in self._cache:
            logger.debug(f"使用缓存数据: {cache_key}")
            return self._df_to_bars(request.symbol, self._cache[cache_key])

        # 从 AKShare 加载
        if self._akshare_available:
            df = await self._load_from_akshare(request)
            # 如果 AKShare 失败，回退到模拟数据
            if df is None or df.empty:
                logger.info(f"AKShare 加载失败，使用模拟数据: {request.symbol}")
                df = self._generate_mock_data(request)
        else:
            # 生成模拟数据（用于测试）
            df = self._generate_mock_data(request)

        if df is None or df.empty:
            logger.warning(f"未找到历史数据: {request.symbol}")
            return []

        # 缓存数据
        self._cache[cache_key] = df

        return self._df_to_bars(request.symbol, df)

    async def _load_from_akshare(
        self,
        request: HistoryDataRequest
    ) -> Optional[pd.DataFrame]:
        """从 AKShare 加载数据"""
        try:
            import akshare as ak

            # 解析代码
            code, exchange = self._parse_symbol(request.symbol)

            # 转换周期
            period_map = {
                '1d': 'daily',
                '1w': 'weekly',
                '1M': 'monthly',
            }
            ak_period = period_map.get(request.period, 'daily')

            # 日期格式
            start_str = request.start_date.strftime('%Y%m%d')
            end_str = request.end_date.strftime('%Y%m%d')

            # 异步执行（AKShare 是同步的）
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                lambda: ak.stock_zh_a_hist(
                    symbol=code,
                    period=ak_period,
                    start_date=start_str,
                    end_date=end_str,
                    adjust="qfq" if request.adjusted else ""
                )
            )

            return df

        except Exception as e:
            logger.error(f"从 AKShare 加载数据失败: {e}")
            return None

    def _generate_mock_data(
        self,
        request: HistoryDataRequest
    ) -> pd.DataFrame:
        """生成模拟数据（用于测试）"""
        import numpy as np

        # 生成日期范围
        dates = pd.date_range(
            start=request.start_date,
            end=request.end_date,
            freq='D'
        )

        # 排除周末
        dates = dates[dates.dayofweek < 5]

        if len(dates) == 0:
            return pd.DataFrame()

        # 生成随机价格数据
        np.random.seed(42)
        base_price = 10.0
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = base_price * np.exp(np.cumsum(returns))

        # 生成 OHLCV
        df = pd.DataFrame({
            '日期': dates.strftime('%Y-%m-%d'),
            '开盘': prices * (1 + np.random.normal(0, 0.01, len(dates))),
            '收盘': prices,
            '最高': prices * (1 + abs(np.random.normal(0, 0.02, len(dates)))),
            '最低': prices * (1 - abs(np.random.normal(0, 0.02, len(dates)))),
            '成交量': np.random.randint(1000000, 10000000, len(dates)),
            '成交额': np.random.randint(10000000, 100000000, len(dates)),
        })

        return df

    def _df_to_bars(self, symbol: str, df: pd.DataFrame) -> List[BarData]:
        """DataFrame 转换为 BarData 列表"""
        bars = []

        for _, row in df.iterrows():
            try:
                # 解析日期
                if '日期' in row:
                    date_val = row['日期']
                    if isinstance(date_val, str):
                        timestamp = datetime.strptime(date_val, '%Y-%m-%d')
                    else:
                        # 已经是 datetime 或 Timestamp
                        timestamp = pd.to_datetime(date_val)
                else:
                    timestamp = row.name if hasattr(row, 'name') else datetime.now()

                bar = BarData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=Decimal(str(row.get('开盘', row.get('open', 0)))),
                    high=Decimal(str(row.get('最高', row.get('high', 0)))),
                    low=Decimal(str(row.get('最低', row.get('low', 0)))),
                    close=Decimal(str(row.get('收盘', row.get('close', 0)))),
                    volume=int(row.get('成交量', row.get('volume', 0))),
                    amount=Decimal(str(row.get('成交额', row.get('amount', 0)))),
                    period="1d"
                )
                bars.append(bar)
            except Exception as e:
                logger.warning(f"转换 BarData 失败: {e}")
                continue

        return bars

    def _parse_symbol(self, symbol: str) -> tuple:
        """解析标的代码"""
        if '.' in symbol:
            code, exchange = symbol.split('.')
            return code, exchange
        return symbol, "SZ"

    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
        logger.info("历史数据缓存已清除")
