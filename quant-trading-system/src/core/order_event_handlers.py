"""
订单事件处理器

处理订单状态变更时的业务逻辑：
- 资金冻结/解冻
- 持仓冻结/解冻
- 资金流水记录
- 风控检查
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.order_state_machine import (
    OrderStateMachine, OrderEvent, StateTransition
)
from src.models.order import Order
from src.models.account import Account
from src.models.position import Position
from src.models.balance_flow import BalanceFlow, FlowType
from src.models.enums import OrderDirection, OrderStatus
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class OrderEventHandler:
    """
    订单事件处理器

    处理订单状态变更时的资金和持仓操作。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化处理器

        Args:
            session: 数据库会话
        """
        self.session = session

    async def on_submit(self, order: Order, transition: StateTransition) -> bool:
        """
        订单提交事件处理

        职责：
        1. 冻结资金（买入）或持仓（卖出）
        2. 记录资金流水

        Returns:
            bool: 处理是否成功
        """
        try:
            if order.direction == OrderDirection.BUY:
                # 买入：冻结资金
                await self._freeze_cash_for_buy(order)
            else:
                # 卖出：冻结持仓
                await self._freeze_position_for_sell(order)

            logger.info(
                "订单提交处理完成",
                order_id=order.order_id,
                direction=order.direction.value
            )
            return True

        except Exception as e:
            logger.error(
                f"订单提交处理失败: {e}",
                order_id=order.order_id
            )
            return False

    async def on_fill(
        self,
        order: Order,
        transition: StateTransition,
        fill_qty: int,
        fill_price: Decimal
    ) -> bool:
        """
        订单成交事件处理

        职责：
        1. 解冻部分/全部资金
        2. 扣减/增加资金
        3. 更新持仓
        4. 记录成交流水

        Args:
            order: 订单
            transition: 状态转换
            fill_qty: 成交数量
            fill_price: 成交价格

        Returns:
            bool: 处理是否成功
        """
        try:
            # 计算成交金额
            fill_amount = fill_price * fill_qty

            if order.direction == OrderDirection.BUY:
                # 买入成交
                await self._process_buy_fill(order, fill_qty, fill_price, fill_amount)
            else:
                # 卖出成交
                await self._process_sell_fill(order, fill_qty, fill_price, fill_amount)

            logger.info(
                "订单成交处理完成",
                order_id=order.order_id,
                fill_qty=fill_qty,
                fill_price=float(fill_price)
            )
            return True

        except Exception as e:
            logger.error(
                f"订单成交处理失败: {e}",
                order_id=order.order_id
            )
            return False

    async def on_cancel(self, order: Order, transition: StateTransition) -> bool:
        """
        订单撤单事件处理

        职责：
        1. 解冻全部剩余资金
        2. 解冻全部剩余持仓
        3. 记录资金流水
        """
        try:
            remaining_qty = order.qty - order.filled_qty

            if order.direction == OrderDirection.BUY:
                # 买入撤单：解冻剩余资金
                await self._unfreeze_cash_for_cancel(order, remaining_qty)
            else:
                # 卖出撤单：解冻剩余持仓
                await self._unfreeze_position_for_cancel(order, remaining_qty)

            logger.info(
                "订单撤单处理完成",
                order_id=order.order_id,
                remaining_qty=remaining_qty
            )
            return True

        except Exception as e:
            logger.error(
                f"订单撤单处理失败: {e}",
                order_id=order.order_id
            )
            return False

    async def on_reject(self, order: Order, transition: StateTransition) -> bool:
        """
        订单拒绝事件处理

        职责：
        1. 解冻资金/持仓
        2. 记录拒绝原因
        """
        try:
            if order.direction == OrderDirection.BUY:
                # 解冻资金
                await self._unfreeze_cash_for_cancel(order, order.qty)
            else:
                # 解冻持仓
                await self._unfreeze_position_for_cancel(order, order.qty)

            logger.warning(
                "订单被拒绝",
                order_id=order.order_id,
                reason=order.error_msg
            )
            return True

        except Exception as e:
            logger.error(
                f"订单拒绝处理失败: {e}",
                order_id=order.order_id
            )
            return False

    async def _freeze_cash_for_buy(self, order: Order) -> None:
        """为买入订单冻结资金"""
        from sqlalchemy import select

        # 获取账户
        result = await self.session.execute(
            select(Account).where(Account.id == order.account_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            raise ValueError(f"账户不存在: {order.account_id}")

        # 计算需要冻结的资金（预留手续费 0.2%）
        required_amount = order.price * order.qty * Decimal("1.002")

        # 检查可用资金
        if account.available < required_amount:
            raise ValueError(
                f"资金不足: 可用{account.available}, 需要{required_amount}"
            )

        # 冻结资金
        if not account.freeze(required_amount):
            raise ValueError("冻结资金失败")

        # 记录资金流水
        balance_before = account.available + required_amount
        flow = BalanceFlow.create_order_frozen(
            account_id=account.id,
            order_id=order.id,
            amount=required_amount,
            balance_before=balance_before
        )
        self.session.add(flow)

        logger.info(
            "冻结买入资金",
            order_id=order.order_id,
            amount=float(required_amount)
        )

    async def _freeze_position_for_sell(self, order: Order) -> None:
        """为卖出订单冻结持仓"""
        from sqlalchemy import select

        # 获取持仓
        result = await self.session.execute(
            select(Position).where(
                Position.account_id == order.account_id,
                Position.symbol == order.symbol
            )
        )
        position = result.scalar_one_or_none()

        if not position:
            raise ValueError(f"持仓不存在: {order.symbol}")

        # 检查可用持仓
        if position.available_qty < order.qty:
            raise ValueError(
                f"持仓不足: 可用{position.available_qty}, 需要{order.qty}"
            )

        # 冻结持仓
        if not position.freeze(order.qty):
            raise ValueError("冻结持仓失败")

        logger.info(
            "冻结卖出持仓",
            order_id=order.order_id,
            symbol=order.symbol,
            qty=order.qty
        )

    async def _process_buy_fill(
        self,
        order: Order,
        fill_qty: int,
        fill_price: Decimal,
        fill_amount: Decimal
    ) -> None:
        """处理买入成交"""
        from sqlalchemy import select

        # 获取账户
        result = await self.session.execute(
            select(Account).where(Account.id == order.account_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            raise ValueError(f"账户不存在: {order.account_id}")

        # 计算需要解冻的资金（预留部分）
        reserved_amount = order.price * fill_qty * Decimal("1.002")

        # 解冻资金
        if not account.unfreeze(reserved_amount):
            raise ValueError("解冻资金失败")

        # 计算实际成交金额（含费用）
        fees = self._calculate_fees(fill_amount, OrderDirection.BUY)
        total_cost = fill_amount + fees['total_fee']

        # 扣减资金
        if not account.deduct(total_cost):
            raise ValueError("扣减资金失败")

        # 记录资金流水
        balance_before = account.available + reserved_amount

        # 成交流水
        flow = BalanceFlow.create_trade_buy(
            account_id=account.id,
            order_id=order.id,
            trade_id=None,  # 后续关联
            amount=total_cost,
            balance_before=balance_before
        )
        self.session.add(flow)

        # 费用流水
        for fee_type, fee_amount in fees.items():
            if fee_amount > 0:
                fee_flow = BalanceFlow.create_fee(
                    account_id=account.id,
                    trade_id=None,
                    flow_type=getattr(FlowType, fee_type.upper()),
                    amount=fee_amount,
                    balance_before=account.available
                )
                self.session.add(fee_flow)

        # 更新或创建持仓
        await self._update_position_for_buy(order, fill_qty, fill_price)

    async def _process_sell_fill(
        self,
        order: Order,
        fill_qty: int,
        fill_price: Decimal,
        fill_amount: Decimal
    ) -> None:
        """处理卖出成交"""
        from sqlalchemy import select

        # 获取账户和持仓
        result = await self.session.execute(
            select(Account).where(Account.id == order.account_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            raise ValueError(f"账户不存在: {order.account_id}")

        result = await self.session.execute(
            select(Position).where(
                Position.account_id == order.account_id,
                Position.symbol == order.symbol
            )
        )
        position = result.scalar_one_or_none()

        if not position:
            raise ValueError(f"持仓不存在: {order.symbol}")

        # 解冻持仓并减少
        if not position.unfreeze(fill_qty):
            raise ValueError("解冻持仓失败")

        # 减少持仓（计算盈亏）
        realized_pnl = position.reduce(fill_qty, fill_price)

        # 计算费用
        fees = self._calculate_fees(fill_amount, OrderDirection.SELL)
        net_amount = fill_amount - fees['total_fee']

        # 增加资金
        account.add(net_amount)

        # 记录资金流水
        flow = BalanceFlow.create_trade_sell(
            account_id=account.id,
            order_id=order.id,
            trade_id=None,
            amount=net_amount,
            balance_before=account.available - net_amount
        )
        self.session.add(flow)

        # 费用流水
        for fee_type, fee_amount in fees.items():
            if fee_amount > 0:
                fee_flow = BalanceFlow.create_fee(
                    account_id=account.id,
                    trade_id=None,
                    flow_type=getattr(FlowType, fee_type.upper()),
                    amount=fee_amount,
                    balance_before=account.available
                )
                self.session.add(fee_flow)

        logger.info(
            "卖出成交处理完成",
            order_id=order.order_id,
            fill_qty=fill_qty,
            realized_pnl=float(realized_pnl)
        )

    async def _update_position_for_buy(
        self,
        order: Order,
        fill_qty: int,
        fill_price: Decimal
    ) -> None:
        """更新买入持仓"""
        from sqlalchemy import select

        result = await self.session.execute(
            select(Position).where(
                Position.account_id == order.account_id,
                Position.symbol == order.symbol
            )
        )
        position = result.scalar_one_or_none()

        if position:
            # 加仓
            position.add(fill_qty, fill_price)
        else:
            # 新建仓
            position = Position(
                account_id=order.account_id,
                symbol=order.symbol,
                symbol_name=order.symbol_name
            )
            position.add(fill_qty, fill_price)
            self.session.add(position)

    async def _unfreeze_cash_for_cancel(
        self,
        order: Order,
        remaining_qty: int
    ) -> None:
        """撤单时解冻资金"""
        from sqlalchemy import select

        if remaining_qty <= 0:
            return

        result = await self.session.execute(
            select(Account).where(Account.id == order.account_id)
        )
        account = result.scalar_one_or_none()

        if not account:
            return

        # 计算需要解冻的资金
        unfreeze_amount = order.price * remaining_qty * Decimal("1.002")

        # 解冻
        if account.unfreeze(unfreeze_amount):
            # 记录流水
            balance_before = account.available - unfreeze_amount
            flow = BalanceFlow.create_order_unfrozen(
                account_id=account.id,
                order_id=order.id,
                amount=unfreeze_amount,
                balance_before=balance_before
            )
            self.session.add(flow)

            logger.info(
                "解冻买入资金",
                order_id=order.order_id,
                amount=float(unfreeze_amount)
            )

    async def _unfreeze_position_for_cancel(
        self,
        order: Order,
        remaining_qty: int
    ) -> None:
        """撤单时解冻持仓"""
        from sqlalchemy import select

        if remaining_qty <= 0:
            return

        result = await self.session.execute(
            select(Position).where(
                Position.account_id == order.account_id,
                Position.symbol == order.symbol
            )
        )
        position = result.scalar_one_or_none()

        if position and position.unfreeze(remaining_qty):
            logger.info(
                "解冻卖出持仓",
                order_id=order.order_id,
                symbol=order.symbol,
                qty=remaining_qty
            )

    def _calculate_fees(
        self,
        amount: Decimal,
        direction: OrderDirection
    ) -> dict:
        """
        计算交易费用

        Returns:
            dict: 包含 commission, stamp_tax, transfer_fee, total_fee
        """
        # 佣金（最低 5 元）
        commission = max(amount * Decimal("0.0003"), Decimal("5"))

        # 印花税（仅卖出）
        stamp_tax = amount * Decimal("0.001") if direction == OrderDirection.SELL else Decimal("0")

        # 过户费
        transfer_fee = amount * Decimal("0.00002")

        total_fee = commission + stamp_tax + transfer_fee

        return {
            'commission': commission,
            'stamp_tax': stamp_tax,
            'transfer_fee': transfer_fee,
            'total_fee': total_fee
        }


def register_event_handlers(
    state_machine: OrderStateMachine,
    handler: OrderEventHandler
) -> None:
    """
    注册事件处理器到状态机

    Args:
        state_machine: 订单状态机
        handler: 事件处理器
    """
    # 提交事件
    state_machine.register_callback(
        OrderEvent.SUBMIT,
        lambda order, transition: handler.on_submit(order, transition)
    )

    # 成交事件
    state_machine.register_callback(
        OrderEvent.FILL_PARTIAL,
        lambda order, transition: handler.on_fill(
            order, transition,
            transition.details.get('fill_qty', 0) if transition.details else 0,
            Decimal(str(transition.details.get('fill_price', 0))) if transition.details else Decimal('0')
        )
    )

    state_machine.register_callback(
        OrderEvent.FILL_FULL,
        lambda order, transition: handler.on_fill(
            order, transition,
            transition.details.get('fill_qty', 0) if transition.details else 0,
            Decimal(str(transition.details.get('fill_price', 0))) if transition.details else Decimal('0')
        )
    )

    # 撤单事件
    state_machine.register_callback(
        OrderEvent.CANCEL,
        lambda order, transition: handler.on_cancel(order, transition)
    )

    # 拒绝事件
    state_machine.register_callback(
        OrderEvent.REJECT,
        lambda order, transition: handler.on_reject(order, transition)
    )
