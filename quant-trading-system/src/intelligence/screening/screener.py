"""
股票筛选器

提供多维度股票筛选功能：
- 基本面筛选：PE、PB、ROE、营收增长等
- 技术面筛选：价格、成交量、均线等
- 财务筛选：负债率、现金流、分红等
- 行业板块筛选
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any, Union
from enum import Enum
import asyncio

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class FilterOperator(Enum):
    """筛选操作符"""
    EQ = "eq"           # 等于
    NE = "ne"           # 不等于
    GT = "gt"           # 大于
    GTE = "gte"         # 大于等于
    LT = "lt"           # 小于
    LTE = "lte"         # 小于等于
    BETWEEN = "between" # 介于
    IN = "in"           # 在列表中
    NOT_IN = "not_in"   # 不在列表中


class SortOrder(Enum):
    """排序方向"""
    ASC = "asc"
    DESC = "desc"


@dataclass
class FilterCriterion:
    """筛选条件"""
    field: str                      # 字段名
    operator: FilterOperator        # 操作符
    value: Any                      # 值
    value2: Optional[Any] = None    # 第二个值（用于BETWEEN）


@dataclass
class SortCriterion:
    """排序条件"""
    field: str
    order: SortOrder = SortOrder.DESC


@dataclass
class StockData:
    """股票数据"""
    symbol: str
    name: str
    industry: Optional[str] = None
    sector: Optional[str] = None

    # 价格数据
    price: Optional[Decimal] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    turnover: Optional[Decimal] = None

    # 估值指标
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    dividend_yield: Optional[float] = None

    # 财务指标
    market_cap: Optional[Decimal] = None
    total_revenue: Optional[Decimal] = None
    net_profit: Optional[Decimal] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    gross_margin: Optional[float] = None
    net_margin: Optional[float] = None

    # 成长指标
    revenue_growth: Optional[float] = None
    profit_growth: Optional[float] = None

    # 技术指标
    ma5: Optional[Decimal] = None
    ma10: Optional[Decimal] = None
    ma20: Optional[Decimal] = None
    ma60: Optional[Decimal] = None

    # 更新时间
    update_date: Optional[date] = None

    def get_field(self, field_name: str) -> Any:
        """获取字段值"""
        return getattr(self, field_name, None)


@dataclass
class ScreenResult:
    """筛选结果"""
    stocks: List[StockData]
    total_count: int
    filtered_count: int
    criteria: List[FilterCriterion]
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
            "execution_time_ms": self.execution_time_ms,
            "stocks": [
                {
                    "symbol": s.symbol,
                    "name": s.name,
                    "industry": s.industry,
                    "price": float(s.price) if s.price else None,
                    "pe_ttm": s.pe_ttm,
                    "pb": s.pb,
                    "roe": s.roe,
                    "market_cap": float(s.market_cap) if s.market_cap else None,
                }
                for s in self.stocks
            ]
        }


class StockScreener:
    """
    股票筛选器

    支持多条件组合筛选、排序、分页
    """

    def __init__(self, data_source: Optional[Any] = None):
        self.data_source = data_source
        self._filters: List[FilterCriterion] = []
        self._sorts: List[SortCriterion] = []
        self._limit: Optional[int] = None
        self._offset: int = 0

    def reset(self) -> 'StockScreener':
        """重置筛选条件"""
        self._filters = []
        self._sorts = []
        self._limit = None
        self._offset = 0
        return self

    # ============ 基本面筛选 ============

    def pe_ratio(self, min_val: Optional[float] = None, max_val: Optional[float] = None) -> 'StockScreener':
        """PE市盈率筛选"""
        if min_val is not None and max_val is not None:
            self._filters.append(FilterCriterion("pe_ttm", FilterOperator.BETWEEN, min_val, max_val))
        elif min_val is not None:
            self._filters.append(FilterCriterion("pe_ttm", FilterOperator.GTE, min_val))
        elif max_val is not None:
            self._filters.append(FilterCriterion("pe_ttm", FilterOperator.LTE, max_val))
        return self

    def pb_ratio(self, min_val: Optional[float] = None, max_val: Optional[float] = None) -> 'StockScreener':
        """PB市净率筛选"""
        if min_val is not None and max_val is not None:
            self._filters.append(FilterCriterion("pb", FilterOperator.BETWEEN, min_val, max_val))
        elif min_val is not None:
            self._filters.append(FilterCriterion("pb", FilterOperator.GTE, min_val))
        elif max_val is not None:
            self._filters.append(FilterCriterion("pb", FilterOperator.LTE, max_val))
        return self

    def roe(self, min_val: float) -> 'StockScreener':
        """ROE净资产收益率筛选"""
        self._filters.append(FilterCriterion("roe", FilterOperator.GTE, min_val))
        return self

    def roa(self, min_val: float) -> 'StockScreener':
        """ROA总资产收益率筛选"""
        self._filters.append(FilterCriterion("roa", FilterOperator.GTE, min_val))
        return self

    def revenue_growth(self, min_val: float) -> 'StockScreener':
        """营收增长率筛选"""
        self._filters.append(FilterCriterion("revenue_growth", FilterOperator.GTE, min_val))
        return self

    def profit_growth(self, min_val: float) -> 'StockScreener':
        """利润增长率筛选"""
        self._filters.append(FilterCriterion("profit_growth", FilterOperator.GTE, min_val))
        return self

    def dividend_yield(self, min_val: float) -> 'StockScreener':
        """股息率筛选"""
        self._filters.append(FilterCriterion("dividend_yield", FilterOperator.GTE, min_val))
        return self

    # ============ 市值筛选 ============

    def market_cap(self, min_val: Optional[Decimal] = None, max_val: Optional[Decimal] = None) -> 'StockScreener':
        """市值筛选"""
        if min_val is not None and max_val is not None:
            self._filters.append(FilterCriterion("market_cap", FilterOperator.BETWEEN, min_val, max_val))
        elif min_val is not None:
            self._filters.append(FilterCriterion("market_cap", FilterOperator.GTE, min_val))
        elif max_val is not None:
            self._filters.append(FilterCriterion("market_cap", FilterOperator.LTE, max_val))
        return self

    def large_cap(self) -> 'StockScreener':
        """大盘股筛选（>500亿）"""
        return self.market_cap(min_val=Decimal("50000000000"))

    def mid_cap(self) -> 'StockScreener':
        """中盘股筛选（100-500亿）"""
        return self.market_cap(
            min_val=Decimal("10000000000"),
            max_val=Decimal("50000000000")
        )

    def small_cap(self) -> 'StockScreener':
        """小盘股筛选（<100亿）"""
        return self.market_cap(max_val=Decimal("10000000000"))

    # ============ 行业板块筛选 ============

    def industry(self, industries: Union[str, List[str]]) -> 'StockScreener':
        """行业筛选"""
        if isinstance(industries, str):
            industries = [industries]
        self._filters.append(FilterCriterion("industry", FilterOperator.IN, industries))
        return self

    def sector(self, sectors: Union[str, List[str]]) -> 'StockScreener':
        """板块筛选"""
        if isinstance(sectors, str):
            sectors = [sectors]
        self._filters.append(FilterCriterion("sector", FilterOperator.IN, sectors))
        return self

    def exclude_industry(self, industries: Union[str, List[str]]) -> 'StockScreener':
        """排除行业"""
        if isinstance(industries, str):
            industries = [industries]
        self._filters.append(FilterCriterion("industry", FilterOperator.NOT_IN, industries))
        return self

    # ============ 技术面筛选 ============

    def price_above_ma(self, ma_type: str = "ma20") -> 'StockScreener':
        """价格在均线上方"""
        # 这里简化处理，实际应该比较 price > ma
        self._filters.append(FilterCriterion(f"price_above_{ma_type}", FilterOperator.EQ, True))
        return self

    def volume_min(self, min_volume: int) -> 'StockScreener':
        """最小成交量筛选"""
        self._filters.append(FilterCriterion("volume", FilterOperator.GTE, min_volume))
        return self

    def price_change(self, min_pct: Optional[float] = None, max_pct: Optional[float] = None) -> 'StockScreener':
        """涨跌幅筛选"""
        if min_pct is not None and max_pct is not None:
            self._filters.append(FilterCriterion("change_pct", FilterOperator.BETWEEN, min_pct, max_pct))
        elif min_pct is not None:
            self._filters.append(FilterCriterion("change_pct", FilterOperator.GTE, min_pct))
        elif max_pct is not None:
            self._filters.append(FilterCriterion("change_pct", FilterOperator.LTE, max_pct))
        return self

    # ============ 排序 ============

    def order_by(self, field: str, order: SortOrder = SortOrder.DESC) -> 'StockScreener':
        """排序"""
        self._sorts.append(SortCriterion(field, order))
        return self

    def order_by_pe(self, asc: bool = True) -> 'StockScreener':
        """按PE排序"""
        return self.order_by("pe_ttm", SortOrder.ASC if asc else SortOrder.DESC)

    def order_by_pb(self, asc: bool = True) -> 'StockScreener':
        """按PB排序"""
        return self.order_by("pb", SortOrder.ASC if asc else SortOrder.DESC)

    def order_by_roe(self, desc: bool = True) -> 'StockScreener':
        """按ROE排序"""
        return self.order_by("roe", SortOrder.DESC if desc else SortOrder.ASC)

    def order_by_market_cap(self, desc: bool = True) -> 'StockScreener':
        """按市值排序"""
        return self.order_by("market_cap", SortOrder.DESC if desc else SortOrder.ASC)

    # ============ 分页 ============

    def limit(self, n: int) -> 'StockScreener':
        """限制结果数量"""
        self._limit = n
        return self

    def offset(self, n: int) -> 'StockScreener':
        """跳过前n条"""
        self._offset = n
        return self

    # ============ 执行筛选 ============

    async def execute(self, stock_pool: Optional[List[StockData]] = None) -> ScreenResult:
        """
        执行筛选

        Args:
            stock_pool: 股票池，如果不提供则从数据源获取

        Returns:
            ScreenResult: 筛选结果
        """
        import time
        start_time = time.time()

        # 获取股票池
        if stock_pool is None:
            stock_pool = await self._fetch_stock_pool()

        total_count = len(stock_pool)
        logger.info(f"开始筛选: 总数={total_count}, 条件数={len(self._filters)}")

        # 应用筛选条件
        filtered = stock_pool
        for criterion in self._filters:
            filtered = [s for s in filtered if self._apply_criterion(s, criterion)]

        # 排序
        for sort in self._sorts:
            filtered = self._apply_sort(filtered, sort)

        # 分页
        if self._offset > 0:
            filtered = filtered[self._offset:]
        if self._limit is not None:
            filtered = filtered[:self._limit]

        execution_time = (time.time() - start_time) * 1000

        logger.info(f"筛选完成: 结果={len(filtered)}, 耗时={execution_time:.2f}ms")

        return ScreenResult(
            stocks=filtered,
            total_count=total_count,
            filtered_count=len(filtered),
            criteria=self._filters.copy(),
            execution_time_ms=execution_time
        )

    def execute_sync(self, stock_pool: Optional[List[StockData]] = None) -> ScreenResult:
        """同步执行筛选"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # 在异步上下文中，创建新线程运行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.execute(stock_pool))
                return future.result()
        else:
            # 不在异步上下文中，直接运行
            return asyncio.run(self.execute(stock_pool))

    # ============ 内置筛选策略 ============

    def value_stocks(self) -> 'StockScreener':
        """价值股策略：低PE、低PB、高股息"""
        return self.reset().pe_ratio(max_val=15).pb_ratio(max_val=2).roe(min_val=0.1)

    def growth_stocks(self) -> 'StockScreener':
        """成长股策略：高增长、高ROE"""
        return self.reset().revenue_growth(min_val=0.2).profit_growth(min_val=0.2).roe(min_val=0.15)

    def dividend_stocks(self) -> 'StockScreener':
        """红利股策略：高股息、稳定盈利"""
        return self.reset().dividend_yield(min_val=0.03).roe(min_val=0.1).pe_ratio(max_val=20)

    def blue_chip(self) -> 'StockScreener':
        """蓝筹股策略：大盘股、高ROE、低估值"""
        return self.reset().large_cap().roe(min_val=0.12).pe_ratio(max_val=25)

    # ============ 辅助方法 ============

    async def _fetch_stock_pool(self) -> List[StockData]:
        """从数据源获取股票池"""
        # 实际实现中应该从数据库或API获取
        # 这里返回空列表
        if self.data_source:
            # 调用数据源获取股票列表
            pass
        return []

    def _apply_criterion(self, stock: StockData, criterion: FilterCriterion) -> bool:
        """应用单个筛选条件"""
        value = stock.get_field(criterion.field)

        # 处理None值
        if value is None:
            return False

        op = criterion.operator
        target = criterion.value

        try:
            if op == FilterOperator.EQ:
                return value == target
            elif op == FilterOperator.NE:
                return value != target
            elif op == FilterOperator.GT:
                return value > target
            elif op == FilterOperator.GTE:
                return value >= target
            elif op == FilterOperator.LT:
                return value < target
            elif op == FilterOperator.LTE:
                return value <= target
            elif op == FilterOperator.BETWEEN:
                return target <= value <= criterion.value2
            elif op == FilterOperator.IN:
                return value in target
            elif op == FilterOperator.NOT_IN:
                return value not in target
        except (TypeError, ValueError):
            return False

        return False

    def _apply_sort(self, stocks: List[StockData], sort: SortCriterion) -> List[StockData]:
        """应用排序"""
        reverse = sort.order == SortOrder.DESC

        def key_func(s: StockData):
            val = s.get_field(sort.field)
            if val is None:
                return float('-inf') if reverse else float('inf')
            return val

        return sorted(stocks, key=key_func, reverse=reverse)


class PresetScreeners:
    """预设筛选器"""

    @staticmethod
    def low_pe() -> StockScreener:
        """低PE筛选器"""
        return StockScreener().pe_ratio(max_val=10).order_by_pe(asc=True).limit(50)

    @staticmethod
    def high_roe() -> StockScreener:
        """高ROE筛选器"""
        return StockScreener().roe(min_val=0.2).order_by_roe(desc=True).limit(50)

    @staticmethod
    def small_cap_growth() -> StockScreener:
        """小盘成长股筛选器"""
        return StockScreener().small_cap().revenue_growth(min_val=0.3).profit_growth(min_val=0.3).limit(50)

    @staticmethod
    def blue_chip_dividend() -> StockScreener:
        """蓝筹红利筛选器"""
        return StockScreener().blue_chip().dividend_yield(min_val=0.03).order_by_market_cap(desc=True).limit(50)
