"""
订单状态机单元测试

测试覆盖所有合法状态流转和非法状态转换拦截
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from src.core.order_state_machine import (
    OrderStateMachine,
    OrderEvent,
    StateTransition,
    InvalidStateTransition
)
from src.models.enums import OrderStatus


@pytest.mark.unit
class TestOrderStateMachine:
    """订单状态机测试类"""

    @pytest.fixture
    def mock_order(self):
        """创建Mock订单"""
        order = MagicMock()
        order.order_id = "ORD20240101000001001"
        order.status = OrderStatus.CREATED
        order.created_at = datetime.now()
        order.filled_qty = 0
        order.filled_avg_price = Decimal("0")
        order.filled_amount = Decimal("0")
        order.submitted_at = None
        order.filled_at = None
        order.cancelled_at = None
        order.error_msg = None
        return order

    # ==================== 合法状态流转测试 ====================

    def test_created_to_pending_on_submit(self, mock_order):
        """测试: CREATED → PENDING (提交事件)"""
        # Arrange
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(OrderEvent.SUBMIT)

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.PENDING
        assert len(sm.get_transition_history()) == 2  # 初始 + 本次

    def test_pending_to_filled_on_full_fill(self, mock_order):
        """测试: PENDING → FILLED (全部成交)"""
        # Arrange
        mock_order.status = OrderStatus.PENDING
        mock_order.qty = 1000
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(
            OrderEvent.FILL_FULL,
            details={"fill_qty": 1000, "fill_price": Decimal("10.50")}
        )

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.FILLED
        assert mock_order.filled_qty == 1000
        assert mock_order.filled_avg_price == Decimal("10.50")

    def test_pending_to_partial_on_partial_fill(self, mock_order):
        """测试: PENDING → PARTIAL (部分成交)"""
        # Arrange
        mock_order.status = OrderStatus.PENDING
        mock_order.qty = 1000
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(
            OrderEvent.FILL_PARTIAL,
            details={"fill_qty": 500, "fill_price": Decimal("10.50")}
        )

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.PARTIAL
        assert mock_order.filled_qty == 500

    def test_pending_to_cancelled_on_cancel(self, mock_order):
        """测试: PENDING → CANCELLED (撤单)"""
        # Arrange
        mock_order.status = OrderStatus.PENDING
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(OrderEvent.CANCEL)

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.CANCELLED
        assert mock_order.cancelled_at is not None

    def test_pending_to_rejected_on_reject(self, mock_order):
        """测试: PENDING → REJECTED (拒绝)"""
        # Arrange
        mock_order.status = OrderStatus.PENDING
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(
            OrderEvent.REJECT,
            details={"reason": "资金不足"}
        )

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.REJECTED
        assert mock_order.error_msg == "资金不足"

    def test_partial_to_filled_on_full_fill(self, mock_order):
        """测试: PARTIAL → FILLED (部分成交后全部成交)"""
        # Arrange
        mock_order.status = OrderStatus.PARTIAL
        mock_order.qty = 1000
        mock_order.filled_qty = 500
        mock_order.filled_amount = Decimal("5250")  # 500 * 10.50
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(
            OrderEvent.FILL_FULL,
            details={"fill_qty": 500, "fill_price": Decimal("10.60")}
        )

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.FILLED
        assert mock_order.filled_qty == 1000
        # 验证均价计算: (5250 + 5300) / 1000 = 10.55
        assert mock_order.filled_avg_price == Decimal("10.55")

    def test_partial_to_partial_on_partial_fill(self, mock_order):
        """测试: PARTIAL → PARTIAL (多次部分成交)"""
        # Arrange
        mock_order.status = OrderStatus.PARTIAL
        mock_order.qty = 1000
        mock_order.filled_qty = 300
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(
            OrderEvent.FILL_PARTIAL,
            details={"fill_qty": 200, "fill_price": Decimal("10.50")}
        )

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.PARTIAL
        assert mock_order.filled_qty == 500

    def test_partial_to_cancelled_on_cancel(self, mock_order):
        """测试: PARTIAL → CANCELLED (部分成交后撤单)"""
        # Arrange
        mock_order.status = OrderStatus.PARTIAL
        mock_order.filled_qty = 500
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(OrderEvent.CANCEL)

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.CANCELLED
        assert mock_order.filled_qty == 500  # 已成交部分保留

    def test_created_to_expired(self, mock_order):
        """测试: CREATED → EXPIRED (条件单过期)"""
        # Arrange
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(OrderEvent.EXPIRE)

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.EXPIRED

    def test_pending_to_expired(self, mock_order):
        """测试: PENDING → EXPIRED (订单过期)"""
        # Arrange
        mock_order.status = OrderStatus.PENDING
        sm = OrderStateMachine(mock_order)

        # Act
        result = sm.transition(OrderEvent.EXPIRE)

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.EXPIRED

    # ==================== 非法状态转换测试 ====================

    def test_created_to_filled_raises_error(self, mock_order):
        """测试: CREATED → FILLED 非法，应抛出异常"""
        # Arrange
        sm = OrderStateMachine(mock_order)

        # Act & Assert
        with pytest.raises(InvalidStateTransition):
            sm.transition(OrderEvent.FILL_FULL)

    def test_filled_to_cancelled_raises_error(self, mock_order):
        """测试: FILLED → CANCELLED 非法，应抛出异常"""
        # Arrange
        mock_order.status = OrderStatus.FILLED
        sm = OrderStateMachine(mock_order)

        # Act & Assert
        with pytest.raises(InvalidStateTransition):
            sm.transition(OrderEvent.CANCEL)

    def test_cancelled_to_pending_raises_error(self, mock_order):
        """测试: CANCELLED → PENDING 非法，应抛出异常"""
        # Arrange
        mock_order.status = OrderStatus.CANCELLED
        sm = OrderStateMachine(mock_order)

        # Act & Assert
        with pytest.raises(InvalidStateTransition):
            sm.transition(OrderEvent.SUBMIT)

    def test_rejected_to_any_raises_error(self, mock_order):
        """测试: REJECTED状态任何转换都非法"""
        # Arrange
        mock_order.status = OrderStatus.REJECTED
        sm = OrderStateMachine(mock_order)

        # Act & Assert
        for event in OrderEvent:
            with pytest.raises(InvalidStateTransition):
                sm.transition(event)

    def test_expired_to_any_raises_error(self, mock_order):
        """测试: EXPIRED状态任何转换都非法"""
        # Arrange
        mock_order.status = OrderStatus.EXPIRED
        sm = OrderStateMachine(mock_order)

        # Act & Assert
        for event in OrderEvent:
            with pytest.raises(InvalidStateTransition):
                sm.transition(event)

    # ==================== 状态查询方法测试 ====================

    def test_is_terminal(self, mock_order):
        """测试终结状态判断"""
        terminal_states = [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]

        for status in terminal_states:
            mock_order.status = status
            sm = OrderStateMachine(mock_order)
            assert sm.is_terminal() is True, f"{status.value} 应该是终结状态"

        # 非终结状态
        non_terminal = [OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL]
        for status in non_terminal:
            mock_order.status = status
            sm = OrderStateMachine(mock_order)
            assert sm.is_terminal() is False, f"{status.value} 不应该是终结状态"

    def test_is_active(self, mock_order):
        """测试活跃状态判断"""
        active_states = [OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL]

        for status in active_states:
            mock_order.status = status
            sm = OrderStateMachine(mock_order)
            assert sm.is_active() is True, f"{status.value} 应该是活跃状态"

        # 非活跃状态
        inactive = [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]
        for status in inactive:
            mock_order.status = status
            sm = OrderStateMachine(mock_order)
            assert sm.is_active() is False, f"{status.value} 不应该是活跃状态"

    def test_can_cancel(self, mock_order):
        """测试可撤单判断"""
        cancellable = [OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL]

        for status in cancellable:
            mock_order.status = status
            sm = OrderStateMachine(mock_order)
            assert sm.can_cancel() is True, f"{status.value} 状态应该可以撤单"

        # 不可撤单状态
        not_cancellable = [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]
        for status in not_cancellable:
            mock_order.status = status
            sm = OrderStateMachine(mock_order)
            assert sm.can_cancel() is False, f"{status.value} 状态不应该可以撤单"

    def test_can_fill(self, mock_order):
        """测试可成交判断"""
        fillable = [OrderStatus.PENDING, OrderStatus.PARTIAL]

        for status in fillable:
            mock_order.status = status
            sm = OrderStateMachine(mock_order)
            assert sm.can_fill() is True, f"{status.value} 状态应该可以成交"

        # 不可成交状态
        not_fillable = [OrderStatus.CREATED, OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED]
        for status in not_fillable:
            mock_order.status = status
            sm = OrderStateMachine(mock_order)
            assert sm.can_fill() is False, f"{status.value} 状态不应该可以成交"

    # ==================== 回调机制测试 ====================

    def test_register_and_trigger_callback(self, mock_order):
        """测试回调注册和触发"""
        # Arrange
        sm = OrderStateMachine(mock_order)
        callback_called = []

        def test_callback(order, transition):
            callback_called.append((order, transition))

        sm.register_callback(OrderEvent.SUBMIT, test_callback)

        # Act
        sm.transition(OrderEvent.SUBMIT)

        # Assert
        assert len(callback_called) == 1
        assert callback_called[0][0] == mock_order
        assert callback_called[0][1].event == OrderEvent.SUBMIT

    def test_unregister_callback(self, mock_order):
        """测试回调注销"""
        # Arrange
        sm = OrderStateMachine(mock_order)
        callback_called = []

        def test_callback(order, transition):
            callback_called.append(True)

        sm.register_callback(OrderEvent.SUBMIT, test_callback)
        sm.unregister_callback(OrderEvent.SUBMIT, test_callback)

        # Act
        sm.transition(OrderEvent.SUBMIT)

        # Assert
        assert len(callback_called) == 0

    def test_callback_exception_not_blocking(self, mock_order):
        """测试回调异常不阻塞主流程"""
        # Arrange
        sm = OrderStateMachine(mock_order)

        def failing_callback(order, transition):
            raise ValueError("回调错误")

        sm.register_callback(OrderEvent.SUBMIT, failing_callback)

        # Act - 不应抛出异常
        result = sm.transition(OrderEvent.SUBMIT)

        # Assert
        assert result is True
        assert mock_order.status == OrderStatus.PENDING

    # ==================== 转换历史测试 ====================

    def test_transition_history(self, mock_order):
        """测试状态转换历史记录"""
        # Arrange
        sm = OrderStateMachine(mock_order)

        # Act - 执行多次转换
        sm.transition(OrderEvent.SUBMIT)
        sm.transition(OrderEvent.FILL_PARTIAL, details={"fill_qty": 500})
        sm.transition(OrderEvent.FILL_FULL, details={"fill_qty": 500})

        # Assert
        history = sm.get_transition_history()
        assert len(history) == 4  # 初始创建 + 3次转换

        # 验证第二次转换（SUBMIT）
        assert history[1].from_status == OrderStatus.CREATED
        assert history[1].to_status == OrderStatus.PENDING
        assert history[1].event == OrderEvent.SUBMIT

    def test_can_transition(self, mock_order):
        """测试状态转换可行性检查"""
        sm = OrderStateMachine(mock_order)

        # CREATED状态允许的转换
        assert sm.can_transition(OrderEvent.SUBMIT) is True
        assert sm.can_transition(OrderEvent.EXPIRE) is True
        assert sm.can_transition(OrderEvent.CANCEL) is False

        # PENDING状态
        mock_order.status = OrderStatus.PENDING
        sm = OrderStateMachine(mock_order)
        assert sm.can_transition(OrderEvent.FILL_PARTIAL) is True
        assert sm.can_transition(OrderEvent.FILL_FULL) is True
        assert sm.can_transition(OrderEvent.CANCEL) is True

    def test_get_target_status(self, mock_order):
        """测试获取目标状态"""
        sm = OrderStateMachine(mock_order)

        # CREATED + SUBMIT → PENDING
        assert sm.get_target_status(OrderEvent.SUBMIT) == OrderStatus.PENDING

        # CREATED + CANCEL → None (非法转换)
        assert sm.get_target_status(OrderEvent.CANCEL) is None
