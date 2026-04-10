"""
策略模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional, Dict, Any

from sqlalchemy import String, Numeric, DateTime, ForeignKey, JSON, Index, text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import StrategyStatus, RunMode

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.order import Order
    from src.models.trade import Trade


class Strategy(Base):
    """策略表"""
    __tablename__ = "strategy"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(256))

    # 分类
    category: Mapped[Optional[str]] = mapped_column(String(32))  # 趋势/均值回归/套利
    style: Mapped[Optional[str]] = mapped_column(String(32))     # 风格描述

    # 参数（JSONB存储，灵活扩展）
    params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # 风控参数
    max_position: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.10"), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.02"), nullable=False)
    take_profit: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.05"), nullable=False)

    # 运行状态
    status: Mapped[StrategyStatus] = mapped_column(
        String(16), default=StrategyStatus.INACTIVE, nullable=False, index=True
    )
    run_mode: Mapped[RunMode] = mapped_column(
        String(16), default=RunMode.SIMULATE, nullable=False
    )

    # 统计
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loss_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_return: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"), nullable=False)
    sharpe_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)

    # 关联
    account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("account.id"), nullable=True, index=True)
    account: Mapped[Optional["Account"]] = relationship("Account", back_populates="strategies")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
        nullable=False
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 关系
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="strategy", lazy="selectin")
    trades: Mapped[List["Trade"]] = relationship("Trade", back_populates="strategy", lazy="selectin")

    def __init__(
        self,
        strategy_id: str,
        name: str,
        description: str = "",
        account_id: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
        run_mode: RunMode = RunMode.SIMULATE
    ):
        self.strategy_id = strategy_id
        self.name = name
        self.description = description
        self.account_id = account_id
        self.params = params or {}
        self.run_mode = run_mode

    @property
    def win_rate(self) -> Decimal:
        """胜率"""
        if self.total_trades == 0:
            return Decimal("0")
        return Decimal(str(self.win_trades)) / Decimal(str(self.total_trades))

    def activate(self) -> None:
        """激活策略"""
        self.status = StrategyStatus.ACTIVE
        self.activated_at = datetime.now()

    def deactivate(self) -> None:
        """停用策略"""
        self.status = StrategyStatus.INACTIVE

    def pause(self) -> None:
        """暂停策略"""
        if self.status == StrategyStatus.ACTIVE:
            self.status = StrategyStatus.PAUSED

    def resume(self) -> None:
        """恢复策略"""
        if self.status == StrategyStatus.PAUSED:
            self.status = StrategyStatus.ACTIVE

    def update_stats(self, pnl: Decimal) -> None:
        """更新交易统计"""
        self.total_trades += 1
        if pnl > 0:
            self.win_trades += 1
        elif pnl < 0:
            self.loss_trades += 1

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "style": self.style,
            "params": self.params,
            "max_position": float(self.max_position),
            "stop_loss": float(self.stop_loss),
            "take_profit": float(self.take_profit),
            "status": self.status.value,
            "run_mode": self.run_mode.value,
            "total_trades": self.total_trades,
            "win_trades": self.win_trades,
            "loss_trades": self.loss_trades,
            "win_rate": float(self.win_rate),
            "total_return": float(self.total_return),
            "sharpe_ratio": float(self.sharpe_ratio),
            "max_drawdown": float(self.max_drawdown),
            "account_id": self.account_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
        }
