"""
历史数据管理器

职责：
- 历史K线数据存储和检索
- 数据缓存管理
- 数据更新和合并
- 数据导出
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import pickle
import gzip

from src.market_data.models import KLineData, TickData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class StorageBackend(str, Enum):
    """存储后端类型"""
    MEMORY = "memory"
    DATABASE = "database"
    FILE = "file"
    REDIS = "redis"


class DataUpdatePolicy(str, Enum):
    """数据更新策略"""
    APPEND = "append"      # 追加新数据
    MERGE = "merge"        # 合并（更新重复，保留旧数据）
    REPLACE = "replace"    # 完全替换
    UPSERT = "upsert"      # 更新或插入


class CacheManager:
    """
    缓存管理器

    简单的内存缓存，支持TTL和LRU淘汰
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
            ttl_seconds: 默认TTL（秒）
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Any] = {}
        _access_time: Dict[str, datetime] = {}
        self._expire_time: Dict[str, datetime] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        if key not in self._cache:
            return None

        # 检查是否过期
        if key in self._expire_time:
            if datetime.now() > self._expire_time[key]:
                self.delete(key)
                return None

        # 更新访问时间
        self._access_time[key] = datetime.now()
        return self._cache[key]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: 自定义TTL（秒）
        """
        # 检查是否需要淘汰
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_lru()

        self._cache[key] = value
        self._access_time[key] = datetime.now()

        # 设置过期时间
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        self._expire_time[key] = datetime.now() + timedelta(seconds=ttl)

    def delete(self, key: str) -> None:
        """删除缓存项"""
        self._cache.pop(key, None)
        self._access_time.pop(key, None)
        self._expire_time.pop(key, None)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._access_time.clear()
        self._expire_time.clear()

    def keys(self) -> List[str]:
        """获取所有键"""
        return list(self._cache.keys())

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)

    def _evict_lru(self) -> None:
        """淘汰最久未使用的项"""
        if not self._access_time:
            return

        # 找到最久未访问的键
        lru_key = min(self._access_time.keys(), key=lambda k: self._access_time[k])
        self.delete(lru_key)


class DataStorage:
    """
    数据存储

    管理数据的持久化存储
    """

    def __init__(self, backend: StorageBackend = StorageBackend.MEMORY):
        """
        初始化存储

        Args:
            backend: 存储后端类型
        """
        self.backend = backend
        # 内存存储
        self._memory_store: Dict[str, List[KLineData]] = {}
        self._tick_store: Dict[str, TickData] = {}

    def _make_key(self, symbol: str, period: str) -> str:
        """生成存储键"""
        return f"{symbol}:{period}"

    def store_klines(self, symbol: str, period: str, klines: List[KLineData]) -> None:
        """
        存储K线数据

        Args:
            symbol: 股票代码
            period: 周期
            klines: K线数据列表
        """
        key = self._make_key(symbol, period)

        if self.backend == StorageBackend.MEMORY:
            # 按时间戳排序存储
            sorted_klines = sorted(klines, key=lambda k: k.timestamp)
            self._memory_store[key] = sorted_klines
        else:
            # TODO: 实现数据库/文件/Redis存储
            pass

        logger.debug(f"存储K线数据: {symbol} {period}, {len(klines)}条")

    def get_klines(
        self,
        symbol: str,
        period: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[KLineData]:
        """
        获取K线数据

        Args:
            symbol: 股票代码
            period: 周期
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            K线数据列表
        """
        key = self._make_key(symbol, period)

        if self.backend == StorageBackend.MEMORY:
            klines = self._memory_store.get(key, [])

            # 过滤日期范围
            if start_date:
                klines = [k for k in klines if k.timestamp >= start_date]
            if end_date:
                klines = [k for k in klines if k.timestamp <= end_date]

            return klines
        else:
            # TODO: 实现其他后端
            return []

    def store_tick(self, symbol: str, tick: TickData) -> None:
        """
        存储Tick数据

        Args:
            symbol: 股票代码
            tick: Tick数据
        """
        if self.backend == StorageBackend.MEMORY:
            self._tick_store[symbol] = tick
        else:
            # TODO: 实现其他后端
            pass

    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """
        获取最新Tick数据

        Args:
            symbol: 股票代码

        Returns:
            Tick数据或None
        """
        if self.backend == StorageBackend.MEMORY:
            return self._tick_store.get(symbol)
        else:
            # TODO: 实现其他后端
            return None

    def delete_klines(self, symbol: str, period: str) -> None:
        """删除K线数据"""
        key = self._make_key(symbol, period)
        if self.backend == StorageBackend.MEMORY:
            self._memory_store.pop(key, None)

    def has_data(self, symbol: str, period: str) -> bool:
        """检查是否有数据"""
        key = self._make_key(symbol, period)
        if self.backend == StorageBackend.MEMORY:
            return key in self._memory_store and len(self._memory_store[key]) > 0
        return False

    def get_date_range(self, symbol: str, period: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取数据日期范围

        Returns:
            (开始日期, 结束日期)
        """
        klines = self.get_klines(symbol, period)
        if not klines:
            return None, None
        return klines[0].timestamp, klines[-1].timestamp


class HistoricalDataManager:
    """
    历史数据管理器

    提供历史数据的统一管理接口
    """

    def __init__(self, session=None, backend: StorageBackend = StorageBackend.MEMORY):
        """
        初始化管理器

        Args:
            session: 数据库会话
            backend: 存储后端
        """
        self.session = session
        self.storage = DataStorage(backend)
        self.cache = CacheManager()

    async def save_klines(
        self,
        symbol: str,
        period: str,
        klines: List[KLineData]
    ) -> None:
        """
        保存K线数据

        Args:
            symbol: 股票代码
            period: 周期
            klines: K线数据列表
        """
        # 存储到持久化存储
        self.storage.store_klines(symbol, period, klines)

        # 更新缓存
        cache_key = f"kline:{symbol}:{period}"
        self.cache.set(cache_key, klines)

        logger.info(f"保存K线数据: {symbol} {period}, {len(klines)}条")

    async def get_klines(
        self,
        symbol: str,
        period: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[KLineData]:
        """
        获取K线数据

        Args:
            symbol: 股票代码
            period: 周期
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            K线数据列表
        """
        cache_key = f"kline:{symbol}:{period}"

        # 尝试从缓存获取
        cached = self.cache.get(cache_key)
        if cached:
            # 过滤日期范围
            result = cached
            if start_date:
                result = [k for k in result if k.timestamp >= start_date]
            if end_date:
                result = [k for k in result if k.timestamp <= end_date]
            return result

        # 从存储获取
        klines = self.storage.get_klines(symbol, period, start_date, end_date)

        # 更新缓存
        if klines:
            self.cache.set(cache_key, self.storage.get_klines(symbol, period))

        return klines

    async def update_klines(
        self,
        symbol: str,
        period: str,
        new_klines: List[KLineData],
        policy: DataUpdatePolicy = DataUpdatePolicy.MERGE
    ) -> None:
        """
        更新K线数据

        Args:
            symbol: 股票代码
            period: 周期
            new_klines: 新数据
            policy: 更新策略
        """
        existing = self.storage.get_klines(symbol, period)

        if policy == DataUpdatePolicy.REPLACE:
            merged = new_klines
        elif policy == DataUpdatePolicy.APPEND:
            merged = existing + new_klines
        elif policy == DataUpdatePolicy.MERGE or policy == DataUpdatePolicy.UPSERT:
            # 创建时间戳索引
            existing_dict = {k.timestamp: k for k in existing}
            for new_k in new_klines:
                existing_dict[new_k.timestamp] = new_k
            merged = list(existing_dict.values())
        else:
            merged = new_klines

        # 排序
        merged = sorted(merged, key=lambda k: k.timestamp)

        # 保存
        await self.save_klines(symbol, period, merged)

    async def get_latest_bars(
        self,
        symbol: str,
        period: str,
        n: int = 100
    ) -> List[KLineData]:
        """
        获取最新N条K线

        Args:
            symbol: 股票代码
            period: 周期
            n: 条数

        Returns:
            K线数据列表
        """
        klines = await self.get_klines(symbol, period)
        return klines[-n:] if len(klines) > n else klines

    async def export_to_csv(
        self,
        symbol: str,
        period: str,
        output_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> None:
        """
        导出数据到CSV

        Args:
            symbol: 股票代码
            period: 周期
            output_path: 输出路径
            start_date: 开始日期
            end_date: 结束日期
        """
        klines = await self.get_klines(symbol, period, start_date, end_date)

        import csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'open', 'high', 'low', 'close', 'volume', 'amount', 'symbol'])

            for k in klines:
                writer.writerow([
                    k.timestamp.isoformat(),
                    float(k.open),
                    float(k.high),
                    float(k.low),
                    float(k.close),
                    k.volume,
                    float(k.amount) if k.amount else '',
                    k.symbol
                ])

        logger.info(f"导出CSV: {output_path}, {len(klines)}条")

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")

    async def get_data_info(self, symbol: str, period: str) -> Optional[Dict[str, Any]]:
        """
        获取数据信息

        Args:
            symbol: 股票代码
            period: 周期

        Returns:
            数据信息字典
        """
        if not self.storage.has_data(symbol, period):
            return None

        klines = self.storage.get_klines(symbol, period)
        start, end = self.storage.get_date_range(symbol, period)

        return {
            "symbol": symbol,
            "period": period,
            "count": len(klines),
            "start_date": start,
            "end_date": end,
            "has_data": len(klines) > 0,
        }

    async def delete_symbol_data(self, symbol: str) -> None:
        """
        删除标的的所有数据

        Args:
            symbol: 股票代码
        """
        # 获取所有周期
        periods = ["1m", "5m", "15m", "1h", "1d", "1w", "1M"]

        for period in periods:
            self.storage.delete_klines(symbol, period)
            cache_key = f"kline:{symbol}:{period}"
            self.cache.delete(cache_key)

        logger.info(f"删除数据: {symbol}")


# 数据压缩工具函数
def compress_klines(klines: List[KLineData]) -> bytes:
    """
    压缩K线数据

    Args:
        klines: K线数据列表

    Returns:
        压缩后的字节数据
    """
    pickled = pickle.dumps(klines)
    return gzip.compress(pickled)


def decompress_klines(compressed: bytes) -> List[KLineData]:
    """
    解压K线数据

    Args:
        compressed: 压缩后的字节数据

    Returns:
        K线数据列表
    """
    pickled = gzip.decompress(compressed)
    return pickle.loads(pickled)
