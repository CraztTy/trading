"""
订单状态机

职责：
- 管理订单状态流转
- 状态转换校验
- 触发状态变更事件
- 记录状态变更历史

状态流转图：
    CREATED → PENDING → PARTIAL → FILLED
       ↓         ↓         ↓
    REJECTED  CANCELLED  CANCELLED(PARTIAL)
       ↓         ↓
    (结束)    (结束)     (结束)

    任何活跃状态 → EXPIRED (条件单过期)
"""
from datetime import datetime
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum, auto

from src.models.order import Order
from src.models.enums import OrderStatus
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class OrderEvent(Enum):
    """订单事件类型"""
    CREATE = auto()          # 创建
    SUBMIT = auto()          # 提交
    FILL_PARTIAL = auto()    # 部分成交
    FILL_FULL = auto()       # 全部成交
    CANCEL = auto()          # 撤单
    REJECT = auto()          # 拒绝
    EXPIRE = auto()          # 过期


@dataclass
class StateTransition:
    """状态转换记录"""
    from_status: OrderStatus
    to_status: OrderStatus
    event: OrderEvent
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class OrderStateMachine:
    """
    订单状态机

    负责管理订单状态的生命周期，确保状态转换的合法性。
    """

    # 定义合法的状态转换规则
    # (当前状态, 事件) -> 目标状态
    TRANSITIONS: Dict[tuple, OrderStatus] = {
        # 创建 -> 提交
        (OrderStatus.CREATED, OrderEvent.SUBMIT): OrderStatus.PENDING,

        # 提交 -> 部分成交/全部成交/撤单/拒绝
        (OrderStatus.PENDING, OrderEvent.FILL_PARTIAL): OrderStatus.PARTIAL,
        (OrderStatus.PENDING, OrderEvent.FILL_FULL): OrderStatus.FILLED,
        (OrderStatus.PENDING, OrderEvent.CANCEL): OrderStatus.CANCELLED,
        (OrderStatus.PENDING, OrderEvent.REJECT): OrderStatus.REJECTED,

        # 部分成交 -> 全部成交/继续部分成交/撤单
        (OrderStatus.PARTIAL, OrderEvent.FILL_PARTIAL): OrderStatus.PARTIAL,
        (OrderStatus.PARTIAL, OrderEvent.FILL_FULL): OrderStatus.FILLED,
        (OrderStatus.PARTIAL, OrderEvent.CANCEL): OrderStatus.CANCELLED,

        # 过期规则（任何活跃状态都可以过期）
        (OrderStatus.CREATED, OrderEvent.EXPIRE): OrderStatus.EXPIRED,
        (OrderStatus.PENDING, OrderEvent.EXPIRE): OrderStatus.EXPIRED,
        (OrderStatus.PARTIAL, OrderEvent.EXPIRE): OrderStatus.EXPIRED,
    }

    # 终结状态（不可再转换）
    TERMINAL_STATES = {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
    }

    def __init__(self, order: Order):
        """
        初始化状态机

        Args:
            order: 订单实例
        """
        self.order = order
        self._transitions: List[StateTransition] = []
        self._callbacks: Dict[OrderEvent, List[Callable]] = {
            event: [] for event in OrderEvent
        }

        # 记录初始状态
        if order.created_at:
            self._transitions.append(StateTransition(
                from_status=OrderStatus.CREATED,
                to_status=order.status,
                event=OrderEvent.CREATE,
                timestamp=order.created_at
            ))

    def can_transition(self, event: OrderEvent) -> bool:
        """
        检查是否可以执行状态转换

        Args:
            event: 事件类型

        Returns:
            bool: 是否可以转换
        """
        current_status = self.order.status

        # 终结状态不可转换
        if current_status in self.TERMINAL_STATES:
            return False

        # 检查是否有对应的转换规则
        key = (current_status, event)
        return key in self.TRANSITIONS

    def get_target_status(self, event: OrderEvent) -> Optional[OrderStatus]:
        """
        获取事件对应的目标状态

        Args:
            event: 事件类型

        Returns:
            目标状态，如果不合法返回None
        """
        key = (self.order.status, event)
        return self.TRANSITIONS.get(key)

    def transition(
        self,
        event: OrderEvent,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        执行状态转换

        Args:
            event: 事件类型
            details: 转换详情（成交数量、价格、错误原因等）

        Returns:
            bool: 转换是否成功

        Raises:
            InvalidStateTransition: 非法状态转换
        """
        current_status = self.order.status
        target_status = self.get_target_status(event)

        if target_status is None:
            logger.error(
                f"非法状态转换: {current_status.value} -> {event.name}",
                order_id=self.order.order_id
            )
            raise InvalidStateTransition(
                f"Cannot transition from {current_status.value} with event {event.name}"
            )

        # 记录转换
        transition = StateTransition(
            from_status=current_status,
            to_status=target_status,
            event=event,
            timestamp=datetime.now(),
            details=details
        )
        self._transitions.append(transition)

        # 更新订单状态
        old_status = self.order.status
        self.order.status = target_status

        # 更新时间戳
        self._update_timestamp(event, details)

        logger.info(
            f"订单状态变更: {old_status.value} -> {target_status.value} "
            f"(事件: {event.name})",
            order_id=self.order.order_id,
            from_status=old_status.value,
            to_status=target_status.value,
            event_name=event.name
        )

        # 触发回调
        self._trigger_callbacks(event, transition)

        return True

    def _update_timestamp(
        self,
        event: OrderEvent,
        details: Optional[Dict[str, Any]]
    ) -> None:
        """根据事件更新订单时间戳"""
        if event == OrderEvent.SUBMIT:
            self.order.submitted_at = datetime.now()
        elif event in (OrderEvent.FILL_PARTIAL, OrderEvent.FILL_FULL):
            self.order.filled_at = datetime.now()

            # 更新成交信息
            if details:
                fill_qty = details.get('fill_qty', 0)
                fill_price = details.get('fill_price', Decimal('0'))

                if fill_qty > 0 and fill_price > 0:
                    # 计算新的成交均价
                    new_amount = self.order.filled_amount + (fill_price * fill_qty)
                    self.order.filled_qty += fill_qty

                    if self.order.filled_qty > 0:
                        self.order.filled_avg_price = (
                            new_amount / self.order.filled_qty
                        )
                    self.order.filled_amount = new_amount

        elif event == OrderEvent.CANCEL:
            self.order.cancelled_at = datetime.now()
        elif event == OrderEvent.REJECT:
            if details and 'reason' in details:
                self.order.error_msg = details['reason']

    def register_callback(
        self,
        event: OrderEvent,
        callback: Callable[[Order, StateTransition], None]
    ) -> None:
        """
        注册状态变更回调函数

        Args:
            event: 监听的事件
            callback: 回调函数，接收(order, transition)参数
        """
        self._callbacks[event].append(callback)

    def unregister_callback(
        self,
        event: OrderEvent,
        callback: Callable[[Order, StateTransition], None]
    ) -> None:
        """注销回调函数"""
        if callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    def _trigger_callbacks(
        self,
        event: OrderEvent,
        transition: StateTransition
    ) -> None:
        """触发回调函数"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(self.order, transition)
            except Exception as e:
                logger.error(
                    f"回调执行失败: {e}",
                    order_id=self.order.order_id,
                    event_name=event.name
                )

    def get_transition_history(self) -> List[StateTransition]:
        """获取状态转换历史"""
        return self._transitions.copy()

    def is_terminal(self) -> bool:
        """检查订单是否处于终结状态"""
        return self.order.status in self.TERMINAL_STATES

    def is_active(self) -> bool:
        """检查订单是否处于活跃状态（可以继续成交）"""
        return self.order.status in {
            OrderStatus.CREATED,
            OrderStatus.PENDING,
            OrderStatus.PARTIAL
        }

    def can_cancel(self) -> bool:
        """检查订单是否可以撤单"""
        return self.order.status in {
            OrderStatus.CREATED,
            OrderStatus.PENDING,
            OrderStatus.PARTIAL
        }

    def can_fill(self) -> bool:
        """检查订单是否可以成交"""
        return self.order.status in {
            OrderStatus.PENDING,
            OrderStatus.PARTIAL
        }


class InvalidStateTransition(Exception):
    """非法状态转换异常"""
    pass


# 便捷函数
def create_order_state_machine(order: Order) -> OrderStateMachine:
    """创建订单状态机实例"""
    return OrderStateMachine(order)
