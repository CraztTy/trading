"""
止损止盈管理器

提供实时止损止盈功能：
- 固定价格止损/止盈
- 比例止损/止盈
- 跟踪止损（Trailing Stop）
- 分批止盈
- 实时监控和触发
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Callable
from enum import Enum
import asyncio

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class StopLossType(Enum):
    """止损类型"""
    FIXED = "fixed"           # 固定价格止损
    PERCENTAGE = "percentage" # 比例止损
    TRAILING = "trailing"     # 跟踪止损


class TakeProfitType(Enum):
    """止盈类型"""
    FIXED = "fixed"           # 固定价格止盈
    PERCENTAGE = "percentage" # 比例止盈
    PARTIAL = "partial"       # 分批止盈


@dataclass
class StopLossOrder:
    """止损订单"""
    symbol: str
    position_qty: int
    entry_price: Decimal
    stop_loss_type: StopLossType
    stop_price: Optional[Decimal] = None          # 固定止损价
    stop_pct: Optional[Decimal] = None            # 止损比例
    trailing_distance: Optional[Decimal] = None   # 跟踪距离
    highest_price: Optional[Decimal] = None       # 跟踪止损中的最高价
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    order_id: str = field(default_factory=lambda: f"SL{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}")

    def __post_init__(self):
        if self.stop_loss_type == StopLossType.PERCENTAGE and self.stop_pct:
            # 计算固定止损价
            self.stop_price = self.entry_price * (Decimal("1") - self.stop_pct)
        elif self.stop_loss_type == StopLossType.TRAILING:
            # 跟踪止损初始止损价为 entry - distance
            if self.trailing_distance:
                self.stop_price = self.entry_price - self.trailing_distance
            self.highest_price = self.entry_price


@dataclass
class TakeProfitOrder:
    """止盈订单"""
    symbol: str
    position_qty: int
    entry_price: Decimal
    take_profit_type: TakeProfitType
    target_price: Optional[Decimal] = None        # 固定目标价
    target_pct: Optional[Decimal] = None          # 目标比例
    partial_levels: Optional[List[Dict]] = None   # 分批止盈级别
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    order_id: str = field(default_factory=lambda: f"TP{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}")

    def __post_init__(self):
        if self.take_profit_type == TakeProfitType.PERCENTAGE and self.target_pct:
            # 计算固定目标价
            self.target_price = self.entry_price * (Decimal("1") + self.target_pct)


@dataclass
class StopLossResult:
    """止损触发结果"""
    symbol: str
    should_stop: bool
    stop_price: Optional[Decimal]
    exit_price: Optional[Decimal]
    pnl: Decimal
    reason: str
    order_id: str


@dataclass
class TakeProfitResult:
    """止盈触发结果"""
    symbol: str
    should_take: bool
    target_price: Optional[Decimal]
    exit_price: Optional[Decimal]
    level: Optional[int]          # 分批止盈的级别
    partial_qty: Optional[int]    # 分批止盈的数量
    reason: str
    order_id: str


class StopLossManager:
    """
    止损止盈管理器

    职责：
    - 管理止损订单
    - 管理止盈订单
    - 实时价格监控
    - 触发止损/止盈回调
    """

    def __init__(self, check_interval: float = 1.0):
        self.check_interval = check_interval

        # 止损订单: symbol -> StopLossOrder
        self._stop_losses: Dict[str, StopLossOrder] = {}

        # 止盈订单: symbol -> TakeProfitOrder
        self._take_profits: Dict[str, TakeProfitOrder] = {}

        # 当前价格: symbol -> price
        self._current_prices: Dict[str, Decimal] = {}

        # 回调函数
        self._stop_loss_callbacks: List[Callable[[StopLossResult], None]] = []
        self._take_profit_callbacks: List[Callable[[TakeProfitResult], None]] = []

        # 监控任务
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

        # 并发锁
        self._lock = asyncio.Lock()

    # ============ 订单管理 ============

    def add_stop_loss(
        self,
        symbol: str,
        position_qty: int,
        entry_price: Decimal,
        stop_type: StopLossType,
        stop_price: Optional[Decimal] = None,
        stop_pct: Optional[Decimal] = None,
        trailing_distance: Optional[Decimal] = None
    ) -> str:
        """
        添加止损订单

        Args:
            symbol: 标的代码
            position_qty: 持仓数量
            entry_price: 入场价格
            stop_type: 止损类型
            stop_price: 固定止损价（FIXED类型）
            stop_pct: 止损比例（PERCENTAGE类型）
            trailing_distance: 跟踪距离（TRAILING类型）

        Returns:
            order_id: 订单ID

        Raises:
            ValueError: 参数验证失败
        """
        # 输入验证
        if not symbol or not isinstance(symbol, str):
            raise ValueError(f"symbol must be non-empty string, got {symbol}")
        if position_qty <= 0:
            raise ValueError(f"position_qty must be positive, got {position_qty}")
        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {entry_price}")
        if stop_type == StopLossType.PERCENTAGE:
            if stop_pct is None or stop_pct <= 0 or stop_pct >= 1:
                raise ValueError(f"stop_pct must be between 0 and 1, got {stop_pct}")
        if stop_type == StopLossType.TRAILING:
            if trailing_distance is None or trailing_distance <= 0:
                raise ValueError(f"trailing_distance must be positive, got {trailing_distance}")

        order = StopLossOrder(
            symbol=symbol,
            position_qty=position_qty,
            entry_price=entry_price,
            stop_loss_type=stop_type,
            stop_price=stop_price,
            stop_pct=stop_pct,
            trailing_distance=trailing_distance
        )

        self._stop_losses[symbol] = order
        logger.info(f"添加止损: {symbol} @ {order.stop_price}, 类型: {stop_type.value}")

        return order.order_id

    def add_take_profit(
        self,
        symbol: str,
        position_qty: int,
        entry_price: Decimal,
        tp_type: TakeProfitType,
        target_price: Optional[Decimal] = None,
        target_pct: Optional[Decimal] = None,
        partial_levels: Optional[List[Dict]] = None
    ) -> str:
        """
        添加止盈订单

        Args:
            symbol: 标的代码
            position_qty: 持仓数量
            entry_price: 入场价格
            tp_type: 止盈类型
            target_price: 固定目标价（FIXED类型）
            target_pct: 目标比例（PERCENTAGE类型）
            partial_levels: 分批止盈级别（PARTIAL类型）

        Returns:
            order_id: 订单ID
        """
        order = TakeProfitOrder(
            symbol=symbol,
            position_qty=position_qty,
            entry_price=entry_price,
            take_profit_type=tp_type,
            target_price=target_price,
            target_pct=target_pct,
            partial_levels=partial_levels
        )

        self._take_profits[symbol] = order
        logger.info(f"添加止盈: {symbol} @ {order.target_price}, 类型: {tp_type.value}")

        return order.order_id

    def remove_stop_loss(self, symbol: str) -> bool:
        """移除止损订单"""
        if symbol in self._stop_losses:
            del self._stop_losses[symbol]
            logger.info(f"移除止损: {symbol}")
            return True
        return False

    def remove_take_profit(self, symbol: str) -> bool:
        """移除止盈订单"""
        if symbol in self._take_profits:
            del self._take_profits[symbol]
            logger.info(f"移除止盈: {symbol}")
            return True
        return False

    def get_stop_loss(self, symbol: str) -> Optional[StopLossOrder]:
        """获取止损订单"""
        return self._stop_losses.get(symbol)

    def get_take_profit(self, symbol: str) -> Optional[TakeProfitOrder]:
        """获取止盈订单"""
        return self._take_profits.get(symbol)

    def get_active_orders(self) -> Dict[str, Dict[str, Any]]:
        """获取所有活跃订单"""
        return {
            "stop_losses": self._stop_losses.copy(),
            "take_profits": self._take_profits.copy()
        }

    # ============ 价格更新 ============

    def update_price(self, symbol: str, price: Decimal) -> None:
        """更新价格（触发检查）"""
        self._current_prices[symbol] = price

        # 更新跟踪止损的最高价
        if symbol in self._stop_losses:
            order = self._stop_losses[symbol]
            if order.stop_loss_type == StopLossType.TRAILING:
                if order.highest_price is None or price > order.highest_price:
                    order.highest_price = price
                    # 更新止损价
                    if order.trailing_distance:
                        order.stop_price = price - order.trailing_distance

    # ============ 检查逻辑 ============

    def _check_stop_loss(self, order: StopLossOrder, price: Decimal) -> StopLossResult:
        """检查止损是否触发"""
        should_stop = False
        reason = ""
        current_stop_price = order.stop_price

        if not order.is_active:
            return StopLossResult(
                symbol=order.symbol,
                should_stop=False,
                stop_price=order.stop_price,
                exit_price=None,
                pnl=Decimal("0"),
                reason="Order inactive",
                order_id=order.order_id
            )

        # 对于跟踪止损，根据最高价动态计算止损价
        if order.stop_loss_type == StopLossType.TRAILING:
            if order.highest_price and order.trailing_distance:
                current_stop_price = order.highest_price - order.trailing_distance
            if current_stop_price is None:
                return StopLossResult(
                    symbol=order.symbol,
                    should_stop=False,
                    stop_price=order.stop_price,
                    exit_price=None,
                    pnl=Decimal("0"),
                    reason="Trailing stop not initialized",
                    order_id=order.order_id
                )
        elif order.stop_price is None:
            return StopLossResult(
                symbol=order.symbol,
                should_stop=False,
                stop_price=order.stop_price,
                exit_price=None,
                pnl=Decimal("0"),
                reason="Order inactive",
                order_id=order.order_id
            )

        # 检查是否触发止损
        if price <= current_stop_price:
            should_stop = True

            if order.stop_loss_type == StopLossType.FIXED:
                reason = f"固定止损触发: 当前价 {price} <= 止损价 {current_stop_price}"
            elif order.stop_loss_type == StopLossType.PERCENTAGE:
                loss_pct = (order.entry_price - price) / order.entry_price * 100
                reason = f"比例止损触发: 跌幅 {loss_pct:.2f}%"
            elif order.stop_loss_type == StopLossType.TRAILING:
                if order.highest_price:
                    pullback = order.highest_price - price
                    reason = f"跟踪止损触发: 从最高价 {order.highest_price} 回落 {pullback}"
                else:
                    reason = "跟踪止损触发"

        # 计算盈亏
        pnl = Decimal("0")
        if should_stop:
            pnl = (price - order.entry_price) * order.position_qty

        return StopLossResult(
            symbol=order.symbol,
            should_stop=should_stop,
            stop_price=current_stop_price,
            exit_price=price if should_stop else None,
            pnl=pnl,
            reason=reason,
            order_id=order.order_id
        )

    def _check_take_profit(self, order: TakeProfitOrder, price: Decimal) -> TakeProfitResult:
        """检查止盈是否触发"""
        if not order.is_active or order.target_price is None:
            return TakeProfitResult(
                symbol=order.symbol,
                should_take=False,
                target_price=order.target_price,
                exit_price=None,
                level=None,
                partial_qty=None,
                reason="Order inactive",
                order_id=order.order_id
            )

        should_take = False
        reason = ""
        level = None
        partial_qty = None

        # 检查是否触发止盈
        if price >= order.target_price:
            should_take = True

            if order.take_profit_type == TakeProfitType.FIXED:
                reason = f"固定止盈触发: 当前价 {price} >= 目标价 {order.target_price}"
            elif order.take_profit_type == TakeProfitType.PERCENTAGE:
                gain_pct = (price - order.entry_price) / order.entry_price * 100
                reason = f"比例止盈触发: 涨幅 {gain_pct:.2f}%"
            elif order.take_profit_type == TakeProfitType.PARTIAL:
                reason = "分批止盈触发"
                # TODO: 实现分批止盈逻辑

        return TakeProfitResult(
            symbol=order.symbol,
            should_take=should_take,
            target_price=order.target_price,
            exit_price=price if should_take else None,
            level=level,
            partial_qty=partial_qty,
            reason=reason,
            order_id=order.order_id
        )

    async def _monitor_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                await self._check_all_orders()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                await asyncio.sleep(self.check_interval)

    async def _check_all_orders(self) -> None:
        """检查所有订单"""
        # 检查止损
        for symbol, order in list(self._stop_losses.items()):
            if symbol in self._current_prices:
                price = self._current_prices[symbol]
                result = self._check_stop_loss(order, price)

                if result.should_stop:
                    order.is_active = False
                    await self._trigger_stop_loss(result)

        # 检查止盈
        for symbol, order in list(self._take_profits.items()):
            if symbol in self._current_prices:
                price = self._current_prices[symbol]
                result = self._check_take_profit(order, price)

                if result.should_take:
                    order.is_active = False
                    await self._trigger_take_profit(result)

    async def _trigger_stop_loss(self, result: StopLossResult) -> None:
        """触发止损回调"""
        logger.warning(f"止损触发: {result.symbol} @ {result.exit_price}, 盈亏: {result.pnl}")

        for callback in self._stop_loss_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"止损回调错误: {e}")

    async def _trigger_take_profit(self, result: TakeProfitResult) -> None:
        """触发止盈回调"""
        logger.info(f"止盈触发: {result.symbol} @ {result.exit_price}, 原因: {result.reason}")

        for callback in self._take_profit_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"止盈回调错误: {e}")

    # ============ 回调注册 ============

    def on_stop_loss(self, callback: Callable[[StopLossResult], None]) -> None:
        """注册止损回调"""
        self._stop_loss_callbacks.append(callback)

    def on_take_profit(self, callback: Callable[[TakeProfitResult], None]) -> None:
        """注册止盈回调"""
        self._take_profit_callbacks.append(callback)

    # ============ 监控控制 ============

    async def start_monitoring(self) -> None:
        """启动监控"""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("止损止盈监控已启动")

    async def stop_monitoring(self) -> None:
        """停止监控"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("止损止盈监控已停止")

    # ============ 手动更新 ============

    def update_stop_loss_price(self, symbol: str, new_stop_price: Decimal) -> bool:
        """手动更新止损价格"""
        if symbol in self._stop_losses:
            self._stop_losses[symbol].stop_price = new_stop_price
            self._stop_losses[symbol].stop_loss_type = StopLossType.FIXED
            logger.info(f"更新止损价: {symbol} -> {new_stop_price}")
            return True
        return False

    def update_take_profit_price(self, symbol: str, new_target_price: Decimal) -> bool:
        """手动更新止盈价格"""
        if symbol in self._take_profits:
            self._take_profits[symbol].target_price = new_target_price
            self._take_profits[symbol].take_profit_type = TakeProfitType.FIXED
            logger.info(f"更新止盈价: {symbol} -> {new_target_price}")
            return True
        return False
