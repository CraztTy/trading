"""
交易报告生成器测试

测试覆盖：
1. 日报告生成
2. 周报告生成
3. 月报告生成
4. 自定义时间段报告
5. 报告导出
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List
from unittest.mock import Mock, AsyncMock, patch

from src.reports.generator import (
    ReportGenerator, ReportType, ReportPeriod,
    DailyReport, WeeklyReport, MonthlyReport
)
from src.reports.metrics import TradeMetrics, PerformanceMetrics
from src.models.order import Order
from src.models.trade import Trade


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_trades() -> List[Trade]:
    """样本交易数据"""
    return [
        Mock(
            id=1,
            symbol="000001.SZ",
            side="BUY",
            qty=100,
            price=Decimal("10.50"),
            amount=Decimal("1050"),
            commission=Decimal("5"),
            pnl=None,
            trade_time=datetime(2024, 1, 15, 10, 30, 0)
        ),
        Mock(
            id=2,
            symbol="000001.SZ",
            side="SELL",
            qty=100,
            price=Decimal("11.00"),
            amount=Decimal("1100"),
            commission=Decimal("5"),
            stamp_tax=Decimal("1"),
            pnl=Decimal("44"),  # (11-10.5)*100 - 5 - 5 - 1
            trade_time=datetime(2024, 1, 15, 14, 30, 0)
        ),
        Mock(
            id=3,
            symbol="600519.SH",
            side="BUY",
            qty=10,
            price=Decimal("1000"),
            amount=Decimal("10000"),
            commission=Decimal("25"),
            pnl=None,
            trade_time=datetime(2024, 1, 16, 10, 0, 0)
        ),
    ]


@pytest.fixture
def sample_orders() -> List[Order]:
    """样本订单数据"""
    return [
        Mock(
            order_id="ORD001",
            symbol="000001.SZ",
            direction="BUY",
            qty=100,
            price=Decimal("10.50"),
            status="FILLED",
            filled_qty=100,
            created_at=datetime(2024, 1, 15, 10, 30, 0)
        ),
        Mock(
            order_id="ORD002",
            symbol="000001.SZ",
            direction="SELL",
            qty=100,
            price=Decimal("11.00"),
            status="FILLED",
            filled_qty=100,
            created_at=datetime(2024, 1, 15, 14, 30, 0)
        ),
    ]


class TestReportType:
    """报告类型测试"""

    def test_type_values(self):
        """测试类型值"""
        assert ReportType.DAILY.value == "daily"
        assert ReportType.WEEKLY.value == "weekly"
        assert ReportType.MONTHLY.value == "monthly"
        assert ReportType.YEARLY.value == "yearly"
        assert ReportType.CUSTOM.value == "custom"


class TestDailyReport:
    """日报告测试"""

    @pytest.fixture
    def generator(self, mock_db_session):
        return ReportGenerator(session=mock_db_session)

    @pytest.mark.asyncio
    async def test_generate_daily_report(self, generator, mock_db_session, sample_trades, sample_orders):
        """测试生成日报告"""
        with patch.object(generator, '_get_trades') as mock_get_trades, \
             patch.object(generator, '_get_orders') as mock_get_orders, \
             patch.object(generator, '_get_portfolio_snapshots') as mock_get_snapshots:

            mock_get_trades.return_value = sample_trades
            mock_get_orders.return_value = sample_orders
            mock_get_snapshots.return_value = [
                Mock(date=datetime(2024, 1, 15), total_value=Decimal("100000")),
                Mock(date=datetime(2024, 1, 15, 15, 0), total_value=Decimal("100044"))
            ]

            report = await generator.generate_daily_report(
                account_id=1,
                report_date=date(2024, 1, 15)
            )

            assert report.report_type == ReportType.DAILY
            assert report.account_id == 1
            assert report.report_date == date(2024, 1, 15)
            assert report.trade_count == 2  # 当天的2笔交易
            assert report.realized_pnl == Decimal("44")

    @pytest.mark.asyncio
    async def test_daily_report_empty_data(self, generator, mock_db_session):
        """测试无数据时的日报告"""
        with patch.object(generator, '_get_trades') as mock_get_trades, \
             patch.object(generator, '_get_orders') as mock_get_orders:

            mock_get_trades.return_value = []
            mock_get_orders.return_value = []

            report = await generator.generate_daily_report(
                account_id=1,
                report_date=date(2024, 1, 15)
            )

            assert report.trade_count == 0
            assert report.realized_pnl == Decimal("0")


class TestWeeklyReport:
    """周报告测试"""

    @pytest.fixture
    def generator(self, mock_db_session):
        return ReportGenerator(session=mock_db_session)

    @pytest.mark.asyncio
    async def test_generate_weekly_report(self, generator, mock_db_session, sample_trades):
        """测试生成周报告"""
        with patch.object(generator, '_get_trades') as mock_get_trades, \
             patch.object(generator, '_get_daily_settlements') as mock_get_settlements:

            mock_get_trades.return_value = sample_trades
            mock_get_settlements.return_value = [
                Mock(trade_date=date(2024, 1, 15), return_pct=Decimal("0.02")),
                Mock(trade_date=date(2024, 1, 16), return_pct=Decimal("0.01")),
                Mock(trade_date=date(2024, 1, 17), return_pct=Decimal("-0.01")),
            ]

            report = await generator.generate_weekly_report(
                account_id=1,
                year=2024,
                week=3  # 第3周
            )

            assert report.report_type == ReportType.WEEKLY
            assert report.year == 2024
            assert report.week == 3
            assert len(report.daily_returns) == 3


class TestMonthlyReport:
    """月报告测试"""

    @pytest.fixture
    def generator(self, mock_db_session):
        return ReportGenerator(session=mock_db_session)

    @pytest.mark.asyncio
    async def test_generate_monthly_report(self, generator, mock_db_session, sample_trades):
        """测试生成月报告"""
        with patch.object(generator, '_get_trades') as mock_get_trades, \
             patch.object(generator, '_get_daily_settlements') as mock_get_settlements:

            mock_get_trades.return_value = sample_trades
            mock_get_settlements.return_value = [
                Mock(trade_date=date(2024, 1, i), return_pct=Decimal("0.01"))
                for i in range(1, 16)
            ]

            report = await generator.generate_monthly_report(
                account_id=1,
                year=2024,
                month=1
            )

            assert report.report_type == ReportType.MONTHLY
            assert report.year == 2024
            assert report.month == 1
            assert report.trading_days == 15

    @pytest.mark.asyncio
    async def test_monthly_report_statistics(self, generator, mock_db_session):
        """测试月报告统计计算"""
        with patch.object(generator, '_get_trades') as mock_get_trades, \
             patch.object(generator, '_get_daily_settlements') as mock_get_settlements:

            mock_get_trades.return_value = [
                Mock(symbol="000001.SZ", side="BUY", qty=100, price=Decimal("10"), amount=Decimal("1000")),
                Mock(symbol="000001.SZ", side="SELL", qty=100, price=Decimal("11"), amount=Decimal("1100"), pnl=Decimal("90")),
            ]
            mock_get_settlements.return_value = [
                Mock(trade_date=date(2024, 1, 1), return_pct=Decimal("0.02")),
                Mock(trade_date=date(2024, 1, 2), return_pct=Decimal("-0.01")),
                Mock(trade_date=date(2024, 1, 3), return_pct=Decimal("0.015")),
            ]

            report = await generator.generate_monthly_report(
                account_id=1,
                year=2024,
                month=1
            )

            assert report.win_days == 2  # 2天盈利
            assert report.lose_days == 1  # 1天亏损
            assert report.win_rate == pytest.approx(2/3, abs=0.01)


class TestTradeMetrics:
    """交易指标测试"""

    def test_calculate_trade_metrics(self, sample_trades):
        """测试交易指标计算"""
        metrics = TradeMetrics.calculate(sample_trades)

        assert metrics.total_trades == 3
        assert metrics.winning_trades == 1  # 只有1笔有盈利
        assert metrics.losing_trades == 0
        assert metrics.win_rate == pytest.approx(1/1, abs=0.01)  # 1笔盈利，1笔平仓

    def test_calculate_empty_trades(self):
        """测试空交易列表"""
        metrics = TradeMetrics.calculate([])

        assert metrics.total_trades == 0
        assert metrics.win_rate == 0
        assert metrics.profit_factor == 0

    def test_calculate_commission_and_tax(self, sample_trades):
        """测试佣金和税费计算"""
        metrics = TradeMetrics.calculate(sample_trades)

        expected_commission = Decimal("5") + Decimal("5") + Decimal("25")
        expected_tax = Decimal("1")

        assert metrics.total_commission == expected_commission
        assert metrics.total_tax == expected_tax


class TestPerformanceMetrics:
    """绩效指标测试"""

    def test_calculate_returns(self):
        """测试收益率计算"""
        portfolio_values = [
            Decimal("100000"),
            Decimal("102000"),
            Decimal("101000"),
            Decimal("105000"),
        ]

        metrics = PerformanceMetrics.calculate(portfolio_values)

        assert metrics.total_return == pytest.approx(0.05, abs=0.001)  # 5%
        assert metrics.max_drawdown < 0  # 应该有回撤

    def test_calculate_sharpe_ratio(self):
        """测试夏普比率计算"""
        daily_returns = [0.01, 0.02, -0.01, 0.015, 0.005]

        sharpe = PerformanceMetrics.calculate_sharpe(
            daily_returns,
            risk_free_rate=0.0001
        )

        assert isinstance(sharpe, float)
        assert sharpe > 0

    def test_calculate_volatility(self):
        """测试波动率计算"""
        daily_returns = [0.01, -0.01, 0.015, -0.005, 0.02]

        vol = PerformanceMetrics.calculate_volatility(daily_returns)

        assert isinstance(vol, float)
        assert vol > 0


class TestReportExport:
    """报告导出测试"""

    @pytest.fixture
    def sample_report(self):
        """样本报告"""
        return DailyReport(
            account_id=1,
            report_date=date(2024, 1, 15),
            trade_count=10,
            realized_pnl=Decimal("1000"),
            total_commission=Decimal("50"),
            total_tax=Decimal("10"),
            win_rate=0.6,
            trades=[],
            orders=[]
        )

    def test_export_to_json(self, sample_report, tmp_path):
        """测试导出JSON"""
        from src.reports.export import ReportExporter

        output_path = tmp_path / "report.json"
        ReportExporter.to_json(sample_report, str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert "trade_count" in content
        assert "realized_pnl" in content

    def test_export_to_csv(self, sample_report, tmp_path):
        """测试导出CSV"""
        from src.reports.export import ReportExporter

        output_path = tmp_path / "report.csv"
        ReportExporter.to_csv(sample_report, str(output_path))

        assert output_path.exists()

    def test_export_to_html(self, sample_report, tmp_path):
        """测试导出HTML"""
        from src.reports.export import ReportExporter

        output_path = tmp_path / "report.html"
        ReportExporter.to_html(sample_report, str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert "<html>" in content.lower()


class TestReportComparison:
    """报告对比测试"""

    def test_compare_reports(self):
        """测试报告对比"""
        from src.reports.comparison import ReportComparator

        report1 = DailyReport(
            account_id=1,
            report_date=date(2024, 1, 15),
            trade_count=10,
            realized_pnl=Decimal("1000"),
            win_rate=0.6
        )

        report2 = DailyReport(
            account_id=1,
            report_date=date(2024, 1, 16),
            trade_count=12,
            realized_pnl=Decimal("1500"),
            win_rate=0.65
        )

        comparison = ReportComparator.compare(report1, report2)

        assert comparison.pnl_change == Decimal("500")
        assert comparison.trade_count_change == 2
        assert comparison.win_rate_change == pytest.approx(0.05, abs=0.01)

    def test_generate_comparison_chart_data(self):
        """测试生成对比图表数据"""
        from src.reports.comparison import ReportComparator

        reports = [
            DailyReport(
                account_id=1,
                report_date=date(2024, 1, 15),
                realized_pnl=Decimal("1000"),
                total_value=Decimal("100000")
            ),
            DailyReport(
                account_id=1,
                report_date=date(2024, 1, 16),
                realized_pnl=Decimal("1500"),
                total_value=Decimal("101500")
            ),
        ]

        chart_data = ReportComparator.generate_chart_data(reports)

        assert len(chart_data.dates) == 2
        assert len(chart_data.pnl_values) == 2
        assert len(chart_data.nav_values) == 2
