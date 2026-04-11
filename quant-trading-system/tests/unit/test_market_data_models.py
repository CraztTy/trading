"""
行情数据模型单元测试
"""
from datetime import datetime
from decimal import Decimal
import pytest

from src.market_data.models import TickData, KLineData, MarketDepth, MarketSnapshot


class TestTickData:
    """测试TickData"""

    def test_create_tick(self):
        """测试创建TickData"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )

        assert tick.symbol == "000001.SZ"
        assert tick.price == Decimal("10.50")
        assert tick.volume == 1000
        assert tick.source == "unknown"

    def test_tick_to_dict(self):
        """测试TickData序列化"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
            bid_price=Decimal("10.49"),
            ask_price=Decimal("10.51"),
            source="test",
        )

        data = tick.to_dict()

        assert data["symbol"] == "000001.SZ"
        assert data["price"] == 10.50
        assert data["volume"] == 1000
        assert data["bid_price"] == 10.49
        assert data["ask_price"] == 10.51
        assert data["source"] == "test"

    def test_tick_from_dict(self):
        """测试TickData反序列化"""
        data = {
            "symbol": "600519.SH",
            "timestamp": "2024-01-15T09:30:00",
            "price": 1688.00,
            "volume": 500,
            "bid_price": 1687.50,
            "ask_price": 1688.50,
            "source": "test",
        }

        tick = TickData.from_dict(data)

        assert tick.symbol == "600519.SH"
        assert tick.price == Decimal("1688.00")
        assert tick.volume == 500
        assert tick.source == "test"

    def test_tick_optional_fields(self):
        """测试可选字段"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.00"),
            volume=100,
        )

        assert tick.amount is None
        assert tick.bid_price is None
        assert tick.change is None

        # to_dict中None字段应正确处理
        data = tick.to_dict()
        assert data["amount"] is None
        assert data["bid_price"] is None


class TestKLineData:
    """测试KLineData"""

    def test_create_kline(self):
        """测试创建K线"""
        kline = KLineData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            open=Decimal("10.00"),
            high=Decimal("10.50"),
            low=Decimal("9.80"),
            close=Decimal("10.30"),
            volume=10000,
            amount=Decimal("102000"),
            period="1m",
        )

        assert kline.symbol == "000001.SZ"
        assert kline.open == Decimal("10.00")
        assert kline.high == Decimal("10.50")
        assert kline.low == Decimal("9.80")
        assert kline.close == Decimal("10.30")
        assert kline.period == "1m"

    def test_kline_to_dict(self):
        """测试K线序列化"""
        kline = KLineData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            open=Decimal("10.00"),
            high=Decimal("10.50"),
            low=Decimal("9.80"),
            close=Decimal("10.30"),
            volume=10000,
            amount=Decimal("102000"),
            period="5m",
        )

        data = kline.to_dict()

        assert data["symbol"] == "000001.SZ"
        assert data["open"] == 10.00
        assert data["high"] == 10.50
        assert data["low"] == 9.80
        assert data["close"] == 10.30
        assert data["volume"] == 10000
        assert data["period"] == "5m"


class TestMarketDepth:
    """测试MarketDepth"""

    def test_create_depth(self):
        """测试创建深度数据"""
        depth = MarketDepth(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            bids=[(Decimal("10.49"), 1000), (Decimal("10.48"), 2000)],
            asks=[(Decimal("10.51"), 1500), (Decimal("10.52"), 2500)],
        )

        assert depth.symbol == "000001.SZ"
        assert len(depth.bids) == 2
        assert len(depth.asks) == 2
        assert depth.bids[0] == (Decimal("10.49"), 1000)


class TestMarketSnapshot:
    """测试MarketSnapshot"""

    def test_create_snapshot(self):
        """测试创建市场快照"""
        snapshot = MarketSnapshot(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            open=Decimal("10.00"),
            high=Decimal("10.80"),
            low=Decimal("9.90"),
            pre_close=Decimal("9.95"),
            volume=100000,
            amount=Decimal("1050000"),
            bid_price_1=Decimal("10.49"),
            bid_volume_1=5000,
            ask_price_1=Decimal("10.51"),
            ask_volume_1=3000,
            status="交易中",
        )

        assert snapshot.symbol == "000001.SZ"
        assert snapshot.status == "交易中"

        data = snapshot.to_dict()
        assert data["status"] == "交易中"
        assert data["price"] == 10.50
