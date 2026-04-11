"""
优化器基类与接口定义

定义所有策略优化器的统一接口和数据结构
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import random

from src.backtest.metrics import BacktestMetrics


class ParameterType(Enum):
    """参数类型"""
    INTEGER = "integer"
    FLOAT = "float"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


@dataclass
class ParameterSpace:
    """
    参数空间定义

    用于定义优化参数的搜索范围
    """
    name: str
    param_type: ParameterType
    # 连续/整数参数范围
    low: Optional[float] = None
    high: Optional[float] = None
    step: Optional[float] = None
    # 分类参数选项
    choices: Optional[List[Any]] = None
    # 默认值
    default: Any = None

    def __post_init__(self):
        """验证参数定义"""
        if self.param_type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            if self.low is None or self.high is None:
                raise ValueError(f"连续/整数参数必须指定 low 和 high: {self.name}")
            if self.low >= self.high:
                raise ValueError(f"low 必须小于 high: {self.name}")

        if self.param_type == ParameterType.CATEGORICAL:
            if not self.choices:
                raise ValueError(f"分类参数必须指定 choices: {self.name}")

    def sample(self) -> Any:
        """从参数空间中随机采样"""
        if self.param_type == ParameterType.INTEGER:
            return random.randint(int(self.low), int(self.high))

        elif self.param_type == ParameterType.FLOAT:
            return random.uniform(self.low, self.high)

        elif self.param_type == ParameterType.CATEGORICAL:
            return random.choice(self.choices)

        elif self.param_type == ParameterType.BOOLEAN:
            return random.choice([True, False])

        return self.default

    def get_grid_values(self) -> List[Any]:
        """获取网格搜索的所有可能值"""
        if self.param_type == ParameterType.INTEGER:
            step = int(self.step) if self.step else 1
            return list(range(int(self.low), int(self.high) + 1, step))

        elif self.param_type == ParameterType.FLOAT:
            step = self.step if self.step else (self.high - self.low) / 10
            values = []
            current = self.low
            while current <= self.high:
                values.append(round(current, 6))
                current += step
            return values

        elif self.param_type == ParameterType.CATEGORICAL:
            return self.choices

        elif self.param_type == ParameterType.BOOLEAN:
            return [True, False]

        return [self.default]


@dataclass
class OptimizationConfig:
    """
    优化配置
    """
    # 优化目标
    objective: str = "sharpe_ratio"  # sharpe_ratio, total_return, sortino_ratio, etc.
    direction: str = "maximize"  # maximize, minimize

    # 迭代限制
    max_iterations: int = 100

    # 早停配置
    early_stopping: bool = True
    patience: int = 10  # 连续多少次没有改善就停止
    min_improvement: float = 0.001  # 最小改善幅度

    # 并行配置
    n_jobs: int = 1  # -1 表示使用所有CPU

    # 随机种子
    random_seed: Optional[int] = None

    def __post_init__(self):
        """验证配置"""
        valid_objectives = [
            "sharpe_ratio", "total_return", "annual_return",
            "sortino_ratio", "calmar_ratio", "win_rate",
            "profit_factor", "max_drawdown"
        ]
        if self.objective not in valid_objectives:
            raise ValueError(f"不支持的优化目标: {self.objective}")

        if self.direction not in ["maximize", "minimize"]:
            raise ValueError(f"不支持的优化方向: {self.direction}")


@dataclass
class OptimizationResult:
    """
    优化结果
    """
    best_params: Dict[str, Any]
    best_score: float
    objective: str
    total_iterations: int = 0
    duration_seconds: float = 0.0
    iterations: List[Dict[str, Any]] = field(default_factory=list)

    def add_iteration(
        self,
        iteration: int,
        params: Dict[str, Any],
        score: float,
        metrics: Optional[Dict[str, Any]] = None
    ):
        """添加迭代记录"""
        self.iterations.append({
            "iteration": iteration,
            "params": params.copy(),
            "score": score,
            "metrics": metrics or {},
            "timestamp": datetime.now()
        })
        self.total_iterations = len(self.iterations)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "objective": self.objective,
            "total_iterations": self.total_iterations,
            "duration_seconds": self.duration_seconds,
        }


class Optimizer(ABC):
    """
    优化器基类

    所有参数优化器必须继承此类
    """

    def __init__(
        self,
        param_space: List[ParameterSpace],
        config: OptimizationConfig
    ):
        self.param_space = param_space
        self.config = config

        # 设置随机种子
        if config.random_seed is not None:
            random.seed(config.random_seed)

        # 参数名映射
        self.param_names = [p.name for p in param_space]

        # 最佳结果跟踪
        self.best_score = float('-inf') if config.direction == "maximize" else float('inf')
        self.best_params: Optional[Dict[str, Any]] = None
        self.no_improvement_count = 0

    @abstractmethod
    async def optimize(
        self,
        strategy_class,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> OptimizationResult:
        """
        执行优化

        Args:
            strategy_class: 策略类
            symbols: 交易标的
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            OptimizationResult: 优化结果
        """
        pass

    async def _evaluate_params(
        self,
        strategy_class,
        params: Dict[str, Any],
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> tuple[float, BacktestMetrics]:
        """
        评估一组参数

        Returns:
            (得分, 回测指标)
        """
        from src.backtest.engine import BacktestEngine, BacktestConfig

        # 创建策略实例
        strategy = strategy_class(
            strategy_id=f"opt_{datetime.now().strftime('%H%M%S%f')}",
            name="optimization",
            symbols=symbols,
            params=params
        )

        # 运行回测
        engine = BacktestEngine()
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date
        )

        result = await engine.run(strategy, config)
        metrics = result.metrics

        # 计算得分
        score = self._calculate_score(metrics)

        return score, metrics

    def _calculate_score(self, metrics: BacktestMetrics) -> float:
        """
        根据优化目标计算得分
        """
        objective = self.config.objective

        if objective == "sharpe_ratio":
            score = metrics.sharpe_ratio
        elif objective == "total_return":
            score = metrics.total_return
        elif objective == "annual_return":
            score = metrics.annual_return
        elif objective == "sortino_ratio":
            score = metrics.sortino_ratio
        elif objective == "calmar_ratio":
            score = metrics.calmar_ratio
        elif objective == "max_drawdown":
            score = -metrics.max_drawdown  # 越小越好，取负
        elif objective == "win_rate":
            score = metrics.win_rate
        elif objective == "profit_factor":
            score = metrics.profit_factor
        else:
            score = metrics.sharpe_ratio

        # 处理优化方向
        if self.config.direction == "minimize":
            score = -score

        return score

    def _is_better(self, score: float) -> bool:
        """检查是否为更好的得分"""
        if self.config.direction == "maximize":
            return score > self.best_score + self.config.min_improvement
        else:
            return score < self.best_score - self.config.min_improvement

    def _update_best(self, score: float, params: Dict[str, Any]):
        """更新最佳结果"""
        if self._is_better(score):
            self.best_score = score
            self.best_params = params.copy()
            self.no_improvement_count = 0
        else:
            self.no_improvement_count += 1

    def _should_stop_early(self) -> bool:
        """检查是否应该早停"""
        if not self.config.early_stopping:
            return False
        return self.no_improvement_count >= self.config.patience

    def sample_random_params(self) -> Dict[str, Any]:
        """随机采样一组参数"""
        return {p.name: p.sample() for p in self.param_space}
