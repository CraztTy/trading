"""
资金流水模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index, text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import FlowType

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.order import Order
    from src.models.trade import Trade


class BalanceFlow(Base):
    """资金流水表"""
    __tablename__ = "balance_flow"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 关联
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False, index=True)
    account: Mapped["Account"] = relationship("Account", back_populates="balance_flows")

    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    order: Mapped[Optional["Order"]] = relationship("Order")

    trade_id: Mapped[Optional[int]] = mapped_column(ForeignKey("trade.id"), nullable=True, index=True)
    trade: Mapped[Optional["Trade"]] = relationship("Trade")

    # 流水类型
    flow_type: Mapped[FlowType] = mapped_column(String(32), nullable=False, index=True)

    # 金额（正数增加，负数减少）
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # 说明
    description: Mapped[Optional[str]] = mapped_column(String(256))
    remark: Mapped[Optional[str]] = mapped_column(String(512))

    # 时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False, index=True
    )

    def __init__(
        self,
        account_id: int,
        flow_type: FlowType,
        amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        order_id: Optional[int] = None,
        trade_id: Optional[int] = None,
        description: str = "",
        remark: str = ""
    ):
        self.account_id = account_id
        self.flow_type = flow_type
        self.amount = amount
        self.balance_before = balance_before
        self.balance_after = balance_after
        self.order_id = order_id
        self.trade_id = trade_id
        self.description = description
        self.remark = remark

    @classmethod
    def create_order_frozen(
        cls,
        account_id: int,
        order_id: int,
        amount: Decimal,
        balance_before: Decimal
    ) -> "BalanceFlow":
        """创建委托冻结流水"""
        return cls(
            account_id=account_id,
            flow_type=FlowType.ORDER_FROZEN,
            amount=-amount,  # 冻结是负向变动
            balance_before=balance_before,
            balance_after=balance_before - amount,
            order_id=order_id,
            description=f"委托冻结资金: {amount}"
        )

    @classmethod
    def create_order_unfrozen(
        cls,
        account_id: int,
        order_id: int,
        amount: Decimal,
        balance_before: Decimal
    ) -> "BalanceFlow":
        """创建委托解冻流水"""
        return cls(
            account_id=account_id,
            flow_type=FlowType.ORDER_UNFROZEN,
            amount=amount,  # 解冻是正向变动
            balance_before=balance_before,
            balance_after=balance_before + amount,
            order_id=order_id,
            description=f"委托解冻资金: {amount}"
        )

    @classmethod
    def create_trade_buy(
        cls,
        account_id: int,
        order_id: int,
        trade_id: int,
        amount: Decimal,
        balance_before: Decimal
    ) -> "BalanceFlow":
        """创建买入成交流水"""
        return cls(
            account_id=account_id,
            flow_type=FlowType.TRADE_BUY,
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_before - amount,
            order_id=order_id,
            trade_id=trade_id,
            description=f"买入成交扣款: {amount}"
        )

    @classmethod
    def create_trade_sell(
        cls,
        account_id: int,
        order_id: int,
        trade_id: int,
        amount: Decimal,
        balance_before: Decimal
    ) -> "BalanceFlow":
        """创建卖出成交流水"""
        return cls(
            account_id=account_id,
            flow_type=FlowType.TRADE_SELL,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_before + amount,
            order_id=order_id,
            trade_id=trade_id,
            description=f"卖出成交入账: {amount}"
        )

    @classmethod
    def create_fee(
        cls,
        account_id: int,
        trade_id: int,
        flow_type: FlowType,
        amount: Decimal,
        balance_before: Decimal
    ) -> "BalanceFlow":
        """创建费用流水"""
        fee_name = {
            FlowType.COMMISSION: "佣金",
            FlowType.STAMP_TAX: "印花税",
            FlowType.TRANSFER_FEE: "过户费"
        }.get(flow_type, "费用")

        return cls(
            account_id=account_id,
            flow_type=flow_type,
            amount=-amount,
            balance_before=balance_before,
            balance_after=balance_before - amount,
            trade_id=trade_id,
            description=f"{fee_name}: {amount}"
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "account_id": self.account_id,
            "order_id": self.order_id,
            "trade_id": self.trade_id,
            "flow_type": self.flow_type.value,
            "amount": float(self.amount),
            "balance_before": float(self.balance_before),
            "balance_after": float(self.balance_after),
            "description": self.description,
            "remark": self.remark,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
