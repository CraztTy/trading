"""
实时风控系统

包含：
- position_manager: 仓位管理器
- stop_loss: 止损止盈机制
- risk_manager: 风控管理器（集成到策略执行）
"""
from src.risk.position_manager import PositionManager, PositionLimit, PositionLimitType
from src.risk.stop_loss import (
    StopLossManager, StopLossOrder, StopLossType,
    TakeProfitOrder, TakeProfitType,
    StopLossResult, TakeProfitResult
)
from src.risk.risk_manager import RiskManager, RiskConfig, TradeSignal

__all__ = [
    # 仓位管理
    "PositionManager",
    "PositionLimit",
    "PositionLimitType",
    # 止损止盈
    "StopLossManager",
    "StopLossOrder",
    "StopLossType",
    "TakeProfitOrder",
    "TakeProfitType",
    "StopLossResult",
    "TakeProfitResult",
    # 风控管理
    "RiskManager",
    "RiskConfig",
    "TradeSignal",
]
