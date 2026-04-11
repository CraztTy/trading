"""
策略系统模块

包含：
- base: 策略基类与接口
- indicators: 技术指标计算引擎
- manager: 策略管理器
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
]
