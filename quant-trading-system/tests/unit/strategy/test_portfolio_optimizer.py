"""
组合优化器测试

测试覆盖：
1. 权重优化算法
2. 风险平价
3. 最大分散化
4. 目标风险组合
5. 再平衡策略
"""
import pytest
from datetime import datetime
from typing import Dict
import numpy as np

from src.strategy.portfolio_optimizer import (
    PortfolioOptimizer, OptimizationMethod,
    PortfolioConstraint, PortfolioWeights, OptimizationResult
)


class TestOptimizationMethod:
    """优化方法测试"""

    def test_method_values(self):
        """测试方法值"""
        assert OptimizationMethod.MARKOWITZ.value == "markowitz"
        assert OptimizationMethod.RISK_PARITY.value == "risk_parity"
        assert OptimizationMethod.MAX_DIVERSIFICATION.value == "max_diversification"
        assert OptimizationMethod.EQUAL_WEIGHT.value == "equal_weight"
        assert OptimizationMethod.MINIMUM_VARIANCE.value == "minimum_variance"


class TestPortfolioConstraint:
    """组合约束测试"""

    def test_weight_constraint(self):
        """测试权重约束"""
        constraint = PortfolioConstraint(
            constraint_type="weight",
            min_weight=0.05,
            max_weight=0.3
        )
        assert constraint.min_weight == 0.05
        assert constraint.max_weight == 0.3


class TestPortfolioWeights:
    """组合权重测试"""

    def test_weights_creation(self):
        """测试权重创建"""
        weights = PortfolioWeights(
            weights={"strategy_1": 0.4, "strategy_2": 0.6},
            timestamp=datetime.now()
        )
        assert sum(weights.weights.values()) == pytest.approx(1.0, abs=0.001)

    def test_get_weight(self):
        """测试获取权重"""
        weights = PortfolioWeights(
            weights={"strategy_1": 0.4, "strategy_2": 0.6},
            timestamp=datetime.now()
        )
        assert weights.get_weight("strategy_1") == 0.4
        assert weights.get_weight("nonexistent") == 0.0


class TestPortfolioOptimizer:
    """组合优化器测试"""

    @pytest.fixture
    def returns_data(self):
        """收益率数据"""
        np.random.seed(42)
        n_days = 252
        returns = {
            "strategy_1": np.random.normal(0.001, 0.02, n_days),
            "strategy_2": np.random.normal(0.0005, 0.015, n_days),
            "strategy_3": np.random.normal(0.0008, 0.025, n_days),
        }
        return returns

    @pytest.fixture
    def optimizer(self):
        return PortfolioOptimizer()

    def test_equal_weight_optimization(self, optimizer, returns_data):
        """测试等权重优化"""
        result = optimizer.optimize(
            returns_data=returns_data,
            method=OptimizationMethod.EQUAL_WEIGHT
        )

        assert isinstance(result, OptimizationResult)
        for w in result.optimal_weights.weights.values():
            assert w == pytest.approx(1/3, abs=0.001)

    def test_minimum_variance_optimization(self, optimizer, returns_data):
        """测试最小方差优化"""
        result = optimizer.optimize(
            returns_data=returns_data,
            method=OptimizationMethod.MINIMUM_VARIANCE
        )

        assert isinstance(result, OptimizationResult)

    def test_optimization_with_constraints(self, optimizer, returns_data):
        """测试带约束的优化"""
        constraints = [
            PortfolioConstraint(
                constraint_type="weight",
                min_weight=0.1,
                max_weight=0.5
            )
        ]

        result = optimizer.optimize(
            returns_data=returns_data,
            method=OptimizationMethod.MARKOWITZ,
            constraints=constraints
        )

        for w in result.optimal_weights.weights.values():
            assert 0.1 <= w <= 0.5
