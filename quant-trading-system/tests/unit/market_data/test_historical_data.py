"""
历史数据管理器测试

测试覆盖：
1. 数据存储和检索
2. 数据更新和合并
3. 缓存管理
4. 数据导出
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.market_data.historical import (
    HistoricalDataManager, DataStorage, CacheManager,
    DataUpdatePolicy, StorageBackend
)
from src.market_data.models import KLineData, TickData


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_klines():
    """样本K线数据"""
    base_time = datetime(2024, 1, 1)
    klines = []
    for i in range(10):
        klines.append(KLineData(
            symbol="000001.SZ",
            timestamp=base_time + timedelta(days=i),
            open=Decimal(str(10 + i * 0.1)),
            high=Decimal(str(11 + i * 0.1)),
            low=Decimal(str(9 + i * 0.1)),
            close=Decimal(str(10.5 + i * 0.1)),
            volume=10000 + i * 1000,
            amount=Decimal(str(100000 + i * 10000)),
            period="1d"
        ))
    return klines


class TestStorageBackend:
    """存储后端枚举测试"""

    def test_backend_values(self):
        """测试后端值"""
        assert StorageBackend.MEMORY.value == "memory"
        assert StorageBackend.DATABASE.value == "database"
        assert StorageBackend.FILE.value == "file"
        assert StorageBackend.REDIS.value == "redis"


class TestDataUpdatePolicy:
    """数据更新策略测试"""

    def test_policy_values(self):
        """测试策略值"""
        assert DataUpdatePolicy.APPEND.value == "append"
        assert DataUpdatePolicy.MERGE.value == "merge"
        assert DataUpdatePolicy.REPLACE.value == "replace"
        assert DataUpdatePolicy.UPSERT.value == "upsert"


class TestCacheManager:
    """缓存管理器测试"""

    @pytest.fixture
    def cache(self):
        return CacheManager(max_size=100, ttl_seconds=60)

    def test_cache_initialization(self, cache):
        """测试缓存初始化"""
        assert cache.max_size == 100
        assert cache.ttl_seconds == 60

    def test_set_and_get(self, cache):
        """测试设置和获取"""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent(self, cache):
        """测试获取不存在的键"""
        assert cache.get("nonexistent") is None

    def test_cache_expiration(self, cache):
        """测试缓存过期"""
        cache.set("key1", "value1", ttl_seconds=0.001)
        import time
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_cache_eviction(self):
        """测试缓存淘汰"""
        cache = CacheManager(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        cache.set("key4", "value4")  # 应该淘汰key1

        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_cache_clear(self, cache):
        """测试清空缓存"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_keys(self, cache):
        """测试获取所有键"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        keys = cache.keys()
        assert "key1" in keys
        assert "key2" in keys

    def test_cache_size(self, cache):
        """测试缓存大小"""
        assert cache.size() == 0
        cache.set("key1", "value1")
        assert cache.size() == 1


class TestDataStorage:
    """数据存储测试"""

    @pytest.fixture
    def storage(self):
        return DataStorage(backend=StorageBackend.MEMORY)

    def test_storage_initialization(self, storage):
        """测试存储初始化"""
        assert storage.backend == StorageBackend.MEMORY

    def test_store_kline_data(self, storage, sample_klines):
        """测试存储K线数据"""
        storage.store_klines("000001.SZ", "1d", sample_klines)

        retrieved = storage.get_klines("000001.SZ", "1d")
        assert len(retrieved) == 10

    def test_store_tick_data(self, storage):
        """测试存储Tick数据"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=1000,
            source="test"
        )

        storage.store_tick("000001.SZ", tick)

        retrieved = storage.get_latest_tick("000001.SZ")
        assert retrieved is not None
        assert retrieved.price == Decimal("10.50")

    def test_get_klines_with_date_range(self, storage, sample_klines):
        """测试按日期范围获取K线"""
        storage.store_klines("000001.SZ", "1d", sample_klines)

        start_date = datetime(2024, 1, 3)
        end_date = datetime(2024, 1, 7)

        retrieved = storage.get_klines(
            "000001.SZ", "1d",
            start_date=start_date,
            end_date=end_date
        )

        assert len(retrieved) == 5

    def test_delete_klines(self, storage, sample_klines):
        """测试删除K线数据"""
        storage.store_klines("000001.SZ", "1d", sample_klines)

        storage.delete_klines("000001.SZ", "1d")

        retrieved = storage.get_klines("000001.SZ", "1d")
        assert len(retrieved) == 0

    def test_has_data(self, storage, sample_klines):
        """测试数据存在性检查"""
        assert not storage.has_data("000001.SZ", "1d")

        storage.store_klines("000001.SZ", "1d", sample_klines)

        assert storage.has_data("000001.SZ", "1d")

    def test_get_date_range(self, storage, sample_klines):
        """测试获取数据日期范围"""
        storage.store_klines("000001.SZ", "1d", sample_klines)

        start, end = storage.get_date_range("000001.SZ", "1d")

        assert start == datetime(2024, 1, 1)
        assert end == datetime(2024, 1, 10)


class TestHistoricalDataManager:
    """历史数据管理器测试"""

    @pytest.fixture
    def manager(self, mock_db_session):
        return HistoricalDataManager(session=mock_db_session)

    def test_manager_initialization(self, manager):
        """测试管理器初始化"""
        assert manager.session is not None
        assert manager.cache is not None
        assert manager.storage is not None

    @pytest.mark.asyncio
    async def test_save_historical_klines(self, manager, sample_klines):
        """测试保存历史K线"""
        await manager.save_klines("000001.SZ", "1d", sample_klines)

        # 验证数据已缓存
        assert manager.cache.get("kline:000001.SZ:1d") is not None

    @pytest.mark.asyncio
    async def test_get_historical_klines_cached(self, manager, sample_klines):
        """测试获取缓存的K线"""
        # 先存入缓存
        manager.cache.set("kline:000001.SZ:1d", sample_klines)

        retrieved = await manager.get_klines("000001.SZ", "1d")

        assert len(retrieved) == 10

    @pytest.mark.asyncio
    async def test_update_klines_append(self, manager):
        """测试追加更新K线"""
        old_klines = [
            KLineData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 1),
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10.5"),
                volume=10000,
                period="1d"
            )
        ]

        new_klines = [
            KLineData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 2),
                open=Decimal("10.5"),
                high=Decimal("11.5"),
                low=Decimal("9.5"),
                close=Decimal("11"),
                volume=11000,
                period="1d"
            )
        ]

        await manager.save_klines("000001.SZ", "1d", old_klines)
        await manager.update_klines(
            "000001.SZ", "1d", new_klines,
            policy=DataUpdatePolicy.APPEND
        )

        all_klines = await manager.get_klines("000001.SZ", "1d")
        assert len(all_klines) == 2

    @pytest.mark.asyncio
    async def test_update_klines_merge(self, manager):
        """测试合并更新K线"""
        # 创建有重叠的数据
        old_klines = [
            KLineData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 1),
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10.5"),
                volume=10000,
                period="1d"
            ),
            KLineData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 2),
                open=Decimal("10.5"),
                high=Decimal("11.5"),
                low=Decimal("9.5"),
                close=Decimal("11"),
                volume=11000,
                period="1d"
            )
        ]

        # 更新的第二条数据
        updated_klines = [
            KLineData(
                symbol="000001.SZ",
                timestamp=datetime(2024, 1, 2),
                open=Decimal("10.6"),  # 更新后的值
                high=Decimal("11.6"),
                low=Decimal("9.6"),
                close=Decimal("11.1"),
                volume=12000,
                period="1d"
            )
        ]

        await manager.save_klines("000001.SZ", "1d", old_klines)
        await manager.update_klines(
            "000001.SZ", "1d", updated_klines,
            policy=DataUpdatePolicy.MERGE
        )

        all_klines = await manager.get_klines("000001.SZ", "1d")
        assert len(all_klines) == 2
        # 验证第二条数据已更新
        second_kline = [k for k in all_klines if k.timestamp.day == 2][0]
        assert second_kline.open == Decimal("10.6")

    @pytest.mark.asyncio
    async def test_get_latest_bars(self, manager, sample_klines):
        """测试获取最新N条K线"""
        await manager.save_klines("000001.SZ", "1d", sample_klines)

        latest = await manager.get_latest_bars("000001.SZ", "1d", n=5)

        assert len(latest) == 5
        # 应该是最新的5条
        assert latest[0].timestamp == datetime(2024, 1, 6)
        assert latest[-1].timestamp == datetime(2024, 1, 10)

    @pytest.mark.asyncio
    async def test_export_to_csv(self, manager, sample_klines, tmp_path):
        """测试导出到CSV"""
        await manager.save_klines("000001.SZ", "1d", sample_klines)

        output_file = tmp_path / "test_export.csv"
        await manager.export_to_csv(
            "000001.SZ", "1d",
            output_path=str(output_file)
        )

        assert output_file.exists()
        content = output_file.read_text()
        assert "timestamp,open,high,low,close,volume" in content
        assert "000001.SZ" in content

    @pytest.mark.asyncio
    async def test_clear_cache(self, manager, sample_klines):
        """测试清空缓存"""
        await manager.save_klines("000001.SZ", "1d", sample_klines)
        assert manager.cache.size() > 0

        manager.clear_cache()
        assert manager.cache.size() == 0

    @pytest.mark.asyncio
    async def test_get_data_info(self, manager, sample_klines):
        """测试获取数据信息"""
        await manager.save_klines("000001.SZ", "1d", sample_klines)

        info = await manager.get_data_info("000001.SZ", "1d")

        assert info is not None
        assert info["symbol"] == "000001.SZ"
        assert info["period"] == "1d"
        assert info["count"] == 10
        assert info["start_date"] == datetime(2024, 1, 1)
        assert info["end_date"] == datetime(2024, 1, 10)

    @pytest.mark.asyncio
    async def test_delete_symbol_data(self, manager, sample_klines):
        """测试删除标的的所有数据"""
        await manager.save_klines("000001.SZ", "1d", sample_klines)
        await manager.save_klines("000001.SZ", "1h", sample_klines[:5])

        await manager.delete_symbol_data("000001.SZ")

        assert not manager.storage.has_data("000001.SZ", "1d")
        assert not manager.storage.has_data("000001.SZ", "1h")


class TestDataCompression:
    """数据压缩测试"""

    def test_kline_compression(self, sample_klines):
        """测试K线数据压缩"""
        from src.market_data.historical import compress_klines, decompress_klines

        # 压缩
        compressed = compress_klines(sample_klines)
        assert compressed is not None

        # 解压
        decompressed = decompress_klines(compressed)
        assert len(decompressed) == len(sample_klines)

        # 验证数据一致性
        for orig, decomp in zip(sample_klines, decompressed):
            assert orig.symbol == decomp.symbol
            assert orig.open == decomp.open
            assert orig.close == decomp.close
