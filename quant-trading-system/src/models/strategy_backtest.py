"""
策略回测关联模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Integer, Numeric, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.strategy import Strategy
    from src.models.backtest_task import BacktestTask


class StrategyBacktest(Base):
    """策略回测关联表"""
    __tablename__ = "strategy_backtest"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 关联
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategy.id"), nullable=False, index=True)
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="backtests")

    backtest_task_id: Mapped[str] = mapped_column(String(32), ForeignKey("backtest_task.task_id"), nullable=False)
    # backtest_task relationship 在 BacktestTask 中定义

    # 使用的参数
    parameters_used: Mapped[dict] = mapped_column(JSON, default=dict)

    # 结果摘要
    total_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    total_trades: Mapped[int] = mapped_column(Integer, default=0)

    # 是否为最优参数
    is_optimal: Mapped[bool] = mapped_column(default=False)
    optimization_id: Mapped[Optional[str]] = mapped_column(String(32), index=True)  # 关联优化任务

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # 索引
    __table_args__ = (
        Index("idx_strategy_backtest_strategy", "strategy_id", "created_at"),
        Index("idx_strategy_backtest_optimal", "strategy_id", "is_optimal"),
    )

    def __init__(
        self,
        strategy_id: int,
        backtest_task_id: str,
        parameters_used: dict = None,
        optimization_id: str = None
    ):
        self.strategy_id = strategy_id
        self.backtest_task_id = backtest_task_id
        self.parameters_used = parameters_used or {}
        self.optimization_id = optimization_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "backtest_task_id": self.backtest_task_id,
            "parameters_used": self.parameters_used,
            "total_return": float(self.total_return) if self.total_return else None,
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            "win_rate": float(self.win_rate) if self.win_rate else None,
            "total_trades": self.total_trades,
            "is_optimal": self.is_optimal,
            "optimization_id": self.optimization_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
