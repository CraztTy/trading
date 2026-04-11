"""
账户模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index, text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import AccountStatus, AccountType

if TYPE_CHECKING:
    from src.models.strategy import Strategy
    from src.models.order import Order
    from src.models.position import Position
    from src.models.balance_flow import BalanceFlow
    from src.models.daily_settlement import DailySettlement


class Account(Base):
    """账户表"""
    __tablename__ = "account"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        String(16),
        default=AccountType.SIMULATE,
        nullable=False
    )

    # 资金字段（DECIMAL精确计算）
    total_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0"), nullable=False
    )
    available: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0"), nullable=False
    )
    frozen: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0"), nullable=False
    )
    market_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0"), nullable=False
    )

    # 盈亏统计
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0"), nullable=False
    )
    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0"), nullable=False
    )

    # 配置
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("1000000"), nullable=False
    )
    max_drawdown: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), default=Decimal("0"), nullable=False
    )

    # 状态
    status: Mapped[AccountStatus] = mapped_column(
        String(16), default=AccountStatus.ACTIVE, nullable=False
    )

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

    # 关系
    strategies: Mapped[List["Strategy"]] = relationship(
        "Strategy", back_populates="account", lazy="selectin"
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order", back_populates="account", lazy="selectin"
    )
    positions: Mapped[List["Position"]] = relationship(
        "Position", back_populates="account", lazy="selectin"
    )
    balance_flows: Mapped[List["BalanceFlow"]] = relationship(
        "BalanceFlow", back_populates="account", lazy="selectin"
    )
    settlements: Mapped[List["DailySettlement"]] = relationship(
        "DailySettlement", back_populates="account", lazy="selectin"
    )

    # 表级约束
    __table_args__ = (
        CheckConstraint("total_balance >= 0", name="check_total_balance_non_negative"),
        CheckConstraint("available >= 0", name="check_available_non_negative"),
        CheckConstraint("frozen >= 0", name="check_frozen_non_negative"),
        CheckConstraint("available + frozen <= total_balance", name="check_balance_consistency"),
        CheckConstraint("initial_capital > 0", name="check_initial_capital_positive"),
    )

    def __init__(
        self,
        account_no: str,
        name: str,
        initial_capital: Decimal = Decimal("1000000"),
        account_type: AccountType = AccountType.SIMULATE
    ):
        self.account_no = account_no
        self.name = name
        self.initial_capital = initial_capital
        self.account_type = account_type
        self.total_balance = initial_capital
        self.available = initial_capital
        self.frozen = Decimal("0")
        self.market_value = Decimal("0")

    @property
    def total_equity(self) -> Decimal:
        """总权益 = 可用资金 + 冻结资金 + 持仓市值"""
        return self.available + self.frozen + self.market_value

    @property
    def total_return_pct(self) -> Decimal:
        """总收益率"""
        if self.initial_capital <= 0:
            return Decimal("0")
        return (self.total_equity - self.initial_capital) / self.initial_capital

    def freeze(self, amount: Decimal) -> bool:
        """冻结资金"""
        if self.available < amount:
            return False
        self.available -= amount
        self.frozen += amount
        return True

    def unfreeze(self, amount: Decimal) -> bool:
        """解冻资金"""
        if self.frozen < amount:
            return False
        self.frozen -= amount
        self.available += amount
        return True

    def deduct(self, amount: Decimal) -> bool:
        """从冻结资金中扣减（成交后）"""
        if self.frozen < amount:
            return False
        self.frozen -= amount
        self.total_balance -= amount
        return True

    def add(self, amount: Decimal) -> None:
        """增加可用资金（卖出成交后）"""
        self.available += amount
        self.total_balance += amount

    def update_market_value(self) -> None:
        """更新持仓市值（由外部调用，传入计算后的市值）"""
        total_mv = sum(pos.market_value for pos in self.positions)
        self.market_value = total_mv
        # 更新浮动盈亏
        self.unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "account_no": self.account_no,
            "name": self.name,
            "account_type": self.account_type.value,
            "total_balance": float(self.total_balance),
            "available": float(self.available),
            "frozen": float(self.frozen),
            "market_value": float(self.market_value),
            "total_equity": float(self.total_equity),
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "initial_capital": float(self.initial_capital),
            "total_return_pct": float(self.total_return_pct),
            "max_drawdown": float(self.max_drawdown),
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
