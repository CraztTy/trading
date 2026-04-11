"""
基本面分析模块

提供股票基本面分析功能：
- 财务指标分析
- 估值分析
- 成长性分析
- 盈利能力分析
- 财务健康度评估
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class FinancialHealthGrade(Enum):
    """财务健康等级"""
    EXCELLENT = "A"      # 优秀
    GOOD = "B"           # 良好
    FAIR = "C"           # 一般
    POOR = "D"           # 较差
    DISTRESS = "F"       # 危险


@dataclass
class FinancialMetrics:
    """财务指标"""
    # 盈利能力
    gross_margin: Optional[float] = None      # 毛利率
    operating_margin: Optional[float] = None  # 营业利润率
    net_margin: Optional[float] = None        # 净利率
    roe: Optional[float] = None               # 净资产收益率
    roa: Optional[float] = None               # 总资产收益率
    roic: Optional[float] = None              # 投入资本回报率

    # 成长性
    revenue_growth: Optional[float] = None    # 营收增长率
    profit_growth: Optional[float] = None     # 利润增长率
    asset_growth: Optional[float] = None      # 资产增长率
    equity_growth: Optional[float] = None     # 净资产增长率

    # 估值指标
    pe_ttm: Optional[float] = None            # 市盈率TTM
    pe_forward: Optional[float] = None        # 预测市盈率
    pb: Optional[float] = None                # 市净率
    ps: Optional[float] = None                # 市销率
    pcf: Optional[float] = None               # 市现率
    peg: Optional[float] = None               # PEG比率

    # 财务健康
    current_ratio: Optional[float] = None     # 流动比率
    quick_ratio: Optional[float] = None       # 速动比率
    debt_to_equity: Optional[float] = None    # 资产负债率
    interest_coverage: Optional[float] = None # 利息保障倍数
    cash_ratio: Optional[float] = None        # 现金比率

    # 运营效率
    inventory_turnover: Optional[float] = None    # 存货周转率
    receivables_turnover: Optional[float] = None  # 应收账款周转率
    asset_turnover: Optional[float] = None        # 总资产周转率

    # 现金流
    operating_cash_flow: Optional[Decimal] = None  # 经营现金流
    free_cash_flow: Optional[Decimal] = None       # 自由现金流
    capex: Optional[Decimal] = None                # 资本支出

    # 分红
    dividend_yield: Optional[float] = None         # 股息率
    payout_ratio: Optional[float] = None           # 分红率


@dataclass
class ValuationAnalysis:
    """估值分析结果"""
    pe_assessment: str = ""          # PE评估
    pb_assessment: str = ""          # PB评估
    ps_assessment: str = ""          # PS评估
    peg_assessment: str = ""         # PEG评估

    fair_value_estimate: Optional[Decimal] = None  # 公允价值估算
    upside_potential: Optional[float] = None       # 上涨空间

    valuation_grade: str = "N/A"     # 估值评级
    is_undervalued: bool = False
    is_overvalued: bool = False


@dataclass
class GrowthAnalysis:
    """成长性分析"""
    revenue_growth_assessment: str = ""
    profit_growth_assessment: str = ""
    consistent_growth: bool = False
    growth_sustainability: str = ""  # 增长可持续性

    growth_grade: str = "N/A"
    is_high_growth: bool = False
    is_stable_growth: bool = False


@dataclass
class ProfitabilityAnalysis:
    """盈利能力分析"""
    margin_trend: str = ""           # 利润率趋势
    roe_sustainability: str = ""     # ROE可持续性
    competitive_advantage: bool = False

    profitability_grade: str = "N/A"
    is_high_quality: bool = False


@dataclass
class FinancialHealthAnalysis:
    """财务健康分析"""
    liquidity_assessment: str = ""   # 流动性评估
    solvency_assessment: str = ""    # 偿债能力评估
    working_capital_health: str = "" # 营运资本健康度

    overall_grade: FinancialHealthGrade = FinancialHealthGrade.FAIR
    red_flags: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


@dataclass
class FundamentalReport:
    """基本面分析报告"""
    symbol: str
    name: Optional[str] = None
    report_date: Optional[date] = None

    # 原始数据
    metrics: FinancialMetrics = field(default_factory=FinancialMetrics)

    # 分析结果
    valuation: ValuationAnalysis = field(default_factory=ValuationAnalysis)
    growth: GrowthAnalysis = field(default_factory=GrowthAnalysis)
    profitability: ProfitabilityAnalysis = field(default_factory=ProfitabilityAnalysis)
    health: FinancialHealthAnalysis = field(default_factory=FinancialHealthAnalysis)

    # 综合评分
    overall_score: float = 0.0
    investment_recommendation: str = "HOLD"  # BUY, HOLD, SELL

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "overall_score": round(self.overall_score, 2),
            "recommendation": self.investment_recommendation,
            "valuation": {
                "grade": self.valuation.valuation_grade,
                "is_undervalued": self.valuation.is_undervalued,
                "upside_potential": round(self.valuation.upside_potential, 2) if self.valuation.upside_potential else None,
            },
            "growth": {
                "grade": self.growth.growth_grade,
                "is_high_growth": self.growth.is_high_growth,
            },
            "profitability": {
                "grade": self.profitability.profitability_grade,
                "is_high_quality": self.profitability.is_high_quality,
            },
            "health": {
                "grade": self.health.overall_grade.value,
                "red_flags": self.health.red_flags,
                "strengths": self.health.strengths,
            },
        }


class FundamentalAnalyzer:
    """
    基本面分析器

    分析股票的基本面数据，生成分析报告
    """

    def __init__(self):
        self._industry_benchmarks: Dict[str, Dict[str, float]] = {}

    def analyze(self, symbol: str, metrics: FinancialMetrics, name: Optional[str] = None) -> FundamentalReport:
        """
        分析股票基本面

        Args:
            symbol: 股票代码
            metrics: 财务指标
            name: 股票名称

        Returns:
            FundamentalReport: 分析报告
        """
        report = FundamentalReport(
            symbol=symbol,
            name=name,
            report_date=date.today(),
            metrics=metrics
        )

        # 估值分析
        report.valuation = self._analyze_valuation(metrics)

        # 成长性分析
        report.growth = self._analyze_growth(metrics)

        # 盈利能力分析
        report.profitability = self._analyze_profitability(metrics)

        # 财务健康分析
        report.health = self._analyze_financial_health(metrics)

        # 综合评分
        report.overall_score = self._calculate_overall_score(report)

        # 投资建议
        report.investment_recommendation = self._generate_recommendation(report)

        return report

    def _analyze_valuation(self, metrics: FinancialMetrics) -> ValuationAnalysis:
        """估值分析"""
        analysis = ValuationAnalysis()

        # PE分析
        if metrics.pe_ttm is not None:
            if metrics.pe_ttm < 10:
                analysis.pe_assessment = "极低估值"
                analysis.is_undervalued = True
            elif metrics.pe_ttm < 20:
                analysis.pe_assessment = "合理偏低"
            elif metrics.pe_ttm < 30:
                analysis.pe_assessment = "合理估值"
            elif metrics.pe_ttm < 50:
                analysis.pe_assessment = "偏高估值"
                analysis.is_overvalued = True
            else:
                analysis.pe_assessment = "高估值"
                analysis.is_overvalued = True

        # PB分析
        if metrics.pb is not None:
            if metrics.pb < 1:
                analysis.pb_assessment = "破净"
                analysis.is_undervalued = True
            elif metrics.pb < 2:
                analysis.pb_assessment = "合理偏低"
            elif metrics.pb < 4:
                analysis.pb_assessment = "合理估值"
            else:
                analysis.pb_assessment = "高估值"

        # PEG分析
        if metrics.peg is not None:
            if metrics.peg < 0.8:
                analysis.peg_assessment = "低估"
                analysis.is_undervalued = True
            elif metrics.peg < 1.2:
                analysis.peg_assessment = "合理"
            else:
                analysis.peg_assessment = "高估"
                analysis.is_overvalued = True

        # 综合估值评级
        scores = []
        if metrics.pe_ttm:
            scores.append(self._score_pe(metrics.pe_ttm))
        if metrics.pb:
            scores.append(self._score_pb(metrics.pb))
        if metrics.peg:
            scores.append(self._score_peg(metrics.peg))

        if scores:
            avg_score = sum(scores) / len(scores)
            analysis.valuation_grade = self._grade_from_score(avg_score)

            # 估算上涨空间（简化计算）
            if analysis.is_undervalued and metrics.pe_ttm:
                fair_pe = 15  # 假设合理PE为15
                analysis.fair_value_estimate = None  # 需要当前价格计算
                analysis.upside_potential = (fair_pe / metrics.pe_ttm - 1) * 100

        return analysis

    def _analyze_growth(self, metrics: FinancialMetrics) -> GrowthAnalysis:
        """成长性分析"""
        analysis = GrowthAnalysis()

        growth_scores = []

        # 营收增长
        if metrics.revenue_growth is not None:
            if metrics.revenue_growth > 0.3:
                analysis.revenue_growth_assessment = "高速增长"
                growth_scores.append(100)
            elif metrics.revenue_growth > 0.15:
                analysis.revenue_growth_assessment = "快速增长"
                growth_scores.append(80)
            elif metrics.revenue_growth > 0.05:
                analysis.revenue_growth_assessment = "稳健增长"
                growth_scores.append(60)
            elif metrics.revenue_growth > 0:
                analysis.revenue_growth_assessment = "缓慢增长"
                growth_scores.append(40)
            else:
                analysis.revenue_growth_assessment = "负增长"
                growth_scores.append(20)

        # 利润增长
        if metrics.profit_growth is not None:
            if metrics.profit_growth > 0.3:
                analysis.profit_growth_assessment = "高速增长"
                growth_scores.append(100)
            elif metrics.profit_growth > 0.15:
                analysis.profit_growth_assessment = "快速增长"
                growth_scores.append(80)
            elif metrics.profit_growth > 0.05:
                analysis.profit_growth_assessment = "稳健增长"
                growth_scores.append(60)
            elif metrics.profit_growth > 0:
                analysis.profit_growth_assessment = "缓慢增长"
                growth_scores.append(40)
            else:
                analysis.profit_growth_assessment = "负增长"
                growth_scores.append(20)

        # 综合评级
        if growth_scores:
            avg_score = sum(growth_scores) / len(growth_scores)
            analysis.growth_grade = self._grade_from_score(avg_score)
            analysis.is_high_growth = avg_score >= 80
            analysis.is_stable_growth = 60 <= avg_score < 80

        return analysis

    def _analyze_profitability(self, metrics: FinancialMetrics) -> ProfitabilityAnalysis:
        """盈利能力分析"""
        analysis = ProfitabilityAnalysis()

        quality_scores = []

        # ROE分析
        if metrics.roe is not None:
            if metrics.roe > 0.2:
                quality_scores.append(100)
                analysis.roe_sustainability = "优秀"
            elif metrics.roe > 0.15:
                quality_scores.append(85)
                analysis.roe_sustainability = "良好"
            elif metrics.roe > 0.1:
                quality_scores.append(70)
                analysis.roe_sustainability = "一般"
            else:
                quality_scores.append(50)
                analysis.roe_sustainability = "较弱"

        # 毛利率分析
        if metrics.gross_margin is not None:
            if metrics.gross_margin > 0.4:
                quality_scores.append(100)
                analysis.competitive_advantage = True
            elif metrics.gross_margin > 0.25:
                quality_scores.append(80)
            elif metrics.gross_margin > 0.15:
                quality_scores.append(60)
            else:
                quality_scores.append(40)

        # 净利率分析
        if metrics.net_margin is not None:
            if metrics.net_margin > 0.2:
                quality_scores.append(100)
            elif metrics.net_margin > 0.1:
                quality_scores.append(80)
            elif metrics.net_margin > 0.05:
                quality_scores.append(60)
            else:
                quality_scores.append(40)

        # 综合评级
        if quality_scores:
            avg_score = sum(quality_scores) / len(quality_scores)
            analysis.profitability_grade = self._grade_from_score(avg_score)
            analysis.is_high_quality = avg_score >= 80

        return analysis

    def _analyze_financial_health(self, metrics: FinancialMetrics) -> FinancialHealthAnalysis:
        """财务健康分析"""
        analysis = FinancialHealthAnalysis()

        health_scores = []

        # 流动性分析
        if metrics.current_ratio is not None:
            if metrics.current_ratio > 2:
                analysis.liquidity_assessment = "非常健康"
                health_scores.append(100)
            elif metrics.current_ratio > 1.5:
                analysis.liquidity_assessment = "健康"
                health_scores.append(85)
            elif metrics.current_ratio > 1:
                analysis.liquidity_assessment = "一般"
                health_scores.append(60)
            else:
                analysis.liquidity_assessment = "紧张"
                health_scores.append(30)
                analysis.red_flags.append("流动比率低于1，短期偿债能力存疑")

        # 偿债能力分析
        if metrics.debt_to_equity is not None:
            if metrics.debt_to_equity < 0.3:
                analysis.solvency_assessment = "非常健康"
                health_scores.append(100)
                analysis.strengths.append("资产负债率低，财务风险小")
            elif metrics.debt_to_equity < 0.5:
                analysis.solvency_assessment = "健康"
                health_scores.append(80)
            elif metrics.debt_to_equity < 0.7:
                analysis.solvency_assessment = "一般"
                health_scores.append(60)
            else:
                analysis.solvency_assessment = "风险较高"
                health_scores.append(40)
                analysis.red_flags.append("资产负债率较高")

        # 现金流分析
        if metrics.free_cash_flow is not None:
            if metrics.free_cash_flow > 0:
                analysis.strengths.append("自由现金流为正")
            else:
                analysis.red_flags.append("自由现金流为负")

        # 综合评级
        if health_scores:
            avg_score = sum(health_scores) / len(health_scores)
            analysis.overall_grade = self._health_grade_from_score(avg_score)

        return analysis

    def _calculate_overall_score(self, report: FundamentalReport) -> float:
        """计算综合评分"""
        scores = []
        weights = []

        # 估值评分
        val_score = self._score_from_grade(report.valuation.valuation_grade)
        scores.append(val_score)
        weights.append(0.25)

        # 成长评分
        growth_score = self._score_from_grade(report.growth.growth_grade)
        scores.append(growth_score)
        weights.append(0.25)

        # 盈利评分
        profit_score = self._score_from_grade(report.profitability.profitability_grade)
        scores.append(profit_score)
        weights.append(0.25)

        # 健康评分
        health_score = self._health_score_from_grade(report.health.overall_grade)
        scores.append(health_score)
        weights.append(0.25)

        # 加权平均
        total_weight = sum(weights)
        if total_weight == 0:
            return 50.0

        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        return weighted_sum / total_weight

    def _generate_recommendation(self, report: FundamentalReport) -> str:
        """生成投资建议"""
        score = report.overall_score
        val = report.valuation
        health = report.health

        # 财务健康度差
        if health.overall_grade in [FinancialHealthGrade.POOR, FinancialHealthGrade.DISTRESS]:
            return "SELL"

        # 高分且低估
        if score >= 80 and val.is_undervalued:
            return "STRONG_BUY"

        # 高分或低估
        if score >= 70 or (score >= 60 and val.is_undervalued):
            return "BUY"

        # 低分且高估
        if score < 40 and val.is_overvalued:
            return "SELL"

        # 低分或高估
        if score < 50 or (score < 60 and val.is_overvalued):
            return "REDUCE"

        return "HOLD"

    @staticmethod
    def _score_pe(pe: float) -> float:
        """PE评分"""
        if pe <= 0:
            return 0
        if pe < 10:
            return 100
        if pe < 15:
            return 90
        if pe < 20:
            return 75
        if pe < 30:
            return 60
        if pe < 50:
            return 40
        return 20

    @staticmethod
    def _score_pb(pb: float) -> float:
        """PB评分"""
        if pb < 0:
            return 0
        if pb < 1:
            return 100
        if pb < 1.5:
            return 85
        if pb < 2:
            return 70
        if pb < 3:
            return 55
        if pb < 5:
            return 40
        return 25

    @staticmethod
    def _score_peg(peg: float) -> float:
        """PEG评分"""
        if peg < 0:
            return 0
        if peg < 0.5:
            return 100
        if peg < 0.8:
            return 90
        if peg < 1.0:
            return 80
        if peg < 1.2:
            return 65
        if peg < 1.5:
            return 50
        return 30

    @staticmethod
    def _grade_from_score(score: float) -> str:
        """分数转等级"""
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"

    @staticmethod
    def _score_from_grade(grade: str) -> float:
        """等级转分数"""
        grade_scores = {
            "A": 95, "B": 85, "C": 65, "D": 45, "F": 25, "N/A": 50
        }
        return grade_scores.get(grade, 50)

    @staticmethod
    def _health_grade_from_score(score: float) -> FinancialHealthGrade:
        """健康分数转等级"""
        if score >= 90:
            return FinancialHealthGrade.EXCELLENT
        if score >= 80:
            return FinancialHealthGrade.GOOD
        if score >= 60:
            return FinancialHealthGrade.FAIR
        if score >= 40:
            return FinancialHealthGrade.POOR
        return FinancialHealthGrade.DISTRESS

    @staticmethod
    def _health_score_from_grade(grade: FinancialHealthGrade) -> float:
        """健康等级转分数"""
        scores = {
            FinancialHealthGrade.EXCELLENT: 95,
            FinancialHealthGrade.GOOD: 85,
            FinancialHealthGrade.FAIR: 65,
            FinancialHealthGrade.POOR: 45,
            FinancialHealthGrade.DISTRESS: 25,
        }
        return scores.get(grade, 50)


class BatchFundamentalAnalyzer:
    """批量基本面分析器"""

    def __init__(self):
        self.analyzer = FundamentalAnalyzer()

    def analyze_batch(
        self,
        stocks_data: List[Dict[str, Any]]
    ) -> List[FundamentalReport]:
        """
        批量分析股票

        Args:
            stocks_data: 股票数据列表

        Returns:
            List[FundamentalReport]: 分析报告列表
        """
        reports = []

        for stock in stocks_data:
            symbol = stock.get('symbol')
            if not symbol:
                continue

            # 构建财务指标
            metrics = FinancialMetrics(
                pe_ttm=stock.get('pe_ttm'),
                pb=stock.get('pb'),
                ps=stock.get('ps'),
                roe=stock.get('roe'),
                roa=stock.get('roa'),
                revenue_growth=stock.get('revenue_growth'),
                profit_growth=stock.get('profit_growth'),
                gross_margin=stock.get('gross_margin'),
                net_margin=stock.get('net_margin'),
                debt_to_equity=stock.get('debt_to_equity'),
                current_ratio=stock.get('current_ratio'),
                dividend_yield=stock.get('dividend_yield'),
            )

            report = self.analyzer.analyze(
                symbol=symbol,
                metrics=metrics,
                name=stock.get('name')
            )
            reports.append(report)

        # 按综合评分排序
        reports.sort(key=lambda x: x.overall_score, reverse=True)

        return reports

    def find_undervalued(
        self,
        stocks_data: List[Dict[str, Any]],
        min_score: float = 70.0
    ) -> List[FundamentalReport]:
        """寻找低估股票"""
        reports = self.analyze_batch(stocks_data)
        return [r for r in reports if r.valuation.is_undervalued and r.overall_score >= min_score]

    def find_quality_stocks(
        self,
        stocks_data: List[Dict[str, Any]],
        min_score: float = 80.0
    ) -> List[FundamentalReport]:
        """寻找优质股票"""
        reports = self.analyze_batch(stocks_data)
        return [r for r in reports if r.profitability.is_high_quality and r.overall_score >= min_score]

    def filter_by_health(
        self,
        stocks_data: List[Dict[str, Any]],
        min_grade: FinancialHealthGrade = FinancialHealthGrade.FAIR
    ) -> List[FundamentalReport]:
        """按财务健康度筛选"""
        reports = self.analyze_batch(stocks_data)
        grade_order = [
            FinancialHealthGrade.EXCELLENT,
            FinancialHealthGrade.GOOD,
            FinancialHealthGrade.FAIR,
            FinancialHealthGrade.POOR,
            FinancialHealthGrade.DISTRESS,
        ]
        min_index = grade_order.index(min_grade)
        return [r for r in reports if grade_order.index(r.health.overall_grade) <= min_index]
