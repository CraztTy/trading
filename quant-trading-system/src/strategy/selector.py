"""
策略选择器

根据市场状态动态选择最优策略
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from src.backtest.metrics import BacktestMetrics
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class MarketState(Enum):
    """市场状态"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class SelectorConfig:
    """选择器配置"""
    lookback_days: int = 30
    min_trades: int = 10
    score_threshold: float = 0.5


@dataclass
class StrategyScore:
    """策略评分"""
    strategy_id: str
    overall_score: float
    sharpe_score: float = 0.0
    return_score: float = 0.0
    drawdown_score: float = 0.0
    consistency_score: float = 0.0


@dataclass
class SelectionRule:
    """选择规则"""
    name: str
    condition: Callable[[BacktestMetrics, MarketState], bool]
    weight: float = 1.0

    def evaluate(self, metrics: BacktestMetrics, state: MarketState) -> bool:
        try:
            return self.condition(metrics, state)
        except Exception:
            return False


@dataclass
class SelectionHistory:
    """选择历史"""
    timestamp: datetime
    selected_strategy: str
    market_state: MarketState
    scores: List[StrategyScore]


class StrategySelector:
    """
    策略选择器

    根据市场状态选择最优策略
    """

    def __init__(self, config: Optional[SelectorConfig] = None):
        self.config = config or SelectorConfig()
        self.selection_history: List[SelectionHistory] = []
        self.rules: List[SelectionRule] = []

    def add_rule(self, rule: SelectionRule) -> None:
        """添加选择规则"""
        self.rules.append(rule)

    def _detect_market_state(self, prices: List[float]) -> MarketState:
        """检测市场状态"""
        if len(prices) < 10:
            return MarketState.RANGING

        # 简单趋势检测
        first_half = sum(prices[:len(prices)//2]) / (len(prices)//2)
        second_half = sum(prices[len(prices)//2:]) / (len(prices) - len(prices)//2)

        change_pct = (second_half - first_half) / first_half if first_half != 0 else 0

        # 波动率检测
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        volatility = sum(r**2 for r in returns) / len(returns) if returns else 0

        if change_pct > 0.05:
            return MarketState.TRENDING_UP
        elif change_pct < -0.05:
            return MarketState.TRENDING_DOWN
        elif volatility > 0.001:
            return MarketState.VOLATILE
        else:
            return MarketState.RANGING

    def _score_strategy(self, metrics: BacktestMetrics) -> StrategyScore:
        """评分策略"""
        return StrategyScore(
            strategy_id="",
            overall_score=metrics.sharpe_ratio,
            sharpe_score=metrics.sharpe_ratio,
            return_score=metrics.total_return,
            drawdown_score=1 + metrics.max_drawdown
        )

    def select(
        self,
        strategies: List[Any],
        market_data: Dict[str, Any]
    ) -> Optional[Any]:
        """选择最优策略"""
        if not strategies:
            return None

        prices = market_data.get("prices", [])
        market_state = self._detect_market_state(prices)

        # 评分所有策略
        scores = []
        for strategy in strategies:
            # 这里简化处理，实际应该获取策略的历史表现
            score = StrategyScore(
                strategy_id=strategy.strategy_id,
                overall_score=1.0  # 简化
            )
            scores.append((strategy, score))

        # 选择最高分
        if scores:
            best = max(scores, key=lambda x: x[1].overall_score)

            # 记录历史
            self.selection_history.append(SelectionHistory(
                timestamp=datetime.now(),
                selected_strategy=best[0].strategy_id,
                market_state=market_state,
                scores=[s[1] for s in scores]
            ))

            return best[0]

        return None

    def get_top_strategies(
        self,
        strategies: List[Any],
        market_data: Dict[str, Any],
        n: int = 3
    ) -> List[Any]:
        """获取Top N策略"""
        # 简化实现
        return strategies[:n]

    def get_selection_history(self) -> List[SelectionHistory]:
        """获取选择历史"""
        return self.selection_history
