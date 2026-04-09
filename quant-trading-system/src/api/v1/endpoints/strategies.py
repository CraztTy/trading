"""
策略管理API
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime

router = APIRouter()

# 模拟策略存储（实际应使用数据库）
strategies_db = {
    "strategy_001": {
        "id": "strategy_001",
        "name": "双均线突破",
        "description": "MA5/MA20交叉策略",
        "status": "active",
        "type": "趋势跟踪",
        "params": {"fast_ma": 5, "slow_ma": 20},
        "created_at": "2025-01-01T00:00:00",
        "activated_at": "2025-01-01T00:00:00",
        "performance": {"return": 24.5, "sharpe": 1.92, "max_drawdown": -5.8}
    },
    "strategy_002": {
        "id": "strategy_002",
        "name": "MACD动量",
        "description": "MACD柱状图动量策略",
        "status": "active",
        "type": "动量",
        "params": {"fast": 12, "slow": 26, "signal": 9},
        "created_at": "2025-01-02T00:00:00",
        "activated_at": "2025-01-02T00:00:00",
        "performance": {"return": 18.2, "sharpe": 1.65, "max_drawdown": -7.2}
    },
    "strategy_003": {
        "id": "strategy_003",
        "name": "布林带均值回归",
        "description": "布林带突破回归策略",
        "status": "active",
        "type": "均值回归",
        "params": {"period": 20, "std": 2},
        "created_at": "2025-01-03T00:00:00",
        "activated_at": "2025-01-03T00:00:00",
        "performance": {"return": 31.8, "sharpe": 2.34, "max_drawdown": -4.5}
    }
}


@router.get("/")
async def list_strategies(active_only: bool = True):
    """获取策略列表"""
    strategy_list = list(strategies_db.values())
    if active_only:
        strategy_list = [s for s in strategy_list if s.get('status') == 'active']
    return {
        "strategies": strategy_list,
        "total": len(strategy_list)
    }


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    """获取策略详情"""
    if strategy_id not in strategies_db:
        raise HTTPException(status_code=404, detail="策略不存在")
    return strategies_db[strategy_id]


@router.post("/")
async def create_strategy(strategy: dict):
    """创建新策略"""
    strategy_id = strategy.get('id', f"stg_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    strategy['id'] = strategy_id
    strategy['status'] = 'inactive'
    strategy['created_at'] = datetime.now().isoformat()
    strategies_db[strategy_id] = strategy
    return strategy


@router.put("/{strategy_id}")
async def update_strategy(strategy_id: str, update: dict):
    """更新策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(status_code=404, detail="策略不存在")
    strategies_db[strategy_id].update(update)
    strategies_db[strategy_id]['updated_at'] = datetime.now().isoformat()
    return strategies_db[strategy_id]


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """删除策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(status_code=404, detail="策略不存在")
    del strategies_db[strategy_id]
    return {"message": "策略已删除"}


@router.post("/{strategy_id}/activate")
async def activate_strategy(strategy_id: str):
    """激活策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(status_code=404, detail="策略不存在")
    strategies_db[strategy_id]['status'] = 'active'
    strategies_db[strategy_id]['activated_at'] = datetime.now().isoformat()
    return strategies_db[strategy_id]


@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(strategy_id: str):
    """停用策略"""
    if strategy_id not in strategies_db:
        raise HTTPException(status_code=404, detail="策略不存在")
    strategies_db[strategy_id]['status'] = 'inactive'
    return strategies_db[strategy_id]
