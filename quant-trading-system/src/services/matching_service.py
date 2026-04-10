"""
撮合服务

整合订单服务和撮合引擎，提供完整的交易流程。
"""
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.order_service import OrderService
from src.core.matching_engine import (
    SimulatedMatchingEngine, MarketDataSimulator, get_matching_engine, get_market_simulator
)
from src.models.order import Order
from src.models.enums import OrderDirection
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class MatchingService:
    """
    撮合服务

    职责：
    1. 初始化市场数据
    2. 撮合待成交订单
    3. 处理成交结果
    4. 更新订单状态
    """

    def __init__(self, session: AsyncSession):
        """
        初始化撮合服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.order_service = OrderService(session)
        self.matching_engine = get_matching_engine()
        self.market_simulator = get_market_simulator()

        # 注册成交回调
        self.matching_engine.register_fill_callback(self._on_fill)

    async def initialize_market(self, symbol: str, base_price: Decimal) -> None:
        """
        初始化标的市场数据

        Args:
            symbol: 股票代码
            base_price: 基准价格
        """
        self.market_simulator.set_base_price(symbol, base_price)
        market_price = self.market_simulator.get_price(symbol)

        if market_price:
            self.matching_engine.update_market_price(market_price)
            logger.info(
                "初始化市场数据",
                symbol=symbol,
                base_price=float(base_price),
                high_limit=float(market_price.high_limit) if market_price.high_limit else None,
                low_limit=float(market_price.low_limit) if market_price.low_limit else None
            )

    async def match_order(self, order: Order) -> bool:
        """
        撮合单个订单

        Args:
            order: 待撮合订单

        Returns:
            bool: 是否发生成交
        """
        # 更新市场数据
        self.market_simulator.tick(order.symbol)
        market_price = self.market_simulator.get_price(order.symbol)

        if market_price:
            self.matching_engine.update_market_price(market_price)

        # 尝试撮合
        result = self.matching_engine.try_match(order)

        if result.success and result.filled_qty > 0:
            # 调用订单服务处理成交
            success = await self.order_service.fill_order(
                order,
                fill_qty=result.filled_qty,
                fill_price=result.filled_price
            )

            if success:
                await self.session.commit()
                logger.info(
                    "订单撮合成功",
                    order_id=order.order_id,
                    filled_qty=result.filled_qty,
                    filled_price=float(result.filled_price),
                    remaining_qty=result.remaining_qty
                )
                return True
            else:
                await self.session.rollback()
                logger.error("订单成交处理失败", order_id=order.order_id)
                return False

        return False

    async def match_all_active_orders(self) -> int:
        """
        撮合所有活跃订单

        Returns:
            int: 成交的订单数量
        """
        # 这里简化处理，实际应该遍历所有账户
        # 获取所有活跃订单（简化：假设账户ID为1）
        active_orders = await self.order_service.get_active_orders(1)

        filled_count = 0

        for order in active_orders:
            if await self.match_order(order):
                filled_count += 1

        logger.info(
            "批量撮合完成",
            total_orders=len(active_orders),
            filled_count=filled_count
        )

        return filled_count

    async def _on_fill(self, order: Order, fill_qty: int, fill_price: Decimal) -> None:
        """
        成交回调（已在外层处理，这里仅记录日志）

        Args:
            order: 订单
            fill_qty: 成交数量
            fill_price: 成交价格
        """
        logger.debug(
            "撮合引擎成交回调",
            order_id=order.order_id,
            fill_qty=fill_qty,
            fill_price=float(fill_price)
        )

    def get_market_price(self, symbol: str) -> Optional[Decimal]:
        """
        获取当前市场价格

        Args:
            symbol: 股票代码

        Returns:
            Decimal: 当前价格，无数据返回None
        """
        price = self.market_simulator.get_price(symbol)
        return price.last_price if price else None

    def can_match(self, order: Order) -> bool:
        """
        检查订单是否可以撮合

        Args:
            order: 订单

        Returns:
            bool: 是否可以撮合
        """
        return self.matching_engine.can_match(order)


# 撮合任务（用于定时轮询）
async def run_matching_task(session: AsyncSession) -> int:
    """
    运行撮合任务

    Args:
        session: 数据库会话

    Returns:
        int: 成交订单数
    """
    service = MatchingService(session)

    # 初始化市场数据（如果没有）
    await service.initialize_market("600519.SH", Decimal("1500.00"))

    # 撮合所有活跃订单
    return await service.match_all_active_orders()
