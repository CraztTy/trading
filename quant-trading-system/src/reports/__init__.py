"""
报告系统

提供完整的交易报告功能：
- 报告生成：日报、周报、月报、自定义报告
- 指标计算：交易指标、绩效指标、风险指标
- 报告导出：JSON、CSV、HTML格式
- 报告对比：趋势分析、图表数据
"""

# 报告生成器
from src.reports.generator import (
    ReportGenerator,
    ReportType,
    ReportPeriod,
    DailyReport,
    WeeklyReport,
    MonthlyReport,
    CustomReport,
)

# 指标计算
from src.reports.metrics import (
    TradeMetrics,
    PerformanceMetrics,
    RiskMetrics,
)

# 报告导出
from src.reports.export import (
    ReportExporter,
    ReportBatchExporter,
    DecimalEncoder,
)

# 报告对比
from src.reports.comparison import (
    ReportComparator,
    ReportComparison,
    ChartData,
)

__all__ = [
    # 报告生成
    "ReportGenerator",
    "ReportType",
    "ReportPeriod",
    "DailyReport",
    "WeeklyReport",
    "MonthlyReport",
    "CustomReport",
    # 指标计算
    "TradeMetrics",
    "PerformanceMetrics",
    "RiskMetrics",
    # 报告导出
    "ReportExporter",
    "ReportBatchExporter",
    "DecimalEncoder",
    # 报告对比
    "ReportComparator",
    "ReportComparison",
    "ChartData",
]
