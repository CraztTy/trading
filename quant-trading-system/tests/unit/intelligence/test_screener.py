"""
智能选股系统测试

测试覆盖：
1. 股票筛选器
2. 多因子模型
3. 基本面分析
"""
import pytest
from datetime import date
from decimal import Decimal
from typing import List, Dict, Any

from src.intelligence import (
    StockScreener, StockData, FilterOperator, SortOrder,
    MultiFactorModel, FactorDefinition, FactorType, FactorDirection,
    FundamentalAnalyzer, FinancialMetrics, FinancialHealthGrade,
    BatchFundamentalAnalyzer, FactorBuilder
)


@pytest.fixture
def sample_stocks() -> List[StockData]:
    """样本股票数据"""
    return [
        StockData(
            symbol="000001.SZ",
            name="平安银行",
            industry="银行",
            price=Decimal("10.50"),
            pe_ttm=5.5,
            pb=0.8,
            roe=0.12,
            market_cap=Decimal("200000000000"),
            revenue_growth=0.05,
            profit_growth=0.08
        ),
        StockData(
            symbol="600519.SH",
            name="贵州茅台",
            industry="白酒",
            price=Decimal("1700.00"),
            pe_ttm=35.0,
            pb=8.5,
            roe=0.25,
            market_cap=Decimal("2100000000000"),
            revenue_growth=0.15,
            profit_growth=0.18
        ),
        StockData(
            symbol="000858.SZ",
            name="五粮液",
            industry="白酒",
            price=Decimal("150.00"),
            pe_ttm=25.0,
            pb=5.0,
            roe=0.20,
            market_cap=Decimal("580000000000"),
            revenue_growth=0.12,
            profit_growth=0.15
        ),
        StockData(
            symbol="300750.SZ",
            name="宁德时代",
            industry="新能源",
            price=Decimal("200.00"),
            pe_ttm=45.0,
            pb=6.0,
            roe=0.18,
            market_cap=Decimal("880000000000"),
            revenue_growth=0.50,
            profit_growth=0.45
        ),
    ]


@pytest.fixture
def sample_stock_dicts() -> List[Dict[str, Any]]:
    """样本股票字典数据（用于多因子测试）"""
    return [
        {
            "symbol": "000001.SZ",
            "name": "平安银行",
            "pe_ttm": 5.5,
            "pb": 0.8,
            "roe": 0.12,
            "revenue_growth": 0.05,
            "profit_growth": 0.08,
        },
        {
            "symbol": "600519.SH",
            "name": "贵州茅台",
            "pe_ttm": 35.0,
            "pb": 8.5,
            "roe": 0.25,
            "revenue_growth": 0.15,
            "profit_growth": 0.18,
        },
        {
            "symbol": "300750.SZ",
            "name": "宁德时代",
            "pe_ttm": 45.0,
            "pb": 6.0,
            "roe": 0.18,
            "revenue_growth": 0.50,
            "profit_growth": 0.45,
        },
    ]


class TestStockScreener:
    """股票筛选器测试"""

    @pytest.mark.asyncio
    async def test_pe_ratio_filter(self, sample_stocks):
        """测试PE筛选"""
        screener = StockScreener()
        result = await screener.pe_ratio(max_val=20).execute(sample_stocks)

        # 只有平安银行 PE=5.5 <= 20
        assert result.filtered_count == 1
        assert all(s.pe_ttm <= 20 for s in result.stocks)

    @pytest.mark.asyncio
    async def test_roe_filter(self, sample_stocks):
        """测试ROE筛选"""
        screener = StockScreener()
        result = await screener.roe(min_val=0.15).execute(sample_stocks)

        assert result.filtered_count == 3
        assert all(s.roe >= 0.15 for s in result.stocks)

    @pytest.mark.asyncio
    async def test_industry_filter(self, sample_stocks):
        """测试行业筛选"""
        screener = StockScreener()
        result = await screener.industry("白酒").execute(sample_stocks)

        assert result.filtered_count == 2
        assert all(s.industry == "白酒" for s in result.stocks)

    @pytest.mark.asyncio
    async def test_market_cap_filter(self, sample_stocks):
        """测试市值筛选"""
        screener = StockScreener()
        result = await screener.large_cap().execute(sample_stocks)

        assert result.filtered_count >= 1
        assert all(s.market_cap >= Decimal("50000000000") for s in result.stocks)

    @pytest.mark.asyncio
    async def test_combined_filters(self, sample_stocks):
        """测试组合筛选"""
        screener = StockScreener()
        result = await (
            screener
            .pe_ratio(max_val=30)
            .roe(min_val=0.15)
            .order_by_roe(desc=True)
            .limit(10)
            .execute(sample_stocks)
        )

        # 五粮液 PE=25, ROE=0.2 满足条件
        assert result.filtered_count == 1
        assert all(s.pe_ttm <= 30 and s.roe >= 0.15 for s in result.stocks)

    @pytest.mark.asyncio
    async def test_sort(self, sample_stocks):
        """测试排序"""
        screener = StockScreener()
        result = await screener.order_by("pe_ttm", SortOrder.ASC).execute(sample_stocks)

        pes = [s.pe_ttm for s in result.stocks]
        assert pes == sorted(pes)

    def test_preset_value_stocks(self, sample_stocks):
        """测试价值股预设"""
        screener = StockScreener()
        result = screener.value_stocks().execute_sync(sample_stocks)

        assert result.filtered_count >= 1

    def test_preset_growth_stocks(self, sample_stocks):
        """测试成长股预设"""
        screener = StockScreener()
        result = screener.growth_stocks().execute_sync(sample_stocks)

        assert result.filtered_count >= 1

    def test_preset_blue_chip(self, sample_stocks):
        """测试蓝筹股预设"""
        screener = StockScreener()
        result = screener.blue_chip().execute_sync(sample_stocks)

        assert result.filtered_count >= 1


class TestMultiFactorModel:
    """多因子模型测试"""

    def test_score_calculation(self, sample_stock_dicts):
        """测试评分计算"""
        model = MultiFactorModel()
        results = model.score(sample_stock_dicts)

        assert len(results) == 3
        assert all(r.total_score > 0 for r in results)
        assert all(r.rank > 0 for r in results)

    def test_factor_weights(self, sample_stock_dicts):
        """测试因子权重"""
        model = MultiFactorModel()
        model.set_factor_weight("roe", 3.0)

        results = model.score(sample_stock_dicts)

        # 高ROE的股票应该排名更靠前
        top_stock = results[0]
        assert top_stock.factor_scores["roe"].weighted_score > 0

    def test_value_model(self, sample_stock_dicts):
        """测试纯价值模型"""
        model = FactorBuilder.value_model()
        results = model.score(sample_stock_dicts)

        # 低PE的股票应该排名靠前
        assert len(results) == 3
        assert results[0].value_score > 0

    def test_growth_model(self, sample_stock_dicts):
        """测试纯成长模型"""
        model = FactorBuilder.growth_model()
        results = model.score(sample_stock_dicts)

        # 高成长的股票应该排名靠前
        assert len(results) == 3
        assert results[0].growth_score > 0

    def test_quality_model(self, sample_stock_dicts):
        """测试纯质量模型"""
        model = FactorBuilder.quality_model()
        results = model.score(sample_stock_dicts)

        assert len(results) == 3
        assert results[0].quality_score > 0

    def test_balanced_model(self, sample_stock_dicts):
        """测试平衡模型"""
        model = FactorBuilder.balanced_model()
        results = model.score(sample_stock_dicts)

        assert len(results) == 3
        # 各类因子都有得分
        assert results[0].value_score > 0 or results[0].quality_score > 0


class TestFundamentalAnalyzer:
    """基本面分析测试"""

    def test_valuation_analysis(self):
        """测试估值分析"""
        analyzer = FundamentalAnalyzer()
        metrics = FinancialMetrics(
            pe_ttm=8.0,
            pb=0.9,
            peg=0.6,
        )

        report = analyzer.analyze("000001.SZ", metrics, "平安银行")

        assert report.valuation.is_undervalued
        assert report.valuation.valuation_grade in ["A", "B"]

    def test_growth_analysis(self):
        """测试成长性分析"""
        analyzer = FundamentalAnalyzer()
        metrics = FinancialMetrics(
            revenue_growth=0.35,
            profit_growth=0.40,
        )

        report = analyzer.analyze("300750.SZ", metrics, "宁德时代")

        assert report.growth.is_high_growth
        assert report.growth.growth_grade == "A"

    def test_profitability_analysis(self):
        """测试盈利能力分析"""
        analyzer = FundamentalAnalyzer()
        metrics = FinancialMetrics(
            roe=0.25,
            gross_margin=0.90,
            net_margin=0.50,
        )

        report = analyzer.analyze("600519.SH", metrics, "贵州茅台")

        assert report.profitability.is_high_quality
        assert report.profitability.profitability_grade == "A"

    def test_financial_health_analysis(self):
        """测试财务健康分析"""
        analyzer = FundamentalAnalyzer()
        metrics = FinancialMetrics(
            current_ratio=2.5,
            debt_to_equity=0.2,
        )

        report = analyzer.analyze("600519.SH", metrics, "贵州茅台")

        assert report.health.overall_grade in [FinancialHealthGrade.EXCELLENT, FinancialHealthGrade.GOOD]

    def test_overall_score(self):
        """测试综合评分"""
        analyzer = FundamentalAnalyzer()
        metrics = FinancialMetrics(
            pe_ttm=15.0,
            roe=0.20,
            revenue_growth=0.20,
            gross_margin=0.40,
            current_ratio=2.0,
            debt_to_equity=0.3,
        )

        report = analyzer.analyze("000001.SZ", metrics, "测试股票")

        assert 0 <= report.overall_score <= 100
        assert report.investment_recommendation in ["STRONG_BUY", "BUY", "HOLD", "REDUCE", "SELL"]

    def test_red_flags(self):
        """测试风险警示"""
        analyzer = FundamentalAnalyzer()
        metrics = FinancialMetrics(
            current_ratio=0.8,  # 流动比率低于1
            debt_to_equity=0.8,  # 高负债率
        )

        report = analyzer.analyze("000001.SZ", metrics, "高风险股票")

        assert len(report.health.red_flags) >= 1
        assert report.health.overall_grade in [FinancialHealthGrade.POOR, FinancialHealthGrade.DISTRESS]


class TestBatchFundamentalAnalyzer:
    """批量分析测试"""

    def test_analyze_batch(self, sample_stock_dicts):
        """测试批量分析"""
        analyzer = BatchFundamentalAnalyzer()
        reports = analyzer.analyze_batch(sample_stock_dicts)

        assert len(reports) == 3
        # 结果按综合评分排序
        scores = [r.overall_score for r in reports]
        assert scores == sorted(scores, reverse=True)

    def test_find_undervalued(self, sample_stock_dicts):
        """测试寻找低估股票"""
        analyzer = BatchFundamentalAnalyzer()
        undervalued = analyzer.find_undervalued(sample_stock_dicts, min_score=50)

        # 至少应该有一个低估的（平安银行）
        assert len(undervalued) >= 1

    def test_filter_by_health(self, sample_stock_dicts):
        """测试按健康度筛选"""
        analyzer = BatchFundamentalAnalyzer()
        healthy = analyzer.filter_by_health(sample_stock_dicts, FinancialHealthGrade.FAIR)

        assert len(healthy) >= 1


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_screening_then_factor_score(self, sample_stocks):
        """测试先筛选再因子评分"""
        # 第一步：筛选低PE股票
        screener = StockScreener()
        screen_result = await screener.pe_ratio(max_val=30).execute(sample_stocks)

        assert screen_result.filtered_count >= 2

        # 转换为字典格式
        stock_dicts = [
            {
                "symbol": s.symbol,
                "name": s.name,
                "pe_ttm": s.pe_ttm,
                "pb": s.pb,
                "roe": s.roe,
                "revenue_growth": s.revenue_growth,
                "profit_growth": s.profit_growth,
            }
            for s in screen_result.stocks
        ]

        # 第二步：多因子评分
        model = FactorBuilder.balanced_model()
        factor_results = model.score(stock_dicts)

        assert len(factor_results) == screen_result.filtered_count

    @pytest.mark.asyncio
    async def test_complete_workflow(self, sample_stocks, sample_stock_dicts):
        """测试完整工作流：筛选 -> 评分 -> 基本面分析"""
        # 1. 筛选
        screener = StockScreener()
        screen_result = await screener.value_stocks().limit(10).execute(sample_stocks)

        # 2. 多因子评分
        model = FactorBuilder.value_model()
        factor_results = model.score(sample_stock_dicts)

        # 3. 基本面分析
        batch_analyzer = BatchFundamentalAnalyzer()
        fundamental_reports = batch_analyzer.analyze_batch(sample_stock_dicts)

        assert len(fundamental_reports) > 0
        assert all(r.overall_score > 0 for r in fundamental_reports)
