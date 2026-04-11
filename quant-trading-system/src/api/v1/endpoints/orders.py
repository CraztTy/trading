"""
订单管理 API

提供订单的创建、查询、撤单等功能
"""
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator

from src.services.order_service import OrderService
from src.models.order import Order
from src.models.base import get_db
from src.models.enums import OrderStatus, OrderDirection, OrderType
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()


# ============ 请求模型 ============

class OrderCreateRequest(BaseModel):
    """创建订单请求"""
    account_id: int = Field(..., description="账户ID")
    symbol: str = Field(..., min_length=6, max_length=16, description="股票代码")
    direction: OrderDirection = Field(..., description="买卖方向")
    qty: int = Field(..., gt=0, le=100_000_000, description="数量（最大1亿股）")
    price: Optional[Decimal] = Field(None, gt=0, description="价格（限价单必填）")
    order_type: OrderType = Field(default=OrderType.LIMIT, description="订单类型")
    strategy_id: Optional[int] = Field(None, description="策略ID")
    symbol_name: str = Field(default="", description="股票名称")

    @validator('price')
    def validate_price(cls, v, values):
        """验证价格"""
        if v is None:
            if values.get('order_type') == OrderType.LIMIT:
                raise ValueError('限价单必须指定价格')
            return v

        # 验证价格精度（A股最多2位小数）
        quantized = v.quantize(Decimal('0.01'))
        if v != quantized:
            raise ValueError('价格最多支持2位小数')

        # 验证价格范围（A股价格范围 0.01 - 99999.99）
        if v > Decimal('99999.99'):
            raise ValueError('价格超出有效范围')

        return v


class OrderFillRequest(BaseModel):
    """订单成交请求（模拟用）"""
    fill_qty: int = Field(..., gt=0, description="成交数量")
    fill_price: Decimal = Field(..., gt=0, description="成交价格")


class OrderResponse(BaseModel):
    """订单响应"""
    id: int
    order_id: str
    account_id: int
    strategy_id: Optional[int]
    symbol: str
    direction: str
    order_type: str
    qty: int
    price: Optional[float]
    status: str
    filled_qty: int
    remaining_qty: int
    filled_avg_price: float
    filled_amount: float
    created_at: Optional[str]
    submitted_at: Optional[str]
    filled_at: Optional[str]
    cancelled_at: Optional[str]
    error_msg: Optional[str]

    class Config:
        from_attributes = True


# ============ API 端点 ============

@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    request: OrderCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新订单

    流程：
    1. 创建订单（状态：CREATED）
    2. 提交订单（状态：PENDING）
    3. 冻结资金/持仓
    """
    service = OrderService(db)

    try:
        # 创建订单
        order = await service.create_order(
            account_id=request.account_id,
            symbol=request.symbol,
            direction=request.direction,
            qty=request.qty,
            price=request.price,
            order_type=request.order_type,
            strategy_id=request.strategy_id,
            symbol_name=request.symbol_name
        )

        # 提交订单（冻结资金/持仓）
        success = await service.submit_order(order)

        if not success:
            raise HTTPException(status_code=400, detail="订单提交失败")

        await db.commit()

        logger.info(
            "API: 创建订单成功",
            order_id=order.order_id,
            symbol=request.symbol
        )

        return order.to_dict()

    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"创建订单失败: {e}")
        raise HTTPException(status_code=500, detail="创建订单失败")


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取订单详情"""
    service = OrderService(db)
    order = await service.get_order(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return order.to_dict()


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    account_id: int = Query(..., description="账户ID"),
    status: Optional[OrderStatus] = Query(None, description="状态过滤"),
    limit: int = Query(100, ge=1, le=1000, description="数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db)
):
    """查询账户订单列表"""
    service = OrderService(db)
    orders = await service.get_account_orders(
        account_id=account_id,
        status=status,
        limit=limit,
        offset=offset
    )
    return [order.to_dict() for order in orders]


@router.get("/account/{account_id}/active", response_model=list[OrderResponse])
async def get_active_orders(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取账户活跃订单"""
    service = OrderService(db)
    orders = await service.get_active_orders(account_id)
    return [order.to_dict() for order in orders]


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    撤单

    解冻资金/持仓
    """
    service = OrderService(db)

    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    success = await service.cancel_order(order)

    if not success:
        raise HTTPException(status_code=400, detail="撤单失败，订单可能已成交或已撤")

    await db.commit()

    logger.info("API: 撤单成功", order_id=order_id)

    return order.to_dict()


@router.post("/{order_id}/fill", response_model=OrderResponse)
async def fill_order(
    order_id: str,
    request: OrderFillRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    模拟订单成交（测试用）

    实际交易中，成交应由交易所推送
    """
    service = OrderService(db)

    order = await service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 检查是否可以成交
    if order.status not in [OrderStatus.PENDING, OrderStatus.PARTIAL]:
        raise HTTPException(status_code=400, detail=f"订单状态 {order.status.value} 不可成交")

    # 检查成交数量
    if request.fill_qty > order.remaining_qty:
        raise HTTPException(
            status_code=400,
            detail=f"成交数量 {request.fill_qty} 超过剩余数量 {order.remaining_qty}"
        )

    success = await service.fill_order(
        order,
        fill_qty=request.fill_qty,
        fill_price=request.fill_price
    )

    if not success:
        raise HTTPException(status_code=500, detail="成交处理失败")

    await db.commit()

    logger.info(
        "API: 订单成交",
        order_id=order_id,
        fill_qty=request.fill_qty,
        fill_price=float(request.fill_price)
    )

    return order.to_dict()


@router.post("/account/{account_id}/cancel-all")
async def cancel_all_orders(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """批量撤单（撤销所有活跃订单）"""
    service = OrderService(db)

    cancelled_count = await service.batch_cancel_orders(account_id)
    await db.commit()

    return {
        "account_id": account_id,
        "cancelled_count": cancelled_count
    }
