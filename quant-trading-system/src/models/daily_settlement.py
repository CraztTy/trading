"""
日终结算模型
"""
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String, Numeric, Date, DateTime, ForeignKey, Index, text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.account import Account


class DailySettlement(Base):
    """日终结算表"""
    __tablename__ = "daily_settlement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 关联
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False, index=True)
    account: Mapped["Account"] = relationship("Account", back_populates="settlements")

    # 交易日期
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # 资金快照
    begin_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    end_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # 资金变动
    deposit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    withdraw: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    total_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    # 持仓快照
    position_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    # 交易统计
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filled_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_volume: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_turnover: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    # 对账状态
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    reconcile_diff: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

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

    # 唯一约束：一个账户一天只能有一条结算记录
    __table_args__ = (
        Index("idx_settlement_account_date", "account_id", "trade_date", unique=True),
    )

    def __init__(
        self,
        account_id: int,
        trade_date: date,
        begin_balance: Decimal,
        end_balance: Decimal
    ):
        self.account_id = account_id
        self.trade_date = trade_date
        self.begin_balance = begin_balance
        self.end_balance = end_balance

    @property
    def net_pnl(self) -> Decimal:
        """净盈亏（已实现盈亏 - 费用）"""
        return self.realized_pnl - self.total_fee

    @property
    def return_pct(self) -> Decimal:
        """日收益率"""
        if self.begin_balance <= 0:
            return Decimal("0")
        return (self.end_balance - self.begin_balance) / self.begin_balance

    def reconcile(self, actual_balance: Decimal) -> bool:
        """
        对账
        返回是否对账成功
        """
        diff = actual_balance - self.end_balance
        self.reconcile_diff = diff
        self.reconciled = abs(diff) < Decimal("0.01")  # 允许0.01元误差
        return self.reconciled

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "begin_balance": float(self.begin_balance),
            "end_balance": float(self.end_balance),
            "deposit": float(self.deposit),
            "withdraw": float(self.withdraw),
            "realized_pnl": float(self.realized_pnl),
            "total_fee": float(self.total_fee),
            "net_pnl": float(self.net_pnl),
            "return_pct": float(self.return_pct),
            "position_count": self.position_count,
            "position_value": float(self.position_value),
            "total_orders": self.total_orders,
            "filled_orders": self.filled_orders,
            "total_trades": self.total_trades,
            "total_volume": self.total_volume,
            "total_turnover": float(self.total_turnover),
            "reconciled": self.reconciled,
            "reconcile_diff": float(self.reconcile_diff),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
