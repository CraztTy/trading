"""
API v1 路由
"""
from fastapi import APIRouter

from src.api.v1.endpoints import strategies, backtest, live, health, intelligence

router = APIRouter(prefix="/v1")

# 注册子路由
router.include_router(strategies.router, prefix="/strategies", tags=["策略管理"])
router.include_router(backtest.router, prefix="/backtest", tags=["回测"])
router.include_router(live.router, prefix="/live", tags=["实盘监控"])
router.include_router(intelligence.router, prefix="/intelligence", tags=["智能分析"])
router.include_router(health.router, prefix="/health", tags=["健康检查"])
