"""
API v1 路由
"""
from fastapi import APIRouter

from src.api.v1.endpoints import strategies, backtest, live, health, intelligence, orders, matching, market, monitoring, auth, positions, capital, risk

router = APIRouter(prefix="/v1")

# 注册子路由
router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(strategies.router, prefix="/strategies", tags=["策略管理"])
router.include_router(orders.router, prefix="/orders", tags=["订单管理"])
router.include_router(matching.router, prefix="/matching", tags=["撮合引擎"])
router.include_router(backtest.router, prefix="/backtest", tags=["回测"])
router.include_router(live.router, prefix="/live", tags=["实盘监控"])
router.include_router(risk.router, prefix="/risk", tags=["风险控制"])
router.include_router(intelligence.router, prefix="/intelligence", tags=["智能分析"])
router.include_router(health.router, prefix="/health", tags=["健康检查"])
router.include_router(market.router, prefix="/market", tags=["行情数据"])
router.include_router(monitoring.router, prefix="/monitoring", tags=["交易监控"])
router.include_router(positions.router, prefix="/positions", tags=["持仓管理"])
router.include_router(capital.router, prefix="/capital", tags=["资金管理"])
