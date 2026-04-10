"""
成交模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index, text, BigInteger, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import OrderDirection, FlowType

if TYPE_CHECKING:
    from src.models.order import Order
    from src.models.strategy import Strategy
    from src.models.account import Account


class Trade(Base):
    """成交表"""
    __tablename__ = "trade"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    trade_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    # 关联
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    order: Mapped["Order"] = relationship("Order", back_populates="trades")

    strategy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.id"), nullable=True, index=True)
    strategy: Mapped[Optional["Strategy"]] = relationship("Strategy", back_populates="trades")

    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False, index=True)
    account: Mapped["Account"] = relationship("Account")

    # 标的
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    symbol_name: Mapped[Optional[str]] = mapped_column(String(32))

    # 成交要素
    direction: Mapped[OrderDirection] = mapped_column(String(8), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # 费用明细
    commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    stamp_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    transfer_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    total_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)

    # 时间
    trade_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # 对账标记
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    def __init__(
        self,
        trade_id: str,
        order_id: int,
        account_id: int,
        symbol: str,
        direction: OrderDirection,
        qty: int,
        price: Decimal,
        trade_time: datetime,
        strategy_id: Optional[int] = None,
        symbol_name: str = ""
    ):
        self.trade_id = trade_id
        self.order_id = order_id
        self.account_id = account_id
        self.symbol = symbol
        self.direction = direction
        self.qty = qty
        self.price = price
        self.amount = price * qty
        self.trade_time = trade_time
        self.strategy_id = strategy_id
        self.symbol_name = symbol_name

    def calculate_fees(self, commission_rate: Decimal, min_commission: Decimal,
                       stamp_tax_rate: Decimal, transfer_fee_rate: Decimal) -> None:
        """计算交易费用"""
        # 佣金
        self.commission = max(self.amount * commission_rate, min_commission)

        # 印花税（仅卖出）
        if self.direction == OrderDirection.SELL:
            self.stamp_tax = self.amount * stamp_tax_rate
        else:
            self.stamp_tax = Decimal("0")

        # 过户费
        self.transfer_fee = self.amount * transfer_fee_rate

        # 总费用
        self.total_fee = self.commission + self.stamp_tax + self.transfer_fee

    @property
    def net_amount(self) -> Decimal:
        """净成交金额（考虑费用）"""
        if self.direction == OrderDirection.BUY:
            return self.amount + self.total_fee
        else:
            return self.amount - self.total_fee

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "trade_id": self.trade_id,
            "order_id": self.order_id,
            "strategy_id": self.strategy_id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "direction": self.direction.value,
            "qty": self.qty,
            "price": float(self.price),
            "amount": float(self.amount),
            "commission": float(self.commission),
            "stamp_tax": float(self.stamp_tax),
            "transfer_fee": float(self.transfer_fee),
            "total_fee": float(self.total_fee),
            "net_amount": float(self.net_amount),
            "trade_time": self.trade_time.isoformat() if self.trade_time else None,
            "reconciled": self.reconciled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
