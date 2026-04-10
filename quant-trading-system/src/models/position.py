"""
持仓模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, String, Numeric, DateTime, ForeignKey, Index, text, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import OrderDirection

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.strategy import Strategy


class Position(Base):
    """持仓表"""
    __tablename__ = "position"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 关联
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False)
    account: Mapped["Account"] = relationship("Account", back_populates="positions")

    strategy_id: Mapped[Optional[int]] = mapped_column(ForeignKey("strategy.id"), nullable=True)
    strategy: Mapped[Optional["Strategy"]] = relationship("Strategy")

    # 标的
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    symbol_name: Mapped[Optional[str]] = mapped_column(String(32))

    # 数量（T+1制度）
    total_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frozen_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 成本
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"), nullable=False)
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    # 市值
    market_price: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    # 盈亏
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)
    unrealized_pnl_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"), nullable=False)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0"), nullable=False)

    # 时间
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        onupdate=text("NOW()"),
        nullable=False
    )

    # 唯一约束：一个账户一个标的只能有一条持仓
    __table_args__ = (
        UniqueConstraint("account_id", "symbol", name="uix_position_account_symbol"),
        Index("idx_position_account_symbol", "account_id", "symbol"),
        Index("idx_position_account", "account_id"),
    )

    def __init__(
        self,
        account_id: int,
        symbol: str,
        symbol_name: str = "",
        strategy_id: Optional[int] = None
    ):
        self.account_id = account_id
        self.symbol = symbol
        self.symbol_name = symbol_name
        self.strategy_id = strategy_id

    @property
    def weight(self) -> Decimal:
        """持仓权重（占总资产）"""
        if not self.account or self.account.total_balance <= 0:
            return Decimal("0")
        return self.market_value / self.account.total_balance

    def update_market_price(self, price: Decimal) -> None:
        """更新市价和计算浮动盈亏"""
        self.market_price = price
        self.market_value = price * self.total_qty

        if self.cost_amount > 0 and self.total_qty > 0:
            self.unrealized_pnl = self.market_value - self.cost_amount
            self.unrealized_pnl_pct = self.unrealized_pnl / self.cost_amount
        else:
            self.unrealized_pnl = Decimal("0")
            self.unrealized_pnl_pct = Decimal("0")

    def add(self, qty: int, price: Decimal, available: bool = False) -> None:
        """买入增加持仓"""
        if self.total_qty == 0:
            # 新建仓
            self.cost_price = price
            self.cost_amount = price * qty
            self.opened_at = datetime.now()
        else:
            # 加仓，计算新的平均成本
            total_cost = self.cost_amount + (price * qty)
            self.total_qty += qty
            self.cost_price = total_cost / self.total_qty
            self.cost_amount = total_cost

        self.total_qty += qty
        if available:
            self.available_qty += qty

        self._update_market_value()

    def reduce(self, qty: int, price: Decimal) -> Decimal:
        """卖出减少持仓，返回实现盈亏"""
        if qty > self.total_qty:
            raise ValueError(f"卖出数量{qty}超过持仓{self.total_qty}")

        # 计算实现盈亏
        sell_cost = self.cost_price * qty
        sell_amount = price * qty
        realized_pnl = sell_amount - sell_cost

        # 更新持仓
        self.total_qty -= qty
        self.available_qty = min(self.available_qty, self.total_qty)
        self.cost_amount = self.cost_price * self.total_qty
        self.realized_pnl += realized_pnl

        if self.total_qty == 0:
            # 清仓
            self.cost_price = Decimal("0")
            self.cost_amount = Decimal("0")
            self.opened_at = None

        self._update_market_value()
        return realized_pnl

    def freeze(self, qty: int) -> bool:
        """冻结持仓（委托卖出时）"""
        if self.available_qty < qty:
            return False
        self.available_qty -= qty
        self.frozen_qty += qty
        return True

    def unfreeze(self, qty: int) -> bool:
        """解冻持仓（撤单时）"""
        if self.frozen_qty < qty:
            return False
        self.frozen_qty -= qty
        self.available_qty += qty
        return True

    def settle_t1(self) -> None:
        """T+1日终清算：将总持仓同步到可用持仓"""
        self.available_qty = self.total_qty

    def _update_market_value(self) -> None:
        """更新市值"""
        self.market_value = self.market_price * self.total_qty
        self.unrealized_pnl = self.market_value - self.cost_amount
        if self.cost_amount > 0:
            self.unrealized_pnl_pct = self.unrealized_pnl / self.cost_amount

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "symbol_name": self.symbol_name,
            "total_qty": self.total_qty,
            "available_qty": self.available_qty,
            "frozen_qty": self.frozen_qty,
            "cost_price": float(self.cost_price),
            "cost_amount": float(self.cost_amount),
            "market_price": float(self.market_price),
            "market_value": float(self.market_value),
            "unrealized_pnl": float(self.unrealized_pnl),
            "unrealized_pnl_pct": float(self.unrealized_pnl_pct),
            "realized_pnl": float(self.realized_pnl),
            "weight": float(self.weight),
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
