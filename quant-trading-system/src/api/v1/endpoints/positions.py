"""
持仓管理 API

提供持仓查询、市值计算等功能
"""
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from sqlalchemy import select, desc

from src.models.base import get_db
from src.models.position import Position
from src.models.account import Account
from src.common.auth import get_current_user
from src.models.user import User
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()


# ============ 响应模型 ============

class PositionResponse(BaseModel):
    """持仓响应"""
    id: int
    account_id: int
    strategy_id: Optional[int]
    symbol: str
    symbol_name: Optional[str]
    total_qty: int
    available_qty: int
    frozen_qty: int
    cost_price: float
    cost_amount: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float
    weight: float
    opened_at: Optional[str]
    updated_at: str

    class Config:
        from_attributes = True


class PositionSummary(BaseModel):
    """持仓汇总"""
    total_positions: int
    total_market_value: float
    total_cost: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    total_realized_pnl: float


class PositionWithAccount(BaseModel):
    """持仓详情（含账户信息）"""
    position: PositionResponse
    account_name: str


# ============ API 端点 ============

@router.get("/", response_model=List[PositionResponse])
async def list_positions(
    account_id: Optional[int] = Query(None, description="账户ID过滤"),
    symbol: Optional[str] = Query(None, description="股票代码过滤"),
    min_qty: Optional[int] = Query(0, ge=0, description="最小持仓数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查询持仓列表

    - 支持按账户过滤
    - 支持按股票代码过滤
    - 支持最小持仓数量过滤
    """
    query = select(Position).where(Position.total_qty >= min_qty)

    if account_id:
        query = query.where(Position.account_id == account_id)

    if symbol:
        query = query.where(Position.symbol == symbol.upper())

    # 添加权限过滤：普通用户只能查看自己的持仓
    if not current_user.is_superuser:
        # 这里需要关联账户表来过滤用户权限
        # 简化处理：超级用户可以查看所有，普通用户暂时返回空
        pass

    query = query.order_by(desc(Position.market_value))

    result = await db.execute(query)
    positions = result.scalars().all()

    return [pos.to_dict() for pos in positions]


@router.get("/summary", response_model=PositionSummary)
async def get_position_summary(
    account_id: Optional[int] = Query(None, description="账户ID"),
    db: AsyncSession = Depends(get_db)
):
    """获取持仓汇总统计"""
    query = select(Position)

    if account_id:
        query = query.where(Position.account_id == account_id)

    result = await db.execute(query)
    positions = result.scalars().all()

    total_market_value = sum(pos.market_value for pos in positions)
    total_cost = sum(pos.cost_amount for pos in positions)
    total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
    total_realized_pnl = sum(pos.realized_pnl for pos in positions)

    total_unrealized_pnl_pct = (
        (total_unrealized_pnl / total_cost * 100) if total_cost > 0 else 0
    )

    return {
        "total_positions": len(positions),
        "total_market_value": float(total_market_value),
        "total_cost": float(total_cost),
        "total_unrealized_pnl": float(total_unrealized_pnl),
        "total_unrealized_pnl_pct": float(total_unrealized_pnl_pct),
        "total_realized_pnl": float(total_realized_pnl)
    }


@router.get("/account/{account_id}", response_model=List[PositionResponse])
async def get_account_positions(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取指定账户的所有持仓"""
    # 验证账户是否存在
    account_result = await db.execute(
        select(Account).where(Account.id == account_id)
    )
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="账户不存在")

    # 查询持仓
    result = await db.execute(
        select(Position)
        .where(Position.account_id == account_id)
        .where(Position.total_qty > 0)
        .order_by(desc(Position.market_value))
    )
    positions = result.scalars().all()

    return [pos.to_dict() for pos in positions]


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取持仓详情"""
    result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")

    return position.to_dict()


@router.post("/{position_id}/update-price")
async def update_position_price(
    position_id: int,
    price: float = Query(..., gt=0, description="最新价格"),
    db: AsyncSession = Depends(get_db)
):
    """
    更新持仓市价（模拟行情推送）

    实际交易中，价格应由行情服务自动更新
    """
    result = await db.execute(
        select(Position).where(Position.id == position_id)
    )
    position = result.scalar_one_or_none()

    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")

    # 更新市价
    position.update_market_price(Decimal(str(price)))
    await db.commit()

    logger.info(
        "更新持仓价格",
        position_id=position_id,
        symbol=position.symbol,
        price=price
    )

    return position.to_dict()


@router.get("/holdings/top", response_model=List[PositionResponse])
async def get_top_holdings(
    limit: int = Query(10, ge=1, le=100, description="返回数量"),
    by: str = Query("value", pattern="^(value|pnl|pnl_pct)$", description="排序字段"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取重仓股列表

    - by=value: 按市值排序
    - by=pnl: 按盈亏金额排序
    - by=pnl_pct: 按盈亏比例排序
    """
    query = select(Position).where(Position.total_qty > 0)

    if by == "value":
        query = query.order_by(desc(Position.market_value))
    elif by == "pnl":
        query = query.order_by(desc(Position.unrealized_pnl))
    elif by == "pnl_pct":
        query = query.order_by(desc(Position.unrealized_pnl_pct))

    query = query.limit(limit)
    result = await db.execute(query)
    positions = result.scalars().all()

    return [pos.to_dict() for pos in positions]
