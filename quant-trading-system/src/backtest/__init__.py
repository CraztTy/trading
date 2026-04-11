"""
回测系统模块

提供完整的策略回测功能：
- 历史数据加载 (data_loader)
- 绩效计算 (metrics)
- 回测引擎 (engine)

使用示例:
```python
from src.backtest import BacktestEngine, BacktestConfig
from datetime import datetime
from decimal import Decimal

engine = BacktestEngine()
config = BacktestConfig(
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    initial_capital=Decimal("1000000")
)
result = await engine.run(strategy, config)
result.print_report()
```
"""
from src.backtest.data_loader import HistoryDataLoader, HistoryDataRequest
from src.backtest.metrics import (
    MetricsCalculator,
    TradeRecord,
    DailyPortfolio,
    BacktestMetrics,
)
from src.backtest.engine import BacktestEngine, BacktestConfig, BacktestResult

__all__ = [
    # 数据加载
    "HistoryDataLoader",
    "HistoryDataRequest",
    # 绩效计算
    "MetricsCalculator",
    "TradeRecord",
    "DailyPortfolio",
    "BacktestMetrics",
    # 回测引擎
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
]
