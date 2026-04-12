"""
太子院 - 数据前置校验与分发

职责：
- 所有进入市场系统的数据首先经过太子院
- 数据格式校验与标准化
- 数据清洗与预处理
- 根据数据类型分发到不同部门

数据流向：
外部数据 → 太子院(校验/标准化) → 中书省(信号生成) / 尚书省(执行)
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
import re

import pandas as pd

from src.market_data.models import TickData, KLineData, MarketDepth
from src.common.logger import TradingLogger
from src.common.metrics import metrics
from src.core.data_quality import DataQualityMonitor, DataQualityScore

logger = TradingLogger(__name__)


class DataType(Enum):
    """数据类型"""
    TICK = "tick"           # Tick数据
    KLINE = "kline"         # K线数据
    DEPTH = "depth"         # 深度数据
    ORDER = "order"         # 订单数据
    SIGNAL = "signal"       # 信号数据
    NEWS = "news"           # 新闻数据
    REPORT = "report"       # 财报数据


class ValidationLevel(Enum):
    """校验级别"""
    STRICT = "strict"       # 严格模式 - 任何异常都拒绝
    NORMAL = "normal"       # 正常模式 - 记录异常但继续处理
    LENIENT = "lenient"     # 宽松模式 - 尽可能修复数据


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    data_type: Optional[DataType] = None
    data: Optional[Any] = None
    errors: List[str] = None
    warnings: List[str] = None
    normalized_symbol: Optional[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class DispatchResult:
    """分发结果"""
    success: bool
    target: Optional[str] = None  # 目标部门
    data: Optional[Any] = None
    error: Optional[str] = None


class SymbolNormalizer:
    """代码标准化器"""

    # 交易所代码映射
    EXCHANGE_MAP = {
        "SH": "SH", "sh": "SH", "上海": "SH", "沪市": "SH",
        "SZ": "SZ", "sz": "SZ", "深圳": "SZ", "深市": "SZ",
        "BJ": "BJ", "bj": "BJ", "北京": "BJ", "北交所": "BJ",
        "HK": "HK", "hk": "HK", "香港": "HK", "港股": "HK",
    }

    @classmethod
    def normalize(cls, symbol: str) -> Optional[str]:
        """
        标准化标的代码

        支持格式：
        - 000001.SZ -> 000001.SZ (标准格式)
        - 000001.sz -> 000001.SZ
        - sz000001 -> 000001.SZ
        - 000001 -> 尝试推断交易所
        """
        if not symbol or not isinstance(symbol, str):
            return None

        symbol = symbol.strip()

        # 已经是标准格式
        if re.match(r'^\d{6}\.[A-Z]{2}$', symbol):
            return symbol

        # 小写交易所后缀，如 000001.sz
        if re.match(r'^\d{6}\.[a-z]{2}$', symbol):
            code, exchange = symbol.split('.')
            return f"{code}.{exchange.upper()}"

        # 交易所前缀格式，如 sz000001
        prefix_match = re.match(r'^([a-zA-Z]{2})(\d{6})$', symbol)
        if prefix_match:
            exchange, code = prefix_match.groups()
            exchange = exchange.upper()
            if exchange in ['SH', 'SZ', 'BJ', 'HK']:
                return f"{code}.{exchange}"

        # 纯数字代码，尝试推断交易所
        if re.match(r'^\d{6}$', symbol):
            return cls._infer_exchange(symbol)

        return None

    @classmethod
    def _infer_exchange(cls, code: str) -> Optional[str]:
        """根据代码规则推断交易所"""
        # 上海主板: 60XXXX, 68XXXX(科创), 69XXXX
        if code.startswith(('60', '68', '69')):
            return f"{code}.SH"

        # 深圳主板: 00XXXX, 30XXXX(创业板)
        if code.startswith(('00', '30')):
            return f"{code}.SZ"

        # 北京交易所: 8XXXXX, 4XXXXX
        if code.startswith(('8', '4')):
            return f"{code}.BJ"

        # 默认上海
        return f"{code}.SH"

    @classmethod
    def get_exchange(cls, symbol: str) -> Optional[str]:
        """获取交易所代码"""
        normalized = cls.normalize(symbol)
        if normalized and '.' in normalized:
            return normalized.split('.')[1]
        return None


class DataValidator:
    """数据校验器"""

    @staticmethod
    def validate_tick(tick: TickData, level: ValidationLevel = ValidationLevel.NORMAL) -> ValidationResult:
        """校验Tick数据"""
        errors = []
        warnings = []

        # 必填字段检查
        if not tick.symbol:
            errors.append("标的代码不能为空")

        if not tick.timestamp:
            errors.append("时间戳不能为空")

        if tick.price is None or tick.price <= 0:
            errors.append(f"价格无效: {tick.price}")

        if tick.volume is None or tick.volume < 0:
            errors.append(f"成交量无效: {tick.volume}")

        # 价格合理性检查
        if tick.price and tick.price > 10000:
            warnings.append(f"价格异常高: {tick.price}")

        # 涨跌幅检查
        if tick.change_pct and abs(tick.change_pct) > 20:
            warnings.append(f"涨跌幅异常: {tick.change_pct}%")

        # 根据级别决定结果
        if level == ValidationLevel.STRICT and (errors or warnings):
            is_valid = False
        else:
            is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            data_type=DataType.TICK,
            data=tick,
            errors=errors,
            warnings=warnings,
            normalized_symbol=SymbolNormalizer.normalize(tick.symbol) if tick.symbol else None
        )

    @staticmethod
    def validate_kline(kline: KLineData, level: ValidationLevel = ValidationLevel.NORMAL) -> ValidationResult:
        """校验K线数据"""
        errors = []
        warnings = []

        # 必填字段
        if not kline.symbol:
            errors.append("标的代码不能为空")

        if not kline.timestamp:
            errors.append("时间戳不能为空")

        # OHLC价格检查
        if kline.open is None or kline.open <= 0:
            errors.append("开盘价无效")

        if kline.high is None or kline.high <= 0:
            errors.append("最高价无效")

        if kline.low is None or kline.low <= 0:
            errors.append("最低价无效")

        if kline.close is None or kline.close <= 0:
            errors.append("收盘价无效")

        # 价格逻辑检查
        if kline.high and kline.low and kline.high < kline.low:
            errors.append("最高价不能低于最低价")

        if kline.open and kline.high and kline.low and kline.close:
            valid_range = kline.low <= kline.open <= kline.high
            if not valid_range:
                warnings.append("开盘价不在高低价范围内")

            valid_range = kline.low <= kline.close <= kline.high
            if not valid_range:
                warnings.append("收盘价不在高低价范围内")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            data_type=DataType.KLINE,
            data=kline,
            errors=errors,
            warnings=warnings,
            normalized_symbol=SymbolNormalizer.normalize(kline.symbol) if kline.symbol else None
        )

    @staticmethod
    def validate_klines_df(klines: pd.DataFrame, symbol: str) -> ValidationResult:
        """校验K线DataFrame"""
        errors = []
        warnings = []

        if klines is None or klines.empty:
            errors.append("数据为空")
            return ValidationResult(is_valid=False, errors=errors)

        # 检查必要列
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in klines.columns:
                errors.append(f"缺少必要列: {col}")

        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        # 检查价格有效性
        if (klines['high'] < klines['low']).any():
            errors.append("存在最高价低于最低价的数据")

        if (klines[['open', 'high', 'low', 'close']] <= 0).any().any():
            errors.append("存在非正价格数据")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            data_type=DataType.KLINE,
            data=klines,
            errors=errors,
            warnings=warnings,
            normalized_symbol=SymbolNormalizer.normalize(symbol)
        )


class CrownPrince:
    """
    太子院 - 数据前置校验与分发中心

    单例模式，整个系统只有一个太子院实例
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.validator = DataValidator()
        self.normalizer = SymbolNormalizer()
        self.quality_monitor = DataQualityMonitor()

        # 禁售股票列表
        self.banned_stocks = set()
        self.min_avg_volume = 1_000_000

        # 分发处理器注册表
        self._handlers: Dict[DataType, List[Callable]] = {
            DataType.TICK: [],
            DataType.KLINE: [],
            DataType.DEPTH: [],
            DataType.ORDER: [],
            DataType.SIGNAL: [],
            DataType.NEWS: [],
            DataType.REPORT: [],
        }

        # 统计
        self._stats = {
            "total_received": 0,
            "valid": 0,
            "invalid": 0,
            "dispatched": 0,
        }

        logger.info("太子院初始化完成")

    def register_handler(self, data_type: DataType, handler: Callable):
        """
        注册数据处理器

        Args:
            data_type: 数据类型
            handler: 处理函数，接收(data, validation_result)参数
        """
        if data_type in self._handlers:
            self._handlers[data_type].append(handler)
            logger.info(f"注册{data_type.value}处理器: {handler.__name__}")

    def unregister_handler(self, data_type: DataType, handler: Callable):
        """注销数据处理器"""
        if data_type in self._handlers and handler in self._handlers[data_type]:
            self._handlers[data_type].remove(handler)

    def process_tick(self, tick: TickData, level: ValidationLevel = ValidationLevel.NORMAL) -> ValidationResult:
        """
        处理Tick数据

        流程：标准化 → 校验 → 分发
        """
        self._stats["total_received"] += 1

        # 1. 标准化代码
        if tick.symbol:
            normalized = self.normalizer.normalize(tick.symbol)
            if normalized:
                tick.symbol = normalized

        # 检查禁售
        if tick.symbol and tick.symbol in self.banned_stocks:
            return ValidationResult(
                is_valid=False,
                data_type=DataType.TICK,
                errors=[f"股票{tick.symbol}在禁售列表中"]
            )

        # 2. 校验
        result = self.validator.validate_tick(tick, level)

        if not result.is_valid:
            self._stats["invalid"] += 1
            # 记录数据校验失败指标
            metrics.increment("data.validation", tags={
                "type": "tick",
                "result": "invalid",
                "symbol": tick.symbol
            })
            logger.warning(f"Tick数据校验失败: {result.errors}")
            return result

        self._stats["valid"] += 1

        # 记录数据校验通过指标
        metrics.increment("data.validation", tags={
            "type": "tick",
            "result": "valid",
            "symbol": tick.symbol
        })

        # 3. 数据质量评估
        quality_score = self.quality_monitor.evaluate_tick(tick)
        # 记录数据质量指标
        metrics.gauge("data.quality_score", quality_score.overall, tags={
            "symbol": tick.symbol,
            "type": "tick"
        })
        if quality_score.overall < 0.6:
            logger.warning(f"[{tick.symbol}] 数据质量较低: {quality_score.overall:.2f}")

        # 4. 分发
        self._dispatch(DataType.TICK, tick, result)

        return result

    def process_kline(self, kline: KLineData, level: ValidationLevel = ValidationLevel.NORMAL) -> ValidationResult:
        """处理K线数据"""
        self._stats["total_received"] += 1

        # 标准化
        if kline.symbol:
            normalized = self.normalizer.normalize(kline.symbol)
            if normalized:
                kline.symbol = normalized

        # 检查禁售
        if kline.symbol and kline.symbol in self.banned_stocks:
            return ValidationResult(
                is_valid=False,
                data_type=DataType.KLINE,
                errors=[f"股票{kline.symbol}在禁售列表中"]
            )

        # 校验
        result = self.validator.validate_kline(kline, level)

        if not result.is_valid:
            self._stats["invalid"] += 1
            # 记录数据校验失败指标
            metrics.increment("data.validation", tags={
                "type": "kline",
                "result": "invalid",
                "symbol": kline.symbol
            })
            logger.warning(f"K线数据校验失败: {result.errors}")
            return result

        self._stats["valid"] += 1

        # 记录数据校验通过指标
        metrics.increment("data.validation", tags={
            "type": "kline",
            "result": "valid",
            "symbol": kline.symbol
        })

        # 分发
        self._dispatch(DataType.KLINE, kline, result)

        return result

    def validate_and_distribute(self, klines: pd.DataFrame, symbol: str) -> Optional[pd.DataFrame]:
        """
        验证K线DataFrame并分发

        兼容旧版API
        """
        self._stats["total_received"] += 1

        # 标准化代码
        normalized_symbol = self.normalizer.normalize(symbol)
        if normalized_symbol:
            symbol = normalized_symbol

        # 检查禁售
        if symbol in self.banned_stocks:
            logger.warning(f"股票{symbol}在禁售列表中，跳过")
            return None

        # 校验
        result = self.validator.validate_klines_df(klines, symbol)

        if not result.is_valid:
            self._stats["invalid"] += 1
            # 记录数据校验失败指标
            metrics.increment("data.validation", tags={
                "type": "klines_df",
                "result": "invalid",
                "symbol": symbol
            })
            logger.warning(f"K线数据校验失败: {result.errors}")
            return None

        # 流动性检查
        if not self._check_liquidity(klines):
            logger.warning(f"股票{symbol}流动性不足")
            # 记录流动性不足指标
            metrics.increment("data.validation", tags={
                "type": "klines_df",
                "result": "liquidity_insufficient",
                "symbol": symbol
            })
            return None

        self._stats["valid"] += 1

        # 记录数据校验通过指标
        metrics.increment("data.validation", tags={
            "type": "klines_df",
            "result": "valid",
            "symbol": symbol
        })

        # 分发
        self._dispatch(DataType.KLINE, klines, result)

        return klines

    def _check_liquidity(self, klines: pd.DataFrame) -> bool:
        """检查股票流动性"""
        avg_volume = klines['volume'].mean()
        return avg_volume >= self.min_avg_volume

    def _dispatch(self, data_type: DataType, data: Any, validation_result: ValidationResult):
        """分发数据到注册的处理器"""
        handlers = self._handlers.get(data_type, [])

        for handler in handlers:
            try:
                handler(data, validation_result)
                self._stats["dispatched"] += 1
            except Exception as e:
                logger.error(f"数据分发失败 [{handler.__name__}]: {e}")

    def add_banned_stock(self, code: str, reason: str = ""):
        """添加禁售股票"""
        normalized = self.normalizer.normalize(code)
        if normalized:
            self.banned_stocks.add(normalized)
            logger.info(f"添加禁售股票: {normalized}, 原因: {reason}")

    def remove_banned_stock(self, code: str):
        """移除禁售股票"""
        normalized = self.normalizer.normalize(code)
        if normalized:
            self.banned_stocks.discard(normalized)
            logger.info(f"移除禁售股票: {normalized}")

    def is_banned(self, code: str) -> bool:
        """检查股票是否在禁售列表"""
        normalized = self.normalizer.normalize(code)
        return normalized in self.banned_stocks if normalized else False

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self._stats.copy()

    def reset_stats(self):
        """重置统计"""
        self._stats = {
            "total_received": 0,
            "valid": 0,
            "invalid": 0,
            "dispatched": 0,
        }

    def get_data_quality(self, symbol: str) -> Optional[DataQualityScore]:
        """
        获取数据质量评分

        Args:
            symbol: 标的代码

        Returns:
            DataQualityScore: 数据质量评分，无记录时返回None

        Example:
            score = crown_prince.get_data_quality("000001.SZ")
            print(score.overall)  # 0.95
            print(score.issues)   # []
        """
        normalized = self.normalizer.normalize(symbol)
        if not normalized:
            logger.warning(f"无效的标的代码: {symbol}")
            return None

        return self.quality_monitor.get_latest_score(normalized)

    def get_data_quality_history(self, symbol: str, limit: int = 10) -> List[DataQualityScore]:
        """
        获取数据质量评分历史

        Args:
            symbol: 标的代码
            limit: 返回记录数量

        Returns:
            List[DataQualityScore]: 质量评分历史列表
        """
        normalized = self.normalizer.normalize(symbol)
        if not normalized:
            return []

        return self.quality_monitor.get_score_history(normalized, limit)

    def get_data_quality_summary(self, symbol: str) -> Dict[str, Any]:
        """
        获取数据质量汇总报告

        Args:
            symbol: 标的代码

        Returns:
            Dict: 包含质量评分汇总信息的字典
        """
        normalized = self.normalizer.normalize(symbol)
        if not normalized:
            return {"symbol": symbol, "has_data": False, "message": "无效的标的代码"}

        return self.quality_monitor.get_quality_summary(normalized)


# 全局太子院实例
crown_prince = CrownPrince()
