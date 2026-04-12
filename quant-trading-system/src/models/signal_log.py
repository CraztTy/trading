"""
信号生成记录模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Dict

from sqlalchemy import String, Numeric, DateTime, ForeignKey, BigInteger, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.account import Account


class SignalLog(Base):
    """信号生成记录表"""
    __tablename__ = "signal_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    signal_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    strategy_id: Mapped[str] = mapped_column(String(32), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False)

    # 信号内容
    symbol: Mapped[str] = mapped_column(String(16), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(8), nullable=False)  # buy/sell
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    volume: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)
    reason: Mapped[str] = mapped_column(String(256))

    # 处理状态
    status: Mapped[str] = mapped_column(String(16), default="generated")  # generated, audited, executed, rejected
    audit_result: Mapped[Optional[Dict]] = mapped_column(JSON)
    order_id: Mapped[Optional[str]] = mapped_column(String(32))

    # 时间戳
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 关系
    account: Mapped["Account"] = relationship("Account")

    def __init__(
        self,
        signal_id: str,
        strategy_id: str,
        account_id: int,
        symbol: str,
        signal_type: str,
        price: Optional[Decimal] = None,
        volume: Optional[int] = None,
        confidence: float = 0.5,
        reason: str = "",
    ):
        self.signal_id = signal_id
        self.strategy_id = strategy_id
        self.account_id = account_id
        self.symbol = symbol
        self.signal_type = signal_type
        self.price = price
        self.volume = volume
        self.confidence = confidence
        self.reason = reason

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "strategy_id": self.strategy_id,
            "account_id": self.account_id,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "price": float(self.price) if self.price else None,
            "volume": self.volume,
            "confidence": float(self.confidence),
            "reason": self.reason,
            "status": self.status,
            "audit_result": self.audit_result,
            "order_id": self.order_id,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }
