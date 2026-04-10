"""
撮合引擎 API

提供市场数据管理和订单撮合功能
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.services.matching_service import MatchingService, run_matching_task
from src.services.order_service import OrderService
from src.models.base import get_db
from src.models.order import Order
from src.models.enums import OrderStatus
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()


# ============ 请求模型 ============

class MarketDataRequest(BaseModel):
    """市场数据设置请求"""
    symbol: str = Field(..., description="股票代码")
    base_price: Decimal = Field(..., gt=0, description="基准价格")


class MatchResultResponse(BaseModel):
    """撮合结果响应"""
    success: bool
    filled_qty: int
    filled_price: float
    remaining_qty: int
    message: str


class MarketPriceResponse(BaseModel):
    """市场价格响应"""
    symbol: str
    last_price: float
    bid_price: float
    ask_price: float
    high_limit: Optional[float]
    low_limit: Optional[float]


# ============ API 端点 ============

@router.post("/market/init")
async def init_market(
    request: MarketDataRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    初始化市场数据

    设置标的基准价格和涨跌停限制
    """
    service = MatchingService(db)
    await service.initialize_market(request.symbol, request.base_price)
    await db.commit()

    logger.info(
        "API: 初始化市场数据",
        symbol=request.symbol,
        base_price=float(request.base_price)
    )

    return {
        "symbol": request.symbol,
        "base_price": float(request.base_price),
        "status": "initialized"
    }


@router.get("/market/{symbol}/price", response_model=MarketPriceResponse)
async def get_market_price(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """获取当前市场价格"""
    service = MatchingService(db)

    from src.core.matching_engine import get_market_simulator

    simulator = get_market_simulator()
    price = simulator.get_price(symbol)

    if not price:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的市场数据")

    return {
        "symbol": price.symbol,
        "last_price": float(price.last_price),
        "bid_price": float(price.bid_price),
        "ask_price": float(price.ask_price),
        "high_limit": float(price.high_limit) if price.high_limit else None,
        "low_limit": float(price.low_limit) if price.low_limit else None
    }


@router.post("/market/{symbol}/tick")
async def market_tick(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    模拟价格变动

    触发一次价格随机变动（-1% ~ +1%）
    """
    from src.core.matching_engine import get_market_simulator

    simulator = get_market_simulator()
    simulator.tick(symbol)

    price = simulator.get_price(symbol)

    if not price:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的市场数据")

    logger.info(
        "API: 价格变动",
        symbol=symbol,
        new_price=float(price.last_price)
    )

    return {
        "symbol": symbol,
        "last_price": float(price.last_price),
        "timestamp": price.timestamp.isoformat()
    }


@router.post("/orders/{order_id}/match", response_model=MatchResultResponse)
async def match_single_order(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    撮合单个订单

    尝试对指定订单进行撮合
    """
    order_service = OrderService(db)
    matching_service = MatchingService(db)

    # 获取订单
    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查订单状态
    if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
        raise HTTPException(
            status_code=400,
            detail=f"订单状态 {order.status.value} 不可撮合"
        )

    # 初始化市场数据（如果没有）
    await matching_service.initialize_market(order.symbol, order.price or Decimal("100"))

    # 尝试撮合
    from src.core.matching_engine import get_market_simulator

    simulator = get_market_simulator()
    simulator.tick(order.symbol)

    market_price = simulator.get_price(order.symbol)
    if market_price:
        matching_service.matching_engine.update_market_price(market_price)

    result = matching_service.matching_engine.try_match(order)

    if result.success and result.filled_qty > 0:
        # 执行成交
        success = await order_service.fill_order(
            order,
            fill_qty=result.filled_qty,
            fill_price=result.filled_price
        )

        if success:
            await db.commit()
            logger.info(
                "API: 订单撮合成功",
                order_id=order_id,
                filled_qty=result.filled_qty
            )
        else:
            await db.rollback()
            raise HTTPException(status_code=500, detail="成交处理失败")
    else:
        await db.rollback()

    return {
        "success": result.success,
        "filled_qty": result.filled_qty,
        "filled_price": float(result.filled_price) if result.filled_price else 0,
        "remaining_qty": result.remaining_qty,
        "message": result.message
    }


@router.post("/run")
async def run_matching(
    db: AsyncSession = Depends(get_db)
):
    """
    运行撮合任务

    撮合所有活跃订单
    """
    filled_count = await run_matching_task(db)
    await db.commit()

    logger.info("API: 批量撮合完成", filled_count=filled_count)

    return {
        "filled_count": filled_count,
        "status": "completed"
    }


@router.get("/orders/{order_id}/can-match")
async def can_order_match(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    """检查订单是否可以撮合"""
    order_service = OrderService(db)
    matching_service = MatchingService(db)

    order = await order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    can_match = matching_service.can_match(order)

    return {
        "order_id": order_id,
        "can_match": can_match,
        "status": order.status.value
    }
