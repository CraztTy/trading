"""
数据库模型模块
SQLAlchemy 2.0 声明式基类和模型导出
"""

from src.models.base import (
    Base,
    get_db,
    db_manager,
    init_db,
    close_db,
    check_db_connection,
)
from src.models.enums import (
    AccountStatus,
    AccountType,
    StrategyStatus,
    RunMode,
    OrderStatus,
    OrderDirection,
    OrderType,
    FlowType,
)
from src.models.account import Account
from src.models.strategy import Strategy
from src.models.order import Order
from src.models.trade import Trade
from src.models.position import Position
from src.models.balance_flow import BalanceFlow
from src.models.daily_settlement import DailySettlement
from src.models.market_data import MarketDataSnapshot
from src.models.user import User
from src.models.order_state_history import OrderStateHistory
from src.models.signal_log import SignalLog
from src.models.audit_log import AuditLog
from src.models.data_quality_log import DataQualityLog
from src.models.backtest_task import BacktestTask

__all__ = [
    # 基础
    "Base",
    "get_db",
    "db_manager",
    "init_db",
    "close_db",
    "check_db_connection",
    # 枚举
    "AccountStatus",
    "AccountType",
    "StrategyStatus",
    "RunMode",
    "OrderStatus",
    "OrderDirection",
    "OrderType",
    "FlowType",
    # 模型
    "Account",
    "Strategy",
    "Order",
    "Trade",
    "Position",
    "BalanceFlow",
    "DailySettlement",
    "MarketDataSnapshot",
    "User",
    "OrderStateHistory",
    # 新模型 - Phase 1优化
    "SignalLog",
    "AuditLog",
    "DataQualityLog",
    # 回测任务
    "BacktestTask",
]
