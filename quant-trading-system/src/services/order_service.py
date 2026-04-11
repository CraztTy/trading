"""
订单服务层

提供完整的订单生命周期管理：
- 创建订单
- 提交订单
- 成交处理
- 撤单
- 查询
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.core.order_state_machine import (
    OrderStateMachine, OrderEvent, create_order_state_machine
)
from src.core.order_event_handlers import OrderEventHandler, register_event_handlers
from src.models.order import Order
from src.models.account import Account
from src.models.enums import OrderStatus, OrderDirection, OrderType
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class OrderService:
    """
    订单服务

    职责：
    1. 创建和管理订单
    2. 处理订单状态流转
    3. 协调资金和持仓操作
    4. 提供订单查询接口
    """

    def __init__(self, session: AsyncSession):
        """
        初始化订单服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.event_handler = OrderEventHandler(session)

    async def create_order(
        self,
        account_id: int,
        symbol: str,
        direction: OrderDirection,
        qty: int,
        price: Optional[Decimal] = None,
        order_type: OrderType = OrderType.LIMIT,
        strategy_id: Optional[int] = None,
        symbol_name: str = ""
    ) -> Order:
        """
        创建新订单

        Args:
            account_id: 账户ID
            symbol: 股票代码
            direction: 买卖方向
            qty: 数量
            price: 价格（市价单可为None）
            order_type: 订单类型
            strategy_id: 策略ID
            symbol_name: 股票名称

        Returns:
            Order: 创建的订单
        """
        # 生成订单号
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"

        # 创建订单
        order = Order(
            order_id=order_id,
            account_id=account_id,
            symbol=symbol,
            direction=direction,
            qty=qty,
            price=price,
            order_type=order_type,
            strategy_id=strategy_id,
            symbol_name=symbol_name
        )

        self.session.add(order)
        await self.session.flush()

        logger.info(
            "创建订单",
            order_id=order.order_id,
            symbol=symbol,
            direction=direction.value if hasattr(direction, 'value') else direction,
            qty=qty,
            price=float(price) if price else None
        )

        return order

    async def submit_order(self, order: Order) -> bool:
        """
        提交订单

        职责：
        1. 状态机转换到 PENDING
        2. 冻结资金/持仓
        3. 发送到交易所（模拟）

        Args:
            order: 订单

        Returns:
            bool: 提交是否成功
        """
        try:
            # 创建状态机
            state_machine = create_order_state_machine(order)
            register_event_handlers(state_machine, self.event_handler)

            # 状态转换
            success = state_machine.transition(OrderEvent.SUBMIT)

            if success:
                await self.session.flush()
                logger.info(
                    "订单提交成功",
                    order_id=order.order_id,
                    status=order.status.value if hasattr(order.status, 'value') else order.status
                )

            return success

        except Exception as e:
            logger.error(
                f"订单提交失败: {e}",
                order_id=order.order_id
            )
            # 标记为拒绝
            await self.reject_order(order, str(e))
            return False

    async def fill_order(
        self,
        order: Order,
        fill_qty: int,
        fill_price: Decimal
    ) -> bool:
        """
        订单成交处理

        Args:
            order: 订单
            fill_qty: 成交数量
            fill_price: 成交价格

        Returns:
            bool: 处理是否成功
        """
        try:
            # 验证成交数量
            if fill_qty <= 0 or fill_qty > order.remaining_qty:
                raise ValueError(f"非法成交数量: {fill_qty}")

            # 创建状态机
            state_machine = create_order_state_machine(order)
            register_event_handlers(state_machine, self.event_handler)

            # 判断是部分成交还是全部成交
            new_filled_qty = order.filled_qty + fill_qty

            if new_filled_qty >= order.qty:
                # 全部成交
                event = OrderEvent.FILL_FULL
            else:
                # 部分成交
                event = OrderEvent.FILL_PARTIAL

            # 状态转换
            success = state_machine.transition(
                event,
                details={
                    'fill_qty': fill_qty,
                    'fill_price': float(fill_price)
                }
            )

            if success:
                await self.session.flush()
                logger.info(
                    "订单成交处理完成",
                    order_id=order.order_id,
                    event=event.name,
                    fill_qty=fill_qty,
                    fill_price=float(fill_price),
                    filled_qty=order.filled_qty,
                    total_qty=order.qty
                )

            return success

        except Exception as e:
            logger.error(
                f"订单成交处理失败: {e}",
                order_id=order.order_id
            )
            return False

    async def cancel_order(self, order: Order) -> bool:
        """
        撤单

        Args:
            order: 订单

        Returns:
            bool: 撤单是否成功
        """
        try:
            # 创建状态机
            state_machine = create_order_state_machine(order)
            register_event_handlers(state_machine, self.event_handler)

            # 检查是否可以撤单
            if not state_machine.can_cancel():
                logger.warning(
                    "订单不可撤",
                    order_id=order.order_id,
                    status=order.status.value if hasattr(order.status, 'value') else order.status
                )
                return False

            # 状态转换
            success = state_machine.transition(OrderEvent.CANCEL)

            if success:
                await self.session.flush()
                logger.info(
                    "订单撤单成功",
                    order_id=order.order_id
                )

            return success

        except Exception as e:
            logger.error(
                f"订单撤单失败: {e}",
                order_id=order.order_id
            )
            return False

    async def reject_order(self, order: Order, reason: str) -> bool:
        """
        拒绝订单

        Args:
            order: 订单
            reason: 拒绝原因

        Returns:
            bool: 处理是否成功
        """
        try:
            # 创建状态机
            state_machine = create_order_state_machine(order)
            register_event_handlers(state_machine, self.event_handler)

            # 状态转换
            success = state_machine.transition(
                OrderEvent.REJECT,
                details={'reason': reason}
            )

            if success:
                await self.session.flush()
                logger.warning(
                    "订单被拒绝",
                    order_id=order.order_id,
                    reason=reason
                )

            return success

        except Exception as e:
            logger.error(
                f"订单拒绝处理失败: {e}",
                order_id=order.order_id
            )
            return False

    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        根据订单号查询订单

        Args:
            order_id: 订单号

        Returns:
            Order: 订单，未找到返回None
        """
        result = await self.session.execute(
            select(Order).where(Order.order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_account_orders(
        self,
        account_id: int,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Order]:
        """
        查询账户订单列表

        Args:
            account_id: 账户ID
            status: 状态过滤
            limit: 数量限制
            offset: 偏移量

        Returns:
            List[Order]: 订单列表
        """
        query = select(Order).where(Order.account_id == account_id)

        if status:
            query = query.where(Order.status == status)

        query = query.order_by(desc(Order.created_at)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_active_orders(self, account_id: int) -> List[Order]:
        """
        获取账户活跃订单

        Args:
            account_id: 账户ID

        Returns:
            List[Order]: 活跃订单列表
        """
        result = await self.session.execute(
            select(Order).where(
                Order.account_id == account_id,
                Order.status.in_([
                    OrderStatus.CREATED,
                    OrderStatus.PENDING,
                    OrderStatus.PARTIAL
                ])
            ).order_by(desc(Order.created_at))
        )
        return result.scalars().all()

    async def batch_cancel_orders(self, account_id: int) -> int:
        """
        批量撤单（撤销账户所有活跃订单）

        Args:
            account_id: 账户ID

        Returns:
            int: 成功撤销的订单数量
        """
        active_orders = await self.get_active_orders(account_id)
        cancelled_count = 0

        for order in active_orders:
            if await self.cancel_order(order):
                cancelled_count += 1

        logger.info(
            "批量撤单完成",
            account_id=account_id,
            total=len(active_orders),
            cancelled=cancelled_count
        )

        return cancelled_count
