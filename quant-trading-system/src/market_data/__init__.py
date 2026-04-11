"""
实时行情数据模块

提供多源行情数据接入、标准化、缓存和分发服务
"""

from src.market_data.models import TickData, KLineData, MarketDepth, MarketSnapshot
from src.market_data.manager import MarketDataManager
from src.market_data.gateway.base import MarketDataGateway
from src.market_data.transformer import (
    DataTransformer, CodeNormalizer, FieldMapper,
    SourceFormat, TransformRule, normalize_symbol
)
from src.market_data.historical import (
    HistoricalDataManager, DataStorage, CacheManager,
    DataUpdatePolicy, StorageBackend, compress_klines, decompress_klines
)
from src.market_data.quality import (
    DataQualityMonitor, QualityCheck, QualityLevel,
    DataValidator, AnomalyDetector, QualityMetrics
)

__all__ = [
    # 数据模型
    'TickData',
    'KLineData',
    'MarketDepth',
    'MarketSnapshot',
    # 核心组件
    'MarketDataManager',
    'MarketDataGateway',
    # 数据转换
    'DataTransformer',
    'CodeNormalizer',
    'FieldMapper',
    'SourceFormat',
    'TransformRule',
    'normalize_symbol',
    # 历史数据
    'HistoricalDataManager',
    'DataStorage',
    'CacheManager',
    'DataUpdatePolicy',
    'StorageBackend',
    'compress_klines',
    'decompress_klines',
    # 质量监控
    'DataQualityMonitor',
    'QualityCheck',
    'QualityLevel',
    'DataValidator',
    'AnomalyDetector',
    'QualityMetrics',
]
