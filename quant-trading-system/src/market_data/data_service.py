"""
行情数据服务层

统一的数据访问接口，整合多个数据源：
- AKShare: 免费A股数据（主数据源）
- Mock: 模拟数据（降级用）

特点：
- 自动数据源切换（主源失败时自动切换到备用源）
- 本地缓存（Redis/Memory）
- 请求频率控制
- 数据质量校验
"""
import asyncio
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Callable
from functools import wraps
import time

from src.market_data.models import TickData, KLineData
from src.market_data.gateway.akshare import AKShareGateway
from src.market_data.gateway.tushare import TushareGateway
from src.market_data.gateway.baostock import BaostockGateway
from src.market_data.mock_provider import MockDataProvider
from src.common.logger import TradingLogger
from src.common.config import settings

logger = TradingLogger(__name__)


def rate_limit(calls_per_second: float = 1.0):
    """请求频率限制装饰器"""
    min_interval = 1.0 / calls_per_second
    last_call_time = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            now = time.time()

            if func_name in last_call_time:
                elapsed = now - last_call_time[func_name]
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)

            last_call_time[func_name] = time.time()
            return await func(*args, **kwargs)

        return wrapper
    return decorator


class DataService:
    """
    行情数据服务

    提供统一的数据访问接口，自动处理：
    - 多数据源切换
    - 数据缓存
    - 错误降级
    - 频率限制
    """

    def __init__(self):
        # 数据源（优先级：AKShare > Tushare > Baostock > Mock）
        self._akshare = AKShareGateway()
        self._tushare = TushareGateway(token=settings.data_sources.tushare_token)
        self._baostock = BaostockGateway()
        self._mock = MockDataProvider()

        # 缓存
        self._tick_cache: Dict[str, TickData] = {}
        self._kline_cache: Dict[str, List[KLineData]] = {}
        self._stock_list_cache: Optional[List[Dict[str, str]]] = None
        self._cache_ttl = 5  # 缓存有效期（秒）
        self._last_update: Dict[str, float] = {}

        # 运行状态
        self._use_real_data = True  # 是否使用真实数据
        self._akshare_available = False
        self._tushare_available = False
        self._baostock_available = False

        # 回调
        self._tick_callbacks: List[Callable[[TickData], None]] = []

        logger.info("数据服务初始化完成")

    async def initialize(self):
        """初始化数据源连接"""
        # 1. 测试AKShare是否可用
        try:
            await self._test_akshare()
            self._akshare_available = True
            logger.info("AKShare数据源可用")
        except Exception as e:
            self._akshare_available = False
            logger.warning(f"AKShare数据源不可用: {e}")

        # 2. 测试Tushare是否可用
        if settings.data_sources.tushare_token:
            try:
                await self._tushare.connect()
                self._tushare_available = True
                logger.info("Tushare数据源可用")
            except Exception as e:
                self._tushare_available = False
                logger.warning(f"Tushare数据源不可用: {e}")
        else:
            logger.info("Tushare Token未配置，跳过")

        # 3. 测试Baostock是否可用
        try:
            await self._baostock.connect()
            self._baostock_available = True
            logger.info("Baostock数据源可用")
        except Exception as e:
            self._baostock_available = False
            logger.warning(f"Baostock数据源不可用: {e}")

    async def _test_akshare(self):
        """测试AKShare连接"""
        import akshare as ak
        # 尝试获取一只股票的数据
        df = ak.stock_zh_a_spot_em()
        if df.empty:
            raise Exception("AKShare返回空数据")

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._last_update:
            return False
        elapsed = time.time() - self._last_update[key]
        return elapsed < self._cache_ttl

    def _update_cache(self, key: str, data: Any):
        """更新缓存"""
        self._last_update[key] = time.time()
        if isinstance(data, TickData):
            self._tick_cache[key] = data
        elif isinstance(data, list) and data and isinstance(data[0], KLineData):
            self._kline_cache[key] = data

    @rate_limit(calls_per_second=0.5)  # 限制请求频率
    async def get_tick(self, symbol: str, use_cache: bool = True) -> Optional[TickData]:
        """
        获取实时Tick数据

        数据源优先级: AKShare > Tushare > Mock

        Args:
            symbol: 标的代码 (如: 000001.SZ)
            use_cache: 是否使用缓存

        Returns:
            TickData 或 None
        """
        cache_key = f"tick:{symbol}"

        # 检查缓存
        if use_cache and self._is_cache_valid(cache_key):
            return self._tick_cache.get(symbol)

        # 1. 尝试 AKShare
        if self._use_real_data and self._akshare_available:
            try:
                tick = await self._akshare.get_snapshot(symbol)
                if tick:
                    self._update_cache(cache_key, tick)
                    return tick
            except Exception as e:
                logger.debug(f"AKShare 获取 {symbol} 失败: {e}")

        # 2. 尝试 Tushare
        if self._use_real_data and self._tushare_available:
            try:
                tick = await self._tushare.get_snapshot(symbol)
                if tick:
                    tick.source = "tushare"
                    self._update_cache(cache_key, tick)
                    return tick
            except Exception as e:
                logger.debug(f"Tushare 获取 {symbol} 失败: {e}")

        # 3. 尝试 Baostock
        if self._use_real_data and self._baostock_available:
            try:
                tick = await self._baostock.get_snapshot(symbol)
                if tick:
                    tick.source = "baostock"
                    self._update_cache(cache_key, tick)
                    return tick
            except Exception as e:
                logger.debug(f"Baostock 获取 {symbol} 失败: {e}")

        # 4. 降级到模拟数据
        mock_tick = self._mock.get_tick(symbol)
        if mock_tick:
            mock_tick.source = "mock_fallback"
            self._update_cache(cache_key, mock_tick)

        return mock_tick

    @rate_limit(calls_per_second=0.3)  # K线数据请求更慢
    async def get_kline(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[KLineData]:
        """
        获取历史K线数据

        Args:
            symbol: 标的代码
            period: 周期 (daily/weekly/monthly)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            limit: 最大条数

        Returns:
            KLineData列表
        """
        cache_key = f"kline:{symbol}:{period}:{start_date}:{end_date}"

        # 检查缓存
        if self._is_cache_valid(cache_key):
            cached = self._kline_cache.get(cache_key, [])
            if cached:
                return cached[:limit]

        # 1. 尝试 AKShare
        if self._use_real_data and self._akshare_available:
            try:
                klines = await self._akshare.get_kline_history(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
                if klines:
                    self._update_cache(cache_key, klines)
                    return klines
            except Exception as e:
                logger.debug(f"AKShare 获取K线失败: {e}")

        # 2. 尝试 Tushare
        if self._use_real_data and self._tushare_available:
            try:
                klines = await self._tushare.get_kline_history(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
                if klines:
                    self._update_cache(cache_key, klines)
                    return klines
            except Exception as e:
                logger.debug(f"Tushare 获取K线失败: {e}")

        # 3. 尝试 Baostock
        if self._use_real_data and self._baostock_available:
            try:
                klines = await self._baostock.get_kline_history(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
                if klines:
                    self._update_cache(cache_key, klines)
                    return klines
            except Exception as e:
                logger.debug(f"Baostock 获取K线失败: {e}")

        # 4. 生成模拟K线数据
        mock_klines = self._generate_mock_klines(symbol, period, limit)
        self._update_cache(cache_key, mock_klines)
        return mock_klines

    def _generate_mock_klines(self, symbol: str, period: str, limit: int) -> List[KLineData]:
        """生成模拟K线数据"""
        base_price = MockDataProvider.STOCK_PRICES.get(symbol, 100.0)
        klines = []

        now = datetime.now()
        for i in range(limit, 0, -1):
            if period == "daily":
                timestamp = now - timedelta(days=i)
            elif period == "weekly":
                timestamp = now - timedelta(weeks=i)
            elif period == "monthly":
                timestamp = now - timedelta(days=i * 30)
            else:
                timestamp = now - timedelta(days=i)

            # 随机生成价格波动
            volatility = 0.02  # 2%日波动
            change = (random.random() - 0.5) * 2 * volatility

            open_price = base_price * (1 + (random.random() - 0.5) * volatility)
            close_price = open_price * (1 + change)
            high_price = max(open_price, close_price) * (1 + random.random() * volatility * 0.5)
            low_price = min(open_price, close_price) * (1 - random.random() * volatility * 0.5)

            kline = KLineData(
                symbol=symbol,
                timestamp=timestamp,
                open=Decimal(str(open_price)),
                high=Decimal(str(high_price)),
                low=Decimal(str(low_price)),
                close=Decimal(str(close_price)),
                volume=int(random.randint(10000, 1000000)),
                amount=Decimal(str(close_price * random.randint(10000, 1000000))),
                period=period
            )
            klines.append(kline)

            base_price = close_price  # 下一个周期的基准价格

        return klines

    async def get_stock_list(self, limit: int = 100, use_cache: bool = True) -> List[Dict[str, str]]:
        """
        获取股票列表

        Args:
            limit: 最大返回数量
            use_cache: 是否使用缓存

        Returns:
            [{"symbol": "000001.SZ", "name": "平安银行"}, ...]
        """
        cache_key = "stock_list"

        # 检查缓存（缓存时间更长）
        if use_cache and self._stock_list_cache and self._is_cache_valid(cache_key):
            return self._stock_list_cache[:limit]

        # 1. 尝试 AKShare
        if self._use_real_data and self._akshare_available:
            try:
                stocks = await self._akshare.get_stock_list()
                if stocks:
                    self._stock_list_cache = stocks
                    self._last_update[cache_key] = time.time()
                    return stocks[:limit]
            except Exception as e:
                logger.debug(f"AKShare 获取股票列表失败: {e}")

        # 2. 尝试 Tushare
        if self._use_real_data and self._tushare_available:
            try:
                stocks = await self._tushare.get_stock_list()
                if stocks:
                    self._stock_list_cache = stocks
                    self._last_update[cache_key] = time.time()
                    return stocks[:limit]
            except Exception as e:
                logger.debug(f"Tushare 获取股票列表失败: {e}")

        # 3. 尝试 Baostock
        if self._use_real_data and self._baostock_available:
            try:
                stocks = await self._baostock.get_stock_list()
                if stocks:
                    self._stock_list_cache = stocks
                    self._last_update[cache_key] = time.time()
                    return stocks[:limit]
            except Exception as e:
                logger.debug(f"Baostock 获取股票列表失败: {e}")

        # 4. 使用模拟数据
        mock_stocks = self._mock.get_stock_list(limit)
        return mock_stocks

    async def search_stocks(self, keyword: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词（代码或名称）
            limit: 最大返回数量

        Returns:
            匹配的股票列表
        """
        keyword = keyword.strip().upper()

        # 先尝试AKShare搜索
        if self._akshare_available and len(keyword) >= 2:
            try:
                stocks = await self.get_stock_list(limit=1000)
                results = []
                for stock in stocks:
                    if keyword in stock["symbol"] or keyword in stock.get("name", ""):
                        results.append(stock)
                        if len(results) >= limit:
                            break
                if results:
                    return results
            except Exception as e:
                logger.debug(f"AKShare搜索失败: {e}")

        # 使用模拟数据搜索
        return self._mock.search_stocks(keyword, limit)

    async def get_batch_ticks(self, symbols: List[str]) -> Dict[str, TickData]:
        """
        批量获取Tick数据

        Args:
            symbols: 标的代码列表

        Returns:
            {symbol: TickData}
        """
        results = {}

        # 并发获取
        tasks = [self.get_tick(symbol) for symbol in symbols]
        ticks = await asyncio.gather(*tasks, return_exceptions=True)

        for symbol, tick in zip(symbols, ticks):
            if isinstance(tick, TickData):
                results[symbol] = tick
            elif isinstance(tick, Exception):
                logger.warning(f"获取 {symbol} 数据失败: {tick}")

        return results

    def set_use_real_data(self, use_real: bool):
        """设置是否使用真实数据"""
        self._use_real_data = use_real
        logger.info(f"数据服务模式: {'真实数据' if use_real else '模拟数据'}")

    def clear_cache(self):
        """清除缓存"""
        self._tick_cache.clear()
        self._kline_cache.clear()
        self._stock_list_cache = None
        self._last_update.clear()
        logger.info("数据缓存已清除")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "tick_cache_size": len(self._tick_cache),
            "kline_cache_size": len(self._kline_cache),
            "stock_list_cached": self._stock_list_cache is not None,
            "use_real_data": self._use_real_data,
            "akshare_available": self._akshare_available,
            "tushare_available": self._tushare_available,
            "tushare_token_configured": settings.data_sources.tushare_token is not None,
            "baostock_available": self._baostock_available,
        }


# 全局实例
data_service = DataService()
