"""
策略基类与接口定义

所有交易策略必须继承 StrategyBase 并实现 on_bar / on_tick 方法。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import asyncio

from src.common.logger import TradingLogger
from src.models.enums import OrderDirection as OrderSide, OrderType

logger = TradingLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"  # 平仓


class StrategyState(Enum):
    """策略状态"""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class Signal:
    """交易信号"""
    type: SignalType
    symbol: str
    timestamp: datetime
    price: Optional[Decimal] = None
    volume: Optional[int] = None  # 手数
    confidence: float = 0.5  # 置信度 0-1
    reason: str = ""  # 信号原因
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class BarData:
    """K线数据"""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal
    period: str = "1d"  # 周期: 1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M


@dataclass
class TickData:
    """Tick数据"""
    symbol: str
    timestamp: datetime
    price: Decimal
    volume: int
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    bid_volume: Optional[int] = None
    ask_volume: Optional[int] = None


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int  # 正数=多头，负数=空头
    avg_price: Decimal
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


@dataclass
class AccountInfo:
    """账户信息"""
    total_equity: Decimal
    available_cash: Decimal
    frozen_cash: Decimal
    margin_used: Decimal
    positions: Dict[str, Position]


class StrategyContext:
    """
    策略上下文

    封装策略运行所需的所有环境和状态信息。
    策略通过 context 获取数据、发送订单、查询持仓等。
    """

    def __init__(self, strategy_id: str, initial_capital: Decimal = Decimal("100000")):
        self.strategy_id = strategy_id
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # 数据缓存
        self._bars: Dict[str, List[BarData]] = {}  # symbol -> bars
        self._ticks: Dict[str, TickData] = {}  # symbol -> latest tick

        # 账户信息
        self._account: Optional[AccountInfo] = None
        self._positions: Dict[str, Position] = {}

        # 订单回调
        self._order_callbacks: List[Callable] = []

        # 运行时状态
        self._current_time: Optional[datetime] = None
        self._market_open: bool = False

    # ============ 数据接口 ============

    def get_bars(self, symbol: str, n: int = 100) -> List[BarData]:
        """获取历史K线数据"""
        bars = self._bars.get(symbol, [])
        return bars[-n:] if len(bars) > n else bars

    def get_latest_bar(self, symbol: str) -> Optional[BarData]:
        """获取最新K线"""
        bars = self._bars.get(symbol, [])
        return bars[-1] if bars else None

    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """获取最新Tick"""
        return self._ticks.get(symbol)

    def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """获取当前价格"""
        tick = self._ticks.get(symbol)
        if tick:
            return tick.price
        bar = self.get_latest_bar(symbol)
        if bar:
            return bar.close
        return None

    # ============ 账户/持仓接口 ============

    @property
    def account(self) -> Optional[AccountInfo]:
        """获取账户信息"""
        return self._account

    @property
    def positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self._positions.copy()

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定标的持仓"""
        return self._positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        """是否持有某标的"""
        pos = self._positions.get(symbol)
        return pos is not None and pos.quantity != 0

    def get_position_quantity(self, symbol: str) -> int:
        """获取持仓数量（正数=多头，负数=空头，0=无持仓）"""
        pos = self._positions.get(symbol)
        return pos.quantity if pos else 0

    # ============ 订单接口 ============

    def buy(
        self,
        symbol: str,
        volume: int,
        price: Optional[Decimal] = None,
        order_type: OrderType = OrderType.MARKET,
        reason: str = ""
    ) -> Optional[str]:
        """
        买入开仓

        Args:
            symbol: 标的代码
            volume: 买入数量（手）
            price: 价格，None 表示市价
            order_type: 订单类型
            reason: 交易原因

        Returns:
            订单ID，失败返回 None
        """
        return self._send_order(
            symbol=symbol,
            side=OrderSide.BUY,
            volume=volume,
            price=price,
            order_type=order_type,
            reason=reason
        )

    def sell(
        self,
        symbol: str,
        volume: int,
        price: Optional[Decimal] = None,
        order_type: OrderType = OrderType.MARKET,
        reason: str = ""
    ) -> Optional[str]:
        """
        卖出平仓（平多头）

        Args:
            symbol: 标的代码
            volume: 卖出数量（手）
            price: 价格，None 表示市价
            order_type: 订单类型
            reason: 交易原因

        Returns:
            订单ID，失败返回 None
        """
        return self._send_order(
            symbol=symbol,
            side=OrderSide.SELL,
            volume=volume,
            price=price,
            order_type=order_type,
            reason=reason
        )

    def close_position(
        self,
        symbol: str,
        price: Optional[Decimal] = None,
        reason: str = ""
    ) -> Optional[str]:
        """
        平仓（卖出全部持仓）

        Args:
            symbol: 标的代码
            price: 价格，None 表示市价
            reason: 平仓原因

        Returns:
            订单ID，失败返回 None
        """
        pos = self._positions.get(symbol)
        if not pos or pos.quantity == 0:
            logger.warning(f"[{self.strategy_id}] 无持仓可平: {symbol}")
            return None

        volume = abs(pos.quantity)
        side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY

        return self._send_order(
            symbol=symbol,
            side=side,
            volume=volume,
            price=price,
            order_type=OrderType.MARKET,
            reason=f"平仓: {reason}"
        )

    def _send_order(
        self,
        symbol: str,
        side: OrderSide,
        volume: int,
        price: Optional[Decimal],
        order_type: OrderType,
        reason: str
    ) -> Optional[str]:
        """内部发送订单"""
        # 这里将来会调用订单服务
        # 目前先记录日志并返回模拟订单ID
        order_id = f"{self.strategy_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        logger.info(
            f"[{self.strategy_id}] 下单: {side.value} {symbol} "
            f"{volume}手 @ {price or '市价'} ({reason})"
        )

        # 触发回调
        for callback in self._order_callbacks:
            try:
                callback({
                    "order_id": order_id,
                    "strategy_id": self.strategy_id,
                    "symbol": symbol,
                    "side": side,
                    "volume": volume,
                    "price": price,
                    "reason": reason
                })
            except Exception as e:
                logger.error(f"订单回调失败: {e}")

        return order_id

    def on_order_callback(self, callback: Callable):
        """注册订单回调"""
        self._order_callbacks.append(callback)

    # ============ 内部更新接口（由管理器调用） ============

    def _update_bar(self, bar: BarData) -> None:
        """更新K线数据"""
        if bar.symbol not in self._bars:
            self._bars[bar.symbol] = []
        self._bars[bar.symbol].append(bar)
        self._current_time = bar.timestamp

    def _update_tick(self, tick: TickData) -> None:
        """更新Tick数据"""
        self._ticks[tick.symbol] = tick
        self._current_time = tick.timestamp

    def _update_account(self, account: AccountInfo) -> None:
        """更新账户信息"""
        self._account = account
        self._positions = account.positions.copy()
        self.current_capital = account.total_equity

    def _set_market_open(self, is_open: bool) -> None:
        """设置市场状态"""
        self._market_open = is_open


class StrategyBase(ABC):
    """
    策略基类

    所有交易策略必须继承此类，并实现以下方法：
    - on_init: 初始化（一次性）
    - on_bar: K线触发（回测/实盘）
    - on_tick: Tick触发（实盘高频）
    - on_order_update: 订单状态更新
    - on_position_update: 持仓更新
    """

    def __init__(
        self,
        strategy_id: str,
        name: str,
        symbols: List[str],
        params: Optional[Dict[str, Any]] = None
    ):
        self.strategy_id = strategy_id
        self.name = name
        self.symbols = symbols
        self.params = params or {}

        # 运行时状态
        self.state = StrategyState.INITIALIZING
        self.context: Optional[StrategyContext] = None

        # 信号记录
        self._signals: List[Signal] = []
        self._signal_callbacks: List[Callable[[Signal], None]] = []

        # 统计
        self._init_time: Optional[datetime] = None
        self._start_time: Optional[datetime] = None
        self._bar_count = 0
        self._tick_count = 0

        logger.info(f"策略实例创建: {strategy_id} ({name})")

    # ============ 抽象方法（子类必须实现） ============

    @abstractmethod
    def on_init(self, context: StrategyContext) -> None:
        """
        策略初始化

        在策略启动时调用一次，用于：
        - 加载历史数据
        - 计算初始指标
        - 设置初始参数
        """
        pass

    @abstractmethod
    def on_bar(self, bar: BarData) -> None:
        """
        K线数据触发

        每当新的K线数据到来时调用，用于：
        - 计算技术指标
        - 生成交易信号
        - 执行交易逻辑
        """
        pass

    @abstractmethod
    def on_tick(self, tick: TickData) -> None:
        """
        Tick数据触发

        每当新的Tick数据到来时调用（实盘高频），用于：
        - 高频策略逻辑
        - 实时止损止盈
        - 盘口分析

        注意：回测时可能不调用此方法
        """
        pass

    async def on_bar_async(self, bar: BarData) -> Optional[Signal]:
        """
        异步K线数据触发（返回Signal版本）

        用于中书省驱动策略信号生成

        Args:
            bar: K线数据

        Returns:
            Signal or None: 交易信号
        """
        # 默认调用同步版本（子类可重写）
        self.on_bar(bar)

        # 子类应该重写此方法返回Signal
        # 示例:
        # if self.should_buy(bar):
        #     return Signal(type=SignalType.BUY, symbol=bar.symbol, ...)
        return None

    async def on_tick_async(self, tick: TickData) -> Optional[Signal]:
        """
        异步Tick数据触发（返回Signal版本）

        用于中书省驱动策略信号生成

        Args:
            tick: Tick数据

        Returns:
            Signal or None: 交易信号
        """
        # 默认调用同步版本（子类可重写）
        self.on_tick(tick)
        return None

    def on_order_update(self, order: Dict[str, Any]) -> None:
        """
        订单状态更新

        当订单状态变化时调用
        """
        pass

    def on_position_update(self, position: Position) -> None:
        """
        持仓更新

        当持仓变化时调用
        """
        pass

    # ============ 信号生成 ============

    def emit_signal(self, signal: Signal) -> None:
        """发出交易信号"""
        self._signals.append(signal)
        logger.info(
            f"[{self.strategy_id}] 信号: {signal.type.value} "
            f"{signal.symbol} @ {signal.price} ({signal.reason})"
        )

        # 触发回调
        for callback in self._signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"信号回调失败: {e}")

    def on_signal(self, callback: Callable[[Signal], None]) -> None:
        """注册信号回调"""
        self._signal_callbacks.append(callback)

    @property
    def signals(self) -> List[Signal]:
        """获取所有信号"""
        return self._signals.copy()

    # ============ 生命周期方法 ============

    def initialize(self, context: StrategyContext) -> None:
        """初始化策略"""
        self.context = context
        self._init_time = datetime.now()

        try:
            self.on_init(context)
            self.state = StrategyState.READY
            logger.info(f"[{self.strategy_id}] 初始化完成")
        except Exception as e:
            self.state = StrategyState.ERROR
            logger.error(f"[{self.strategy_id}] 初始化失败: {e}")
            raise

    def start(self) -> None:
        """启动策略"""
        if self.state not in [StrategyState.READY, StrategyState.PAUSED]:
            logger.warning(f"[{self.strategy_id}] 策略状态不正确，无法启动: {self.state}")
            return

        self.state = StrategyState.RUNNING
        self._start_time = datetime.now()
        logger.info(f"[{self.strategy_id}] 策略启动")

    def stop(self) -> None:
        """停止策略"""
        self.state = StrategyState.STOPPED
        logger.info(f"[{self.strategy_id}] 策略停止")

    def pause(self) -> None:
        """暂停策略"""
        if self.state == StrategyState.RUNNING:
            self.state = StrategyState.PAUSED
            logger.info(f"[{self.strategy_id}] 策略暂停")

    def resume(self) -> None:
        """恢复策略"""
        if self.state == StrategyState.PAUSED:
            self.state = StrategyState.RUNNING
            logger.info(f"[{self.strategy_id}] 策略恢复")

    # ============ 数据获取快捷方法 ============

    def get_bars(self, symbol: str, n: int = 100) -> List[BarData]:
        """获取历史K线"""
        if self.context:
            return self.context.get_bars(symbol, n)
        return []

    def get_latest_bar(self, symbol: str) -> Optional[BarData]:
        """获取最新K线"""
        if self.context:
            return self.context.get_latest_bar(symbol)
        return None

    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """获取最新Tick"""
        if self.context:
            return self.context.get_latest_tick(symbol)
        return None

    def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """获取当前价格"""
        if self.context:
            return self.context.get_current_price(symbol)
        return None

    def get_position_quantity(self, symbol: str) -> int:
        """获取持仓数量"""
        if self.context:
            return self.context.get_position_quantity(symbol)
        return 0

    # ============ 交易快捷方法 ============

    def buy(
        self,
        symbol: str,
        volume: int,
        price: Optional[Decimal] = None,
        reason: str = ""
    ) -> Optional[str]:
        """买入"""
        if self.context:
            return self.context.buy(symbol, volume, price, reason=reason)
        return None

    def sell(
        self,
        symbol: str,
        volume: int,
        price: Optional[Decimal] = None,
        reason: str = ""
    ) -> Optional[str]:
        """卖出"""
        if self.context:
            return self.context.sell(symbol, volume, price, reason=reason)
        return None

    def close_position(self, symbol: str, reason: str = "") -> Optional[str]:
        """平仓"""
        if self.context:
            return self.context.close_position(symbol, reason=reason)
        return None

    # ============ 统计信息 ============

    @property
    def stats(self) -> Dict[str, Any]:
        """获取策略统计"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "state": self.state.value,
            "symbols": self.symbols,
            "params": self.params,
            "bar_count": self._bar_count,
            "tick_count": self._tick_count,
            "signal_count": len(self._signals),
            "init_time": self._init_time.isoformat() if self._init_time else None,
            "start_time": self._start_time.isoformat() if self._start_time else None,
        }
