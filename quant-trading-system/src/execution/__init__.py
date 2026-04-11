"""
订单执行系统

提供完整的订单执行能力：
- 执行引擎：统一管理订单执行
- 智能路由：根据账户类型和订单特征选择执行渠道
- 算法执行：TWAP/VWAP等算法订单
- 执行监控：实时跟踪执行状态和性能
"""
from src.execution.engine import ExecutionEngine, ExecutionConfig, ExecutionResult, ValidationResult
from src.execution.router import OrderRouter, RouteTarget, RoutingDecision, RoutingRule
from src.execution.monitor import ExecutionMonitor, ExecutionMetrics, ExecutionEvent

__all__ = [
    # 执行引擎
    "ExecutionEngine",
    "ExecutionConfig",
    "ExecutionResult",
    "ValidationResult",
    # 路由器
    "OrderRouter",
    "RouteTarget",
    "RoutingDecision",
    "RoutingRule",
    # 监控
    "ExecutionMonitor",
    "ExecutionMetrics",
    "ExecutionEvent",
]
