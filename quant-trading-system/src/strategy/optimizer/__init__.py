"""
策略优化器模块

提供策略参数优化、策略选择和组合优化功能：
- 参数优化：网格搜索、遗传算法、贝叶斯优化
- 策略选择：根据市场状态动态选择最优策略
- 组合优化：多策略权重优化、风险平价
"""
from src.strategy.optimizer.base import (
    ParameterSpace, OptimizationConfig, OptimizationResult,
    ParameterType, Optimizer
)
from src.strategy.optimizer.grid_search import GridSearchOptimizer
from src.strategy.optimizer.genetic import GeneticOptimizer
from src.strategy.optimizer.walkforward import WalkForwardOptimizer
from src.strategy.optimizer.utils import (
    param_dict_to_key, get_param_hash, clip_params, validate_params
)

__all__ = [
    # 参数优化
    "ParameterSpace",
    "OptimizationConfig",
    "OptimizationResult",
    "ParameterType",
    "Optimizer",
    "GridSearchOptimizer",
    "GeneticOptimizer",
    "WalkForwardOptimizer",
    # 工具函数
    "param_dict_to_key",
    "get_param_hash",
    "clip_params",
    "validate_params",
]
