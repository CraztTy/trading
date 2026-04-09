"""
回测API
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Optional, List

router = APIRouter()

# 模拟回测任务存储
backtest_tasks = {}


@router.post("/")
async def run_backtest(request: dict, background_tasks: BackgroundTasks):
    """
    启动回测任务

    请求体示例:
    {
        "symbols": ["000001.SZ", "600036.SH"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "strategies": ["strategy_01"],
        "initial_capital": 1000000
    }
    """
    import uuid
    from datetime import datetime

    task_id = f"bt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    backtest_tasks[task_id] = {
        'id': task_id,
        'status': 'pending',
        'params': request,
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    # 后台执行回测
    background_tasks.add_task(_run_backtest_task, task_id, request)

    return {
        'task_id': task_id,
        'status': 'pending',
        'message': '回测任务已启动'
    }


async def _run_backtest_task(task_id: str, params: dict):
    """后台执行回测"""
    import asyncio

    task = backtest_tasks[task_id]
    task['status'] = 'running'

    try:
        # 模拟回测进度
        for i in range(101):
            await asyncio.sleep(0.1)  # 模拟计算
            task['progress'] = i

        # 模拟回测结果
        task['results'] = {
            'summary': {
                'total_return': 0.15,
                'total_return_pct': '15.00%',
                'total_trades': 42,
                'win_rate': '52.38%',
                'max_drawdown': '8.50%',
                'sharpe_ratio': 1.23
            },
            'trades': [],
            'daily_values': []
        }
        task['status'] = 'completed'

    except Exception as e:
        task['status'] = 'failed'
        task['error'] = str(e)


@router.get("/tasks")
async def list_backtest_tasks(status: Optional[str] = None):
    """获取回测任务列表"""
    tasks = list(backtest_tasks.values())
    if status:
        tasks = [t for t in tasks if t['status'] == status]
    return {'tasks': tasks, 'total': len(tasks)}


@router.get("/tasks/{task_id}")
async def get_backtest_task(task_id: str):
    """获取回测任务详情"""
    if task_id not in backtest_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return backtest_tasks[task_id]


@router.get("/tasks/{task_id}/results")
async def get_backtest_results(task_id: str):
    """获取回测结果"""
    if task_id not in backtest_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = backtest_tasks[task_id]
    if task['status'] != 'completed':
        raise HTTPException(status_code=400, detail="回测尚未完成")

    return task.get('results', {})


@router.delete("/tasks/{task_id}")
async def delete_backtest_task(task_id: str):
    """删除回测任务"""
    if task_id not in backtest_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    del backtest_tasks[task_id]
    return {'message': '任务已删除'}
