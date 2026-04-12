"""
回测API

提供回测任务的创建、查询、结果获取等功能
"""
import asyncio
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator

from src.backtest import BacktestEngine, BacktestConfig
from src.backtest.engine import BacktestResult
from src.models.base import get_db
from src.api.v1.exceptions import NotFoundError, ValidationError
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()

# ============ 请求/响应模型 ============


class CreateBacktestRequest(BaseModel):
    """创建回测请求"""
    symbols: List[str] = Field(..., min_items=1, max_items=100, description="股票代码列表")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    strategy_id: str = Field(..., min_length=1, max_length=64, description="策略ID")
    initial_capital: Decimal = Field(default=Decimal("1000000"), gt=0, description="初始资金")
    params: Optional[Dict[str, Any]] = Field(default=None, description="策略参数")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """验证日期范围"""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('结束日期必须晚于开始日期')
        return v

    @validator('symbols')
    def validate_symbols(cls, v):
        """验证股票代码格式"""
        if not v:
            raise ValueError('股票代码列表不能为空')
        for symbol in v:
            if not symbol or len(symbol) < 6:
                raise ValueError(f'无效的股票代码: {symbol}')
        return v


class BacktestTaskResponse(BaseModel):
    """回测任务响应"""
    task_id: str
    status: str  # pending/running/completed/failed
    progress: int
    symbols: List[str]
    start_date: date
    end_date: date
    strategy_id: str
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class BacktestTaskSummary(BaseModel):
    """回测任务摘要"""
    task_id: str
    status: str
    progress: int
    symbols_count: int
    start_date: date
    end_date: date
    strategy_id: str
    created_at: str

    class Config:
        from_attributes = True


class TradeRecordResponse(BaseModel):
    """交易记录响应"""
    timestamp: str
    symbol: str
    side: str
    qty: int
    price: float
    amount: float
    commission: float
    pnl: Optional[float] = None


class DailyValueResponse(BaseModel):
    """每日市值响应"""
    date: str
    cash: float
    market_value: float
    total_value: float


class MonthlyReturnResponse(BaseModel):
    """月度收益响应"""
    month: str
    return_pct: float


class BacktestSummary(BaseModel):
    """回测摘要"""
    total_return: float
    total_return_pct: str
    total_trades: int
    win_rate: str
    max_drawdown: str
    sharpe_ratio: float
    annualized_return: str


class BacktestResultsResponse(BaseModel):
    """回测结果响应"""
    summary: BacktestSummary
    trades: List[TradeRecordResponse]
    daily_values: List[DailyValueResponse]
    monthly_returns: List[MonthlyReturnResponse]


# ============ 内存任务存储（临时，后续替换为数据库） ============

# TODO: 迁移到BacktestService和数据库
_backtest_tasks: Dict[str, Dict] = {}


# ============ 后台任务 ============


async def _run_backtest_task(task_id: str, request: CreateBacktestRequest):
    """
    后台执行回测任务

    Args:
        task_id: 任务ID
        request: 回测请求
    """
    task = _backtest_tasks.get(task_id)
    if not task:
        logger.error(f"回测任务不存在: {task_id}")
        return

    try:
        # 更新状态为运行中
        task['status'] = 'running'
        task['progress'] = 0
        logger.info(f"开始执行回测任务: {task_id}")

        # 加载策略
        strategy = await _load_strategy(request.strategy_id, request.params)
        if not strategy:
            raise ValueError(f"策略加载失败: {request.strategy_id}")

        # 创建回测配置
        config = BacktestConfig(
            start_date=datetime.combine(request.start_date, datetime.min.time()),
            end_date=datetime.combine(request.end_date, datetime.min.time()),
            initial_capital=request.initial_capital,
            commission_rate=0.0003,
            min_commission=5.0,
            stamp_tax_rate=0.001
        )

        # 执行回测
        engine = BacktestEngine()

        # 使用进度回调更新任务进度
        total_days = (request.end_date - request.start_date).days
        processed_days = 0

        def on_progress(current_date: datetime):
            nonlocal processed_days
            processed_days += 1
            progress = min(int((processed_days / total_days) * 100), 99)
            task['progress'] = progress

        # 执行回测
        result = await engine.run(strategy, config)

        # 保存结果
        task['results'] = _convert_result_to_dict(result)
        task['status'] = 'completed'
        task['progress'] = 100
        task['completed_at'] = datetime.now().isoformat()

        logger.info(
            f"回测任务完成: {task_id}, "
            f"总收益: {result.metrics.total_return:.2%}, "
            f"夏普比率: {result.metrics.sharpe_ratio:.2f}"
        )

    except Exception as e:
        logger.error(f"回测任务失败: {task_id}, 错误: {e}")
        task['status'] = 'failed'
        task['error_message'] = str(e)
        task['completed_at'] = datetime.now().isoformat()


async def _load_strategy(strategy_id: str, params: Optional[Dict[str, Any]]) -> Any:
    """
    加载策略实例

    Args:
        strategy_id: 策略ID
        params: 策略参数

    Returns:
        StrategyBase: 策略实例
    """
    # TODO: 从数据库或策略注册表加载策略
    # 临时实现：根据strategy_id创建示例策略
    from src.strategy.examples.ma_cross import MACrossStrategy

    # 合并默认参数和传入参数
    strategy_params = params or {}

    # 创建策略实例
    strategy = MACrossStrategy(
        strategy_id=strategy_id,
        name=f"Strategy_{strategy_id}",
        symbols=[],  # 将在运行时设置
        params=strategy_params
    )

    return strategy


def _convert_result_to_dict(result: BacktestResult) -> Dict[str, Any]:
    """
    将回测结果转换为字典

    Args:
        result: 回测结果

    Returns:
        dict: 结果字典
    """
    metrics = result.metrics

    # 计算月度收益
    monthly_returns = _calc_monthly_returns(result.daily_portfolios)

    return {
        'summary': {
            'total_return': float(metrics.total_return),
            'total_return_pct': f"{metrics.total_return * 100:.2f}%",
            'total_trades': metrics.total_trades,
            'win_rate': f"{metrics.win_rate * 100:.2f}%",
            'max_drawdown': f"{metrics.max_drawdown * 100:.2f}%",
            'sharpe_ratio': float(metrics.sharpe_ratio),
            'annualized_return': f"{metrics.annual_return * 100:.2f}%",
        },
        'trades': [
            {
                'timestamp': t.timestamp.isoformat(),
                'symbol': t.symbol,
                'side': t.side,
                'qty': t.qty,
                'price': float(t.price),
                'amount': float(t.amount),
                'commission': float(t.commission),
                'pnl': float(t.pnl) if t.pnl else None
            }
            for t in result.trades
        ],
        'daily_values': [
            {
                'date': p.date.strftime('%Y-%m-%d'),
                'cash': float(p.cash),
                'market_value': float(p.market_value),
                'total_value': float(p.total_value)
            }
            for p in result.daily_portfolios
        ],
        'monthly_returns': monthly_returns
    }


def _calc_monthly_returns(daily_portfolios: List[Any]) -> List[Dict[str, Any]]:
    """
    计算月度收益

    Args:
        daily_portfolios: 每日持仓记录

    Returns:
        List[dict]: 月度收益列表
    """
    if not daily_portfolios:
        return []

    # 按月份分组
    monthly_data: Dict[str, List[float]] = {}

    for p in daily_portfolios:
        month_key = p.date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = []
        monthly_data[month_key].append(float(p.total_value))

    # 计算每月收益
    monthly_returns = []
    prev_month_end_value = None

    for month in sorted(monthly_data.keys()):
        values = monthly_data[month]
        if not values:
            continue

        month_start = values[0]
        month_end = values[-1]

        if prev_month_end_value:
            # 使用上月末值计算收益
            return_pct = (month_end - prev_month_end_value) / prev_month_end_value
        else:
            # 第一个月
            return_pct = (month_end - month_start) / month_start if month_start > 0 else 0

        monthly_returns.append({
            'month': month,
            'return_pct': return_pct * 100  # 转换为百分比
        })

        prev_month_end_value = month_end

    return monthly_returns


# ============ API端点 ============


@router.post("/", response_model=BacktestTaskResponse, status_code=201)
async def create_backtest(
    request: CreateBacktestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    创建并启动回测任务

    请求示例:
    ```json
    {
        "symbols": ["000001.SZ", "600036.SH"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "strategy_id": "strategy_01",
        "initial_capital": 1000000,
        "params": {"period": 20}
    }
    ```

    返回任务ID，回测在后台异步执行
    """
    try:
        # 生成任务ID
        task_id = f"bt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 创建任务记录
        task = {
            'task_id': task_id,
            'status': 'pending',
            'progress': 0,
            'symbols': request.symbols,
            'start_date': request.start_date,
            'end_date': request.end_date,
            'strategy_id': request.strategy_id,
            'initial_capital': request.initial_capital,
            'params': request.params,
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'error_message': None,
            'results': None
        }

        _backtest_tasks[task_id] = task

        # 启动后台任务
        background_tasks.add_task(_run_backtest_task, task_id, request)

        logger.info(
            f"创建回测任务: {task_id}",
            symbols=request.symbols,
            strategy_id=request.strategy_id
        )

        return BacktestTaskResponse(
            task_id=task_id,
            status='pending',
            progress=0,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            strategy_id=request.strategy_id,
            created_at=task['created_at']
        )

    except Exception as e:
        logger.error(f"创建回测任务失败: {e}")
        raise ValidationError(message=f"创建回测任务失败: {str(e)}")


@router.get("/{task_id}", response_model=BacktestTaskResponse)
async def get_backtest_status(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    查询回测任务状态

    返回任务的当前状态、进度和基本信息
    """
    task = _backtest_tasks.get(task_id)

    if not task:
        raise NotFoundError(resource_type="BacktestTask", resource_id=task_id)

    return BacktestTaskResponse(
        task_id=task['task_id'],
        status=task['status'],
        progress=task['progress'],
        symbols=task['symbols'],
        start_date=task['start_date'],
        end_date=task['end_date'],
        strategy_id=task['strategy_id'],
        created_at=task['created_at'],
        completed_at=task.get('completed_at'),
        error_message=task.get('error_message')
    )


@router.get("/{task_id}/results", response_model=BacktestResultsResponse)
async def get_backtest_results(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取回测结果

    仅在任务状态为 completed 时返回完整结果
    """
    task = _backtest_tasks.get(task_id)

    if not task:
        raise NotFoundError(resource_type="BacktestTask", resource_id=task_id)

    if task['status'] != 'completed':
        raise ValidationError(
            message=f"回测尚未完成，当前状态: {task['status']}",
            field="status"
        )

    results = task.get('results')
    if not results:
        raise ValidationError(message="回测结果不存在")

    summary_data = results['summary']

    return BacktestResultsResponse(
        summary=BacktestSummary(
            total_return=summary_data['total_return'],
            total_return_pct=summary_data['total_return_pct'],
            total_trades=summary_data['total_trades'],
            win_rate=summary_data['win_rate'],
            max_drawdown=summary_data['max_drawdown'],
            sharpe_ratio=summary_data['sharpe_ratio'],
            annualized_return=summary_data['annualized_return']
        ),
        trades=[
            TradeRecordResponse(**t) for t in results['trades']
        ],
        daily_values=[
            DailyValueResponse(**d) for d in results['daily_values']
        ],
        monthly_returns=[
            MonthlyReturnResponse(**m) for m in results['monthly_returns']
        ]
    )


@router.get("/", response_model=List[BacktestTaskSummary])
async def list_backtest_tasks(
    status: Optional[str] = Query(None, description="状态过滤 (pending/running/completed/failed)"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db)
):
    """
    查询回测任务列表

    支持按状态过滤和分页
    """
    tasks = list(_backtest_tasks.values())

    # 状态过滤
    if status:
        tasks = [t for t in tasks if t['status'] == status]

    # 按创建时间倒序排序
    tasks.sort(key=lambda x: x['created_at'], reverse=True)

    # 分页
    total = len(tasks)
    tasks = tasks[offset:offset + limit]

    return [
        BacktestTaskSummary(
            task_id=t['task_id'],
            status=t['status'],
            progress=t['progress'],
            symbols_count=len(t['symbols']),
            start_date=t['start_date'],
            end_date=t['end_date'],
            strategy_id=t['strategy_id'],
            created_at=t['created_at']
        )
        for t in tasks
    ]


@router.delete("/{task_id}")
async def delete_backtest_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    删除回测任务

    删除任务及其结果数据
    """
    if task_id not in _backtest_tasks:
        raise NotFoundError(resource_type="BacktestTask", resource_id=task_id)

    # 检查任务是否正在运行
    task = _backtest_tasks[task_id]
    if task['status'] == 'running':
        raise ValidationError(
            message="无法删除正在运行的任务",
            field="status"
        )

    del _backtest_tasks[task_id]

    logger.info(f"删除回测任务: {task_id}")

    return {
        "success": True,
        "message": f"任务 {task_id} 已删除"
    }
