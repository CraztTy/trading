"""
数据标准化转换器测试

测试覆盖：
1. 不同数据源的数据转换
2. 代码格式标准化
3. 数据字段映射
4. 异常数据处理
"""
import pytest
from datetime import datetime
from decimal import Decimal

from src.market_data.transformer import (
    DataTransformer, SourceFormat, TransformRule,
    CodeNormalizer, FieldMapper
)
from src.market_data.models import TickData, KLineData


class TestSourceFormat:
    """数据源格式枚举测试"""

    def test_format_values(self):
        """测试格式值"""
        assert SourceFormat.EASTMONEY.value == "eastmoney"
        assert SourceFormat.AKSHARE.value == "akshare"
        assert SourceFormat.SINA.value == "sina"
        assert SourceFormat.TUSHARE.value == "tushare"
        assert SourceFormat.JQDATA.value == "jqdata"


class TestCodeNormalizer:
    """代码标准化测试"""

    @pytest.fixture
    def normalizer(self):
        return CodeNormalizer()

    def test_normalize_sz_stock(self, normalizer):
        """测试深圳股票标准化"""
        assert normalizer.normalize("000001.SZ") == "000001.SZ"
        assert normalizer.normalize("000001") == "000001.SZ"
        assert normalizer.normalize("sz000001") == "000001.SZ"

    def test_normalize_sh_stock(self, normalizer):
        """测试上海股票标准化"""
        assert normalizer.normalize("600519.SH") == "600519.SH"
        assert normalizer.normalize("600519") == "600519.SH"
        assert normalizer.normalize("sh600519") == "600519.SH"

    def test_normalize_cy_stock(self, normalizer):
        """测试创业板股票标准化"""
        assert normalizer.normalize("300750.SZ") == "300750.SZ"
        assert normalizer.normalize("300750") == "300750.SZ"

    def test_normalize_kc_stock(self, normalizer):
        """测试科创板股票标准化"""
        assert normalizer.normalize("688001.SH") == "688001.SH"
        assert normalizer.normalize("688001") == "688001.SH"

    def test_to_eastmoney_format(self, normalizer):
        """测试转换为东方财富格式"""
        assert normalizer.to_eastmoney("000001.SZ") == "0.000001"
        assert normalizer.to_eastmoney("600519.SH") == "1.600519"

    def test_from_eastmoney_format(self, normalizer):
        """测试从东方财富格式转换"""
        assert normalizer.from_eastmoney("0.000001") == "000001.SZ"
        assert normalizer.from_eastmoney("1.600519") == "600519.SH"

    def test_to_akshare_format(self, normalizer):
        """测试转换为AKShare格式"""
        assert normalizer.to_akshare("000001.SZ") == "000001"
        assert normalizer.to_akshare("600519.SH") == "600519"


class TestFieldMapper:
    """字段映射测试"""

    @pytest.fixture
    def mapper(self):
        return FieldMapper()

    def test_eastmoney_field_mapping(self, mapper):
        """测试东方财富字段映射"""
        raw_data = {
            "f43": 1050,  # 最新价*100
            "f44": 1000,  # 开盘价*100
            "f45": 1100,  # 最高价*100
            "f46": 980,   # 最低价*100
            "f47": 10000, # 成交量
            "f48": 10500000, # 成交额
            "f49": 5,     # 买一价*100
            "f50": 100,   # 买一量
            "f51": 6,     # 卖一价*100
            "f52": 200,   # 卖一量
        }

        result = mapper.map_eastmoney_fields(raw_data)

        assert result["price"] == Decimal("10.50")
        assert result["open"] == Decimal("10.00")
        assert result["high"] == Decimal("11.00")
        assert result["low"] == Decimal("9.80")
        assert result["volume"] == 10000

    def test_akshare_field_mapping(self, mapper):
        """测试AKShare字段映射"""
        raw_data = {
            "代码": "000001",
            "名称": "平安银行",
            "最新价": 10.50,
            "今开": 10.00,
            "最高": 11.00,
            "最低": 9.80,
            "成交量": 1000000,
            "成交额": 10500000,
            "买一": 10.48,
            "买一量": 10000,
            "卖一": 10.52,
            "卖一量": 20000,
        }

        result = mapper.map_akshare_fields(raw_data)

        assert result["price"] == Decimal("10.50")
        assert result["open"] == Decimal("10.00")
        assert result["volume"] == 10000  # 转换为手

    def test_invalid_field_mapping(self, mapper):
        """测试无效字段映射"""
        with pytest.raises(ValueError):
            mapper.map_fields({}, "unknown_source")


class TestDataTransformer:
    """数据转换器测试"""

    @pytest.fixture
    def transformer(self):
        return DataTransformer()

    def test_transform_eastmoney_tick(self, transformer):
        """测试转换东方财富tick数据"""
        raw_data = {
            "code": "0.000001",
            "price": 10.50,
            "volume": 1000,
            "bid1": 10.48,
            "bid1_volume": 500,
            "ask1": 10.52,
            "ask1_volume": 600,
        }

        tick = transformer.transform_tick(raw_data, SourceFormat.EASTMONEY)

        assert isinstance(tick, TickData)
        assert tick.symbol == "000001.SZ"
        assert tick.price == Decimal("10.50")
        assert tick.volume == 1000
        assert tick.bid_price == Decimal("10.48")
        assert tick.ask_price == Decimal("10.52")
        assert tick.source == "eastmoney"

    def test_transform_akshare_tick(self, transformer):
        """测试转换AKShare tick数据"""
        raw_data = {
            "代码": "000001",
            "最新价": 10.50,
            "成交量": 100000,  # 股数
            "买一": 10.48,
            "买一量": 50000,
            "卖一": 10.52,
            "卖一量": 60000,
        }

        tick = transformer.transform_tick(raw_data, SourceFormat.AKSHARE)

        assert isinstance(tick, TickData)
        assert tick.symbol == "000001.SZ"
        assert tick.price == Decimal("10.50")
        assert tick.volume == 1000  # 转换为手
        assert tick.source == "akshare"

    def test_transform_kline_data(self, transformer):
        """测试转换K线数据"""
        raw_data = {
            "date": "2024-01-15",
            "open": 10.00,
            "high": 11.00,
            "low": 9.80,
            "close": 10.50,
            "volume": 1000000,
            "amount": 10500000,
        }

        kline = transformer.transform_kline(
            raw_data, "000001.SZ", "1d", SourceFormat.AKSHARE
        )

        assert isinstance(kline, KLineData)
        assert kline.symbol == "000001.SZ"
        assert kline.open == Decimal("10.00")
        assert kline.high == Decimal("11.00")
        assert kline.low == Decimal("9.80")
        assert kline.close == Decimal("10.50")
        assert kline.period == "1d"

    def test_transform_with_missing_fields(self, transformer):
        """测试缺失字段处理"""
        raw_data = {
            "code": "0.000001",
            "price": 10.50,
            # 缺少其他字段
        }

        tick = transformer.transform_tick(raw_data, SourceFormat.EASTMONEY)

        assert tick.symbol == "000001.SZ"
        assert tick.price == Decimal("10.50")
        assert tick.volume == 0  # 默认值

    def test_validate_tick_data_valid(self, transformer):
        """测试有效tick数据验证"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=1000,
        )

        assert transformer.validate_tick(tick) is True

    def test_validate_tick_data_invalid(self, transformer):
        """测试无效tick数据验证"""
        tick = TickData(
            symbol="",
            timestamp=datetime.now(),
            price=Decimal("0"),
            volume=0,
        )

        assert transformer.validate_tick(tick) is False

    def test_validate_negative_price(self, transformer):
        """测试负价格验证"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("-10.50"),
            volume=1000,
        )

        assert transformer.validate_tick(tick) is False

    def test_transform_batch(self, transformer):
        """测试批量转换"""
        raw_data_list = [
            {"code": "0.000001", "price": 10.50, "volume": 1000},
            {"code": "0.000002", "price": 20.00, "volume": 2000},
            {"code": "0.000003", "price": 30.00, "volume": 3000},
        ]

        ticks = transformer.transform_batch(raw_data_list, SourceFormat.EASTMONEY)

        assert len(ticks) == 3
        assert ticks[0].symbol == "000001.SZ"
        assert ticks[1].symbol == "000002.SZ"
        assert ticks[2].symbol == "000003.SZ"

    def test_add_custom_transform_rule(self, transformer):
        """测试添加自定义转换规则"""
        rule = TransformRule(
            name="custom_rule",
            source_format=SourceFormat.SINA,
            field_mapping={"last": "price", "vol": "volume"},
            value_transforms={"price": lambda x: Decimal(str(x))}
        )

        transformer.add_rule(rule)

        raw_data = {"last": 10.50, "vol": 1000}
        tick = transformer.transform_tick(raw_data, SourceFormat.SINA)

        assert tick.price == Decimal("10.50")
        assert tick.volume == 1000


class TestTransformErrorHandling:
    """转换错误处理测试"""

    def test_handle_none_data(self):
        """测试处理None数据"""
        transformer = DataTransformer()

        with pytest.raises(ValueError):
            transformer.transform_tick(None, SourceFormat.EASTMONEY)

    def test_handle_empty_data(self):
        """测试处理空数据"""
        transformer = DataTransformer()

        with pytest.raises(ValueError):
            transformer.transform_tick({}, SourceFormat.EASTMONEY)

    def test_handle_invalid_timestamp(self):
        """测试处理无效时间戳"""
        transformer = DataTransformer()

        raw_data = {
            "code": "0.000001",
            "price": 10.50,
            "timestamp": "invalid_timestamp"
        }

        # 应该使用当前时间作为默认值
        tick = transformer.transform_tick(raw_data, SourceFormat.EASTMONEY)
        assert tick.timestamp is not None

    def test_handle_type_conversion_error(self):
        """测试类型转换错误处理"""
        transformer = DataTransformer()

        raw_data = {
            "code": "0.000001",
            "price": "not_a_number",  # 无效的价格
        }

        # 应该使用默认值或抛出异常
        with pytest.raises((ValueError, TypeError)):
            transformer.transform_tick(raw_data, SourceFormat.EASTMONEY)
