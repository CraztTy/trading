"""
数据标准化转换器

职责：
- 将不同数据源的数据格式统一
- 股票代码格式转换
- 数据字段映射
- 数据验证
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from src.market_data.models import TickData, KLineData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class SourceFormat(str, Enum):
    """数据源格式"""
    EASTMONEY = "eastmoney"
    AKSHARE = "akshare"
    SINA = "sina"
    TUSHARE = "tushare"
    JQDATA = "jqdata"


@dataclass
class TransformRule:
    """转换规则"""
    name: str
    source_format: SourceFormat
    field_mapping: Dict[str, str]  # 原始字段名 -> 标准字段名
    value_transforms: Dict[str, Callable] = field(default_factory=dict)
    required_fields: List[str] = field(default_factory=list)


class CodeNormalizer:
    """
    股票代码标准化器

    统一不同数据源的股票代码格式
    标准格式: {code}.{exchange} (如: 000001.SZ)
    """

    @staticmethod
    def normalize(symbol: str) -> str:
        """
        标准化股票代码

        Args:
            symbol: 原始代码 (如: sz000001, 000001, 000001.SZ)

        Returns:
            标准化代码 (如: 000001.SZ)
        """
        if not symbol:
            return ""

        symbol = symbol.strip().upper()

        # 已经是标准格式
        if "." in symbol:
            return symbol

        # 处理前缀格式 (sz000001, sh600519)
        if symbol.startswith("SZ"):
            return f"{symbol[2:]}.SZ"
        if symbol.startswith("SH"):
            return f"{symbol[2:]}.SH"
        if symbol.startswith("BJ"):
            return f"{symbol[2:]}.BJ"

        # 根据代码规则判断交易所
        if len(symbol) == 6:
            if symbol.startswith("6") or symbol.startswith("5") or symbol.startswith("68") or symbol.startswith("8"):
                # 上海: 600xxx(主板), 688xxx(科创板), 50xxxx(基金)
                return f"{symbol}.SH"
            else:
                # 深圳: 000xxx(主板), 300xxx(创业板), 002xxx(中小板)
                return f"{symbol}.SZ"

        return symbol

    @staticmethod
    def to_eastmoney(symbol: str) -> str:
        """
        转换为东方财富格式

        Examples:
            000001.SZ -> 0.000001
            600519.SH -> 1.600519
        """
        normalized = CodeNormalizer.normalize(symbol)
        if "." not in normalized:
            return f"0.{normalized}"

        code, exchange = normalized.split(".")
        if exchange == "SH":
            return f"1.{code}"
        else:
            return f"0.{code}"

    @staticmethod
    def from_eastmoney(em_code: str) -> str:
        """从东方财富格式转换"""
        if "." not in em_code:
            return em_code

        prefix, code = em_code.split(".")
        if prefix == "1":
            return f"{code}.SH"
        else:
            return f"{code}.SZ"

    @staticmethod
    def to_akshare(symbol: str) -> str:
        """
        转换为AKShare格式 (只有代码，不带后缀)

        Example: 000001.SZ -> 000001
        """
        normalized = CodeNormalizer.normalize(symbol)
        if "." in normalized:
            return normalized.split(".")[0]
        return normalized


class FieldMapper:
    """字段映射器"""

    # 东方财富字段映射 (fxx格式)
    EASTMONEY_FIELD_MAP = {
        "f43": "price",       # 最新价 * 100
        "f44": "open",        # 开盘价 * 100
        "f45": "high",        # 最高价 * 100
        "f46": "low",         # 最低价 * 100
        "f47": "volume",      # 成交量
        "f48": "amount",      # 成交额
        "f49": "bid_price",   # 买一价 * 100
        "f50": "bid_volume",  # 买一量
        "f51": "ask_price",   # 卖一价 * 100
        "f52": "ask_volume",  # 卖一量
        "f57": "code",        # 股票代码
        "f58": "name",        # 股票名称
        "f60": "pre_close",   # 昨收 * 100
        "f169": "change",     # 涨跌额 * 100
        "f170": "change_pct", # 涨跌幅 * 100
    }

    # AKShare字段映射
    AKSHARE_FIELD_MAP = {
        "代码": "code",
        "名称": "name",
        "最新价": "price",
        "今开": "open",
        "最高": "high",
        "最低": "low",
        "昨收": "pre_close",
        "成交量": "volume",
        "成交额": "amount",
        "买一": "bid_price",
        "买一量": "bid_volume",
        "卖一": "ask_price",
        "卖一量": "ask_volume",
        "涨跌额": "change",
        "涨跌幅": "change_pct",
    }

    def map_eastmoney_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """映射东方财富字段"""
        result = {}
        for raw_field, standard_field in self.EASTMONEY_FIELD_MAP.items():
            if raw_field in data:
                value = data[raw_field]
                # 东方财富价格数据需要除以100
                if standard_field in ["price", "open", "high", "low", "bid_price", "ask_price", "pre_close"]:
                    try:
                        value = Decimal(str(value)) / 100 if value else Decimal("0")
                    except:
                        value = Decimal("0")
                result[standard_field] = value
        return result

    def map_akshare_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """映射AKShare字段"""
        result = {}
        for raw_field, standard_field in self.AKSHARE_FIELD_MAP.items():
            if raw_field in data:
                value = data[raw_field]
                # 成交量转换为手（AKShare返回的是股数）
                if standard_field == "volume" and value:
                    try:
                        value = int(value) // 100
                    except:
                        value = 0
                result[standard_field] = value
        return result

    def map_fields(self, data: Dict[str, Any], source: SourceFormat) -> Dict[str, Any]:
        """
        根据数据源映射字段

        Args:
            data: 原始数据
            source: 数据源类型

        Returns:
            映射后的数据
        """
        if source == SourceFormat.EASTMONEY:
            return self.map_eastmoney_fields(data)
        elif source == SourceFormat.AKSHARE:
            return self.map_akshare_fields(data)
        else:
            raise ValueError(f"不支持的数据源: {source}")


class DataTransformer:
    """
    数据转换器

    将各种数据源的数据转换为标准格式
    """

    def __init__(self):
        self.code_normalizer = CodeNormalizer()
        self.field_mapper = FieldMapper()
        self._custom_rules: Dict[SourceFormat, TransformRule] = {}

    def add_rule(self, rule: TransformRule) -> None:
        """添加自定义转换规则"""
        self._custom_rules[rule.source_format] = rule
        logger.info(f"添加转换规则: {rule.name} for {rule.source_format}")

    def transform_tick(self, data: Dict[str, Any], source: SourceFormat) -> TickData:
        """
        转换Tick数据

        Args:
            data: 原始数据
            source: 数据源类型

        Returns:
            TickData: 标准格式的tick数据
        """
        if not data:
            raise ValueError("数据不能为空")

        # 字段映射
        mapped_data = self.field_mapper.map_fields(data, source)

        # 代码标准化
        symbol = mapped_data.get("code", "")
        if source == SourceFormat.EASTMONEY:
            symbol = self.code_normalizer.from_eastmoney(symbol)
        else:
            symbol = self.code_normalizer.normalize(symbol)

        # 提取时间戳
        timestamp = mapped_data.get("timestamp")
        if timestamp is None:
            timestamp = datetime.now()
        elif isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()

        # 构建TickData
        tick = TickData(
            symbol=symbol,
            timestamp=timestamp,
            price=self._to_decimal(mapped_data.get("price")),
            volume=int(mapped_data.get("volume", 0)) if mapped_data.get("volume") else 0,
            amount=self._to_decimal(mapped_data.get("amount")),
            bid_price=self._to_decimal(mapped_data.get("bid_price")),
            bid_volume=int(mapped_data.get("bid_volume")) if mapped_data.get("bid_volume") else None,
            ask_price=self._to_decimal(mapped_data.get("ask_price")),
            ask_volume=int(mapped_data.get("ask_volume")) if mapped_data.get("ask_volume") else None,
            open=self._to_decimal(mapped_data.get("open")),
            high=self._to_decimal(mapped_data.get("high")),
            low=self._to_decimal(mapped_data.get("low")),
            pre_close=self._to_decimal(mapped_data.get("pre_close")),
            change=self._to_decimal(mapped_data.get("change")),
            change_pct=self._to_decimal(mapped_data.get("change_pct")),
            source=source.value,
            raw_data=data if isinstance(data, dict) else None,
        )

        return tick

    def transform_kline(
        self,
        data: Dict[str, Any],
        symbol: str,
        period: str,
        source: SourceFormat
    ) -> KLineData:
        """
        转换K线数据

        Args:
            data: 原始数据
            symbol: 股票代码
            period: 周期 (1m, 5m, 1h, 1d, etc.)
            source: 数据源类型

        Returns:
            KLineData: 标准格式的K线数据
        """
        if not data:
            raise ValueError("数据不能为空")

        # 代码标准化
        symbol = self.code_normalizer.normalize(symbol)

        # 解析时间戳
        timestamp = data.get("date") or data.get("timestamp") or data.get("time")
        if isinstance(timestamp, str):
            # 尝试多种格式
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y%m%d"]:
                try:
                    timestamp = datetime.strptime(timestamp, fmt)
                    break
                except ValueError:
                    continue
            else:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()

        # 字段名可能有差异
        open_price = data.get("open") or data.get("开盘")
        high_price = data.get("high") or data.get("最高")
        low_price = data.get("low") or data.get("最低")
        close_price = data.get("close") or data.get("收盘")
        volume = data.get("volume") or data.get("成交量")
        amount = data.get("amount") or data.get("成交额")

        kline = KLineData(
            symbol=symbol,
            timestamp=timestamp,
            open=self._to_decimal(open_price),
            high=self._to_decimal(high_price),
            low=self._to_decimal(low_price),
            close=self._to_decimal(close_price),
            volume=int(volume) if volume else 0,
            amount=self._to_decimal(amount),
            period=period,
        )

        return kline

    def transform_batch(
        self,
        data_list: List[Dict[str, Any]],
        source: SourceFormat
    ) -> List[TickData]:
        """
        批量转换Tick数据

        Args:
            data_list: 原始数据列表
            source: 数据源类型

        Returns:
            List[TickData]: 标准格式的tick数据列表
        """
        result = []
        for data in data_list:
            try:
                tick = self.transform_tick(data, source)
                result.append(tick)
            except Exception as e:
                logger.warning(f"转换数据失败: {e}, data: {data}")
                continue
        return result

    def validate_tick(self, tick: TickData) -> bool:
        """
        验证Tick数据有效性

        Args:
            tick: Tick数据

        Returns:
            bool: 是否有效
        """
        if not tick:
            return False

        # 检查必填字段
        if not tick.symbol:
            return False

        if tick.price is None or tick.price <= 0:
            return False

        if tick.volume is None or tick.volume < 0:
            return False

        # 检查买卖盘合理性
        if tick.bid_price and tick.ask_price:
            if tick.bid_price > tick.ask_price:
                return False

        return True

    def validate_kline(self, kline: KLineData) -> bool:
        """
        验证K线数据有效性

        Args:
            kline: K线数据

        Returns:
            bool: 是否有效
        """
        if not kline:
            return False

        # 检查必填字段
        if not kline.symbol:
            return False

        # 检查OHLC关系
        if kline.high < kline.low:
            return False

        if kline.high < kline.open or kline.high < kline.close:
            return False

        if kline.low > kline.open or kline.low > kline.close:
            return False

        # 检查价格非负
        if kline.open < 0 or kline.high < 0 or kline.low < 0 or kline.close < 0:
            return False

        # 检查成交量非负
        if kline.volume < 0:
            return False

        return True

    @staticmethod
    def _to_decimal(value: Any) -> Optional[Decimal]:
        """安全转换为Decimal"""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except:
            return None


# 便捷函数
def normalize_symbol(symbol: str) -> str:
    """标准化股票代码"""
    return CodeNormalizer.normalize(symbol)


def transform_tick_data(data: Dict[str, Any], source: SourceFormat) -> TickData:
    """转换Tick数据（便捷函数）"""
    transformer = DataTransformer()
    return transformer.transform_tick(data, source)
