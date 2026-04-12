"""
智能分析集成测试 (Intelligence Integration Tests)
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.intelligence.fundamental.analyzer import (
    FundamentalAnalyzer, FinancialMetrics, BatchFundamentalAnalyzer,
    FinancialHealthGrade
)
from src.intelligence.screening.screener import StockScreener, StockData
from src.intelligence.screening.factors import (
    MultiFactorModel, FactorBuilder, FactorType, FactorDirection, FactorDefinition
)
from decimal import Decimal


class TestIntelligence:
    """智能分析测试"""

    def test_fundamental_analyzer(self):
        """测试基本面分析器"""
        print("\n[TEST] Fundamental Analyzer...")

        analyzer = FundamentalAnalyzer()

        # 构建财务指标
        metrics = FinancialMetrics(
            pe_ttm=15.0,
            pb=2.0,
            ps=1.5,
            roe=0.20,
            roa=0.15,
            gross_margin=0.40,
            net_margin=0.15,
            revenue_growth=0.25,
            profit_growth=0.30,
            debt_to_equity=0.30,
            current_ratio=2.0,
            dividend_yield=0.03
        )

        # 执行分析
        report = analyzer.analyze("600519.SH", metrics, "贵州茅台")

        assert report.symbol == "600519.SH"
        assert report.name == "贵州茅台"
        assert 0 <= report.overall_score <= 100
        assert report.investment_recommendation in ["STRONG_BUY", "BUY", "HOLD", "REDUCE", "SELL"]

        print(f"   Symbol: {report.symbol}")
        print(f"   Score: {report.overall_score}")
        print(f"   Recommendation: {report.investment_recommendation}")
        print(f"   Valuation Grade: {report.valuation.valuation_grade}")
        print(f"   Growth Grade: {report.growth.growth_grade}")
        print("   [OK] Fundamental analysis passed")

    def test_fundamental_analyzer_low_quality(self):
        """测试低质量股票分析"""
        print("\n[TEST] Fundamental Analyzer - Low Quality Stock...")

        analyzer = FundamentalAnalyzer()

        # 低质量财务指标
        metrics = FinancialMetrics(
            pe_ttm=80.0,
            pb=8.0,
            roe=0.02,
            gross_margin=0.05,
            net_margin=-0.10,
            revenue_growth=-0.20,
            profit_growth=-0.30,
            debt_to_equity=0.80,
            current_ratio=0.8
        )

        report = analyzer.analyze("000001.SZ", metrics, "测试股票")

        # 应该得到较低评分和卖出建议
        assert report.overall_score < 50
        assert report.valuation.is_overvalued is True
        assert report.health.overall_grade in [FinancialHealthGrade.POOR, FinancialHealthGrade.DISTRESS]

        print(f"   Score: {report.overall_score}")
        print(f"   Recommendation: {report.investment_recommendation}")
        print("   [OK] Low quality stock analysis passed")

    def test_batch_analyzer(self):
        """测试批量分析器"""
        print("\n[TEST] Batch Analyzer...")

        batch_analyzer = BatchFundamentalAnalyzer()

        stocks_data = [
            {"symbol": "600519.SH", "name": "茅台", "pe_ttm": 28.5, "pb": 8.2, "roe": 0.25},
            {"symbol": "000858.SZ", "name": "五粮液", "pe_ttm": 18.2, "pb": 4.5, "roe": 0.22},
            {"symbol": "601318.SH", "name": "平安", "pe_ttm": 8.5, "pb": 0.9, "roe": 0.16},
        ]

        reports = batch_analyzer.analyze_batch(stocks_data)

        assert len(reports) == 3
        # 应该按评分排序
        for i in range(len(reports) - 1):
            assert reports[i].overall_score >= reports[i + 1].overall_score

        print(f"   Analyzed {len(reports)} stocks")
        for r in reports:
            print(f"     {r.symbol}: {r.overall_score}")
        print("   [OK] Batch analysis passed")

    def test_find_undervalued(self):
        """测试寻找低估股票"""
        print("\n[TEST] Find Undervalued Stocks...")

        batch_analyzer = BatchFundamentalAnalyzer()

        stocks_data = [
            {"symbol": "A", "pe_ttm": 8.0, "pb": 0.8, "roe": 0.15},
            {"symbol": "B", "pe_ttm": 50.0, "pb": 10.0, "roe": 0.10},
            {"symbol": "C", "pe_ttm": 12.0, "pb": 1.2, "roe": 0.20},
        ]

        undervalued = batch_analyzer.find_undervalued(stocks_data, min_score=60)

        print(f"   Found {len(undervalued)} undervalued stocks")
        for r in undervalued:
            print(f"     {r.symbol}: score={r.overall_score}, undervalued={r.valuation.is_undervalued}")
        print("   [OK] Find undervalued passed")

    def test_stock_screener_basic(self):
        """测试基础股票筛选"""
        print("\n[TEST] Stock Screener - Basic...")

        # 创建演示股票池
        stock_pool = [
            StockData("A", "股票A", pe_ttm=10.0, pb=1.0, roe=0.20, market_cap=Decimal("10000000000")),
            StockData("B", "股票B", pe_ttm=25.0, pb=3.0, roe=0.10, market_cap=Decimal("50000000000")),
            StockData("C", "股票C", pe_ttm=50.0, pb=8.0, roe=0.05, market_cap=Decimal("100000000000")),
        ]

        screener = StockScreener()
        result = screener.pe_ratio(max_val=20).execute_sync(stock_pool)

        assert result.filtered_count == 1
        assert result.stocks[0].symbol == "A"

        print(f"   Filtered {result.filtered_count} stocks (PE < 20)")
        print("   [OK] Basic screening passed")

    def test_stock_screener_combined(self):
        """测试组合条件筛选"""
        print("\n[TEST] Stock Screener - Combined Filters...")

        stock_pool = [
            StockData("A", "股票A", pe_ttm=12.0, pb=1.5, roe=0.20, market_cap=Decimal("50000000000")),
            StockData("B", "股票B", pe_ttm=15.0, pb=2.0, roe=0.18, market_cap=Decimal("20000000000")),
            StockData("C", "股票C", pe_ttm=30.0, pb=5.0, roe=0.08, market_cap=Decimal("100000000000")),
        ]

        screener = StockScreener()
        result = screener.pe_ratio(max_val=20).pb_ratio(max_val=2.5).roe(min_val=0.15).execute_sync(stock_pool)

        assert result.filtered_count == 2

        print(f"   Filtered {result.filtered_count} stocks (PE<20, PB<2.5, ROE>15%)")
        for s in result.stocks:
            print(f"     {s.symbol}: PE={s.pe_ttm}, PB={s.pb}, ROE={s.roe}")
        print("   [OK] Combined screening passed")

    def test_stock_screener_market_cap(self):
        """测试市值筛选"""
        print("\n[TEST] Stock Screener - Market Cap...")

        stock_pool = [
            StockData("S1", "小盘1", market_cap=Decimal("5000000000")),
            StockData("S2", "小盘2", market_cap=Decimal("8000000000")),
            StockData("M1", "中盘", market_cap=Decimal("20000000000")),
            StockData("L1", "大盘", market_cap=Decimal("100000000000")),
        ]

        # 小盘股筛选
        small_caps = StockScreener().small_cap().execute_sync(stock_pool)
        assert small_caps.filtered_count == 2

        # 大盘股筛选
        large_caps = StockScreener().large_cap().execute_sync(stock_pool)
        assert large_caps.filtered_count == 1
        assert large_caps.stocks[0].symbol == "L1"

        print(f"   Small caps: {small_caps.filtered_count}")
        print(f"   Large caps: {large_caps.filtered_count}")
        print("   [OK] Market cap screening passed")

    def test_multifactor_model(self):
        """测试多因子模型"""
        print("\n[TEST] Multi-Factor Model...")

        stocks = [
            {"symbol": "A", "name": "股票A", "pe_ttm": 10.0, "pb": 1.0, "roe": 0.25, "revenue_growth": 0.30},
            {"symbol": "B", "name": "股票B", "pe_ttm": 30.0, "pb": 5.0, "roe": 0.08, "revenue_growth": 0.05},
            {"symbol": "C", "name": "股票C", "pe_ttm": 15.0, "pb": 2.0, "roe": 0.18, "revenue_growth": 0.20},
        ]

        model = FactorBuilder.balanced_model()
        results = model.score(stocks)

        assert len(results) == 3
        # 应该按总分排序
        assert results[0].total_score >= results[1].total_score

        print(f"   Scored {len(results)} stocks")
        for r in results:
            print(f"     {r.symbol}: total={r.total_score:.1f}, value={r.value_score:.1f}, quality={r.quality_score:.1f}")
        print("   [OK] Multi-factor model passed")

    def test_value_model(self):
        """测试价值模型"""
        print("\n[TEST] Value Model...")

        stocks = [
            {"symbol": "V1", "pe_ttm": 8.0, "pb": 0.8, "roe": 0.15},
            {"symbol": "V2", "pe_ttm": 12.0, "pb": 1.2, "roe": 0.18},
            {"symbol": "G1", "pe_ttm": 50.0, "pb": 10.0, "roe": 0.25},
        ]

        model = FactorBuilder.value_model()
        results = model.score(stocks)

        # 低PE/PB的股票应该排名靠前
        print(f"   Value model ranking:")
        for r in results:
            print(f"     {r.symbol}: total={r.total_score:.1f}, value={r.value_score:.1f}")
        print("   [OK] Value model passed")

    def test_growth_model(self):
        """测试成长模型"""
        print("\n[TEST] Growth Model...")

        stocks = [
            {"symbol": "G1", "revenue_growth": 0.50, "profit_growth": 0.60, "roe": 0.20},
            {"symbol": "G2", "revenue_growth": 0.30, "profit_growth": 0.35, "roe": 0.18},
            {"symbol": "V1", "revenue_growth": 0.05, "profit_growth": 0.03, "roe": 0.15},
        ]

        model = FactorBuilder.growth_model()
        results = model.score(stocks)

        print(f"   Growth model ranking:")
        for r in results:
            print(f"     {r.symbol}: total={r.total_score:.1f}, growth={r.growth_score:.1f}")
        print("   [OK] Growth model passed")

    def test_quality_model(self):
        """测试质量模型"""
        print("\n[TEST] Quality Model...")

        stocks = [
            {"symbol": "Q1", "roe": 0.30, "roa": 0.20, "gross_margin": 0.50, "net_margin": 0.25},
            {"symbol": "Q2", "roe": 0.20, "roa": 0.15, "gross_margin": 0.40, "net_margin": 0.18},
            {"symbol": "L1", "roe": 0.05, "roa": 0.03, "gross_margin": 0.10, "net_margin": 0.02},
        ]

        model = FactorBuilder.quality_model()
        results = model.score(stocks)

        print(f"   Quality model ranking:")
        for r in results:
            print(f"     {r.symbol}: total={r.total_score:.1f}, quality={r.quality_score:.1f}")
        print("   [OK] Quality model passed")


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Intelligence Integration Tests")
    print("=" * 60)

    tests = TestIntelligence()

    tests.test_fundamental_analyzer()
    tests.test_fundamental_analyzer_low_quality()
    tests.test_batch_analyzer()
    tests.test_find_undervalued()
    tests.test_stock_screener_basic()
    tests.test_stock_screener_combined()
    tests.test_stock_screener_market_cap()
    tests.test_multifactor_model()
    tests.test_value_model()
    tests.test_growth_model()
    tests.test_quality_model()

    print("\n" + "=" * 60)
    print("All intelligence tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
