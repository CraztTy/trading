"""
资金管理器测试

测试覆盖：
1. 出入金操作
2. 资金冻结/解冻
3. 资金流水记录
4. 资金查询统计
"""
import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from src.finance.capital_manager import CapitalManager, CapitalOperationType
from src.models.balance_flow import BalanceFlow
from src.models.enums import FlowType


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
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
    account.status.value = "ACTIVE"
    return account


class TestCapitalOperationType:
    """资金操作类型测试"""

    def test_type_values(self):
        """测试类型值"""
        assert CapitalOperationType.DEPOSIT.value == "deposit"
        assert CapitalOperationType.WITHDRAW.value == "withdraw"
        assert CapitalOperationType.FREEZE.value == "freeze"
        assert CapitalOperationType.UNFREEZE.value == "unfreeze"


class TestCapitalManager:
    """资金管理器测试"""

    @pytest.fixture
    def manager(self, mock_db_session):
        """创建资金管理器"""
        return CapitalManager(session=mock_db_session)

    @pytest.mark.asyncio
    async def test_deposit_success(self, manager, mock_account):
        """测试入金成功"""
        with patch('src.finance.capital_manager.AccountService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_account = AsyncMock(return_value=mock_account)
            mock_service.return_value = mock_service_instance

            result = await manager.deposit(
                account_id=1,
                amount=Decimal("50000"),
                remark="测试入金"
            )

            assert result.success is True
            assert result.amount == Decimal("50000")
            assert mock_account.total_balance == Decimal("150000")
            assert mock_account.available == Decimal("130000")

    @pytest.mark.asyncio
    async def test_deposit_invalid_amount(self, manager, mock_account):
        """测试无效入金金额"""
        result = await manager.deposit(
            account_id=1,
            amount=Decimal("-1000"),
            remark="测试入金"
        )

        assert result.success is False
        assert "金额必须大于0" in result.error_msg

    @pytest.mark.asyncio
    async def test_withdraw_success(self, manager, mock_account):
        """测试出金成功"""
        with patch('src.finance.capital_manager.AccountService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_account = AsyncMock(return_value=mock_account)
            mock_service.return_value = mock_service_instance

            result = await manager.withdraw(
                account_id=1,
                amount=Decimal("30000"),
                remark="测试出金"
            )

            assert result.success is True
            assert result.amount == Decimal("30000")
            assert mock_account.total_balance == Decimal("70000")
            assert mock_account.available == Decimal("50000")

    @pytest.mark.asyncio
    async def test_withdraw_insufficient_balance(self, manager, mock_account):
        """测试出金余额不足"""
        mock_account.available = Decimal("1000")

        with patch('src.finance.capital_manager.AccountService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_account = AsyncMock(return_value=mock_account)
            mock_service.return_value = mock_service_instance

            result = await manager.withdraw(
                account_id=1,
                amount=Decimal("5000"),
                remark="测试出金"
            )

            assert result.success is False
            assert "可用资金不足" in result.error_msg

    @pytest.mark.asyncio
    async def test_freeze_for_order(self, manager, mock_account):
        """测试委托冻结"""
        with patch('src.finance.capital_manager.AccountService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_account = AsyncMock(return_value=mock_account)
            mock_service.return_value = mock_service_instance

            result = await manager.freeze_for_order(
                account_id=1,
                order_id=100,
                amount=Decimal("10000")
            )

            assert result.success is True
            assert mock_account.available == Decimal("70000")
            assert mock_account.frozen == Decimal("30000")

    @pytest.mark.asyncio
    async def test_unfreeze_for_order(self, manager, mock_account):
        """测试委托解冻"""
        mock_account.frozen = Decimal("30000")

        with patch('src.finance.capital_manager.AccountService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_account = AsyncMock(return_value=mock_account)
            mock_service.return_value = mock_service_instance

            result = await manager.unfreeze_for_order(
                account_id=1,
                order_id=100,
                amount=Decimal("10000")
            )

            assert result.success is True
            assert mock_account.available == Decimal("90000")
            assert mock_account.frozen == Decimal("20000")

    @pytest.mark.asyncio
    async def test_transfer_between_accounts(self, manager):
        """测试账户间转账"""
        from_account = Mock()
        from_account.id = 1
        from_account.available = Decimal("50000")

        to_account = Mock()
        to_account.id = 2
        to_account.available = Decimal("30000")

        with patch('src.finance.capital_manager.AccountService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service_instance.get_account = AsyncMock(side_effect=[from_account, to_account])
            mock_service.return_value = mock_service_instance

            result = await manager.transfer(
                from_account_id=1,
                to_account_id=2,
                amount=Decimal("10000"),
                remark="转账测试"
            )

            assert result.success is True
            assert from_account.available == Decimal("40000")
            assert to_account.available == Decimal("40000")


class TestBalanceFlowQuery:
    """资金流水查询测试"""

    @pytest.fixture
    def manager(self, mock_db_session):
        return CapitalManager(session=mock_db_session)

    @pytest.mark.asyncio
    async def test_get_balance_flows(self, manager, mock_db_session):
        """测试获取资金流水"""
        # 模拟查询结果
        mock_flows = [
            Mock(
                id=1,
                flow_type=FlowType.DEPOSIT,
                amount=Decimal("50000"),
                created_at=datetime.now()
            ),
            Mock(
                id=2,
                flow_type=FlowType.TRADE_BUY,
                amount=Decimal("-10000"),
                created_at=datetime.now()
            )
        ]

        # 模拟execute返回
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_flows
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        flows = await manager.get_balance_flows(account_id=1, limit=10)

        assert len(flows) == 2
        assert flows[0].flow_type == FlowType.DEPOSIT

    @pytest.mark.asyncio
    async def test_get_flow_statistics(self, manager, mock_db_session):
        """测试获取流水统计"""
        # 模拟统计数据
        mock_stats = [
            (FlowType.DEPOSIT.value, Decimal("100000")),
            (FlowType.WITHDRAW.value, Decimal("-30000")),
            (FlowType.TRADE_BUY.value, Decimal("-50000")),
        ]

        mock_result = AsyncMock()
        mock_result.all.return_value = mock_stats
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        stats = await manager.get_flow_statistics(
            account_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        assert "total_deposit" in stats
        assert "total_withdraw" in stats
        assert "total_buy" in stats


class TestCapitalValidation:
    """资金验证测试"""

    def test_validate_amount_positive(self):
        """测试验证正金额"""
        from src.finance.capital_manager import validate_amount

        assert validate_amount(Decimal("1000")) is True
        assert validate_amount(Decimal("0.01")) is True

    def test_validate_amount_zero_or_negative(self):
        """测试验证零或负金额"""
        from src.finance.capital_manager import validate_amount

        assert validate_amount(Decimal("0")) is False
        assert validate_amount(Decimal("-100")) is False

    def test_validate_amount_too_large(self):
        """测试验证超大金额"""
        from src.finance.capital_manager import validate_amount

        assert validate_amount(Decimal("1000000001")) is False  # 超过10亿

    def test_validate_amount_precision(self):
        """测试验证金额精度"""
        from src.finance.capital_manager import validate_amount

        assert validate_amount(Decimal("1000.001")) is False  # 超过2位小数


class TestCapitalSnapshot:
    """资金快照测试"""

    @pytest.mark.asyncio
    async def test_create_snapshot(self, mock_db_session):
        """测试创建资金快照"""
        from src.finance.capital_manager import CapitalSnapshot

        snapshot = CapitalSnapshot(
            account_id=1,
            total_balance=Decimal("100000"),
            available=Decimal("80000"),
            frozen=Decimal("20000"),
            position_value=Decimal("50000"),
            timestamp=datetime.now()
        )

        assert snapshot.account_id == 1
        assert snapshot.total_balance == Decimal("100000")
        assert snapshot.net_asset == Decimal("150000")  # 总资产 + 持仓市值

    def test_calculate_buying_power(self):
        """测试计算购买力"""
        from src.finance.capital_manager import calculate_buying_power

        # 模拟账户和持仓
        account = Mock()
        account.available = Decimal("50000")

        positions = [
            Mock(symbol="000001.SZ", market_value=Decimal("30000")),
            Mock(symbol="600519.SH", market_value=Decimal("70000"))
        ]

        buying_power = calculate_buying_power(account, positions)

        assert buying_power["available_cash"] == Decimal("50000")
        assert buying_power["position_value"] == Decimal("100000")
        assert buying_power["total_buying_power"] == Decimal("150000")
