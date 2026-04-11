"""
组合优化器

多策略权重优化、风险平价、再平衡
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import numpy as np
from scipy.optimize import minimize

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class OptimizationMethod(Enum):
    """优化方法"""
    MARKOWITZ = "markowitz"
    RISK_PARITY = "risk_parity"
    MAX_DIVERSIFICATION = "max_diversification"
    EQUAL_WEIGHT = "equal_weight"
    MINIMUM_VARIANCE = "minimum_variance"


@dataclass
class PortfolioConstraint:
    """组合约束"""
    constraint_type: str  # weight, sector, etc.
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    sector_limits: Optional[Dict[str, float]] = None


@dataclass
class PortfolioWeights:
    """组合权重"""
    weights: Dict[str, float]
    timestamp: datetime

    def __post_init__(self):
        """验证权重和为1"""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"权重和必须等于1，当前为{total}")

    def get_weight(self, strategy_id: str) -> float:
        """获取权重"""
        return self.weights.get(strategy_id, 0.0)

    def adjust_weight(self, strategy_id: str, new_weight: float):
        """调整权重"""
        old_weight = self.weights.get(strategy_id, 0.0)
        diff = new_weight - old_weight

        # 按比例调整其他权重
        others = {k: v for k, v in self.weights.items() if k != strategy_id}
        others_total = sum(others.values())

        if others_total > 0:
            for k in others:
                self.weights[k] -= diff * (others[k] / others_total)

        self.weights[strategy_id] = new_weight


@dataclass
class OptimizationResult:
    """优化结果"""
    optimal_weights: PortfolioWeights
    expected_return: float
    expected_risk: float
    sharpe_ratio: float


class PortfolioOptimizer:
    """
    组合优化器

    多策略权重优化
    """

    def __init__(self):
        pass

    def optimize(
        self,
        returns_data: Dict[str, np.ndarray],
        method: OptimizationMethod = OptimizationMethod.EQUAL_WEIGHT,
        constraints: Optional[List[PortfolioConstraint]] = None,
        target_return: Optional[float] = None,
        target_risk: Optional[float] = None
    ) -> OptimizationResult:
        """
        优化组合权重

        Args:
            returns_data: 各策略收益率数据
            method: 优化方法
            constraints: 约束条件
            target_return: 目标收益率
            target_risk: 目标风险

        Returns:
            OptimizationResult: 优化结果
        """
        if method == OptimizationMethod.EQUAL_WEIGHT:
            return self._equal_weight_optimize(returns_data)
        elif method == OptimizationMethod.MINIMUM_VARIANCE:
            return self._min_variance_optimize(returns_data, constraints)
        elif method == OptimizationMethod.RISK_PARITY:
            return self._risk_parity_optimize(returns_data)
        else:
            # 默认等权重
            return self._equal_weight_optimize(returns_data)

    def _calculate_covariance_matrix(
        self,
        returns_data: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """计算协方差矩阵"""
        returns_matrix = np.array(list(returns_data.values()))
        return np.cov(returns_matrix)

    def _calculate_expected_returns(
        self,
        returns_data: Dict[str, np.ndarray]
    ) -> Dict[str, float]:
        """计算预期收益率"""
        return {
            name: np.mean(returns)
            for name, returns in returns_data.items()
        }

    def _equal_weight_optimize(
        self,
        returns_data: Dict[str, np.ndarray]
    ) -> OptimizationResult:
        """等权重优化"""
        n = len(returns_data)
        weights = {name: 1.0 / n for name in returns_data.keys()}

        expected = self._calculate_expected_returns(returns_data)
        expected_return = np.mean(list(expected.values()))

        cov_matrix = self._calculate_covariance_matrix(returns_data)
        portfolio_risk = np.sqrt(np.mean(np.diag(cov_matrix)))

        return OptimizationResult(
            optimal_weights=PortfolioWeights(
                weights=weights,
                timestamp=datetime.now()
            ),
            expected_return=expected_return,
            expected_risk=portfolio_risk,
            sharpe_ratio=expected_return / portfolio_risk if portfolio_risk > 0 else 0
        )

    def _min_variance_optimize(
        self,
        returns_data: Dict[str, np.ndarray],
        constraints: Optional[List[PortfolioConstraint]] = None
    ) -> OptimizationResult:
        """最小方差优化"""
        names = list(returns_data.keys())
        n = len(names)
        cov_matrix = self._calculate_covariance_matrix(returns_data)

        # 目标函数：组合方差
        def portfolio_variance(weights):
            return weights @ cov_matrix @ weights

        # 约束：权重和为1
        cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})

        # 边界
        bounds = [(0.05, 0.5) for _ in range(n)]

        # 初始猜测
        x0 = np.array([1.0 / n] * n)

        # 优化
        result = minimize(
            portfolio_variance,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=cons
        )

        weights = {names[i]: result.x[i] for i in range(n)}

        expected = self._calculate_expected_returns(returns_data)
        expected_return = sum(expected[name] * weights[name] for name in names)

        return OptimizationResult(
            optimal_weights=PortfolioWeights(
                weights=weights,
                timestamp=datetime.now()
            ),
            expected_return=expected_return,
            expected_risk=np.sqrt(result.fun),
            sharpe_ratio=expected_return / np.sqrt(result.fun) if result.fun > 0 else 0
        )

    def _risk_parity_optimize(
        self,
        returns_data: Dict[str, np.ndarray]
    ) -> OptimizationResult:
        """风险平价优化"""
        # 简化实现：使用波动率的倒数作为权重
        volatilities = {
            name: np.std(returns)
            for name, returns in returns_data.items()
        }

        inv_vol = {name: 1.0 / vol for name, vol in volatilities.items()}
        total = sum(inv_vol.values())
        weights = {name: v / total for name, v in inv_vol.items()}

        expected = self._calculate_expected_returns(returns_data)
        expected_return = sum(expected[name] * weights[name] for name in weights)

        return OptimizationResult(
            optimal_weights=PortfolioWeights(
                weights=weights,
                timestamp=datetime.now()
            ),
            expected_return=expected_return,
            expected_risk=0.0,  # 简化
            sharpe_ratio=0.0
        )

    def _calculate_risk_contribution(
        self,
        weights: Dict[str, float],
        cov_matrix: np.ndarray
    ) -> Dict[str, float]:
        """计算风险贡献"""
        w = np.array(list(weights.values()))
        portfolio_var = w @ cov_matrix @ w
        marginal_risk = cov_matrix @ w
        risk_contrib = w * marginal_risk / portfolio_var if portfolio_var > 0 else w * 0
        return {name: risk_contrib[i] for i, name in enumerate(weights.keys())}
