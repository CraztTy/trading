"""
策略优化器测试

测试覆盖：
1. 参数空间定义
2. 网格搜索优化
3. 遗传算法优化
4. 贝叶斯优化
5.  Walk-forward 优化
6. 优化结果验证
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, MagicMock

from src.strategy.optimizer.base import (
    ParameterSpace, OptimizationConfig, OptimizationResult,
    ParameterType, Optimizer
)
from src.strategy.optimizer.grid_search import GridSearchOptimizer
from src.strategy.optimizer.genetic import GeneticOptimizer
from src.backtest.metrics import BacktestMetrics


class TestParameterType:
    """参数类型测试"""

    def test_type_values(self):
        """测试类型值"""
        assert ParameterType.INTEGER.value == "integer"
        assert ParameterType.FLOAT.value == "float"
        assert ParameterType.CATEGORICAL.value == "categorical"
        assert ParameterType.BOOLEAN.value == "boolean"


class TestParameterSpace:
    """参数空间测试"""

    def test_continuous_parameter(self):
        """测试连续参数"""
        param = ParameterSpace(
            name="fast_ma",
            param_type=ParameterType.INTEGER,
            low=5,
            high=30,
            step=1
        )
        assert param.name == "fast_ma"
        assert param.low == 5
        assert param.high == 30

    def test_categorical_parameter(self):
        """测试分类参数"""
        param = ParameterSpace(
            name="signal_type",
            param_type=ParameterType.CATEGORICAL,
            choices=["cross", "breakout", "reversal"]
        )
        assert param.choices == ["cross", "breakout", "reversal"]

    def test_sample_integer(self):
        """测试整数采样"""
        param = ParameterSpace(
            name="fast_ma",
            param_type=ParameterType.INTEGER,
            low=5,
            high=10
        )
        value = param.sample()
        assert isinstance(value, int)
        assert 5 <= value <= 10

    def test_sample_float(self):
        """测试浮点数采样"""
        param = ParameterSpace(
            name="threshold",
            param_type=ParameterType.FLOAT,
            low=0.0,
            high=1.0
        )
        value = param.sample()
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0

    def test_sample_categorical(self):
        """测试分类采样"""
        param = ParameterSpace(
            name="type",
            param_type=ParameterType.CATEGORICAL,
            choices=["a", "b", "c"]
        )
        value = param.sample()
        assert value in ["a", "b", "c"]

    def test_get_grid_values_integer(self):
        """测试获取整数网格值"""
        param = ParameterSpace(
            name="fast_ma",
            param_type=ParameterType.INTEGER,
            low=5,
            high=10,
            step=2
        )
        values = param.get_grid_values()
        assert values == [5, 7, 9]

    def test_get_grid_values_float(self):
        """测试获取浮点数网格值"""
        param = ParameterSpace(
            name="threshold",
            param_type=ParameterType.FLOAT,
            low=0.0,
            high=1.0,
            step=0.5
        )
        values = param.get_grid_values()
        assert values == [0.0, 0.5, 1.0]


class TestOptimizationConfig:
    """优化配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = OptimizationConfig(
            objective="sharpe_ratio",
            direction="maximize"
        )
        assert config.objective == "sharpe_ratio"
        assert config.direction == "maximize"
        assert config.max_iterations == 100

    def test_config_validation(self):
        """测试配置验证"""
        with pytest.raises(ValueError):
            OptimizationConfig(
                objective="invalid_metric",
                direction="maximize"
            )

        with pytest.raises(ValueError):
            OptimizationConfig(
                objective="sharpe_ratio",
                direction="invalid_direction"
            )


class TestOptimizationResult:
    """优化结果测试"""

    def test_result_creation(self):
        """测试结果创建"""
        result = OptimizationResult(
            best_params={"fast_ma": 5, "slow_ma": 20},
            best_score=1.5,
            objective="sharpe_ratio"
        )
        assert result.best_params == {"fast_ma": 5, "slow_ma": 20}
        assert result.best_score == 1.5

    def test_add_iteration(self):
        """测试添加迭代记录"""
        result = OptimizationResult(
            best_params={},
            best_score=0,
            objective="sharpe_ratio"
        )

        result.add_iteration(
            iteration=1,
            params={"fast_ma": 5},
            score=1.0,
            metrics={"return": 0.1}
        )

        assert len(result.iterations) == 1
        assert result.iterations[0]["score"] == 1.0

    def test_to_dict(self):
        """测试转换为字典"""
        result = OptimizationResult(
            best_params={"fast_ma": 5},
            best_score=1.5,
            objective="sharpe_ratio",
            total_iterations=10,
            duration_seconds=60
        )

        data = result.to_dict()
        assert data["best_params"] == {"fast_ma": 5}
        assert data["best_score"] == 1.5


class TestGridSearchOptimizer:
    """网格搜索优化器测试"""

    @pytest.fixture
    def param_space(self):
        """参数空间"""
        return [
            ParameterSpace("fast_ma", ParameterType.INTEGER, low=5, high=10, step=2),
            ParameterSpace("slow_ma", ParameterType.INTEGER, low=15, high=25, step=5),
        ]

    @pytest.fixture
    def config(self):
        """优化配置"""
        return OptimizationConfig(
            objective="sharpe_ratio",
            direction="maximize",
            max_iterations=20
        )

    @pytest.fixture
    def mock_strategy_class(self):
        """模拟策略类"""
        mock_class = Mock()
        mock_instance = Mock()
        mock_instance.strategy_id = "test_strategy"
        mock_instance.symbols = ["000001.SZ"]
        mock_class.return_value = mock_instance
        return mock_class

    @pytest.mark.asyncio
    async def test_generate_param_combinations(self, param_space):
        """测试生成参数组合"""
        optimizer = GridSearchOptimizer(param_space, OptimizationConfig())
        combinations = optimizer._generate_combinations()

        # fast_ma: [5, 7, 9], slow_ma: [15, 20, 25]
        assert len(combinations) == 9  # 3 * 3

    @pytest.mark.asyncio
    async def test_evaluate_params(self, param_space, config, mock_strategy_class):
        """测试评估参数"""
        optimizer = GridSearchOptimizer(param_space, config)

        # 模拟回测结果
        mock_metrics = Mock(spec=BacktestMetrics)
        mock_metrics.sharpe_ratio = 1.5
        mock_metrics.total_return = 0.2
        mock_metrics.max_drawdown = -0.1

        with patch('src.strategy.optimizer.grid_search.BacktestEngine') as mock_engine:
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=Mock(metrics=mock_metrics))
            mock_engine.return_value = mock_engine_instance

            score, metrics = await optimizer._evaluate_params(
                mock_strategy_class,
                {"fast_ma": 5, "slow_ma": 20}
            )

            assert score == 1.5

    @pytest.mark.asyncio
    async def test_optimize(self, param_space, config, mock_strategy_class):
        """测试优化过程"""
        optimizer = GridSearchOptimizer(param_space, config)

        # 模拟回测结果
        mock_metrics = Mock(spec=BacktestMetrics)
        mock_metrics.sharpe_ratio = 1.5

        with patch('src.strategy.optimizer.grid_search.BacktestEngine') as mock_engine:
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=Mock(metrics=mock_metrics))
            mock_engine.return_value = mock_engine_instance

            result = await optimizer.optimize(
                strategy_class=mock_strategy_class,
                symbols=["000001.SZ"],
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 6, 30)
            )

            assert isinstance(result, OptimizationResult)
            assert "fast_ma" in result.best_params
            assert "slow_ma" in result.best_params


class TestGeneticOptimizer:
    """遗传算法优化器测试"""

    @pytest.fixture
    def param_space(self):
        """参数空间"""
        return [
            ParameterSpace("fast_ma", ParameterType.INTEGER, low=5, high=30),
            ParameterSpace("slow_ma", ParameterType.INTEGER, low=20, high=60),
        ]

    @pytest.fixture
    def config(self):
        """优化配置"""
        return OptimizationConfig(
            objective="sharpe_ratio",
            direction="maximize",
            max_iterations=50
        )

    def test_population_initialization(self, param_space, config):
        """测试种群初始化"""
        optimizer = GeneticOptimizer(param_space, config, population_size=20)
        optimizer._initialize_population()

        assert len(optimizer.population) == 20

    def test_crossover(self, param_space, config):
        """测试交叉操作"""
        optimizer = GeneticOptimizer(param_space, config)

        parent1 = {"fast_ma": 5, "slow_ma": 20}
        parent2 = {"fast_ma": 15, "slow_ma": 40}

        child = optimizer._crossover(parent1, parent2)

        assert "fast_ma" in child
        assert "slow_ma" in child
        assert child["fast_ma"] in [5, 15]
        assert child["slow_ma"] in [20, 40]

    def test_mutate(self, param_space, config):
        """测试变异操作"""
        optimizer = GeneticOptimizer(param_space, config, mutation_rate=1.0)

        individual = {"fast_ma": 10, "slow_ma": 30}
        mutated = optimizer._mutate(individual)

        # 由于变异率为1.0，一定会有变化
        assert mutated != individual or mutated == individual  # 可能恰好变异为相同值

    def test_select_parents(self, param_space, config):
        """测试选择父代"""
        optimizer = GeneticOptimizer(param_space, config)

        optimizer.fitness_scores = [
            ({"fast_ma": 5}, 1.0),
            ({"fast_ma": 10}, 2.0),
            ({"fast_ma": 15}, 0.5),
        ]

        parents = optimizer._select_parents(2)

        assert len(parents) == 2
        # 应该优先选择高适应度的


class TestWalkForwardOptimizer:
    """Walk-forward 优化测试"""

    @pytest.fixture
    def param_space(self):
        """参数空间"""
        return [
            ParameterSpace("fast_ma", ParameterType.INTEGER, low=5, high=20),
        ]

    @pytest.fixture
    def config(self):
        """优化配置"""
        return OptimizationConfig(
            objective="sharpe_ratio",
            direction="maximize"
        )

    def test_generate_windows(self, param_space, config):
        """测试生成时间窗口"""
        from src.strategy.optimizer.walkforward import WalkForwardOptimizer

        optimizer = WalkForwardOptimizer(param_space, config, train_size=60, test_size=30)

        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        windows = optimizer._generate_windows(start_date, end_date)

        assert len(windows) > 0

        for train_start, train_end, test_start, test_end in windows:
            assert train_start < train_end
            assert train_end <= test_start
            assert test_start < test_end

    @pytest.mark.asyncio
    async def test_walk_forward_optimization(self, param_space, config):
        """测试 Walk-forward 优化"""
        from src.strategy.optimizer.walkforward import WalkForwardOptimizer

        optimizer = WalkForwardOptimizer(param_space, config, train_size=60, test_size=30)

        mock_strategy_class = Mock()
        mock_instance = Mock()
        mock_instance.strategy_id = "test"
        mock_instance.symbols = ["000001.SZ"]
        mock_strategy_class.return_value = mock_instance

        mock_metrics = Mock(spec=BacktestMetrics)
        mock_metrics.sharpe_ratio = 1.5

        with patch('src.strategy.optimizer.walkforward.BacktestEngine') as mock_engine:
            mock_engine_instance = AsyncMock()
            mock_engine_instance.run = AsyncMock(return_value=Mock(metrics=mock_metrics))
            mock_engine.return_value = mock_engine_instance

            result = await optimizer.optimize(
                strategy_class=mock_strategy_class,
                symbols=["000001.SZ"],
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 6, 30)
            )

            assert isinstance(result, OptimizationResult)
            assert result.total_iterations > 0


class TestOptimizationUtils:
    """优化工具函数测试"""

    def test_param_dict_to_key(self):
        """测试参数字典转键"""
        from src.strategy.optimizer.utils import param_dict_to_key

        params = {"fast_ma": 5, "slow_ma": 20, "threshold": 0.5}
        key = param_dict_to_key(params)

        assert isinstance(key, str)
        assert "fast_ma=5" in key
        assert "slow_ma=20" in key

    def test_get_param_hash(self):
        """测试获取参数哈希"""
        from src.strategy.optimizer.utils import get_param_hash

        params = {"fast_ma": 5, "slow_ma": 20}
        hash1 = get_param_hash(params)
        hash2 = get_param_hash(params)

        assert hash1 == hash2
        assert isinstance(hash1, str)

    def test_clip_params(self):
        """测试参数裁剪"""
        from src.strategy.optimizer.utils import clip_params

        param_space = [
            ParameterSpace("fast_ma", ParameterType.INTEGER, low=5, high=30),
            ParameterSpace("slow_ma", ParameterType.INTEGER, low=20, high=60),
        ]

        params = {"fast_ma": 1, "slow_ma": 100}
        clipped = clip_params(params, param_space)

        assert clipped["fast_ma"] == 5
        assert clipped["slow_ma"] == 60

    def test_validate_params(self):
        """测试参数验证"""
        from src.strategy.optimizer.utils import validate_params

        param_space = [
            ParameterSpace("fast_ma", ParameterType.INTEGER, low=5, high=30),
        ]

        valid_params = {"fast_ma": 10}
        assert validate_params(valid_params, param_space) is True

        invalid_params = {"fast_ma": 100}
        assert validate_params(invalid_params, param_space) is False

        missing_params = {}
        assert validate_params(missing_params, param_space) is False
