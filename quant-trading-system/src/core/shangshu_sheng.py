"""
尚书省 - 执行调度与资金清算

职责：
- 订单队列管理
- 资金冻结/解冻
- 订单路由到执行算法
- 成交结果处理
- 持仓更新
- T+1结算准备

数据流向：
门下省(审核通过) → 尚书省(执行调度) → 订单成交 → 更新持仓/资金 → 流水记录
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from queue import PriorityQueue
import uuid

from sqlalchemy import select

from src.strategy.base import Signal, SignalType
from src.models.order import Order
from src.models.trade import Trade
from src.models.position import Position
from src.models.balance_flow import BalanceFlow
from src.models.order_state_history import OrderStateHistory
from src.models.enums import OrderStatus, OrderDirection, FlowType
from src.common.database import db_manager
from src.common.logger import TradingLogger
from src.common.metrics import metrics
from src.core.order_state_machine import (
    OrderStateMachine, OrderEvent, create_order_state_machine
)

logger = TradingLogger(__name__)


class OrderPriority(Enum):
    """订单优先级"""
    EMERGENCY = 0    # 紧急（止损/强平）
    HIGH = 1         # 高优先级
    NORMAL = 2       # 普通
    LOW = 3          # 低优先级（大额拆单）


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"           # 待执行
    FREEZING = "freezing"         # 冻结资金中
    FROZEN = "frozen"             # 资金已冻结
    SUBMITTING = "submitting"     # 提交中
    SUBMITTED = "submitted"       # 已提交
    PARTIAL_FILLED = "partial_filled"  # 部分成交
    FILLED = "filled"             # 全部成交
    CANCELLED = "cancelled"       # 已取消
    REJECTED = "rejected"         # 被拒绝
    ERROR = "error"               # 错误


@dataclass
class OrderRequest:
    """订单请求"""
    signal: Signal
    account_id: int
    priority: OrderPriority = OrderPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])

    def __lt__(self, other):
        """优先级比较（用于优先队列）"""
        return self.priority.value < other.priority.value


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    order_id: Optional[str] = None
    trade_id: Optional[str] = None
    filled_qty: int = 0
    filled_price: Optional[Decimal] = None
    message: str = ""
    error_code: Optional[str] = None


class OrderQueue:
    """订单队列管理"""

    def __init__(self):
        self._queue: PriorityQueue = PriorityQueue()
        self._orders: Dict[str, OrderRequest] = {}
        self._stats = {"total_enqueued": 0, "total_dequeued": 0}

    def enqueue(self, request: OrderRequest) -> str:
        """添加订单到队列"""
        self._queue.put(request)
        self._orders[request.request_id] = request
        self._stats["total_enqueued"] += 1
        logger.info(f"订单入队: {request.request_id} [优先级:{request.priority.name}]")
        return request.request_id

    def dequeue(self) -> Optional[OrderRequest]:
        """从队列取出订单"""
        if self._queue.empty():
            return None

        request = self._queue.get()
        self._stats["total_dequeued"] += 1
        return request

    def get_request(self, request_id: str) -> Optional[OrderRequest]:
        """获取订单请求"""
        return self._orders.get(request_id)

    def is_empty(self) -> bool:
        """队列是否为空"""
        return self._queue.empty()

    def size(self) -> int:
        """队列大小"""
        return self._queue.qsize()

    def get_stats(self) -> Dict[str, int]:
        """获取统计"""
        return self._stats.copy()


class CapitalManager:
    """资金清算管理器"""

    def __init__(self):
        self._frozen_amount: Dict[int, Decimal] = {}  # account_id -> amount
        self._stats = {"total_frozen": 0, "total_unfrozen": 0, "total_fee": Decimal("0")}

    async def freeze_for_order(
        self,
        account_id: int,
        order_id: str,
        amount: Decimal
    ) -> bool:
        """
        为订单冻结资金

        Returns:
            True: 冻结成功
            False: 资金不足
        """
        # 这里应该从数据库查询账户余额并冻结
        # 简化版本：记录冻结金额
        current_frozen = self._frozen_amount.get(account_id, Decimal("0"))
        self._frozen_amount[account_id] = current_frozen + amount
        self._stats["total_frozen"] += 1

        logger.info(f"资金冻结: account={account_id}, order={order_id}, amount={amount}")
        return True

    async def unfreeze_for_order(
        self,
        account_id: int,
        order_id: str,
        amount: Decimal
    ):
        """解冻资金（撤单或失败时）"""
        current_frozen = self._frozen_amount.get(account_id, Decimal("0"))
        self._frozen_amount[account_id] = max(Decimal("0"), current_frozen - amount)
        self._stats["total_unfrozen"] += 1

        logger.info(f"资金解冻: account={account_id}, order={order_id}, amount={amount}")

    async def deduct_for_trade(
        self,
        account_id: int,
        trade: Trade
    ) -> Optional[BalanceFlow]:
        """
        扣除成交资金并创建流水

        Returns:
            BalanceFlow or None
        """
        # 计算实际扣除金额（含费用）
        trade_amount = trade.amount
        commission = trade.commission
        stamp_tax = trade.stamp_tax
        transfer_fee = trade.transfer_fee

        total_deduction = trade_amount + commission + stamp_tax + transfer_fee

        # 解冻并扣除
        await self.unfreeze_for_order(account_id, str(trade.order_id), total_deduction)

        # 创建流水记录
        flow = BalanceFlow(
            account_id=account_id,
            flow_type=FlowType.TRADE_BUY if trade.direction == OrderDirection.BUY else FlowType.TRADE_SELL,
            amount=-total_deduction if trade.direction == OrderDirection.BUY else total_deduction,
            balance_before=Decimal("0"),  # 实际应该从账户获取
            balance_after=Decimal("0"),
            trade_id=trade.id,
            description=f"{'买入' if trade.direction == OrderDirection.BUY else '卖出'}成交: {trade.symbol}"
        )

        self._stats["total_fee"] += commission + stamp_tax + transfer_fee

        logger.info(
            f"资金扣除: account={account_id}, trade={trade.id}, "
            f"amount={trade_amount}, fee={commission + stamp_tax + transfer_fee}"
        )

        return flow

    def get_frozen_amount(self, account_id: int) -> Decimal:
        """获取账户冻结金额"""
        return self._frozen_amount.get(account_id, Decimal("0"))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return self._stats.copy()


class PositionManager:
    """持仓管理器"""

    def __init__(self):
        self._positions: Dict[str, Position] = {}  # position_key -> Position
        self._stats = {"total_opened": 0, "total_closed": 0}

    def _get_position_key(self, account_id: int, symbol: str) -> str:
        """生成持仓键"""
        return f"{account_id}:{symbol}"

    async def update_position(self, trade: Trade) -> Position:
        """
        根据成交更新持仓

        Returns:
            更新后的持仓
        """
        key = self._get_position_key(trade.account_id, trade.symbol)
        position = self._positions.get(key)

        if trade.direction == OrderDirection.BUY:
            # 买入开仓或加仓
            if position is None:
                position = Position(
                    account_id=trade.account_id,
                    symbol=trade.symbol,
                    total_qty=trade.quantity,
                    available_qty=trade.quantity,
                    frozen_qty=0,
                    cost_price=trade.price,
                    cost_amount=trade.amount,
                    market_price=trade.price
                )
                self._positions[key] = position
                self._stats["total_opened"] += 1
            else:
                # 加仓，更新成本价
                old_cost = position.cost_amount
                new_cost = trade.amount
                total_qty = position.total_qty + trade.quantity

                position.total_qty = total_qty
                position.available_qty += trade.quantity
                position.cost_amount = old_cost + new_cost
                position.cost_price = position.cost_amount / total_qty

        else:  # SELL
            # 卖出平仓或减仓
            if position:
                position.total_qty -= trade.quantity
                position.available_qty -= trade.quantity
                position.cost_amount = position.total_qty * position.cost_price

                if position.total_qty <= 0:
                    # 全部平仓
                    del self._positions[key]
                    self._stats["total_closed"] += 1

        logger.info(
            f"持仓更新: {trade.symbol}, qty={trade.quantity}, "
            f"direction={trade.direction.value}, remaining={position.total_qty if position else 0}"
        )

        return position

    def get_position(self, account_id: int, symbol: str) -> Optional[Position]:
        """获取持仓"""
        key = self._get_position_key(account_id, symbol)
        return self._positions.get(key)

    def get_positions(self, account_id: int) -> List[Position]:
        """获取账户所有持仓"""
        prefix = f"{account_id}:"
        return [p for k, p in self._positions.items() if k.startswith(prefix)]

    def get_stats(self) -> Dict[str, int]:
        """获取统计"""
        return self._stats.copy()


class ExecutionEngine:
    """执行引擎"""

    def __init__(self):
        self._execution_algorithms: Dict[str, Callable] = {}

    def register_algorithm(self, name: str, algorithm: Callable):
        """注册执行算法"""
        self._execution_algorithms[name] = algorithm

    async def execute(
        self,
        order: Order,
        algorithm: str = "market"
    ) -> ExecutionResult:
        """
        执行订单

        Args:
            order: 订单
            algorithm: 执行算法名称

        Returns:
            执行结果
        """
        # 简化版本：模拟立即成交
        # 实际应该调用券商API或撮合引擎

        try:
            # 模拟成交价格（滑点）
            slippage = Decimal("0.001")  # 0.1%滑点
            if order.direction == OrderDirection.BUY:
                filled_price = order.price * (1 + slippage)
            else:
                filled_price = order.price * (1 - slippage)

            filled_qty = order.quantity

            # 计算费用
            amount = filled_price * filled_qty
            commission = max(amount * Decimal("0.0003"), Decimal("5"))  # 佣金
            stamp_tax = amount * Decimal("0.001") if order.direction == OrderDirection.SELL else Decimal("0")  # 印花税
            transfer_fee = amount * Decimal("0.00002")  # 过户费

            return ExecutionResult(
                success=True,
                order_id=str(order.id),
                trade_id=str(uuid.uuid4())[:16],
                filled_qty=filled_qty,
                filled_price=filled_price,
                message="成交成功"
            )

        except Exception as e:
            logger.error(f"订单执行失败: {e}")
            return ExecutionResult(
                success=False,
                error_code="EXEC_ERROR",
                message=str(e)
            )


class ShangshuSheng:
    """
    尚书省 - 执行调度中心（单例）

    职责：
    - 订单队列管理
    - 资金冻结/解冻
    - 订单执行
    - 持仓更新
    - 流水记录
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # 订单队列
        self.order_queue = OrderQueue()

        # 资金管理
        self.capital_manager = CapitalManager()

        # 持仓管理
        self.position_manager = PositionManager()

        # 执行引擎
        self.execution_engine = ExecutionEngine()

        # 回调
        self._on_trade_callbacks: List[Callable[[Trade], None]] = []
        self._on_position_callbacks: List[Callable[[Position], None]] = []
        self._on_order_state_callbacks: List[Callable[[Order, str, str], None]] = []

        # 状态机管理
        self._state_machines: Dict[str, OrderStateMachine] = {}

        # 运行状态
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

        # 统计
        self._stats = {
            "orders_submitted": 0,
            "orders_executed": 0,
            "orders_rejected": 0,
            "trades_completed": 0,
        }

        logger.info("尚书省初始化完成")

    async def start(self):
        """启动执行调度"""
        if self._running:
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("尚书省执行调度已启动")

    async def stop(self):
        """停止执行调度"""
        self._running = False

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

        logger.info("尚书省执行调度已停止")

    async def _worker_loop(self):
        """订单处理工作循环"""
        while self._running:
            try:
                # 从队列获取订单
                request = self.order_queue.dequeue()
                if request:
                    await self._process_order(request)
                else:
                    # 队列为空，等待一段时间
                    await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"订单处理异常: {e}")
                await asyncio.sleep(1)

    async def submit_signal(
        self,
        signal: Signal,
        account_id: int,
        priority: OrderPriority = OrderPriority.NORMAL
    ) -> str:
        """
        提交信号到执行队列

        Args:
            signal: 交易信号
            account_id: 账户ID
            priority: 优先级

        Returns:
            request_id
        """
        request = OrderRequest(
            signal=signal,
            account_id=account_id,
            priority=priority
        )

        request_id = self.order_queue.enqueue(request)
        self._stats["orders_submitted"] += 1

        # 记录订单提交指标
        metrics.increment("orders.submitted", tags={
            "symbol": signal.symbol,
            "direction": signal.type.value,
            "priority": priority.name
        })

        logger.info(f"信号提交: {request_id} {signal.symbol} {signal.type.value}")
        return request_id
        """
        提交信号到执行队列

        Args:
            signal: 交易信号
            account_id: 账户ID
            priority: 优先级

        Returns:
            request_id
        """
        request = OrderRequest(
            signal=signal,
            account_id=account_id,
            priority=priority
        )

        request_id = self.order_queue.enqueue(request)
        self._stats["orders_submitted"] += 1

        logger.info(f"信号提交: {request_id} {signal.symbol} {signal.type.value}")
        return request_id

    async def _process_order(self, request: OrderRequest):
        """处理订单请求"""
        signal = request.signal
        account_id = request.account_id

        try:
            # 1. 创建订单
            import uuid
            order = Order(
                order_id=f"ORD{uuid.uuid4().hex[:16].upper()}",
                account_id=account_id,
                symbol=signal.symbol,
                direction=OrderDirection.BUY if signal.type == SignalType.BUY else OrderDirection.SELL,
                order_type=OrderType.MARKET,
                qty=signal.volume or 100,
                price=signal.price or Decimal("0")
            )

            # 2. 初始化状态机
            sm = self._get_or_create_state_machine(order)

            # 3. 保存订单到数据库
            async with db_manager.get_session() as session:
                session.add(order)
                await session.commit()
                # 刷新以获取订单ID
                await session.refresh(order)

            # 4. 冻结资金
            freeze_amount = order.price * order.qty * Decimal("1.002")  # 预留费用
            frozen = await self.capital_manager.freeze_for_order(
                account_id, order.order_id, freeze_amount
            )

            if not frozen:
                # 资金冻结失败，拒绝订单
                sm.transition(OrderEvent.REJECT, {"reason": "资金冻结失败"})
                async with db_manager.get_session() as session:
                    await session.merge(order)
                    await session.commit()
                self._stats["orders_rejected"] += 1
                # 记录订单拒绝指标
                metrics.increment("orders.rejected", tags={
                    "symbol": signal.symbol,
                    "reason": "freeze_failed"
                })
                logger.warning(f"资金冻结失败: {account_id} {signal.symbol}")
                return

            # 5. 提交订单到交易所（状态转换）
            sm.transition(OrderEvent.SUBMIT, {"reason": "提交到交易所"})
            async with db_manager.get_session() as session:
                await session.merge(order)
                await session.commit()

            # 6. 执行订单
            result = await self.execution_engine.execute(order)

            if not result.success:
                # 执行失败，解冻资金并拒绝订单
                await self.capital_manager.unfreeze_for_order(
                    account_id, order.order_id, freeze_amount
                )
                sm.transition(OrderEvent.REJECT, {"reason": result.message})
                async with db_manager.get_session() as session:
                    await session.merge(order)
                    await session.commit()
                self._stats["orders_rejected"] += 1
                # 记录订单拒绝指标
                metrics.increment("orders.rejected", tags={
                    "symbol": signal.symbol,
                    "reason": "execution_failed"
                })
                logger.warning(f"订单执行失败: {result.message}")
                return

            # 7. 处理成交（支持部分成交）
            trade = await self.handle_partial_fill(
                order,
                result.filled_qty,
                result.filled_price,
                f"TRD{uuid.uuid4().hex[:16].upper()}"
            )

            if not trade:
                logger.error(f"成交处理失败: {order.order_id}")
                return

            # 8. 保存成交记录
            async with db_manager.get_session() as session:
                session.add(trade)
                await session.commit()

            # 9. 资金清算
            await self.capital_manager.deduct_for_trade(account_id, trade)

            # 10. 更新持仓
            position = await self.position_manager.update_position(trade)

            # 11. 保存最终订单状态
            async with db_manager.get_session() as session:
                await session.merge(order)
                await session.commit()

            # 12. 触发回调
            self._notify_trade(trade)
            if position:
                self._notify_position(position)

            self._stats["orders_executed"] += 1
            self._stats["trades_completed"] += 1

            # 记录订单执行指标
            metrics.increment("orders.executed", tags={
                "symbol": signal.symbol,
                "direction": signal.type.value
            })

            logger.info(
                f"订单执行完成: {signal.symbol}, qty={result.filled_qty}, "
                f"price={result.filled_price}, status={order.status.value}"
            )

        except Exception as e:
            logger.error(f"订单处理失败: {e}")
            self._stats["orders_rejected"] += 1
            # 记录订单拒绝指标
            metrics.increment("orders.rejected", tags={
                "symbol": signal.symbol,
                "reason": "exception"
            })

    def _notify_trade(self, trade: Trade):
        """通知成交"""
        for callback in self._on_trade_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(trade))
                else:
                    callback(trade)
            except Exception as e:
                logger.error(f"成交回调失败: {e}")

    def _notify_position(self, position: Position):
        """通知持仓更新"""
        for callback in self._on_position_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(position))
                else:
                    callback(position)
            except Exception as e:
                logger.error(f"持仓回调失败: {e}")

    def on_trade(self, callback: Callable[[Trade], None]):
        """注册成交回调"""
        self._on_trade_callbacks.append(callback)

    def on_position(self, callback: Callable[[Position], None]):
        """注册持仓更新回调"""
        self._on_position_callbacks.append(callback)

    def on_order_state_change(self, callback: Callable[[Order, str, str], None]):
        """
        注册订单状态变更回调

        Args:
            callback: 回调函数，参数为(order, from_status, to_status)
        """
        self._on_order_state_callbacks.append(callback)

    def _get_or_create_state_machine(self, order: Order) -> OrderStateMachine:
        """
        获取或创建订单状态机

        Args:
            order: 订单实例

        Returns:
            订单状态机
        """
        if order.order_id not in self._state_machines:
            sm = create_order_state_machine(order)
            # 注册状态变更回调
            sm.register_callback(OrderEvent.SUBMIT, self._on_state_transition)
            sm.register_callback(OrderEvent.FILL_PARTIAL, self._on_state_transition)
            sm.register_callback(OrderEvent.FILL_FULL, self._on_state_transition)
            sm.register_callback(OrderEvent.CANCEL, self._on_state_transition)
            sm.register_callback(OrderEvent.REJECT, self._on_state_transition)
            sm.register_callback(OrderEvent.EXPIRE, self._on_state_transition)
            self._state_machines[order.order_id] = sm
        return self._state_machines[order.order_id]

    def _on_state_transition(self, order: Order, transition):
        """
        状态转换回调处理

        Args:
            order: 订单实例
            transition: 状态转换记录
        """
        from_status = transition.from_status.value
        to_status = transition.to_status.value

        # 异步记录状态历史
        asyncio.create_task(
            self._record_state_history(
                order, from_status, to_status, transition.event.name, transition.details
            )
        )

        # 触发外部回调
        for callback in self._on_order_state_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(order, from_status, to_status))
                else:
                    callback(order, from_status, to_status)
            except Exception as e:
                logger.error(f"订单状态回调失败: {e}")

    async def _record_state_history(
        self,
        order: Order,
        from_status: str,
        to_status: str,
        event: str,
        details: Optional[Dict] = None
    ):
        """
        记录订单状态历史到数据库

        Args:
            order: 订单实例
            from_status: 原状态
            to_status: 新状态
            event: 事件类型
            details: 详情
        """
        try:
            reason = details.get("reason", f"事件: {event}") if details else f"事件: {event}"
            history = OrderStateHistory(
                order_id=order.id,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                metadata=details
            )

            async with db_manager.get_session() as session:
                session.add(history)
                await session.commit()

            logger.debug(
                f"状态历史已记录: {order.order_id} {from_status} -> {to_status}"
            )
        except Exception as e:
            logger.error(f"记录状态历史失败: {e}")

    async def cancel_order(self, order_id: str, reason: str = "用户撤单") -> bool:
        """
        撤单操作

        Args:
            order_id: 订单ID
            reason: 撤单原因

        Returns:
            True如果撤单成功，否则False
        """
        try:
            async with db_manager.get_session() as session:
                # 查询订单
                result = await session.execute(
                    select(Order).where(Order.order_id == order_id)
                )
                order = result.scalar_one_or_none()

                if not order:
                    logger.warning(f"撤单失败: 订单不存在 {order_id}")
                    return False

                # 获取状态机
                sm = self._get_or_create_state_machine(order)

                # 检查是否可以撤单
                if not sm.can_cancel():
                    logger.warning(
                        f"撤单失败: 订单状态不允许撤单 {order_id}, status={order.status.value}"
                    )
                    return False

                # 执行撤单
                # 1. 解冻资金
                freeze_amount = order.price * order.qty * Decimal("1.002")
                await self.capital_manager.unfreeze_for_order(
                    order.account_id, order_id, freeze_amount
                )

                # 2. 状态转换
                sm.transition(OrderEvent.CANCEL, {"reason": reason})

                # 3. 更新数据库
                order.status = OrderStatus.CANCELLED
                order.cancelled_at = datetime.now()
                await session.commit()

                logger.info(f"撤单成功: {order_id}, reason={reason}")
                # 记录撤单指标
                metrics.increment("orders.cancelled", tags={"reason": reason})
                return True

        except Exception as e:
            logger.error(f"撤单异常: {order_id}, error={e}")
            # 记录撤单失败指标
            metrics.increment("orders.cancelled", tags={"reason": "error"})
            return False

    async def handle_partial_fill(
        self,
        order: Order,
        filled_qty: int,
        filled_price: Decimal,
        trade_id: str
    ) -> Optional[Trade]:
        """
        处理部分成交

        Args:
            order: 订单实例
            filled_qty: 本次成交数量
            filled_price: 成交价格
            trade_id: 成交ID

        Returns:
            成交记录，如果处理失败返回None
        """
        try:
            # 获取状态机
            sm = self._get_or_create_state_machine(order)

            # 检查是否可以成交
            if not sm.can_fill():
                logger.warning(
                    f"无法成交: 订单状态不允许 {order.order_id}, status={order.status.value}"
                )
                return None

            # 更新订单成交信息
            order.fill(filled_qty, filled_price)

            # 状态转换
            if order.is_filled:
                sm.transition(
                    OrderEvent.FILL_FULL,
                    {"fill_qty": filled_qty, "fill_price": str(filled_price)}
                )
            else:
                sm.transition(
                    OrderEvent.FILL_PARTIAL,
                    {"fill_qty": filled_qty, "fill_price": str(filled_price)}
                )

            # 创建成交记录
            trade = Trade(
                trade_id=trade_id,
                order_id=order.id,
                account_id=order.account_id,
                symbol=order.symbol,
                direction=order.direction,
                qty=filled_qty,
                price=filled_price,
                trade_time=datetime.now(),
                strategy_id=order.strategy_id,
                symbol_name=order.symbol_name
            )

            # 计算费用
            trade.calculate_fees(
                commission_rate=Decimal("0.0003"),
                min_commission=Decimal("5"),
                stamp_tax_rate=Decimal("0.001"),
                transfer_fee_rate=Decimal("0.00002")
            )

            logger.info(
                f"部分成交处理完成: {order.order_id}, "
                f"filled={filled_qty}, price={filled_price}, "
                f"total_filled={order.filled_qty}/{order.qty}"
            )

            return trade

        except Exception as e:
            logger.error(f"部分成交处理失败: {order.order_id}, error={e}")
            return None

    async def check_order_timeout(self, order: Order, timeout_seconds: float = 300) -> bool:
        """
        检查订单是否超时

        Args:
            order: 订单实例
            timeout_seconds: 超时时间（秒），默认5分钟

        Returns:
            True如果订单已超时并处理，否则False
        """
        if not order.created_at:
            return False

        elapsed = (datetime.now() - order.created_at).total_seconds()
        if elapsed < timeout_seconds:
            return False

        # 订单已超时
        sm = self._get_or_create_state_machine(order)

        if sm.can_cancel():
            logger.warning(f"订单超时，自动撤单: {order.order_id}, elapsed={elapsed}s")
            await self.cancel_order(order.order_id, f"订单超时({elapsed:.0f}s)")
            return True

        return False

    def get_order_state_machine(self, order_id: str) -> Optional[OrderStateMachine]:
        """
        获取订单状态机

        Args:
            order_id: 订单ID

        Returns:
            订单状态机，如果不存在返回None
        """
        return self._state_machines.get(order_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "queue": self.order_queue.get_stats(),
            "capital": self.capital_manager.get_stats(),
            "position": self.position_manager.get_stats(),
        }

    # 兼容旧版API
    async def execute_orders(
        self,
        signals: List[Dict[str, Any]],
        market_data: Dict[str, Any]
    ):
        """执行订单列表（兼容旧版API）"""
        results = []

        for sig_dict in signals:
            signal = Signal(
                type=SignalType(sig_dict.get("direction", "buy").lower()),
                symbol=sig_dict.get("code", ""),
                timestamp=datetime.now(),
                price=Decimal(str(sig_dict.get("price", 0))),
                volume=sig_dict.get("qty", 0)
            )

            request_id = await self.submit_signal(signal, sig_dict.get("account_id", 0))
            results.append({"request_id": request_id, "status": "submitted"})

        return results

    def get_portfolio_state(self) -> Dict[str, Any]:
        """获取账户状态（兼容旧版）"""
        return {
            "cash": 0,  # 应该从账户获取
            "total_value": 0,
            "positions": {},
        }


# 全局尚书省实例
shangshu_sheng = ShangshuSheng()
