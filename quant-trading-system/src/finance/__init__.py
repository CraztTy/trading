"""
资金管理模块

提供完整的资金管理能力：
- 出入金管理
- 资金冻结/解冻
- 资金流水查询
- 日终结算
- 资金报表
"""
from src.finance.capital_manager import (
    CapitalManager,
    CapitalOperationType,
    CapitalOperationResult,
    CapitalSnapshot,
    FlowStatistics,
    validate_amount,
    calculate_buying_power,
)
from src.finance.settlement import (
    SettlementManager,
    SettlementResult,
    SettlementReport,
    calculate_max_drawdown,
    calculate_sharpe,
    calculate_volatility,
)

__all__ = [
    # 资金管理
    "CapitalManager",
    "CapitalOperationType",
    "CapitalOperationResult",
    "CapitalSnapshot",
    "FlowStatistics",
    "validate_amount",
    "calculate_buying_power",
    # 结算管理
    "SettlementManager",
    "SettlementResult",
    "SettlementReport",
    "calculate_max_drawdown",
    "calculate_sharpe",
    "calculate_volatility",
]
