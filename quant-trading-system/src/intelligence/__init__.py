"""
智能分析系统

提供智能选股和分析功能：
- 股票筛选：多维度筛选器
- 多因子模型：多因子评分
- 基本面分析：财务分析、估值分析
"""

# 筛选模块
from src.intelligence.screening.screener import (
    StockScreener,
    StockData,
    ScreenResult,
    FilterCriterion,
    FilterOperator,
    SortCriterion,
    SortOrder,
    PresetScreeners,
)

from src.intelligence.screening.factors import (
    MultiFactorModel,
    FactorDefinition,
    FactorType,
    FactorDirection,
    MultiFactorResult,
    FactorScore,
    FactorNormalizer,
    FactorBuilder,
)

# 基本面分析
from src.intelligence.fundamental.analyzer import (
    FundamentalAnalyzer,
    BatchFundamentalAnalyzer,
    FundamentalReport,
    FinancialMetrics,
    ValuationAnalysis,
    GrowthAnalysis,
    ProfitabilityAnalysis,
    FinancialHealthAnalysis,
    FinancialHealthGrade,
)

__all__ = [
    # 筛选器
    "StockScreener",
    "StockData",
    "ScreenResult",
    "FilterCriterion",
    "FilterOperator",
    "SortCriterion",
    "SortOrder",
    "PresetScreeners",
    # 多因子
    "MultiFactorModel",
    "FactorDefinition",
    "FactorType",
    "FactorDirection",
    "MultiFactorResult",
    "FactorScore",
    "FactorNormalizer",
    "FactorBuilder",
    # 基本面分析
    "FundamentalAnalyzer",
    "BatchFundamentalAnalyzer",
    "FundamentalReport",
    "FinancialMetrics",
    "ValuationAnalysis",
    "GrowthAnalysis",
    "ProfitabilityAnalysis",
    "FinancialHealthAnalysis",
    "FinancialHealthGrade",
]
