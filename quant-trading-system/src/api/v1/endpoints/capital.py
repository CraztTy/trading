"""
资金管理API端点

提供出入金、资金流水、资金统计等功能
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.finance.capital_manager import CapitalManager, CapitalOperationResult, CapitalSnapshot
from src.models.base import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.exceptions import (
    ValidationError,
    NotFoundError,
    AccountNotFoundError,
    InvalidAmountError,
    FlowTypeError,
    BusinessLogicError
)

router = APIRouter()


class DepositRequest(BaseModel):
    """入金请求"""
    amount: Decimal = Field(..., gt=0, description="入金金额")
    remark: str = Field(default="", description="备注")


class WithdrawRequest(BaseModel):
    """出金请求"""
    amount: Decimal = Field(..., gt=0, description="出金金额")
    remark: str = Field(default="", description="备注")


class TransferRequest(BaseModel):
    """转账请求"""
    to_account_id: int = Field(..., description="转入账户ID")
    amount: Decimal = Field(..., gt=0, description="转账金额")
    remark: str = Field(default="", description="备注")


class CapitalOperationResponse(BaseModel):
    """资金操作响应"""
    success: bool
    operation_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    flow_id: Optional[int] = None
    error_msg: Optional[str] = None


class CapitalSnapshotResponse(BaseModel):
    """资金快照响应"""
    account_id: int
    total_balance: Decimal
    available: Decimal
    frozen: Decimal
    position_value: Decimal
    net_asset: Decimal
    timestamp: datetime


class BalanceFlowItem(BaseModel):
    """资金流水项"""
    id: int
    account_id: int
    flow_type: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    description: str
    created_at: datetime


class FlowStatisticsResponse(BaseModel):
    """流水统计响应"""
    total_deposit: Decimal
    total_withdraw: Decimal
    total_buy: Decimal
    total_sell: Decimal
    total_fee: Decimal
    net_flow: Decimal


@router.post("/{account_id}/deposit", response_model=CapitalOperationResponse)
async def deposit(
    account_id: int,
    request: DepositRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    入金

    Args:
        account_id: 账户ID
        request: 入金请求

    Returns:
        CapitalOperationResponse: 操作结果
    """
    manager = CapitalManager(session)
    result = await manager.deposit(
        account_id=account_id,
        amount=request.amount,
        remark=request.remark
    )

    if not result.success:
        # 根据错误信息判断具体异常类型
        error_msg = result.error_msg or ""
        if "账户不存在" in error_msg:
            raise AccountNotFoundError(account_id=account_id)
        elif "金额无效" in error_msg:
            raise InvalidAmountError(
                amount=request.amount,
                reason="Amount must be greater than 0 with at most 2 decimal places"
            )
        elif "账户状态异常" in error_msg:
            raise BusinessLogicError(
                message=f"Account status is not active: {account_id}",
                details={"account_id": account_id}
            )
        else:
            raise BusinessLogicError(message=error_msg)

    return CapitalOperationResponse(
        success=result.success,
        operation_type=result.operation_type.value,
        amount=result.amount,
        balance_before=result.balance_before,
        balance_after=result.balance_after,
        flow_id=result.flow_id
    )


@router.post("/{account_id}/withdraw", response_model=CapitalOperationResponse)
async def withdraw(
    account_id: int,
    request: WithdrawRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    出金

    Args:
        account_id: 账户ID
        request: 出金请求

    Returns:
        CapitalOperationResponse: 操作结果
    """
    manager = CapitalManager(session)
    result = await manager.withdraw(
        account_id=account_id,
        amount=request.amount,
        remark=request.remark
    )

    if not result.success:
        error_msg = result.error_msg or ""
        if "账户不存在" in error_msg:
            raise AccountNotFoundError(account_id=account_id)
        elif "可用资金不足" in error_msg:
            # 从错误消息中提取金额信息
            raise BusinessLogicError(
                message=error_msg,
                details={"account_id": account_id, "requested_amount": float(request.amount)}
            )
        elif "金额无效" in error_msg:
            raise InvalidAmountError(amount=request.amount)
        else:
            raise BusinessLogicError(message=error_msg)

    return CapitalOperationResponse(
        success=result.success,
        operation_type=result.operation_type.value,
        amount=result.amount,
        balance_before=result.balance_before,
        balance_after=result.balance_after,
        flow_id=result.flow_id
    )


@router.post("/{account_id}/transfer", response_model=CapitalOperationResponse)
async def transfer(
    account_id: int,
    request: TransferRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    账户间转账

    Args:
        account_id: 转出账户ID
        request: 转账请求

    Returns:
        CapitalOperationResponse: 操作结果
    """
    manager = CapitalManager(session)
    result = await manager.transfer(
        from_account_id=account_id,
        to_account_id=request.to_account_id,
        amount=request.amount,
        remark=request.remark
    )

    if not result.success:
        error_msg = result.error_msg or ""
        if "转出账户不存在" in error_msg:
            raise AccountNotFoundError(account_id=account_id)
        elif "转入账户不存在" in error_msg:
            raise NotFoundError("Account", str(request.to_account_id))
        elif "转出账户余额不足" in error_msg:
            raise BusinessLogicError(
                message=f"Insufficient balance in source account: {account_id}",
                details={
                    "from_account_id": account_id,
                    "to_account_id": request.to_account_id,
                    "amount": float(request.amount)
                }
            )
        elif "金额无效" in error_msg:
            raise InvalidAmountError(amount=request.amount)
        else:
            raise BusinessLogicError(message=error_msg)

    return CapitalOperationResponse(
        success=result.success,
        operation_type=result.operation_type.value,
        amount=result.amount,
        balance_before=result.balance_before,
        balance_after=result.balance_after,
        flow_id=result.flow_id
    )


@router.get("/{account_id}/snapshot", response_model=CapitalSnapshotResponse)
async def get_capital_snapshot(
    account_id: int,
    session: AsyncSession = Depends(get_db)
):
    """
    获取资金快照

    Args:
        account_id: 账户ID

    Returns:
        CapitalSnapshotResponse: 资金快照
    """
    manager = CapitalManager(session)

    try:
        snapshot = await manager.create_snapshot(account_id)
    except Exception as e:
        if "账户不存在" in str(e) or "NoneType" in str(e):
            raise AccountNotFoundError(account_id=account_id)
        raise

    return CapitalSnapshotResponse(
        account_id=snapshot.account_id,
        total_balance=snapshot.total_balance,
        available=snapshot.available,
        frozen=snapshot.frozen,
        position_value=snapshot.position_value,
        net_asset=snapshot.net_asset,
        timestamp=snapshot.timestamp
    )


@router.get("/{account_id}/flows", response_model=List[BalanceFlowItem])
async def get_balance_flows(
    account_id: int,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    flow_type: Optional[str] = Query(None, description="流水类型"),
    limit: int = Query(100, ge=1, le=1000, description="数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    session: AsyncSession = Depends(get_db)
):
    """
    获取资金流水

    Args:
        account_id: 账户ID
        start_date: 开始日期
        end_date: 结束日期
        flow_type: 流水类型过滤
        limit: 数量限制
        offset: 偏移量

    Returns:
        List[BalanceFlowItem]: 流水列表
    """
    from src.models.enums import FlowType

    manager = CapitalManager(session)

    # 转换flow_type
    flow_type_enum = None
    if flow_type:
        try:
            flow_type_enum = FlowType(flow_type)
        except ValueError:
            raise FlowTypeError(flow_type=flow_type)

    flows = await manager.get_balance_flows(
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        flow_type=flow_type_enum,
        limit=limit,
        offset=offset
    )

    return [
        BalanceFlowItem(
            id=flow.id,
            account_id=flow.account_id,
            flow_type=flow.flow_type.value,
            amount=flow.amount,
            balance_before=flow.balance_before,
            balance_after=flow.balance_after,
            description=flow.description,
            created_at=flow.created_at
        )
        for flow in flows
    ]


@router.get("/{account_id}/statistics", response_model=FlowStatisticsResponse)
async def get_flow_statistics(
    account_id: int,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    session: AsyncSession = Depends(get_db)
):
    """
    获取流水统计

    Args:
        account_id: 账户ID
        start_date: 开始日期，默认为30天前
        end_date: 结束日期，默认为今天

    Returns:
        FlowStatisticsResponse: 统计结果
    """
    manager = CapitalManager(session)

    # 设置默认日期范围
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    stats = await manager.get_flow_statistics(
        account_id=account_id,
        start_date=start_date,
        end_date=end_date
    )

    return FlowStatisticsResponse(
        total_deposit=stats.total_deposit,
        total_withdraw=stats.total_withdraw,
        total_buy=stats.total_buy,
        total_sell=stats.total_sell,
        total_fee=stats.total_fee,
        net_flow=stats.net_flow
    )
