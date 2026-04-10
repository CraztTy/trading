"""
模拟撮合引擎

职责：
- 模拟交易所撮合逻辑
- 限价单价格优先、时间优先
- 模拟滑点（大单部分成交）
- 模拟涨跌停限制
"""
import random
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

from src.models.order import Order
from src.models.enums import OrderDirection, OrderStatus
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass
class MarketPrice:
    """市场价格"""
    symbol: str
    last_price: Decimal
    bid_price: Decimal      # 买一价
    ask_price: Decimal      # 卖一价
    bid_volume: int = 0     # 买一量
    ask_volume: int = 0     # 卖一量
    high_limit: Optional[Decimal] = None   # 涨停价
    low_limit: Optional[Decimal] = None    # 跌停价
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MatchResult:
    """撮合结果"""
    success: bool
    filled_qty: int = 0
    filled_price: Decimal = Decimal("0")
    remaining_qty: int = 0
    message: str = ""


class SimulatedMatchingEngine:
    """
    模拟撮合引擎

    模拟A股交易所的撮合逻辑：
    1. 价格优先：买单价高优先，卖单价低优先
    2. 时间优先：同价格先委托先成交
    3. 涨跌停限制：涨停不能买入，跌停不能卖出
    4. 部分成交：大单可能部分成交
    """

    def __init__(self):
        """初始化撮合引擎"""
        self.market_data: Dict[str, MarketPrice] = {}
        self.order_book: Dict[str, List[Order]] = {}  # 每个标的的订单簿
        self.fill_callbacks: List[Callable[[Order, int, Decimal], None]] = []

        # 撮合参数
        self.slippage_rate = Decimal("0.001")  # 滑点率 0.1%
        self.partial_fill_threshold = 100000  # 部分成交阈值（金额）
        self.min_fill_ratio = 0.3  # 最小成交比例

    def register_fill_callback(
        self,
        callback: Callable[[Order, int, Decimal], None]
    ) -> None:
        """
        注册成交回调

        Args:
            callback: 回调函数(order, fill_qty, fill_price)
        """
        self.fill_callbacks.append(callback)

    def update_market_price(self, price: MarketPrice) -> None:
        """更新市场价格"""
        self.market_data[price.symbol] = price

    def get_market_price(self, symbol: str) -> Optional[MarketPrice]:
        """获取市场价格"""
        return self.market_data.get(symbol)

    def try_match(self, order: Order) -> MatchResult:
        """
        尝试撮合订单

        Args:
            order: 待撮合订单

        Returns:
            MatchResult: 撮合结果
        """
        symbol = order.symbol
        market = self.get_market_price(symbol)

        if not market:
            return MatchResult(
                success=False,
                message=f"无市场数据: {symbol}"
            )

        # 检查涨跌停
        can_trade, message = self._check_price_limit(order, market)
        if not can_trade:
            return MatchResult(success=False, message=message)

        # 计算可成交数量
        fill_qty = self._calculate_fill_qty(order, market)

        if fill_qty <= 0:
            return MatchResult(
                success=False,
                message="无法成交，价格不符合条件"
            )

        # 计算成交价格（含滑点）
        fill_price = self._calculate_fill_price(order, market)

        # 触发回调
        for callback in self.fill_callbacks:
            try:
                callback(order, fill_qty, fill_price)
            except Exception as e:
                logger.error(f"成交回调失败: {e}")

        return MatchResult(
            success=True,
            filled_qty=fill_qty,
            filled_price=fill_price,
            remaining_qty=order.qty - order.filled_qty - fill_qty,
            message="成交成功"
        )

    def _check_price_limit(
        self,
        order: Order,
        market: MarketPrice
    ) -> tuple[bool, str]:
        """
        检查涨跌停限制

        Returns:
            (是否可以交易, 错误信息)
        """
        # 如果没有涨跌停数据，默认允许
        if market.high_limit is None or market.low_limit is None:
            return True, ""

        if order.direction == OrderDirection.BUY:
            # 买入：价格不能超过涨停价
            if order.price and order.price > market.high_limit:
                return False, f"买入价格 {order.price} 超过涨停价 {market.high_limit}"

            # 涨停时不能买入
            if market.last_price >= market.high_limit:
                return False, "已涨停，无法买入"

        else:  # SELL
            # 卖出：价格不能低于跌停价
            if order.price and order.price < market.low_limit:
                return False, f"卖出价格 {order.price} 低于跌停价 {market.low_limit}"

            # 跌停时不能卖出
            if market.last_price <= market.low_limit:
                return False, "已跌停，无法卖出"

        return True, ""

    def _calculate_fill_qty(self, order: Order, market: MarketPrice) -> int:
        """
        计算可成交数量

        规则：
        1. 小单（<10万）全额成交
        2. 大单（>10万）可能部分成交（30%-100%）
        3. 不能超过剩余数量
        """
        remaining_qty = order.qty - order.filled_qty

        if remaining_qty <= 0:
            return 0

        # 计算订单金额
        order_amount = order.price * remaining_qty if order.price else market.last_price * remaining_qty

        # 小单全额成交
        if order_amount < self.partial_fill_threshold:
            return remaining_qty

        # 大单部分成交（随机比例）
        fill_ratio = random.uniform(self.min_fill_ratio, 1.0)
        fill_qty = int(remaining_qty * fill_ratio)

        # 确保至少成交1手（100股）
        fill_qty = max(fill_qty, 100)
        fill_qty = min(fill_qty, remaining_qty)

        # 对齐到100股（A股最小单位）
        fill_qty = (fill_qty // 100) * 100

        return fill_qty

    def _calculate_fill_price(self, order: Order, market: MarketPrice) -> Decimal:
        """
        计算成交价格（含滑点）

        规则：
        1. 限价单：按委托价成交，可能有微小滑点
        2. 买入滑点：成交价 >= 委托价
        3. 卖出滑点：成交价 <= 委托价
        """
        base_price = order.price if order.price else market.last_price

        # 计算滑点
        slippage = base_price * self.slippage_rate

        if order.direction == OrderDirection.BUY:
            # 买入：成交价可能略高于委托价（向上滑点）
            fill_price = base_price + (slippage * Decimal(random.uniform(0, 0.5)))
        else:
            # 卖出：成交价可能略低于委托价（向下滑点）
            fill_price = base_price - (slippage * Decimal(random.uniform(0, 0.5)))

        # 保留两位小数
        return Decimal(str(round(fill_price, 2)))

    def can_match(self, order: Order) -> bool:
        """检查订单是否可以成交"""
        if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
            return False

        market = self.get_market_price(order.symbol)
        if not market:
            return False

        can_trade, _ = self._check_price_limit(order, market)
        return can_trade


class MarketDataSimulator:
    """
    市场数据模拟器

    生成模拟的市场价格数据，用于测试撮合引擎。
    """

    def __init__(self):
        self.base_prices: Dict[str, Decimal] = {}
        self.current_prices: Dict[str, MarketPrice] = {}

    def set_base_price(self, symbol: str, price: Decimal) -> None:
        """设置标的基准价格"""
        self.base_prices[symbol] = price

        # 初始化市场价格
        high_limit = price * Decimal("1.1")   # A股涨停 10%
        low_limit = price * Decimal("0.9")    # A股跌停 10%

        self.current_prices[symbol] = MarketPrice(
            symbol=symbol,
            last_price=price,
            bid_price=price * Decimal("0.999"),
            ask_price=price * Decimal("1.001"),
            bid_volume=random.randint(1000, 10000),
            ask_volume=random.randint(1000, 10000),
            high_limit=high_limit,
            low_limit=low_limit
        )

    def tick(self, symbol: Optional[str] = None) -> None:
        """
        模拟价格变动

        每次调用随机变动价格（-1% ~ +1%）
        """
        symbols = [symbol] if symbol else list(self.current_prices.keys())

        for sym in symbols:
            if sym not in self.current_prices:
                continue

            current = self.current_prices[sym]
            base = self.base_prices.get(sym, current.last_price)

            # 随机变动（-1% ~ +1%）
            change_rate = Decimal(str(random.uniform(-0.01, 0.01)))
            new_price = base * (Decimal("1") + change_rate)

            # 限制在涨跌停范围内
            if current.high_limit:
                new_price = min(new_price, current.high_limit)
            if current.low_limit:
                new_price = max(new_price, current.low_limit)

            new_price = Decimal(str(round(new_price, 2)))

            # 更新价格
            current.last_price = new_price
            current.bid_price = new_price * Decimal("0.999")
            current.ask_price = new_price * Decimal("1.001")
            current.bid_volume = random.randint(1000, 10000)
            current.ask_volume = random.randint(1000, 10000)
            current.timestamp = datetime.now()

    def get_price(self, symbol: str) -> Optional[MarketPrice]:
        """获取当前价格"""
        return self.current_prices.get(symbol)


# 全局撮合引擎实例（单例）
_matching_engine: Optional[SimulatedMatchingEngine] = None
_market_simulator: Optional[MarketDataSimulator] = None


def get_matching_engine() -> SimulatedMatchingEngine:
    """获取全局撮合引擎实例"""
    global _matching_engine
    if _matching_engine is None:
        _matching_engine = SimulatedMatchingEngine()
    return _matching_engine


def get_market_simulator() -> MarketDataSimulator:
    """获取全局市场模拟器实例"""
    global _market_simulator
    if _market_simulator is None:
        _market_simulator = MarketDataSimulator()
    return _market_simulator
