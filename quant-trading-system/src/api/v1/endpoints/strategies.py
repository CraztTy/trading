"""
策略管理API

提供策略的完整生命周期管理：
- 策略创建、查询、更新、删除
- 策略状态控制（启动、停止、暂停）
- 策略统计
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.common.database import get_db
from src.services.strategy_service import StrategyService
from src.models.enums import StrategyStatus, RunMode
from src.api.v1.exceptions import NotFoundError, ValidationError
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()


# ============ 请求/响应模型 ============


class CreateStrategyRequest(BaseModel):
    """创建策略请求"""
    name: str = Field(..., min_length=1, max_length=64, description="策略名称")
    description: str = Field(default="", max_length=256, description="策略描述")
    category: Optional[str] = Field(default=None, max_length=32, description="策略分类")
    style: Optional[str] = Field(default=None, max_length=32, description="策略风格")
    params: dict = Field(default_factory=dict, description="策略参数")
    max_position: float = Field(default=0.10, gt=0, le=1, description="最大持仓比例")
    stop_loss: float = Field(default=0.02, ge=0, le=1, description="止损比例")
    take_profit: float = Field(default=0.05, ge=0, le=1, description="止盈比例")
    run_mode: str = Field(default="SIMULATE", description="运行模式: BACKTEST/SIMULATE/LIVE")


class UpdateStrategyRequest(BaseModel):
    """更新策略请求"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    description: Optional[str] = Field(default=None, max_length=256)
    category: Optional[str] = Field(default=None, max_length=32)
    style: Optional[str] = Field(default=None, max_length=32)
    params: Optional[dict] = None
    max_position: Optional[float] = Field(default=None, gt=0, le=1)
    stop_loss: Optional[float] = Field(default=None, ge=0, le=1)
    take_profit: Optional[float] = Field(default=None, ge=0, le=1)


class StrategyResponse(BaseModel):
    """策略响应"""
    id: int
    strategy_id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    style: Optional[str]
    params: dict
    max_position: float
    stop_loss: float
    take_profit: float
    status: str
    run_mode: str
    total_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    account_id: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]
    activated_at: Optional[str]

    class Config:
        from_attributes = True


class StrategySummaryResponse(BaseModel):
    """策略摘要响应"""
    strategy_id: str
    name: str
    description: Optional[str]
    category: Optional[str]
    style: Optional[str]
    status: str
    run_mode: str
    total_trades: int
    win_rate: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    created_at: Optional[str]
    activated_at: Optional[str]


class StrategyListResponse(BaseModel):
    """策略列表响应"""
    strategies: List[StrategyResponse]
    total: int


class StatusUpdateResponse(BaseModel):
    """状态更新响应"""
    success: bool
    strategy_id: str
    status: str
    message: str


class DeleteStrategyResponse(BaseModel):
    """删除策略响应"""
    success: bool
    message: str


# ============ 辅助函数 ============

def _parse_run_mode(mode: str) -> RunMode:
    """解析运行模式"""
    try:
        return RunMode(mode.upper())
    except ValueError:
        raise ValidationError(
            message=f"Invalid run mode: {mode}. Valid values: BACKTEST, SIMULATE, LIVE",
            field="run_mode",
            value=mode
        )


def _parse_status(status: str) -> StrategyStatus:
    """解析策略状态"""
    try:
        return StrategyStatus(status.upper())
    except ValueError:
        raise ValidationError(
            message=f"Invalid status: {status}. Valid values: INACTIVE, ACTIVE, PAUSED, ERROR",
            field="status",
            value=status
        )


# ============ API端点 ============


@router.post("/", response_model=StrategyResponse, status_code=201)
async def create_strategy(
    request: CreateStrategyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    创建策略

    请求示例:
    ```json
    {
        "name": "双均线突破",
        "description": "MA5/MA20交叉策略",
        "category": "趋势",
        "style": "趋势跟踪",
        "params": {"fast_ma": 5, "slow_ma": 20},
        "max_position": 0.2,
        "stop_loss": 0.03,
        "take_profit": 0.08,
        "run_mode": "SIMULATE"
    }
    ```
    """
    service = StrategyService(db)

    run_mode = _parse_run_mode(request.run_mode)

    strategy = await service.create_strategy(
        account_id=1,  # TODO: 从current_user获取
        name=request.name,
        description=request.description,
        category=request.category,
        style=request.style,
        params=request.params,
        max_position=request.max_position,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        run_mode=run_mode
    )

    logger.info(f"API: 创建策略 {strategy.strategy_id}")
    return strategy.to_dict()


@router.get("/", response_model=StrategyListResponse)
async def list_strategies(
    status: Optional[str] = Query(None, description="状态过滤: INACTIVE/ACTIVE/PAUSED/ERROR"),
    category: Optional[str] = Query(None, description="分类过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取策略列表

    支持按状态和分类过滤，支持分页
    """
    service = StrategyService(db)

    # 解析状态过滤
    status_filter = None
    if status:
        status_filter = _parse_status(status)

    strategies = await service.list_strategies(
        account_id=1,  # TODO: 从current_user获取
        status=status_filter,
        category=category,
        limit=limit,
        offset=offset
    )

    return {
        "strategies": [s.to_dict() for s in strategies],
        "total": len(strategies)
    }


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取策略详情
    """
    service = StrategyService(db)
    strategy = await service.get_strategy(strategy_id, account_id=1)

    if not strategy:
        raise NotFoundError("Strategy", strategy_id)

    return strategy.to_dict()


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    request: UpdateStrategyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    更新策略

    只更新提供的字段，未提供的字段保持不变
    """
    service = StrategyService(db)

    # 构建更新字典
    updates = request.dict(exclude_unset=True)

    if not updates:
        raise ValidationError(
            message="No fields to update",
            field="request"
        )

    strategy = await service.update_strategy(strategy_id, 1, updates)

    if not strategy:
        raise NotFoundError("Strategy", strategy_id)

    logger.info(f"API: 更新策略 {strategy_id}")
    return strategy.to_dict()


@router.delete("/{strategy_id}", response_model=DeleteStrategyResponse)
async def delete_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    删除策略

    注意：运行中的策略无法删除，需要先停止
    """
    service = StrategyService(db)
    success = await service.delete_strategy(strategy_id, 1)

    if not success:
        # 检查是否是策略不存在
        strategy = await service.get_strategy(strategy_id)
        if not strategy:
            raise NotFoundError("Strategy", strategy_id)
        else:
            raise ValidationError(
                message="Cannot delete active strategy. Please stop it first.",
                field="status"
            )

    logger.info(f"API: 删除策略 {strategy_id}")
    return {
        "success": True,
        "message": f"Strategy {strategy_id} deleted successfully"
    }


@router.post("/{strategy_id}/start", response_model=StatusUpdateResponse)
async def start_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    启动策略
    """
    service = StrategyService(db)
    strategy = await service.start_strategy(strategy_id, 1)

    if not strategy:
        raise NotFoundError("Strategy", strategy_id)

    logger.info(f"API: 启动策略 {strategy_id}")
    return {
        "success": True,
        "strategy_id": strategy_id,
        "status": strategy.status.value,
        "message": "Strategy started successfully"
    }


@router.post("/{strategy_id}/stop", response_model=StatusUpdateResponse)
async def stop_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    停止策略
    """
    service = StrategyService(db)
    strategy = await service.stop_strategy(strategy_id, 1)

    if not strategy:
        raise NotFoundError("Strategy", strategy_id)

    logger.info(f"API: 停止策略 {strategy_id}")
    return {
        "success": True,
        "strategy_id": strategy_id,
        "status": strategy.status.value,
        "message": "Strategy stopped successfully"
    }


@router.post("/{strategy_id}/pause", response_model=StatusUpdateResponse)
async def pause_strategy(
    strategy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    暂停策略
    """
    service = StrategyService(db)
    strategy = await service.pause_strategy(strategy_id, 1)

    if not strategy:
        raise NotFoundError("Strategy", strategy_id)

    logger.info(f"API: 暂停策略 {strategy_id}")
    return {
        "success": True,
        "strategy_id": strategy_id,
        "status": strategy.status.value,
        "message": "Strategy paused successfully"
    }


@router.get("/{strategy_id}/summary", response_model=StrategySummaryResponse)
async def get_strategy_summary(
    strategy_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取策略摘要（精简信息）
    """
    service = StrategyService(db)
    summary = await service.get_strategy_summary(strategy_id, account_id=1)

    if not summary:
        raise NotFoundError("Strategy", strategy_id)

    return summary


class BacktestRequest(BaseModel):
    """回测请求"""
    start_date: str = Field(..., description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期 (YYYY-MM-DD)")
    symbols: Optional[List[str]] = Field(default=None, description="股票代码列表")
    initial_capital: float = Field(default=100000, gt=0, description="初始资金")
    parameters: Optional[dict] = Field(default=None, description="策略参数")


class BacktestResponse(BaseModel):
    """回测响应"""
    success: bool
    task_id: str
    message: str
    strategy_id: str


@router.post("/{strategy_id}/backtest", response_model=BacktestResponse)
async def run_strategy_backtest(
    strategy_id: str,
    request: BacktestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    执行策略回测

    请求示例:
    ```json
    {
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "symbols": ["000001.SZ", "600036.SH"],
        "initial_capital": 100000,
        "parameters": {"fast_period": 5, "slow_period": 20}
    }
    ```
    """
    service = StrategyService(db)

    try:
        # 构建回测配置
        backtest_config = {
            "start_date": request.start_date,
            "end_date": request.end_date,
            "symbols": request.symbols,
            "initial_capital": request.initial_capital,
            "parameters": request.parameters
        }

        task_id = await service.run_backtest(
            strategy_id=strategy_id,
            backtest_config=backtest_config,
            account_id=1  # TODO: 从current_user获取
        )

        logger.info(f"API: 启动策略回测 {strategy_id}, 任务ID: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "message": "回测任务已启动",
            "strategy_id": strategy_id
        }
    except ValueError as e:
        raise NotFoundError("Strategy", strategy_id)
    except Exception as e:
        raise BusinessLogicError(f"启动回测失败: {str(e)}")
