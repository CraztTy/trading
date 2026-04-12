"""
订单模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index, text, BigInteger, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import OrderStatus, OrderDirection, OrderType

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.strategy import Strategy
    from src.models.trade import Trade
    from src.models.order_state_history import OrderStateHistory


class Order(Base):
    """订单表"""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # 关联
    strategy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.id"), nullable=True, index=True)
    strategy: Mapped[Optional["Strategy"]] = relationship("Strategy", back_populates="orders")

    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False, index=True)
    account: Mapped["Account"] = relationship("Account", back_populates="orders")

    # 标的
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    symbol_name: Mapped[Optional[str]] = mapped_column(String(32))

    # 订单要素
    direction: Mapped[OrderDirection] = mapped_column(String(8), nullable=False)
    order_type: Mapped[OrderType] = mapped_column(String(16), default=OrderType.LIMIT, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))

    # 状态
    status: Mapped[OrderStatus] = mapped_column(
        String(16), default=OrderStatus.CREATED, nullable=False, index=True
    )

    # 成交统计
    filled_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    filled_avg_price: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"), nullable=False)
    filled_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False, index=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    filled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 错误信息
    error_msg: Mapped[Optional[str]] = mapped_column(String(512))
    remark: Mapped[Optional[str]] = mapped_column(String(256))

    # 关系
    trades: Mapped[List["Trade"]] = relationship("Trade", back_populates="order", lazy="selectin")
    state_history: Mapped[List["OrderStateHistory"]] = relationship(
        "OrderStateHistory",
        back_populates="order",
        lazy="selectin",
        order_by="OrderStateHistory.created_at",
        cascade="all, delete-orphan"
    )

    # 表级约束
    __table_args__ = (
        CheckConstraint("qty > 0", name="check_qty_positive"),
        CheckConstraint("price IS NULL OR price > 0", name="check_price_positive"),
        CheckConstraint("filled_qty >= 0", name="check_filled_qty_non_negative"),
        CheckConstraint("filled_qty <= qty", name="check_filled_qty_not_exceed"),
    )

    def __init__(
        self,
        order_id: str,
        account_id: int,
        symbol: str,
        direction: OrderDirection,
        qty: int,
        price: Optional[Decimal] = None,
        order_type: OrderType = OrderType.LIMIT,
        strategy_id: Optional[int] = None,
        symbol_name: str = ""
    ):
        self.order_id = order_id
        self.account_id = account_id
        self.symbol = symbol
        self.direction = direction
        self.qty = qty
        self.price = price
        self.order_type = order_type
        self.strategy_id = strategy_id
        self.symbol_name = symbol_name

    @property
    def remaining_qty(self) -> int:
        """剩余未成交数量"""
        return self.qty - self.filled_qty

    @property
    def is_filled(self) -> bool:
        """是否全部成交"""
        return self.filled_qty >= self.qty

    @property
    def is_active(self) -> bool:
        """订单是否活跃（可继续成交）"""
        return self.status in [OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL]

    def fill(self, qty: int, price: Decimal) -> None:
        """部分/全部成交"""
        if qty <= 0 or qty > self.remaining_qty:
            raise ValueError(f"Invalid fill qty: {qty}")

        # 计算新的成交均价
        new_amount = self.filled_amount + (price * qty)
        self.filled_qty += qty
        self.filled_avg_price = new_amount / self.filled_qty if self.filled_qty > 0 else Decimal("0")
        self.filled_amount = new_amount

        # 更新状态
        if self.is_filled:
            self.status = OrderStatus.FILLED
            self.filled_at = datetime.now()
        else:
            self.status = OrderStatus.PARTIAL

    def cancel(self) -> bool:
        """撤单"""
        if not self.is_active:
            return False
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.now()
        return True

    def reject(self, reason: str) -> None:
        """拒绝"""
        self.status = OrderStatus.REJECTED
        self.error_msg = reason

    def submit(self) -> None:
        """提交到交易所"""
        if self.status == OrderStatus.CREATED:
            self.status = OrderStatus.PENDING
            self.submitted_at = datetime.now()

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "exchange_order_id": self.exchange_order_id,
            "account_id": self.account_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "direction": self.direction.value if hasattr(self.direction, 'value') else self.direction,
            "order_type": self.order_type.value if hasattr(self.order_type, 'value') else self.order_type,
            "qty": self.qty,
            "price": float(self.price) if self.price else None,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "filled_qty": self.filled_qty,
            "remaining_qty": self.remaining_qty,
            "filled_avg_price": float(self.filled_avg_price),
            "filled_amount": float(self.filled_amount),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "error_msg": self.error_msg,
            "remark": self.remark,
        }
