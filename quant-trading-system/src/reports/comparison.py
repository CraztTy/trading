"""
报告对比模块

提供报告对比分析功能：
- 报告间指标对比
- 趋势分析
- 图表数据生成
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass
class ReportComparison:
    """报告对比结果"""
    # 日期/周期
    date1: Optional[date] = None
    date2: Optional[date] = None

    # 交易对比
    trade_count1: int = 0
    trade_count2: int = 0
    trade_count_change: int = 0
    trade_count_change_pct: float = 0.0

    # 盈亏对比
    pnl1: Decimal = Decimal("0")
    pnl2: Decimal = Decimal("0")
    pnl_change: Decimal = Decimal("0")
    pnl_change_pct: float = 0.0

    # 胜率对比
    win_rate1: float = 0.0
    win_rate2: float = 0.0
    win_rate_change: float = 0.0

    # 费用对比
    fee1: Decimal = Decimal("0")
    fee2: Decimal = Decimal("0")
    fee_change: Decimal = Decimal("0")

    # 资产对比
    total_value1: Decimal = Decimal("0")
    total_value2: Decimal = Decimal("0")
    value_change: Decimal = Decimal("0")
    value_change_pct: float = 0.0

    # 收益率对比
    return1: float = 0.0
    return2: float = 0.0
    return_change: float = 0.0

    # 综合分析
    improvement_areas: List[str] = field(default_factory=list)
    degradation_areas: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "date1": self.date1.isoformat() if self.date1 else None,
            "date2": self.date2.isoformat() if self.date2 else None,
            "trade_count": {
                "period1": self.trade_count1,
                "period2": self.trade_count2,
                "change": self.trade_count_change,
                "change_pct": round(self.trade_count_change_pct, 4)
            },
            "pnl": {
                "period1": float(self.pnl1),
                "period2": float(self.pnl2),
                "change": float(self.pnl_change),
                "change_pct": round(self.pnl_change_pct, 4)
            },
            "win_rate": {
                "period1": round(self.win_rate1, 4),
                "period2": round(self.win_rate2, 4),
                "change": round(self.win_rate_change, 4)
            },
            "total_value": {
                "period1": float(self.total_value1),
                "period2": float(self.total_value2),
                "change": float(self.value_change),
                "change_pct": round(self.value_change_pct, 4)
            },
            "return": {
                "period1": round(self.return1, 4),
                "period2": round(self.return2, 4),
                "change": round(self.return_change, 4)
            },
            "improvement_areas": self.improvement_areas,
            "degradation_areas": self.degradation_areas
        }


@dataclass
class ChartData:
    """图表数据"""
    dates: List[str] = field(default_factory=list)
    pnl_values: List[float] = field(default_factory=list)
    nav_values: List[float] = field(default_factory=list)
    trade_counts: List[int] = field(default_factory=list)
    win_rates: List[float] = field(default_factory=list)
    returns: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dates": self.dates,
            "pnl_values": self.pnl_values,
            "nav_values": self.nav_values,
            "trade_counts": self.trade_counts,
            "win_rates": self.win_rates,
            "returns": self.returns
        }


class ReportComparator:
    """报告比较器"""

    @classmethod
    def compare(cls, report1: Any, report2: Any) -> ReportComparison:
        """
        对比两个报告

        Args:
            report1: 第一个报告
            report2: 第二个报告

        Returns:
            ReportComparison: 对比结果
        """
        comparison = ReportComparison()

        # 提取日期
        if hasattr(report1, 'report_date'):
            comparison.date1 = report1.report_date
        elif hasattr(report1, 'start_date'):
            comparison.date1 = report1.start_date

        if hasattr(report2, 'report_date'):
            comparison.date2 = report2.report_date
        elif hasattr(report2, 'start_date'):
            comparison.date2 = report2.start_date

        # 对比交易数量
        if hasattr(report1, 'trade_count'):
            comparison.trade_count1 = report1.trade_count
        elif hasattr(report1, 'total_trades'):
            comparison.trade_count1 = report1.total_trades

        if hasattr(report2, 'trade_count'):
            comparison.trade_count2 = report2.trade_count
        elif hasattr(report2, 'total_trades'):
            comparison.trade_count2 = report2.total_trades

        comparison.trade_count_change = comparison.trade_count2 - comparison.trade_count1
        if comparison.trade_count1 > 0:
            comparison.trade_count_change_pct = comparison.trade_count_change / comparison.trade_count1

        # 对比盈亏
        if hasattr(report1, 'realized_pnl'):
            comparison.pnl1 = report1.realized_pnl
        elif hasattr(report1, 'net_pnl'):
            comparison.pnl1 = report1.net_pnl

        if hasattr(report2, 'realized_pnl'):
            comparison.pnl2 = report2.realized_pnl
        elif hasattr(report2, 'net_pnl'):
            comparison.pnl2 = report2.net_pnl

        comparison.pnl_change = comparison.pnl2 - comparison.pnl1
        if comparison.pnl1 != 0:
            comparison.pnl_change_pct = float(comparison.pnl_change / abs(comparison.pnl1))

        # 对比胜率
        if hasattr(report1, 'win_rate'):
            comparison.win_rate1 = report1.win_rate
        if hasattr(report2, 'win_rate'):
            comparison.win_rate2 = report2.win_rate
        comparison.win_rate_change = comparison.win_rate2 - comparison.win_rate1

        # 对比费用
        if hasattr(report1, 'total_fee'):
            comparison.fee1 = report1.total_fee
        if hasattr(report2, 'total_fee'):
            comparison.fee2 = report2.total_fee
        comparison.fee_change = comparison.fee2 - comparison.fee1

        # 对比总资产
        if hasattr(report1, 'total_value'):
            comparison.total_value1 = report1.total_value
        elif hasattr(report1, 'end_balance'):
            comparison.total_value1 = report1.end_balance

        if hasattr(report2, 'total_value'):
            comparison.total_value2 = report2.total_value
        elif hasattr(report2, 'end_balance'):
            comparison.total_value2 = report2.end_balance

        comparison.value_change = comparison.total_value2 - comparison.total_value1
        if comparison.total_value1 > 0:
            comparison.value_change_pct = float(comparison.value_change / comparison.total_value1)

        # 对比收益率
        if hasattr(report1, 'total_return'):
            comparison.return1 = report1.total_return
        elif hasattr(report1, 'weekly_return'):
            comparison.return1 = report1.weekly_return
        elif hasattr(report1, 'monthly_return'):
            comparison.return1 = report1.monthly_return

        if hasattr(report2, 'total_return'):
            comparison.return2 = report2.total_return
        elif hasattr(report2, 'weekly_return'):
            comparison.return2 = report2.weekly_return
        elif hasattr(report2, 'monthly_return'):
            comparison.return2 = report2.monthly_return

        comparison.return_change = comparison.return2 - comparison.return1

        # 分析改进和退化领域
        cls._analyze_changes(comparison)

        return comparison

    @staticmethod
    def _analyze_changes(comparison: ReportComparison) -> None:
        """分析变化趋势"""
        # 盈亏改善/恶化
        if comparison.pnl_change > 0:
            comparison.improvement_areas.append("profitability")
        elif comparison.pnl_change < 0:
            comparison.degradation_areas.append("profitability")

        # 胜率改善/恶化
        if comparison.win_rate_change > 0.05:
            comparison.improvement_areas.append("win_rate")
        elif comparison.win_rate_change < -0.05:
            comparison.degradation_areas.append("win_rate")

        # 交易频率
        if comparison.trade_count_change > 0:
            comparison.improvement_areas.append("activity")
        elif comparison.trade_count_change < 0:
            comparison.degradation_areas.append("activity")

        # 收益率
        if comparison.return_change > 0:
            comparison.improvement_areas.append("return")
        elif comparison.return_change < 0:
            comparison.degradation_areas.append("return")

    @classmethod
    def generate_chart_data(cls, reports: List[Any]) -> ChartData:
        """
        生成图表数据

        Args:
            reports: 报告列表（按时间排序）

        Returns:
            ChartData: 图表数据
        """
        chart_data = ChartData()

        if not reports:
            return chart_data

        for report in reports:
            # 日期
            if hasattr(report, 'report_date'):
                chart_data.dates.append(report.report_date.isoformat())
            elif hasattr(report, 'start_date'):
                chart_data.dates.append(report.start_date.isoformat())
            else:
                chart_data.dates.append('')

            # 盈亏
            if hasattr(report, 'realized_pnl'):
                chart_data.pnl_values.append(float(report.realized_pnl))
            elif hasattr(report, 'net_pnl'):
                chart_data.pnl_values.append(float(report.net_pnl))
            else:
                chart_data.pnl_values.append(0.0)

            # 净值
            if hasattr(report, 'total_value'):
                chart_data.nav_values.append(float(report.total_value))
            elif hasattr(report, 'end_balance'):
                chart_data.nav_values.append(float(report.end_balance))
            else:
                chart_data.nav_values.append(0.0)

            # 交易数
            if hasattr(report, 'trade_count'):
                chart_data.trade_counts.append(report.trade_count)
            elif hasattr(report, 'total_trades'):
                chart_data.trade_counts.append(report.total_trades)
            else:
                chart_data.trade_counts.append(0)

            # 胜率
            if hasattr(report, 'win_rate'):
                chart_data.win_rates.append(report.win_rate)
            else:
                chart_data.win_rates.append(0.0)

            # 收益率
            if hasattr(report, 'total_return'):
                chart_data.returns.append(report.total_return)
            elif hasattr(report, 'weekly_return'):
                chart_data.returns.append(report.weekly_return)
            elif hasattr(report, 'monthly_return'):
                chart_data.returns.append(report.monthly_return)
            elif hasattr(report, 'return_pct'):
                chart_data.returns.append(float(report.return_pct))
            else:
                chart_data.returns.append(0.0)

        return chart_data

    @classmethod
    def compare_periods(
        cls,
        reports: List[Any],
        period_type: str = 'weekly'
    ) -> List[ReportComparison]:
        """
        对比多个连续周期

        Args:
            reports: 报告列表（按时间排序）
            period_type: 周期类型

        Returns:
            List[ReportComparison]: 对比结果列表
        """
        comparisons = []

        if len(reports) < 2:
            return comparisons

        for i in range(1, len(reports)):
            comparison = cls.compare(reports[i-1], reports[i])
            comparisons.append(comparison)

        return comparisons

    @classmethod
    def generate_trend_analysis(
        cls,
        reports: List[Any]
    ) -> Dict[str, Any]:
        """
        生成趋势分析

        Args:
            reports: 报告列表（按时间排序）

        Returns:
            Dict: 趋势分析结果
        """
        if not reports:
            return {"error": "No reports provided"}

        # 提取关键指标序列
        pnls = []
        win_rates = []
        returns = []
        values = []

        for report in reports:
            if hasattr(report, 'realized_pnl'):
                pnls.append(float(report.realized_pnl))
            elif hasattr(report, 'net_pnl'):
                pnls.append(float(report.net_pnl))

            if hasattr(report, 'win_rate'):
                win_rates.append(report.win_rate)

            if hasattr(report, 'total_return'):
                returns.append(report.total_return)
            elif hasattr(report, 'weekly_return'):
                returns.append(report.weekly_return)
            elif hasattr(report, 'monthly_return'):
                returns.append(report.monthly_return)

            if hasattr(report, 'total_value'):
                values.append(float(report.total_value))
            elif hasattr(report, 'end_balance'):
                values.append(float(report.end_balance))

        # 计算趋势
        analysis = {
            "period_count": len(reports),
            "pnl": cls._calculate_trend(pnls),
            "win_rate": cls._calculate_trend(win_rates),
            "returns": cls._calculate_trend(returns),
            "values": cls._calculate_trend(values)
        }

        # 综合评分
        score = 0
        factors = 0

        if pnls:
            positive_pnls = sum(1 for p in pnls if p > 0)
            score += positive_pnls / len(pnls) * 100
            factors += 1

        if win_rates:
            avg_win_rate = sum(win_rates) / len(win_rates)
            score += avg_win_rate * 100
            factors += 1

        if returns:
            positive_returns = sum(1 for r in returns if r > 0)
            score += positive_returns / len(returns) * 100
            factors += 1

        if factors > 0:
            analysis["overall_score"] = round(score / factors, 2)
        else:
            analysis["overall_score"] = 0

        return analysis

    @staticmethod
    def _calculate_trend(values: List[float]) -> Dict[str, Any]:
        """计算趋势"""
        if not values:
            return {"trend": "unknown"}

        result = {
            "values": values,
            "mean": round(sum(values) / len(values), 4) if values else 0,
            "min": round(min(values), 4),
            "max": round(max(values), 4)
        }

        if len(values) >= 2:
            # 简单线性趋势
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]

            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0

            if second_avg > first_avg * 1.05:
                result["trend"] = "improving"
                result["trend_strength"] = round((second_avg - first_avg) / abs(first_avg) if first_avg != 0 else 0, 4)
            elif second_avg < first_avg * 0.95:
                result["trend"] = "declining"
                result["trend_strength"] = round((first_avg - second_avg) / abs(first_avg) if first_avg != 0 else 0, 4)
            else:
                result["trend"] = "stable"
                result["trend_strength"] = 0

        return result

    @classmethod
    def generate_summary_report(
        cls,
        reports: List[Any]
    ) -> Dict[str, Any]:
        """
        生成汇总报告

        Args:
            reports: 报告列表

        Returns:
            Dict: 汇总报告
        """
        if not reports:
            return {"error": "No reports provided"}

        # 总交易数
        total_trades = sum(
            getattr(r, 'trade_count', 0) or getattr(r, 'total_trades', 0)
            for r in reports
        )

        # 总盈亏
        total_pnl = sum(
            float(getattr(r, 'realized_pnl', 0) or getattr(r, 'net_pnl', 0))
            for r in reports
        )

        # 平均胜率
        win_rates = [getattr(r, 'win_rate', 0) for r in reports if hasattr(r, 'win_rate')]
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0

        # 总费用
        total_fees = sum(
            float(getattr(r, 'total_fee', 0))
            for r in reports
        )

        # 收益率
        returns = []
        for r in reports:
            if hasattr(r, 'total_return'):
                returns.append(r.total_return)
            elif hasattr(r, 'weekly_return'):
                returns.append(r.weekly_return)
            elif hasattr(r, 'monthly_return'):
                returns.append(r.monthly_return)

        total_return = sum(returns)

        return {
            "report_count": len(reports),
            "total_trades": total_trades,
            "total_pnl": round(total_pnl, 2),
            "total_fees": round(total_fees, 2),
            "net_pnl": round(total_pnl - total_fees, 2),
            "avg_win_rate": round(avg_win_rate, 4),
            "total_return": round(total_return, 4),
            "periods": [
                {
                    "date": getattr(r, 'report_date', getattr(r, 'start_date', None)),
                    "pnl": float(getattr(r, 'realized_pnl', getattr(r, 'net_pnl', 0)))
                }
                for r in reports
            ]
        }
