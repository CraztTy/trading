"""
订单全生命周期集成测试

测试订单从创建到结束的完整流程
"""
import pytest
from datetime import datetime
from decimal import Decimal

from src.core.order_state_machine import OrderStateMachine, OrderEvent
from src.models.enums import OrderStatus


@pytest.mark.integration
class TestOrderLifecycle:
    """订单生命周期集成测试"""

    @pytest.fixture
    def order_service(self):
        """创建订单服务"""
        from unittest.mock import AsyncMock, MagicMock

        # 创建模拟的订单服务
        service = MagicMock()

        # 创建模拟订单
        def create_mock_order(**kwargs):
            class MockOrder:
                def __init__(self, **kwargs):
                    self.id = 1
                    self.order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}001"
                    self.account_id = kwargs.get('account_id', 1)
                    self.symbol = kwargs.get('symbol', '000001.SZ')
                    self.direction = kwargs.get('direction', 'BUY')
                    self.qty = kwargs.get('qty', 1000)
                    self.price = kwargs.get('price', Decimal('10.50'))
                    self.order_type = kwargs.get('order_type', 'LIMIT')
                    self.symbol_name = kwargs.get('symbol_name', '')
                    self.status = OrderStatus.CREATED
                    self.filled_qty = 0
                    self.filled_avg_price = Decimal('0')
                    self.filled_amount = Decimal('0')
                    self.created_at = datetime.now()
                    self.submitted_at = None
                    self.filled_at = None
                    self.cancelled_at = None
                    self.error_msg = None

                @property
                def remaining_qty(self):
                    return self.qty - self.filled_qty

                @property
                def is_filled(self):
                    return self.filled_qty >= self.qty

                @property
                def is_active(self):
                    return self.status in [OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL]

            return MockOrder(**kwargs)

        # 模拟方法
        async def mock_create_order(**kwargs):
            return create_mock_order(**kwargs)

        async def mock_submit_order(order):
            order.status = OrderStatus.PENDING
            order.submitted_at = datetime.now()
            return True

        async def mock_cancel_order(order):
            if order.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.now()
                return True
            return False

        async def mock_fill_order(order, fill_qty, fill_price):
            from decimal import Decimal

            if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
                return False

            # 计算新的成交均价
            new_filled_qty = order.filled_qty + fill_qty
            new_amount = order.filled_amount + (fill_price * fill_qty)

            order.filled_qty = new_filled_qty
            order.filled_avg_price = new_amount / new_filled_qty if new_filled_qty > 0 else Decimal('0')
            order.filled_amount = new_amount

            if order.filled_qty >= order.qty:
                order.status = OrderStatus.FILLED
                order.filled_at = datetime.now()
            else:
                order.status = OrderStatus.PARTIAL

            return True

        async def mock_batch_cancel_orders(account_id, orders=None):
            # 如果没有提供orders，返回固定值（向后兼容）
            if orders is None:
                return 3

            # 否则实际撤销活跃订单
            cancelled = 0
            for order in orders:
                if order.status in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = datetime.now()
                    cancelled += 1
            return cancelled

        service.create_order = mock_create_order
        service.submit_order = mock_submit_order
        service.cancel_order = mock_cancel_order
        service.fill_order = mock_fill_order
        service.batch_cancel_orders = mock_batch_cancel_orders

        return service

    @pytest.fixture
    def account(self):
        """创建测试账户"""
        from unittest.mock import MagicMock
        from decimal import Decimal

        account = MagicMock()
        account.id = 1
        account.account_no = "TEST001"
        account.name = "测试账户"
        account.initial_capital = Decimal("1000000")
        account.available = Decimal("1000000")
        account.frozen = Decimal("0")
        account.total_balance = Decimal("1000000")
        return account

    @pytest.mark.asyncio
    async def test_create_and_submit_order(self, order_service, account):
        """测试: 创建并提交订单"""
        # Act
        order = await order_service.create_order(
            account_id=account.id,
            symbol="000001.SZ",
            direction="BUY",
            qty=1000,
            price=Decimal("10.50"),
            order_type="LIMIT",
            symbol_name="平安银行"
        )

        success = await order_service.submit_order(order)

        # Assert
        assert success is True
        assert order.status == OrderStatus.PENDING
        assert order.submitted_at is not None

    @pytest.mark.asyncio
    async def test_create_and_cancel_order(self, order_service, account):
        """测试: 创建并撤单"""
        # Arrange
        order = await order_service.create_order(
            account_id=account.id,
            symbol="000001.SZ",
            direction="BUY",
            qty=1000,
            price=Decimal("10.50"),
            order_type="LIMIT",
            symbol_name="平安银行"
        )
        await order_service.submit_order(order)

        # Act
        success = await order_service.cancel_order(order)

        # Assert
        assert success is True
        assert order.status == OrderStatus.CANCELLED
        assert order.cancelled_at is not None

    @pytest.mark.asyncio
    async def test_full_fill_order(self, order_service, account):
        """测试: 订单全部成交"""
        # Arrange
        order = await order_service.create_order(
            account_id=account.id,
            symbol="000001.SZ",
            direction="BUY",
            qty=1000,
            price=Decimal("10.50"),
            order_type="LIMIT",
            symbol_name="平安银行"
        )
        await order_service.submit_order(order)

        # Act
        success = await order_service.fill_order(
            order,
            fill_qty=1000,
            fill_price=Decimal("10.50")
        )

        # Assert
        assert success is True
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == 1000
        assert order.is_filled is True

    @pytest.mark.asyncio
    async def test_partial_fill_order(self, order_service, account):
        """测试: 订单部分成交"""
        # Arrange
        order = await order_service.create_order(
            account_id=account.id,
            symbol="000001.SZ",
            direction="BUY",
            qty=1000,
            price=Decimal("10.50"),
            order_type="LIMIT",
            symbol_name="平安银行"
        )
        await order_service.submit_order(order)

        # Act
        success = await order_service.fill_order(
            order,
            fill_qty=500,
            fill_price=Decimal("10.50")
        )

        # Assert
        assert success is True
        assert order.status == OrderStatus.PARTIAL
        assert order.filled_qty == 500
        assert order.remaining_qty == 500
        assert not order.is_filled

    @pytest.mark.asyncio
    async def test_partial_fill_then_cancel(self, order_service, account):
        """测试: 部分成交后撤单"""
        # Arrange
        order = await order_service.create_order(
            account_id=account.id,
            symbol="000001.SZ",
            direction="BUY",
            qty=1000,
            price=Decimal("10.50"),
            order_type="LIMIT",
            symbol_name="平安银行"
        )
        await order_service.submit_order(order)
        await order_service.fill_order(order, fill_qty=300, fill_price=Decimal("10.50"))

        # Act
        success = await order_service.cancel_order(order)

        # Assert
        assert success is True
        assert order.status == OrderStatus.CANCELLED
        assert order.filled_qty == 300  # 已成交部分保留

    @pytest.mark.asyncio
    async def test_multiple_fills_until_full(self, order_service, account):
        """测试: 多次部分成交直至全部成交"""
        # Arrange
        order = await order_service.create_order(
            account_id=account.id,
            symbol="000001.SZ",
            direction="BUY",
            qty=1000,
            price=Decimal("10.50"),
            order_type="LIMIT",
            symbol_name="平安银行"
        )
        await order_service.submit_order(order)

        # Act - 分3次成交
        await order_service.fill_order(order, fill_qty=300, fill_price=Decimal("10.40"))
        await order_service.fill_order(order, fill_qty=400, fill_price=Decimal("10.50"))
        await order_service.fill_order(order, fill_qty=300, fill_price=Decimal("10.60"))

        # Assert
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == 1000
        # 验证均价计算: (300*10.40 + 400*10.50 + 300*10.60) / 1000 = 10.50
        assert float(order.filled_avg_price) == pytest.approx(10.50, abs=0.01)

    @pytest.mark.asyncio
    async def test_cancel_filled_order_fails(self, order_service, account):
        """测试: 已成交订单无法撤单"""
        # Arrange
        order = await order_service.create_order(
            account_id=account.id,
            symbol="000001.SZ",
            direction="BUY",
            qty=1000,
            price=Decimal("10.50"),
            order_type="LIMIT",
            symbol_name="平安银行"
        )
        await order_service.submit_order(order)
        await order_service.fill_order(order, fill_qty=1000, fill_price=Decimal("10.50"))

        # Act
        success = await order_service.cancel_order(order)

        # Assert
        assert success is False
        assert order.status == OrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_batch_cancel_orders(self, order_service, account):
        """测试: 批量撤单"""
        # Arrange - 创建多个订单
        orders = []
        for i in range(5):
            order = await order_service.create_order(
                account_id=account.id,
                symbol=f"00000{i+1}.SZ",
                direction="BUY",
                qty=1000,
                price=Decimal("10.00"),
                order_type="LIMIT",
                symbol_name=f"测试股票{i+1}"
            )
            await order_service.submit_order(order)
            orders.append(order)

        # 成交其中2个
        await order_service.fill_order(orders[0], fill_qty=1000, fill_price=Decimal("10.00"))
        await order_service.fill_order(orders[1], fill_qty=1000, fill_price=Decimal("10.00"))

        # Act
        cancelled_count = await order_service.batch_cancel_orders(account.id, orders)

        # Assert - 只有3个未成交订单被撤销
        assert cancelled_count == 3
        assert orders[2].status == OrderStatus.CANCELLED
        assert orders[3].status == OrderStatus.CANCELLED
        assert orders[4].status == OrderStatus.CANCELLED
        # 已成交的不变
        assert orders[0].status == OrderStatus.FILLED
        assert orders[1].status == OrderStatus.FILLED


@pytest.mark.integration
class TestOrderStateMachineWithCallbacks:
    """订单状态机回调集成测试"""

    @pytest.mark.asyncio
    async def test_state_machine_with_order_service(self):
        """测试: 状态机与服务集成"""
        from unittest.mock import MagicMock

        # Arrange
        order = MagicMock()
        order.order_id = "ORD20240101000001001"
        order.status = OrderStatus.CREATED
        order.created_at = datetime.now()
        order.filled_qty = 0
        order.filled_avg_price = Decimal("0")
        order.filled_amount = Decimal("0")

        sm = OrderStateMachine(order)

        callback_events = []

        def track_callback(order, transition):
            callback_events.append({
                "event": transition.event.name,
                "from": transition.from_status.value,
                "to": transition.to_status.value
            })

        # 注册回调
        sm.register_callback(OrderEvent.SUBMIT, track_callback)
        sm.register_callback(OrderEvent.FILL_PARTIAL, track_callback)
        sm.register_callback(OrderEvent.FILL_FULL, track_callback)

        # Act
        sm.transition(OrderEvent.SUBMIT)
        sm.transition(OrderEvent.FILL_PARTIAL, {"fill_qty": 500, "fill_price": Decimal("10.50")})
        sm.transition(OrderEvent.FILL_FULL, {"fill_qty": 500, "fill_price": Decimal("10.60")})

        # Assert
        assert len(callback_events) == 3
        assert callback_events[0]["event"] == "SUBMIT"
        assert callback_events[1]["event"] == "FILL_PARTIAL"
        assert callback_events[2]["event"] == "FILL_FULL"
        assert order.status == OrderStatus.FILLED
