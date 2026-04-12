"""
策略参数优化器基类
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Any, Callable
from decimal import Decimal


@dataclass
class OptimizationResult:
    """优化结果"""
    parameters: Dict[str, Any]       # 最优参数
    metrics: Dict[str, float]        # 性能指标
    rank: int                        # 排名
    backtest_id: str = None          # 关联的回测ID


@dataclass
class ParameterSpace:
    """参数空间定义"""
    name: str
    param_type: str  # int, float, choice
    min_value: Any = None
    max_value: Any = None
    step: Any = None
    choices: List[Any] = None
    default: Any = None

    def validate(self) -> bool:
        """验证参数定义"""
        if self.param_type in ["int", "float"]:
            return self.min_value is not None and self.max_value is not None
        elif self.param_type == "choice":
            return self.choices is not None and len(self.choices) > 0
        return False


class BaseOptimizer(ABC):
    """优化器基类"""

    def __init__(
        self,
        parameter_spaces: Dict[str, ParameterSpace],
        evaluation_func: Callable[[Dict[str, Any]], Dict[str, float]],
        objective_metric: str = "sharpe_ratio",
        maximize: bool = True
    ):
        """
        Args:
            parameter_spaces: 参数空间定义
            evaluation_func: 评估函数，接收参数返回指标
            objective_metric: 优化目标指标
            maximize: 是否最大化目标
        """
        self.parameter_spaces = parameter_spaces
        self.evaluation_func = evaluation_func
        self.objective_metric = objective_metric
        self.maximize = maximize
        self.results: List[OptimizationResult] = []

    @abstractmethod
    async def optimize(self, max_iterations: int = None) -> List[OptimizationResult]:
        """
        执行优化

        Returns:
            按目标指标排序的结果列表
        """
        pass

    def generate_all_combinations(self) -> List[Dict[str, Any]]:
        """生成所有参数组合（用于网格搜索）"""
        import itertools

        param_ranges = {}
        for name, space in self.parameter_spaces.items():
            if space.param_type == "int":
                param_ranges[name] = list(range(
                    space.min_value,
                    space.max_value + 1,
                    space.step or 1
                ))
            elif space.param_type == "float":
                import numpy as np
                param_ranges[name] = list(np.arange(
                    space.min_value,
                    space.max_value + (space.step or 0.01),
                    space.step or 0.01
                ))
            elif space.param_type == "choice":
                param_ranges[name] = space.choices

        # 生成笛卡尔积
        keys = list(param_ranges.keys())
        values = [param_ranges[k] for k in keys]

        combinations = []
        for combo in itertools.product(*values):
            combinations.append(dict(zip(keys, combo)))

        return combinations

    def _compare_metrics(self, metric1: float, metric2: float) -> int:
        """比较两个指标值"""
        if self.maximize:
            return 1 if metric1 > metric2 else (-1 if metric1 < metric2 else 0)
        else:
            return 1 if metric1 < metric2 else (-1 if metric1 > metric2 else 0)
