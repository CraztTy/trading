"""
订单路由器测试

测试覆盖：
1. 路由决策逻辑
2. 不同订单类型的路由
3. 账户类型路由
4. 智能路由算法
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from src.execution.router import (
    OrderRouter, RouteTarget, RoutingRule, RoutingDecision
)
from src.models.order import Order
from src.models.account import Account
from src.models.enums import OrderDirection, OrderType, OrderStatus, AccountType


@pytest.fixture
def mock_order():
    """模拟订单"""
    order = Mock(spec=Order)
    order.order_id = "ORD202401011200001"
    order.account_id = 1
    order.symbol = "000001.SZ"
    order.direction = OrderDirection.BUY
    order.order_type = OrderType.LIMIT
    order.qty = 1000
    order.price = Decimal("10.50")
    order.filled_qty = 0
    return order


@pytest.fixture
def mock_account():
    """模拟账户"""
    account = Mock(spec=Account)
    account.id = 1
    account.account_type = AccountType.SIMULATE
    account.balance = Decimal("100000")
    return account


class TestRouteTarget:
    """路由目标枚举测试"""

    def test_enum_values(self):
        """测试枚举值"""
        assert RouteTarget.SIMULATED.value == "simulated"
        assert RouteTarget.REAL_EXCHANGE.value == "real_exchange"
        assert RouteTarget.PAPER_TRADING.value == "paper_trading"


class TestRoutingDecision:
    """路由决策测试"""

    def test_decision_creation(self):
        """测试决策创建"""
        decision = RoutingDecision(
            target=RouteTarget.SIMULATED,
            algorithm="MARKET",
            reason="模拟账户",
            priority=1
        )
        assert decision.target == RouteTarget.SIMULATED
        assert decision.algorithm == "MARKET"
        assert decision.reason == "模拟账户"
        assert decision.priority == 1


class TestOrderRouter:
    """订单路由器测试"""

    @pytest.fixture
    def router(self):
        """创建路由器实例"""
        return OrderRouter()

    @pytest.mark.asyncio
    async def test_router_initialization(self, router):
        """测试路由器初始化"""
        assert router is not None
        assert len(router._rules) == 0

    @pytest.mark.asyncio
    async def test_route_simulate_account(self, router, mock_order, mock_account):
        """测试模拟账户路由"""
        mock_account.account_type = AccountType.SIMULATE

        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            target = await router.route_order(mock_order)

            assert target == RouteTarget.SIMULATED

    @pytest.mark.asyncio
    async def test_route_real_account(self, router, mock_order, mock_account):
        """测试实盘账户路由"""
        mock_account.account_type = AccountType.REAL

        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            target = await router.route_order(mock_order)

            assert target == RouteTarget.REAL_EXCHANGE

    @pytest.mark.asyncio
    async def test_route_large_order_uses_twap(self, router, mock_order, mock_account):
        """测试大单使用TWAP算法"""
        mock_account.account_type = AccountType.SIMULATE
        mock_order.qty = 100000  # 大单

        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            decision = await router.get_routing_decision(mock_order)

            assert decision.target == RouteTarget.SIMULATED
            assert decision.algorithm == "TWAP"  # 大单使用TWAP

    @pytest.mark.asyncio
    async def test_route_market_order(self, router, mock_order, mock_account):
        """测试市价单路由"""
        mock_account.account_type = AccountType.SIMULATE
        mock_order.order_type = OrderType.MARKET

        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            decision = await router.get_routing_decision(mock_order)

            assert decision.algorithm == "MARKET"

    @pytest.mark.asyncio
    async def test_route_limit_order(self, router, mock_order, mock_account):
        """测试限价单路由"""
        mock_account.account_type = AccountType.SIMULATE
        mock_order.order_type = OrderType.LIMIT
        mock_order.qty = 1000  # 小单

        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            decision = await router.get_routing_decision(mock_order)

            assert decision.algorithm == "LIMIT"

    @pytest.mark.asyncio
    async def test_add_custom_rule(self, router, mock_order, mock_account):
        """测试添加自定义规则"""
        # 添加自定义规则：特定股票代码路由到特定目标
        custom_rule = RoutingRule(
            name="special_symbol",
            condition=lambda order, account: order.symbol == "000001.SZ",
            target=RouteTarget.PAPER_TRADING,
            priority=10
        )
        router.add_rule(custom_rule)

        mock_account.account_type = AccountType.REAL

        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            target = await router.route_order(mock_order)

            # 自定义规则优先级更高
            assert target == RouteTarget.PAPER_TRADING

    @pytest.mark.asyncio
    async def test_route_with_multiple_rules(self, router, mock_order, mock_account):
        """测试多规则优先级"""
        # 添加两个规则，测试优先级
        rule_low = RoutingRule(
            name="low_priority",
            condition=lambda order, account: True,
            target=RouteTarget.SIMULATED,
            priority=1
        )
        rule_high = RoutingRule(
            name="high_priority",
            condition=lambda order, account: order.qty > 500,
            target=RouteTarget.PAPER_TRADING,
            priority=10
        )

        router.add_rule(rule_low)
        router.add_rule(rule_high)

        mock_account.account_type = AccountType.REAL
        mock_order.qty = 1000  # 触发高优先级规则

        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            target = await router.route_order(mock_order)

            # 高优先级规则应该生效
            assert target == RouteTarget.PAPER_TRADING

    @pytest.mark.asyncio
    async def test_route_account_not_found(self, router, mock_order):
        """测试账户不存在"""
        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            with pytest.raises(Exception) as exc_info:
                await router.route_order(mock_order)

            assert "账户不存在" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_route_suspended_account(self, router, mock_order, mock_account):
        """测试暂停状态账户"""
        from src.models.enums import AccountStatus
        mock_account.status = AccountStatus.SUSPENDED

        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            with pytest.raises(Exception) as exc_info:
                await router.route_order(mock_order)

            assert "账户状态异常" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_account_routing_info(self, router, mock_account):
        """测试获取账户路由信息"""
        with patch('src.execution.router.AccountService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_account = AsyncMock(return_value=mock_account)
            mock_service_class.return_value = mock_service

            info = await router.get_account_routing_info(1)

            assert info is not None
            assert info.account_id == 1
            assert info.account_type == AccountType.SIMULATE

    def test_remove_rule(self, router):
        """测试移除规则"""
        rule = RoutingRule(
            name="test_rule",
            condition=lambda order, account: True,
            target=RouteTarget.SIMULATED,
            priority=1
        )
        router.add_rule(rule)
        assert len(router._rules) == 1

        router.remove_rule("test_rule")
        assert len(router._rules) == 0

    def test_clear_rules(self, router):
        """测试清除所有规则"""
        rule = RoutingRule(
            name="test_rule",
            condition=lambda order, account: True,
            target=RouteTarget.SIMULATED,
            priority=1
        )
        router.add_rule(rule)
        assert len(router._rules) == 1

        router.clear_rules()
        assert len(router._rules) == 0
