"""
策略系统模块

包含：
- base: 策略基类与接口
- indicators: 技术指标计算引擎
- manager: 策略管理器
- optimizer: 策略优化器
- selector: 策略选择器
- portfolio_optimizer: 组合优化器
- examples: 示例策略
"""
from src.strategy.base import (
    StrategyBase,
    StrategyContext,
    BarData,
    TickData,
    Signal,
    SignalType,
    StrategyState,
    Position,
    AccountInfo,
)

from src.strategy.manager import StrategyManager, strategy_manager

from src.strategy.indicators import (
    MovingAverage,
    MACD,
    RSI,
    BollingerBands,
    KDJ,
    ATR,
    OBV,
    IndicatorEngine,
)

from src.strategy.optimizer import (
    ParameterSpace,
    OptimizationConfig,
    OptimizationResult,
    ParameterType,
    Optimizer,
    GridSearchOptimizer,
    GeneticOptimizer,
    WalkForwardOptimizer,
)

from src.strategy.selector import (
    StrategySelector,
    MarketState,
    StrategyScore,
    SelectorConfig,
)

from src.strategy.portfolio_optimizer import (
    PortfolioOptimizer,
    OptimizationMethod,
    PortfolioConstraint,
    PortfolioWeights,
)

__all__ = [
    # 基类
    "StrategyBase",
    "StrategyContext",
    "BarData",
    "TickData",
    "Signal",
    "SignalType",
    "StrategyState",
    "Position",
    "AccountInfo",
    # 管理器
    "StrategyManager",
    "strategy_manager",
    # 指标
    "MovingAverage",
    "MACD",
    "RSI",
    "BollingerBands",
    "KDJ",
    "ATR",
    "OBV",
    "IndicatorEngine",
    # 优化器
    "ParameterSpace",
    "OptimizationConfig",
    "OptimizationResult",
    "ParameterType",
    "Optimizer",
    "GridSearchOptimizer",
    "GeneticOptimizer",
    "WalkForwardOptimizer",
    # 选择器
    "StrategySelector",
    "MarketState",
    "StrategyScore",
    "SelectorConfig",
    # 组合优化
    "PortfolioOptimizer",
    "OptimizationMethod",
    "PortfolioConstraint",
    "PortfolioWeights",
]
