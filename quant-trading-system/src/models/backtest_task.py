"""
回测任务模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Dict, Any

from sqlalchemy import BigInteger, String, Numeric, DateTime, ForeignKey, Integer, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.account import Account


class BacktestTask(Base):
    """回测任务表"""
    __tablename__ = "backtest_task"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    # 关联
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False, index=True)

    # 回测参数
    symbols: Mapped[list] = mapped_column(JSON, nullable=False)  # ["000001.SZ", "600036.SH"]
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)  # "2024-01-01"
    end_date: Mapped[str] = mapped_column(String(10), nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    strategy_params: Mapped[Optional[Dict]] = mapped_column(JSON)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("1000000"))

    # 状态
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100

    # 结果（JSON格式）
    results: Mapped[Optional[Dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 索引
    __table_args__ = (
        Index("idx_backtest_task_account", "account_id", "created_at"),
        Index("idx_backtest_task_status", "status", "created_at"),
    )

    def __init__(
        self,
        task_id: str,
        account_id: int,
        symbols: list,
        start_date: str,
        end_date: str,
        strategy_id: str,
        initial_capital: Decimal = Decimal("1000000"),
        strategy_params: dict = None
    ):
        self.task_id = task_id
        self.account_id = account_id
        self.symbols = symbols
        self.start_date = start_date
        self.end_date = end_date
        self.strategy_id = strategy_id
        self.initial_capital = initial_capital
        self.strategy_params = strategy_params

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "account_id": self.account_id,
            "symbols": self.symbols,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "strategy_id": self.strategy_id,
            "strategy_params": self.strategy_params,
            "initial_capital": float(self.initial_capital),
            "status": self.status,
            "progress": self.progress,
            "results": self.results,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
