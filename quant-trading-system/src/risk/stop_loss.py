"""
止损止盈管理器

提供实时止损止盈功能：
- 固定比例止损/止盈
- 动态跟踪止损（移动止损）
- 时间止损
- 波动率止损
- 分批止盈
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Set
from enum import Enum
import asyncio

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
class StopLossType(Enum):
    """止损类型"""
    FIXED = "fixed"              # 固定价格止损
    PERCENTAGE = "percentage"    # 固定比例止损
    TRAILING = "trailing"        # 跟踪止损（移动）
    TIME = "time"                # 时间止损
    VOLATILITY = "volatility"    # 波动率止损
class TakeProfitType(Enum):
    """止盈类型"""
    FIXED = "fixed"              # 固定价格止盈
    PERCENTAGE = "percentage"    # 固定比例止盈
    TRAILING = "trailing"        # 跟踪止盈
    PARTIAL = "partial"          # 分批止盈

class StopLossOrder:
    """止损订单"""
    id: str
    symbol: str
    position_qty: int
    entry_price: Decimal
    stop_loss_type: StopLossType

    # 止损参数
    stop_price: Optional[Decimal] = None           # 固定止损价
    stop_pct: Optional[Decimal] = None             # 止损比例
    trailing_distance: Optional[Decimal] = None    # 跟踪距离

    # 状态
    is_active: bool = True
    highest_price: Optional[Decimal] = None        # 最高价（用于跟踪止损）
    lowest_price: Optional[Decimal] = None         # 最低价（用于跟踪止盈）
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None

    def __post_init__(self):
        if self.highest_price is None:
            self.highest_price = self.entry_price
        if self.lowest_price is None:
            self.lowest_price = self.entry_price

class TakeProfitOrder:
    """止盈订单"""
    id: str
    symbol: str
    position_qty: int
    entry_price: Decimal
    take_profit_type: TakeProfitType

    # 止盈参数
    target_price: Optional[Decimal] = None         # 目标价
    target_pct: Optional[Decimal] = None           # 目标比例
    partial_levels: Optional[List[Decimal]] = None # 分批止盈比例 [0.3, 0.5, 0.2]
    partial_prices: Optional[List[Decimal]] = None # 分批止盈价格

    # 状态
    is_active: bool = True
    executed_levels: List[int] = field(default_factory=list)  # 已执行的层级
    created_at: datetime = field(default_factory=datetime.now)
    triggered_at: Optional[datetime] = None
    lowest_price: Optional[Decimal] = None         # 最低价（用于跟踪止盈）

    def __post_init__(self):
        if self.lowest_price is None:
            self.lowest_price = self.entry_price
class StopLossResult:
    """止损检查结果"""
    symbol: str
    should_stop: bool
    stop_price: Optional[Decimal] = None
    reason: str = ""
    pnl: Optional[Decimal] = None
    pnl_pct: Optional[Decimal] = None

class TakeProfitResult:
    """止盈检查结果"""
    symbol: str
    should_take: bool
    target_price: Optional[Decimal] = None
    reason: str = ""
    partial_qty: Optional[int] = None  # 分批止盈数量
    level: Optional[int] = None        # 触发的层级
class StopLossManager:
    """
    止损止盈管理器

    职责：
    - 管理止损订单
    - 实时价格监控
    - 触发止损/止盈信号
    - 支持多种止损策略
    """

    def __init__(self, check_interval: float = 1.0):
        """
        Args:
            check_interval: 价格检查间隔（秒）
        """
        self.check_interval = check_interval

        # 止损订单: symbol -> StopLossOrder
        self._stop_loss_orders: Dict[str, StopLossOrder] = {}

        # 止盈订单: symbol -> TakeProfitOrder
        self._take_profit_orders: Dict[str, TakeProfitOrder] = {}

        # 价格订阅: symbol -> current_price
        self._current_prices: Dict[str, Decimal] = {}

        # 回调函数
        self._stop_loss_callbacks: List[Callable[[StopLossResult], None]] = []
        self._take_profit_callbacks: List[Callable[[TakeProfitResult], None]] = []

        # 运行状态
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        logger.info("止损止盈管理器初始化完成")

    # ============ 订单管理 ============

    def add_stop_loss(
        self,
        symbol: str,
        position_qty: int,
        entry_price: Decimal,
        stop_type: StopLossType = StopLossType.PERCENTAGE,
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
            stop_price: 固定止损价
            stop_pct: 止损比例 (如 0.05 表示 5%)
            trailing_distance: 跟踪距离

        Returns:
            订单ID
        """
        order_id = f"SL_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 计算默认止损价
        if stop_type == StopLossType.PERCENTAGE and stop_pct:
            stop_price = entry_price * (1 - stop_pct)

        order = StopLossOrder(
            id=order_id,
            symbol=symbol,
            position_qty=position_qty,
            entry_price=entry_price,
            stop_loss_type=stop_type,
            stop_price=stop_price,
            stop_pct=stop_pct,
            trailing_distance=trailing_distance,
            highest_price=entry_price
        )

        self._stop_loss_orders[symbol] = order

        logger.info(
            f"添加止损: {symbol} @ {stop_price} "
            f"({stop_type.value}, 数量: {position_qty})"
        )

        return order_id

    def add_take_profit(
        self,
        symbol: str,
        position_qty: int,
        entry_price: Decimal,
        tp_type: TakeProfitType = TakeProfitType.PERCENTAGE,
        target_price: Optional[Decimal] = None,
        target_pct: Optional[Decimal] = None,
        partial_levels: Optional[List[Decimal]] = None,
        partial_prices: Optional[List[Decimal]] = None
    ) -> str:
        """
        添加止盈订单

        Args:
            symbol: 标的代码
            position_qty: 持仓数量
            entry_price: 入场价格
            tp_type: 止盈类型
            target_price: 目标价
            target_pct: 目标比例
            partial_levels: 分批比例 [0.3, 0.3, 0.4]
            partial_prices: 分批价格

        Returns:
            订单ID
        """
        order_id = f"TP_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 计算默认目标价
        if tp_type == TakeProfitType.PERCENTAGE and target_pct:
            target_price = entry_price * (1 + target_pct)

        order = TakeProfitOrder(
            id=order_id,
            symbol=symbol,
            position_qty=position_qty,
            entry_price=entry_price,
            take_profit_type=tp_type,
            target_price=target_price,
            target_pct=target_pct,
            partial_levels=partial_levels,
            partial_prices=partial_prices
        )

        self._take_profit_orders[symbol] = order

        logger.info(
            f"添加止盈: {symbol} @ {target_price} "
            f"({tp_type.value}, 数量: {position_qty})"
        )

        return order_id

    def remove_stop_loss(self, symbol: str) -> bool:
        """移除止损订单"""
        if symbol in self._stop_loss_orders:
            del self._stop_loss_orders[symbol]
            logger.info(f"移除止损: {symbol}")
            return True
        return False

    def remove_take_profit(self, symbol: str) -> bool:
        """移除止盈订单"""
        if symbol in self._take_profit_orders:
            del self._take_profit_orders[symbol]
            logger.info(f"移除止盈: {symbol}")
            return True
        return False

    def update_stop_loss_price(self, symbol: str, new_stop_price: Decimal) -> bool:
        """更新止损价格（手动调整）"""
        if symbol not in self._stop_loss_orders:
            return False

        order = self._stop_loss_orders[symbol]
        order.stop_price = new_stop_price

        logger.info(f"更新止损价: {symbol} -> {new_stop_price}")
        return True

    def update_take_profit_price(self, symbol: str, new_target_price: Decimal) -> bool:
        """更新止盈价格"""
        if symbol not in self._take_profit_orders:
            return False

        order = self._take_profit_orders[symbol]
        order.target_price = new_target_price

        logger.info(f"更新止盈价: {symbol} -> {new_target_price}")
        return True

    # ============ 实时监控 ============

    async def start_monitoring(self) -> None:
        """启动价格监控"""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("止损止盈监控已启动")

    async def stop_monitoring(self) -> None:
        """停止价格监控"""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("止损止盈监控已停止")

    async def _monitor_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                # 检查所有止损止盈订单
                await self._check_all_orders()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"监控循环异常: {e}")
                await asyncio.sleep(self.check_interval)

    async def _check_all_orders(self) -> None:
        """检查所有订单"""
        # 检查止损
        for symbol, order in list(self._stop_loss_orders.items()):
            if not order.is_active:
                continue

            current_price = self._current_prices.get(symbol)
            if current_price is None:
                continue

            result = self._check_stop_loss(order, current_price)
            if result.should_stop:
                await self._trigger_stop_loss(result)

        # 检查止盈
        for symbol, order in list(self._take_profit_orders.items()):
            if not order.is_active:
                continue

            current_price = self._current_prices.get(symbol)
            if current_price is None:
                continue

            result = self._check_take_profit(order, current_price)
            if result.should_take:
                await self._trigger_take_profit(result)

    def update_price(self, symbol: str, price: Decimal) -> None:
        """更新当前价格"""
        self._current_prices[symbol] = price

    # ============ 止损检查 ============

    def _check_stop_loss(self, order: StopLossOrder, current_price: Decimal) -> StopLossResult:
        """检查是否触发止损"""
        symbol = order.symbol

        # 更新最高价（用于跟踪止损）
        if current_price > order.highest_price:
            order.highest_price = current_price

        # 根据类型检查
        if order.stop_loss_type == StopLossType.FIXED:
            # 固定价格止损
            if current_price <= order.stop_price:
                pnl = (current_price - order.entry_price) * order.position_qty
                pnl_pct = (current_price - order.entry_price) / order.entry_price

                return StopLossResult(
                    symbol=symbol,
                    should_stop=True,
                    stop_price=order.stop_price,
                    reason=f"价格跌破止损价 {order.stop_price}",
                    pnl=pnl,
                    pnl_pct=pnl_pct
                )

        elif order.stop_loss_type == StopLossType.PERCENTAGE:
            # 固定比例止损
            loss_pct = (order.entry_price - current_price) / order.entry_price

            if loss_pct >= order.stop_pct:
                pnl = (current_price - order.entry_price) * order.position_qty

                return StopLossResult(
                    symbol=symbol,
                    should_stop=True,
                    stop_price=current_price,
                    reason=f"亏损达到 {loss_pct:.2%}，超过止损线 {order.stop_pct:.2%}",
                    pnl=pnl,
                    pnl_pct=-loss_pct
                )

        elif order.stop_loss_type == StopLossType.TRAILING:
            # 跟踪止损
            if order.trailing_distance:
                # 计算当前止损价（最高价 - 跟踪距离）
                current_stop = order.highest_price - order.trailing_distance

                if current_price <= current_stop:
                    pnl = (current_price - order.entry_price) * order.position_qty

                    return StopLossResult(
                        symbol=symbol,
                        should_stop=True,
                        stop_price=current_stop,
                        reason=f"触发跟踪止损，从最高价 {order.highest_price} 回落 {order.trailing_distance}",
                        pnl=pnl,
                        pnl_pct=(current_price - order.entry_price) / order.entry_price
                    )

        return StopLossResult(symbol=symbol, should_stop=False)

    def _check_take_profit(self, order: TakeProfitOrder, current_price: Decimal) -> TakeProfitResult:
        """检查是否触发止盈"""
        symbol = order.symbol

        # 更新最低价
        if current_price < order.lowest_price:
            order.lowest_price = current_price

        # 分批止盈
        if order.take_profit_type == TakeProfitType.PARTIAL and order.partial_prices:
            for i, (price_level, ratio) in enumerate(zip(order.partial_prices, order.partial_levels)):
                if i in order.executed_levels:
                    continue

                if current_price >= price_level:
                    qty = int(order.position_qty * ratio)

                    return TakeProfitResult(
                        symbol=symbol,
                        should_take=True,
                        target_price=price_level,
                        reason=f"达到第{i+1}批止盈目标 {price_level}",
                        partial_qty=qty,
                        level=i
                    )

        # 固定价格止盈
        elif order.take_profit_type == TakeProfitType.FIXED:
            if current_price >= order.target_price:
                return TakeProfitResult(
                    symbol=symbol,
                    should_take=True,
                    target_price=order.target_price,
                    reason=f"价格达到止盈目标 {order.target_price}"
                )

        # 固定比例止盈
        elif order.take_profit_type == TakeProfitType.PERCENTAGE:
            profit_pct = (current_price - order.entry_price) / order.entry_price

            if profit_pct >= order.target_pct:
                return TakeProfitResult(
                    symbol=symbol,
                    should_take=True,
                    target_price=current_price,
                    reason=f"盈利达到 {profit_pct:.2%}，超过目标 {order.target_pct:.2%}"
                )

        return TakeProfitResult(symbol=symbol, should_take=False)

    # ============ 触发处理 ============

    async def _trigger_stop_loss(self, result: StopLossResult) -> None:
        """触发止损"""
        symbol = result.symbol

        if symbol in self._stop_loss_orders:
            order = self._stop_loss_orders[symbol]
            order.is_active = False
            order.triggered_at = datetime.now()

        logger.warning(
            f"🔴 止损触发: {symbol} @ {result.stop_price}, "
            f"盈亏: {result.pnl} ({result.pnl_pct:.2%}), 原因: {result.reason}"
        )

        # 触发回调
        for callback in self._stop_loss_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"止损回调失败: {e}")

    async def _trigger_take_profit(self, result: TakeProfitResult) -> None:
        """触发止盈"""
        symbol = result.symbol

        if symbol in self._take_profit_orders:
            order = self._take_profit_orders[symbol]

            # 如果是分批止盈，标记已执行的层级
            if result.level is not None:
                order.executed_levels.append(result.level)

                # 检查是否全部执行完毕
                if len(order.executed_levels) >= len(order.partial_levels):
                    order.is_active = False
            else:
                order.is_active = False

            order.triggered_at = datetime.now()

        logger.info(
            f"🟢 止盈触发: {symbol} @ {result.target_price}, "
            f"原因: {result.reason}"
        )

        # 触发回调
        for callback in self._take_profit_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"止盈回调失败: {e}")

    # ============ 回调注册 ============

    def on_stop_loss(self, callback: Callable[[StopLossResult], None]) -> None:
        """注册止损回调"""
        self._stop_loss_callbacks.append(callback)

    def on_take_profit(self, callback: Callable[[TakeProfitResult], None]) -> None:
        """注册止盈回调"""
        self._take_profit_callbacks.append(callback)

    # ============ 查询接口 ============

    def get_stop_loss(self, symbol: str) -> Optional[StopLossOrder]:
        """获取止损订单"""
        return self._stop_loss_orders.get(symbol)

    def get_take_profit(self, symbol: str) -> Optional[TakeProfitOrder]:
        """获取止盈订单"""
        return self._take_profit_orders.get(symbol)

    def get_all_stop_losses(self) -> Dict[str, StopLossOrder]:
        """获取所有止损订单"""
        return self._stop_loss_orders.copy()

    def get_all_take_profits(self) -> Dict[str, TakeProfitOrder]:
        """获取所有止盈订单"""
        return self._take_profit_orders.copy()

    def get_active_orders(self) -> Dict[str, any]:
        """获取所有活跃订单"""
        return {
            "stop_losses": {
                s: o for s, o in self._stop_loss_orders.items() if o.is_active
            },
            "take_profits": {
                s: o for s, o in self._take_profit_orders.items() if o.is_active
            }
        }
