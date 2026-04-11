"""
日终结算测试

测试覆盖：
1. 结算数据生成
2. 对账逻辑
3. 结算报表
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from src.finance.settlement import SettlementManager, SettlementResult
from src.models.daily_settlement import DailySettlement


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_account():
    """模拟账户"""
    account = Mock()
    account.id = 1
    account.account_no = "TEST001"
    account.total_balance = Decimal("100000")
    account.available = Decimal("80000")
    account.frozen = Decimal("20000")
    account.market_value = Decimal("150000")
    account.realized_pnl = Decimal("5000")
    return account


class TestSettlementManager:
    """结算管理器测试"""

    @pytest.fixture
    def manager(self, mock_db_session):
        """创建结算管理器"""
        return SettlementManager(session=mock_db_session)

    @pytest.mark.asyncio
    async def test_generate_settlement(self, manager, mock_account, mock_db_session):
        """测试生成结算数据"""
        # 模拟交易数据
        trades = [
            Mock(
                symbol="000001.SZ",
                qty=100,
                price=Decimal("10.50"),
                amount=Decimal("1050"),
                commission=Decimal("5"),
                stamp_tax=Decimal("0"),
                side="BUY"
            ),
            Mock(
                symbol="600519.SH",
                qty=50,
                price=Decimal("1000"),
                amount=Decimal("50000"),
                commission=Decimal("25"),
                stamp_tax=Decimal("50"),
                side="SELL"
            )
        ]

        # 模拟订单数据
        orders = [
            Mock(id=1, status="FILLED"),
            Mock(id=2, status="PARTIAL")
        ]

        with patch('src.finance.settlement.AccountService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_account = AsyncMock(return_value=mock_account)
            mock_service.return_value = mock_service_instance

            # 模拟持仓
            positions = [
                Mock(symbol="000001.SZ", qty=100, market_value=Decimal("1050")),
                Mock(symbol="600519.SH", qty=50, market_value=Decimal("50000"))
            ]
            mock_service_instance.get_positions = AsyncMock(return_value=positions)

            result = await manager.generate_settlement(
                account_id=1,
                trade_date=date(2024, 1, 15),
                trades=trades,
                orders=orders
            )

            assert isinstance(result, SettlementResult)
            assert result.success is True
            assert result.settlement.trade_date == date(2024, 1, 15)
            assert result.settlement.total_trades == 2

    @pytest.mark.asyncio
    async def test_reconcile_success(self, manager, mock_db_session):
        """测试对账成功"""
        settlement = DailySettlement(
            account_id=1,
            trade_date=date(2024, 1, 15),
            begin_balance=Decimal("100000"),
            end_balance=Decimal("105000")
        )

        # 实际余额与结算一致
        reconciled = settlement.reconcile(Decimal("105000"))

        assert reconciled is True
        assert settlement.reconciled is True
        assert settlement.reconcile_diff == Decimal("0")

    @pytest.mark.asyncio
    async def test_reconcile_with_diff(self, manager, mock_db_session):
        """测试对账有差异"""
        settlement = DailySettlement(
            account_id=1,
            trade_date=date(2024, 1, 15),
            begin_balance=Decimal("100000"),
            end_balance=Decimal("105000")
        )

        # 实际余额有差异
        reconciled = settlement.reconcile(Decimal("105001"))

        assert reconciled is False
        assert settlement.reconciled is False
        assert settlement.reconcile_diff == Decimal("1")

    @pytest.mark.asyncio
    async def test_get_settlement_history(self, manager, mock_db_session):
        """测试获取结算历史"""
        # 模拟历史结算数据
        mock_settlements = [
            Mock(
                id=1,
                trade_date=date(2024, 1, 15),
                return_pct=Decimal("0.02"),
                reconciled=True
            ),
            Mock(
                id=2,
                trade_date=date(2024, 1, 14),
                return_pct=Decimal("-0.01"),
                reconciled=True
            )
        ]

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_settlements
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        settlements = await manager.get_settlement_history(
            account_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        assert len(settlements) == 2
        assert settlements[0].trade_date == date(2024, 1, 15)

    @pytest.mark.asyncio
    async def test_calculate_period_return(self, manager, mock_db_session):
        """测试计算期间收益"""
        # 模拟多日结算数据
        mock_settlements = [
            Mock(trade_date=date(2024, 1, 15), return_pct=Decimal("0.02")),
            Mock(trade_date=date(2024, 1, 14), return_pct=Decimal("0.01")),
            Mock(trade_date=date(2024, 1, 13), return_pct=Decimal("-0.01")),
        ]

        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_settlements
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        period_return = await manager.calculate_period_return(
            account_id=1,
            start_date=date(2024, 1, 13),
            end_date=date(2024, 1, 15)
        )

        assert period_return["total_days"] == 3
        assert period_return["positive_days"] == 2
        assert period_return["negative_days"] == 1
        assert "cumulative_return" in period_return


class TestSettlementReport:
    """结算报表测试"""

    @pytest.mark.asyncio
    async def test_generate_daily_report(self, mock_db_session):
        """测试生成日报"""
        from src.finance.settlement import SettlementReport

        settlement = DailySettlement(
            account_id=1,
            trade_date=date(2024, 1, 15),
            begin_balance=Decimal("100000"),
            end_balance=Decimal("105000"),
            deposit=Decimal("0"),
            withdraw=Decimal("0"),
            realized_pnl=Decimal("5000"),
            total_fee=Decimal("100"),
            position_count=5,
            position_value=Decimal("80000"),
            total_orders=10,
            filled_orders=8,
            total_trades=15,
            total_volume=1500,
            total_turnover=Decimal("50000")
        )

        report = SettlementReport.generate_daily_report(settlement)

        assert report["trade_date"] == "2024-01-15"
        assert report["begin_balance"] == 100000.0
        assert report["end_balance"] == 105000.0
        assert report["net_pnl"] == 4900.0  # 5000 - 100
        assert report["return_pct"] == 0.05  # 5%

    @pytest.mark.asyncio
    async def test_generate_monthly_summary(self, mock_db_session):
        """测试生成月报"""
        from src.finance.settlement import SettlementReport

        # 模拟月内多日结算
        settlements = [
            Mock(
                trade_date=date(2024, 1, i),
                return_pct=Decimal("0.01"),
                net_pnl=Decimal("1000"),
                total_fee=Decimal("50"),
                total_trades=10
            )
            for i in range(1, 11)  # 10天数据
        ]

        summary = SettlementReport.generate_monthly_summary(
            account_id=1,
            year=2024,
            month=1,
            settlements=settlements
        )

        assert summary["total_days"] == 10
        assert summary["total_trades"] == 100
        assert summary["total_fee"] == 500.0
        assert summary["total_pnl"] == 10000.0


class TestSettlementUtils:
    """结算工具函数测试"""

    def test_calculate_drawdown(self):
        """测试计算回撤"""
        from src.finance.settlement import calculate_max_drawdown

        # 净值序列
        nav_values = [
            Decimal("1.0"),
            Decimal("1.1"),
            Decimal("1.05"),
            Decimal("1.0"),
            Decimal("1.15"),
            Decimal("1.08")
        ]

        max_dd = calculate_max_drawdown(nav_values)

        # 最大回撤应该是从1.1到1.0
        assert max_dd == pytest.approx(Decimal("-0.0909"), abs=Decimal("0.01"))

    def test_calculate_sharpe_from_returns(self):
        """测试从收益率计算夏普"""
        from src.finance.settlement import calculate_sharpe

        daily_returns = [
            Decimal("0.01"),
            Decimal("0.02"),
            Decimal("-0.01"),
            Decimal("0.015"),
            Decimal("0.005")
        ]

        sharpe = calculate_sharpe(daily_returns, risk_free_rate=Decimal("0.0001"))

        assert isinstance(sharpe, float)
        assert sharpe > 0  # 正收益应该有正夏普

    def test_calculate_volatility(self):
        """测试计算波动率"""
        from src.finance.settlement import calculate_volatility

        daily_returns = [
            Decimal("0.01"),
            Decimal("-0.01"),
            Decimal("0.015"),
            Decimal("-0.005"),
            Decimal("0.02")
        ]

        vol = calculate_volatility(daily_returns)

        assert isinstance(vol, float)
        assert vol > 0

