"""
K线合成器单元测试
"""
from datetime import datetime
from decimal import Decimal
import pytest

from src.market_data.builder import KLineBuilder, MultiPeriodKLineBuilder, KLinePeriod
from src.market_data.models import TickData, KLineData


class TestKLinePeriod:
    """测试K线周期定义"""

    def test_period_constants(self):
        """测试周期常量"""
        assert KLinePeriod.MIN_1.seconds == 60
        assert KLinePeriod.MIN_5.seconds == 300
        assert KLinePeriod.MIN_15.seconds == 900
        assert KLinePeriod.HOUR_1.seconds == 3600
        assert KLinePeriod.DAY_1.seconds == 86400


class TestKLineBuilder:
    """测试K线合成器"""

    def test_create_builder(self):
        """测试创建合成器"""
        builder = KLineBuilder("000001.SZ", "1m")
        assert builder.symbol == "000001.SZ"
        assert builder.period.name == "1m"
        assert builder.current_bar is None

    def test_first_tick_creates_bar(self):
        """测试第一个tick创建K线"""
        builder = KLineBuilder("000001.SZ", "1m")

        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )

        result = builder.on_tick(tick)

        # 第一个tick不会完成K线
        assert result is None
        # 但会创建当前K线
        assert builder.current_bar is not None
        assert builder.current_bar.open == Decimal("10.50")
        assert builder.current_bar.high == Decimal("10.50")
        assert builder.current_bar.low == Decimal("10.50")
        assert builder.current_bar.close == Decimal("10.50")
        assert builder.current_bar.volume == 1000

    def test_multiple_ticks_update_bar(self):
        """测试多个tick更新K线"""
        builder = KLineBuilder("000001.SZ", "1m")

        # 第一个tick
        tick1 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )
        builder.on_tick(tick1)

        # 同周期内的第二个tick (更高价格)
        tick2 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 30),
            price=Decimal("10.80"),
            volume=2000,
        )
        result = builder.on_tick(tick2)

        # 同周期内不会完成K线
        assert result is None
        # K线被更新
        assert builder.current_bar.high == Decimal("10.80")
        assert builder.current_bar.close == Decimal("10.80")
        assert builder.current_bar.volume == 3000

        # 同周期内的第三个tick (更低价格)
        tick3 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 45),
            price=Decimal("10.20"),
            volume=500,
        )
        builder.on_tick(tick3)

        assert builder.current_bar.low == Decimal("10.20")
        assert builder.current_bar.close == Decimal("10.20")
        assert builder.current_bar.volume == 3500

    def test_new_period_completes_bar(self):
        """测试新周期完成K线"""
        builder = KLineBuilder("000001.SZ", "1m")

        # 9:30:00的tick
        tick1 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )
        builder.on_tick(tick1)

        # 9:31:00的tick (新周期)
        tick2 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 31, 0),
            price=Decimal("10.60"),
            volume=2000,
        )
        result = builder.on_tick(tick2)

        # 应该返回完成的K线
        assert result is not None
        assert result.open == Decimal("10.50")
        assert result.close == Decimal("10.50")
        assert result.volume == 1000

        # 新的K线已创建
        assert builder.current_bar is not None
        assert builder.current_bar.timestamp == datetime(2024, 1, 15, 9, 31, 0)
        assert builder.current_bar.open == Decimal("10.60")

    def test_5m_period(self):
        """测试5分钟周期"""
        builder = KLineBuilder("000001.SZ", "5m")

        # 9:30的tick
        tick1 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )
        builder.on_tick(tick1)

        # 9:34的tick (同周期)
        tick2 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 34, 0),
            price=Decimal("10.60"),
            volume=2000,
        )
        result = builder.on_tick(tick2)
        assert result is None  # 未完成

        # 9:35的tick (新周期)
        tick3 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 35, 0),
            price=Decimal("10.70"),
            volume=3000,
        )
        result = builder.on_tick(tick3)
        assert result is not None  # 完成

    def test_force_complete(self):
        """测试强制完成K线"""
        builder = KLineBuilder("000001.SZ", "1m")

        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )
        builder.on_tick(tick)

        # 强制完成
        result = builder.force_complete()

        assert result is not None
        assert result.open == Decimal("10.50")
        assert builder.current_bar is None


class TestMultiPeriodKLineBuilder:
    """测试多周期K线合成器"""

    def test_create_multi_period(self):
        """测试创建多周期合成器"""
        builder = MultiPeriodKLineBuilder("000001.SZ", ["1m", "5m", "1h"])
        assert builder.symbol == "000001.SZ"
        assert len(builder.builders) == 3
        assert "1m" in builder.builders
        assert "5m" in builder.builders
        assert "1h" in builder.builders

    def test_default_periods(self):
        """测试默认周期"""
        builder = MultiPeriodKLineBuilder("000001.SZ")
        assert len(builder.builders) == 6
        assert "1m" in builder.builders
        assert "1d" in builder.builders

    def test_on_tick_all_periods(self):
        """测试tick更新所有周期"""
        builder = MultiPeriodKLineBuilder("000001.SZ", ["1m", "5m"])

        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )
        completed = builder.on_tick(tick)

        # 所有周期都收到tick
        bars = builder.get_current_bars()
        assert bars["1m"] is not None
        assert bars["5m"] is not None

    def test_different_period_completion(self):
        """测试不同周期独立完成"""
        builder = MultiPeriodKLineBuilder("000001.SZ", ["1m", "5m"])

        # 9:30的tick
        tick1 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )
        builder.on_tick(tick1)

        # 9:31的tick - 应该完成1m，但不完成5m
        tick2 = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 31, 0),
            price=Decimal("10.60"),
            volume=2000,
        )
        completed = builder.on_tick(tick2)

        assert "1m" in completed
        assert completed["1m"] is not None
        # 5m不会完成
        assert "5m" not in completed or completed["5m"] is None
