"""
K线数据合成器

从tick数据合成不同周期的K线
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field

from src.market_data.models import TickData, KLineData


@dataclass
class KLinePeriod:
    """K线周期定义"""
    name: str           # 1m, 5m, 15m, 1h, 1d, 1w, 1M
    seconds: int        # 周期对应的秒数

    # 预定义周期
    MIN_1 = None
    MIN_5 = None
    MIN_15 = None
    MIN_30 = None
    HOUR_1 = None
    DAY_1 = None
    WEEK_1 = None
    MONTH_1 = None

# 初始化周期常量
KLinePeriod.MIN_1 = KLinePeriod("1m", 60)
KLinePeriod.MIN_5 = KLinePeriod("5m", 300)
KLinePeriod.MIN_15 = KLinePeriod("15m", 900)
KLinePeriod.MIN_30 = KLinePeriod("30m", 1800)
KLinePeriod.HOUR_1 = KLinePeriod("1h", 3600)
KLinePeriod.DAY_1 = KLinePeriod("1d", 86400)
KLinePeriod.WEEK_1 = KLinePeriod("1w", 604800)
KLinePeriod.MONTH_1 = KLinePeriod("1M", 2592000)


class KLineBuilder:
    """
    K线数据合成器

    从实时tick数据合成K线，支持多周期
    """

    # 周期映射
    PERIODS = {
        "1m": KLinePeriod.MIN_1,
        "5m": KLinePeriod.MIN_5,
        "15m": KLinePeriod.MIN_15,
        "30m": KLinePeriod.MIN_30,
        "1h": KLinePeriod.HOUR_1,
        "1d": KLinePeriod.DAY_1,
        "1w": KLinePeriod.WEEK_1,
        "1M": KLinePeriod.MONTH_1,
    }

    def __init__(self, symbol: str, period: str = "1m"):
        """
        初始化K线合成器

        Args:
            symbol: 标的代码
            period: 周期，支持 1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M
        """
        self.symbol = symbol
        self.period = self.PERIODS.get(period, KLinePeriod.MIN_1)
        self.current_bar: Optional[KLineData] = None
        self.on_bar_completed: Optional[Callable[[KLineData], None]] = None

    def _get_bar_start_time(self, dt: datetime) -> datetime:
        """计算tick所属K线的开始时间"""
        if self.period.name == "1m":
            return dt.replace(second=0, microsecond=0)
        elif self.period.name == "5m":
            minute = (dt.minute // 5) * 5
            return dt.replace(minute=minute, second=0, microsecond=0)
        elif self.period.name == "15m":
            minute = (dt.minute // 15) * 15
            return dt.replace(minute=minute, second=0, microsecond=0)
        elif self.period.name == "30m":
            minute = (dt.minute // 30) * 30
            return dt.replace(minute=minute, second=0, microsecond=0)
        elif self.period.name == "1h":
            return dt.replace(minute=0, second=0, microsecond=0)
        elif self.period.name == "1d":
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # 周和月的处理较复杂，简化处理
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    def on_tick(self, tick: TickData) -> Optional[KLineData]:
        """
        处理tick数据

        Args:
            tick: tick数据

        Returns:
            如果当前K线完成，返回完成的K线数据，否则返回None
        """
        bar_start = self._get_bar_start_time(tick.timestamp)
        completed_bar = None

        if self.current_bar is None:
            # 第一根K线
            self.current_bar = KLineData(
                symbol=tick.symbol,
                timestamp=bar_start,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.volume,
                amount=tick.price * tick.volume,
                period=self.period.name
            )
        elif bar_start > self.current_bar.timestamp:
            # K线周期结束，完成当前K线
            completed_bar = self.current_bar

            # 开始新K线
            self.current_bar = KLineData(
                symbol=tick.symbol,
                timestamp=bar_start,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.volume,
                amount=tick.price * tick.volume,
                period=self.period.name
            )

            # 触发回调
            if self.on_bar_completed:
                self.on_bar_completed(completed_bar)
        else:
            # 更新当前K线
            self.current_bar.high = max(self.current_bar.high, tick.price)
            self.current_bar.low = min(self.current_bar.low, tick.price)
            self.current_bar.close = tick.price
            self.current_bar.volume += tick.volume
            self.current_bar.amount += tick.price * tick.volume

        return completed_bar

    def force_complete(self) -> Optional[KLineData]:
        """强制完成当前K线（用于收盘等场景）"""
        if self.current_bar:
            completed_bar = self.current_bar
            self.current_bar = None

            if self.on_bar_completed:
                self.on_bar_completed(completed_bar)

            return completed_bar
        return None


class MultiPeriodKLineBuilder:
    """多周期K线合成器"""

    DEFAULT_PERIODS = ["1m", "5m", "15m", "30m", "1h", "1d"]

    def __init__(self, symbol: str, periods: Optional[List[str]] = None):
        """
        初始化多周期合成器

        Args:
            symbol: 标的代码
            periods: 周期列表，默认 ["1m", "5m", "15m", "30m", "1h", "1d"]
        """
        self.symbol = symbol
        self.periods = periods or self.DEFAULT_PERIODS
        self.builders: Dict[str, KLineBuilder] = {}
        self.on_bar_callbacks: Dict[str, Callable] = {}

        # 为每个周期创建合成器
        for period in self.periods:
            builder = KLineBuilder(symbol, period)
            self.builders[period] = builder

    def on_tick(self, tick: TickData) -> Dict[str, Optional[KLineData]]:
        """
        处理tick，更新所有周期

        Returns:
            各周期完成的K线，key为周期名称
        """
        completed_bars = {}

        for period, builder in self.builders.items():
            completed = builder.on_tick(tick)
            if completed:
                completed_bars[period] = completed

        return completed_bars

    def get_current_bars(self) -> Dict[str, Optional[KLineData]]:
        """获取所有周期的当前K线"""
        return {
            period: builder.current_bar
            for period, builder in self.builders.items()
        }

    def force_complete_all(self) -> Dict[str, Optional[KLineData]]:
        """强制完成所有周期的当前K线"""
        completed_bars = {}

        for period, builder in self.builders.items():
            completed = builder.force_complete()
            if completed:
                completed_bars[period] = completed

        return completed_bars
