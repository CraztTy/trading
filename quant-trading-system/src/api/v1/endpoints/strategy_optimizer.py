"""
策略参数优化API

提供策略参数优化功能，支持网格搜索和遗传算法
"""
import asyncio
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field, validator

from src.strategy.optimizer import GridSearchOptimizer, GeneticOptimizer, ParameterSpace
from src.api.v1.exceptions import NotFoundError, ValidationError
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()

# ============ 请求/响应模型 ============


class ParameterSpaceDefinition(BaseModel):
    """参数空间定义"""
    name: str = Field(..., description="参数名称")
    param_type: Literal["int", "float", "choice"] = Field(..., description="参数类型")
    min_value: Optional[float] = Field(None, description="最小值（int/float类型）")
    max_value: Optional[float] = Field(None, description="最大值（int/float类型）")
    step: Optional[float] = Field(None, description="步长（int/float类型）")
    choices: Optional[List[Any]] = Field(None, description="可选值列表（choice类型）")
    default: Optional[Any] = Field(None, description="默认值")


class CreateOptimizationRequest(BaseModel):
    """创建优化任务请求"""
    strategy_id: str = Field(..., description="策略ID")
    symbols: List[str] = Field(..., min_items=1, max_items=100, description="股票代码列表")
    start_date: date = Field(..., description="回测开始日期")
    end_date: date = Field(..., description="回测结束日期")
    parameter_spaces: List[ParameterSpaceDefinition] = Field(..., min_items=1, description="参数空间定义")
    optimizer_type: Literal["grid_search", "genetic"] = Field("grid_search", description="优化器类型")
    objective_metric: str = Field("sharpe_ratio", description="优化目标指标")
    maximize: bool = Field(True, description="是否最大化目标")
    max_iterations: Optional[int] = Field(None, description="最大迭代次数")
    initial_capital: Decimal = Field(default=Decimal("1000000"), gt=0, description="初始资金")

    # 遗传算法特有参数
    population_size: int = Field(20, ge=5, le=100, description="种群大小（遗传算法）")
    generations: int = Field(10, ge=1, le=100, description="迭代代数（遗传算法）")
    crossover_rate: float = Field(0.8, ge=0.0, le=1.0, description="交叉概率（遗传算法）")
    mutation_rate: float = Field(0.1, ge=0.0, le=1.0, description="变异概率（遗传算法）")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """验证日期范围"""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('结束日期必须晚于开始日期')
        return v


class OptimizationResultItem(BaseModel):
    """优化结果项"""
    rank: int = Field(..., description="排名")
    parameters: Dict[str, Any] = Field(..., description="参数组合")
    metrics: Dict[str, float] = Field(..., description="性能指标")


class OptimizationTaskResponse(BaseModel):
    """优化任务响应"""
    task_id: str
    status: str  # pending/running/completed/failed
    optimizer_type: str
    strategy_id: str
    objective_metric: str
    progress: int
    total_iterations: int
    current_iteration: int
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class OptimizationResultsResponse(BaseModel):
    """优化结果响应"""
    task_id: str
    strategy_id: str
    optimizer_type: str
    objective_metric: str
    maximize: bool
    total_results: int
    best_result: Optional[OptimizationResultItem] = None
    top_results: List[OptimizationResultItem]
    duration_seconds: float


# ============ 内存任务存储（临时） ============

_optimization_tasks: Dict[str, Dict] = {}


# ============ 评估函数 ============

async def evaluate_strategy_params(
    params: Dict[str, Any],
    strategy_id: str,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    initial_capital: Decimal
) -> Dict[str, float]:
    """
    评估策略参数

    Args:
        params: 策略参数
        strategy_id: 策略ID
        symbols: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金

    Returns:
        Dict[str, float]: 性能指标
    """
    from src.backtest.engine import BacktestEngine, BacktestConfig
    from src.strategy.examples.ma_cross import MACrossStrategy

    try:
        # 创建策略实例
        strategy = MACrossStrategy(
            strategy_id=f"opt_{strategy_id}_{uuid.uuid4().hex[:8]}",
            name=f"Optimization_{strategy_id}",
            symbols=symbols,
            params=params
        )

        # 创建回测配置
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission_rate=0.0003,
            min_commission=5.0,
            stamp_tax_rate=0.001
        )

        # 执行回测
        engine = BacktestEngine()
        result = await engine.run(strategy, config)
        metrics = result.metrics

        return {
            "sharpe_ratio": float(metrics.sharpe_ratio) if metrics.sharpe_ratio else 0.0,
            "total_return": float(metrics.total_return) if metrics.total_return else 0.0,
            "annual_return": float(metrics.annual_return) if metrics.annual_return else 0.0,
            "max_drawdown": float(metrics.max_drawdown) if metrics.max_drawdown else 0.0,
            "win_rate": float(metrics.win_rate) if metrics.win_rate else 0.0,
            "profit_factor": float(metrics.profit_factor) if metrics.profit_factor else 0.0,
            "sortino_ratio": float(metrics.sortino_ratio) if metrics.sortino_ratio else 0.0,
            "calmar_ratio": float(metrics.calmar_ratio) if metrics.calmar_ratio else 0.0,
            "total_trades": int(metrics.total_trades) if metrics.total_trades else 0,
        }

    except Exception as e:
        logger.error(f"评估参数失败: {e}, params={params}")
        # 返回极差的指标
        return {
            "sharpe_ratio": float('-inf'),
            "total_return": float('-inf'),
            "annual_return": float('-inf'),
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "sortino_ratio": float('-inf'),
            "calmar_ratio": float('-inf'),
            "total_trades": 0,
        }


# ============ 后台任务 ============

async def _run_optimization_task(task_id: str, request: CreateOptimizationRequest):
    """
    后台执行优化任务

    Args:
        task_id: 任务ID
        request: 优化请求
    """
    task = _optimization_tasks.get(task_id)
    if not task:
        logger.error(f"优化任务不存在: {task_id}")
        return

    try:
        # 更新状态为运行中
        task['status'] = 'running'
        task['progress'] = 0
        logger.info(f"开始执行优化任务: {task_id}")

        # 构建参数空间
        param_spaces = {}
        for param_def in request.parameter_spaces:
            param_spaces[param_def.name] = ParameterSpace(
                name=param_def.name,
                param_type=param_def.param_type,
                min_value=param_def.min_value,
                max_value=param_def.max_value,
                step=param_def.step,
                choices=param_def.choices,
                default=param_def.default
            )

        # 构建评估函数
        async def evaluation_func(params: Dict[str, Any]) -> Dict[str, float]:
            return await evaluate_strategy_params(
                params=params,
                strategy_id=request.strategy_id,
                symbols=request.symbols,
                start_date=datetime.combine(request.start_date, datetime.min.time()),
                end_date=datetime.combine(request.end_date, datetime.min.time()),
                initial_capital=request.initial_capital
            )

        # 创建优化器
        if request.optimizer_type == "grid_search":
            optimizer = GridSearchOptimizer(
                parameter_spaces=param_spaces,
                evaluation_func=evaluation_func,
                objective_metric=request.objective_metric,
                maximize=request.maximize
            )
        else:  # genetic
            optimizer = GeneticOptimizer(
                parameter_spaces=param_spaces,
                evaluation_func=evaluation_func,
                objective_metric=request.objective_metric,
                maximize=request.maximize,
                population_size=request.population_size,
                generations=request.generations,
                crossover_rate=request.crossover_rate,
                mutation_rate=request.mutation_rate
            )

        # 执行优化
        start_time = datetime.now()
        results = await optimizer.optimize(max_iterations=request.max_iterations)
        duration = (datetime.now() - start_time).total_seconds()

        # 保存结果
        task['results'] = {
            'optimizer_type': request.optimizer_type,
            'strategy_id': request.strategy_id,
            'objective_metric': request.objective_metric,
            'maximize': request.maximize,
            'total_results': len(results),
            'best_result': _convert_result_to_dict(results[0]) if results else None,
            'top_results': [_convert_result_to_dict(r) for r in results[:20]],
            'duration_seconds': duration
        }
        task['status'] = 'completed'
        task['progress'] = 100
        task['completed_at'] = datetime.now().isoformat()

        logger.info(
            f"优化任务完成: {task_id}, "
            f"共 {len(results)} 个结果, "
            f"耗时 {duration:.1f}秒"
        )

    except Exception as e:
        logger.error(f"优化任务失败: {task_id}, 错误: {e}")
        task['status'] = 'failed'
        task['error_message'] = str(e)
        task['completed_at'] = datetime.now().isoformat()


def _convert_result_to_dict(result) -> Dict[str, Any]:
    """将优化结果转换为字典"""
    return {
        'rank': result.rank,
        'parameters': result.parameters,
        'metrics': result.metrics
    }


# ============ API端点 ============

@router.post("/", response_model=OptimizationTaskResponse, status_code=201)
async def create_optimization(
    request: CreateOptimizationRequest,
    background_tasks: BackgroundTasks
):
    """
    创建并启动策略参数优化任务

    请求示例:
    ```json
    {
        "strategy_id": "ma_cross",
        "symbols": ["000001.SZ", "600036.SH"],
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "parameter_spaces": [
            {"name": "fast_period", "param_type": "int", "min_value": 5, "max_value": 20, "step": 5},
            {"name": "slow_period", "param_type": "int", "min_value": 30, "max_value": 60, "step": 10}
        ],
        "optimizer_type": "grid_search",
        "objective_metric": "sharpe_ratio",
        "maximize": true
    }
    ```

    返回任务ID，优化在后台异步执行
    """
    try:
        # 生成任务ID
        task_id = f"opt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 估算总迭代次数
        total_iterations = 0
        if request.optimizer_type == "grid_search":
            total = 1
            for param in request.parameter_spaces:
                if param.param_type == "int":
                    count = len(range(int(param.min_value), int(param.max_value) + 1, int(param.step or 1)))
                    total *= count
                elif param.param_type == "float":
                    step = param.step or 0.01
                    count = int((param.max_value - param.min_value) / step) + 1
                    total *= count
                elif param.param_type == "choice":
                    total *= len(param.choices) if param.choices else 1
            total_iterations = min(total, request.max_iterations or total)
        else:  # genetic
            total_iterations = request.population_size * request.generations

        # 创建任务记录
        task = {
            'task_id': task_id,
            'status': 'pending',
            'optimizer_type': request.optimizer_type,
            'strategy_id': request.strategy_id,
            'objective_metric': request.objective_metric,
            'progress': 0,
            'total_iterations': total_iterations,
            'current_iteration': 0,
            'created_at': datetime.now().isoformat(),
            'completed_at': None,
            'error_message': None,
            'results': None
        }

        _optimization_tasks[task_id] = task

        # 启动后台任务
        background_tasks.add_task(_run_optimization_task, task_id, request)

        logger.info(
            f"创建优化任务: {task_id}",
            strategy_id=request.strategy_id,
            optimizer_type=request.optimizer_type
        )

        return OptimizationTaskResponse(
            task_id=task_id,
            status='pending',
            optimizer_type=request.optimizer_type,
            strategy_id=request.strategy_id,
            objective_metric=request.objective_metric,
            progress=0,
            total_iterations=total_iterations,
            current_iteration=0,
            created_at=task['created_at']
        )

    except Exception as e:
        logger.error(f"创建优化任务失败: {e}")
        raise ValidationError(message=f"创建优化任务失败: {str(e)}")


@router.get("/{task_id}", response_model=OptimizationTaskResponse)
async def get_optimization_status(task_id: str):
    """
    查询优化任务状态

    返回任务的当前状态、进度和基本信息
    """
    task = _optimization_tasks.get(task_id)

    if not task:
        raise NotFoundError(resource_type="OptimizationTask", resource_id=task_id)

    return OptimizationTaskResponse(
        task_id=task['task_id'],
        status=task['status'],
        optimizer_type=task['optimizer_type'],
        strategy_id=task['strategy_id'],
        objective_metric=task['objective_metric'],
        progress=task['progress'],
        total_iterations=task['total_iterations'],
        current_iteration=task.get('current_iteration', 0),
        created_at=task['created_at'],
        completed_at=task.get('completed_at'),
        error_message=task.get('error_message')
    )


@router.get("/{task_id}/results", response_model=OptimizationResultsResponse)
async def get_optimization_results(task_id: str):
    """
    获取优化结果

    仅在任务状态为 completed 时返回完整结果
    """
    task = _optimization_tasks.get(task_id)

    if not task:
        raise NotFoundError(resource_type="OptimizationTask", resource_id=task_id)

    if task['status'] != 'completed':
        raise ValidationError(
            message=f"优化尚未完成，当前状态: {task['status']}",
            field="status"
        )

    results = task.get('results')
    if not results:
        raise ValidationError(message="优化结果不存在")

    best_result = None
    if results.get('best_result'):
        best = results['best_result']
        best_result = OptimizationResultItem(
            rank=best['rank'],
            parameters=best['parameters'],
            metrics=best['metrics']
        )

    return OptimizationResultsResponse(
        task_id=task_id,
        strategy_id=results['strategy_id'],
        optimizer_type=results['optimizer_type'],
        objective_metric=results['objective_metric'],
        maximize=results['maximize'],
        total_results=results['total_results'],
        best_result=best_result,
        top_results=[
            OptimizationResultItem(
                rank=r['rank'],
                parameters=r['parameters'],
                metrics=r['metrics']
            )
            for r in results['top_results']
        ],
        duration_seconds=results['duration_seconds']
    )


@router.get("/")
async def list_optimization_tasks(
    status: Optional[str] = Query(None, description="状态过滤 (pending/running/completed/failed)"),
    optimizer_type: Optional[str] = Query(None, description="优化器类型过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    查询优化任务列表

    支持按状态、优化器类型过滤和分页
    """
    tasks = list(_optimization_tasks.values())

    # 状态过滤
    if status:
        tasks = [t for t in tasks if t['status'] == status]

    # 优化器类型过滤
    if optimizer_type:
        tasks = [t for t in tasks if t['optimizer_type'] == optimizer_type]

    # 按创建时间倒序排序
    tasks.sort(key=lambda x: x['created_at'], reverse=True)

    # 分页
    total = len(tasks)
    tasks = tasks[offset:offset + limit]

    return {
        "tasks": [
            {
                "task_id": t['task_id'],
                "status": t['status'],
                "optimizer_type": t['optimizer_type'],
                "strategy_id": t['strategy_id'],
                "objective_metric": t['objective_metric'],
                "progress": t['progress'],
                "total_iterations": t['total_iterations'],
                "created_at": t['created_at'],
                "completed_at": t.get('completed_at')
            }
            for t in tasks
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.delete("/{task_id}")
async def delete_optimization_task(task_id: str):
    """
    删除优化任务

    删除任务及其结果数据
    """
    if task_id not in _optimization_tasks:
        raise NotFoundError(resource_type="OptimizationTask", resource_id=task_id)

    # 检查任务是否正在运行
    task = _optimization_tasks[task_id]
    if task['status'] == 'running':
        raise ValidationError(
            message="无法删除正在运行的任务",
            field="status"
        )

    del _optimization_tasks[task_id]

    logger.info(f"删除优化任务: {task_id}")

    return {
        "success": True,
        "message": f"任务 {task_id} 已删除"
    }


@router.post("/{task_id}/cancel")
async def cancel_optimization_task(task_id: str):
    """
    取消优化任务

    将正在运行的任务标记为取消（实际停止需要任务自行检查）
    """
    if task_id not in _optimization_tasks:
        raise NotFoundError(resource_type="OptimizationTask", resource_id=task_id)

    task = _optimization_tasks[task_id]

    if task['status'] not in ['pending', 'running']:
        raise ValidationError(
            message=f"无法取消状态为 {task['status']} 的任务",
            field="status"
        )

    task['status'] = 'cancelled'
    task['completed_at'] = datetime.now().isoformat()

    logger.info(f"取消优化任务: {task_id}")

    return {
        "success": True,
        "message": f"任务 {task_id} 已取消"
    }
