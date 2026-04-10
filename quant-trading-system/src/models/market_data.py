"""
行情快照模型
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Numeric, DateTime, Index, text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class MarketDataSnapshot(Base):
    """行情快照表"""
    __tablename__ = "market_data_snapshot"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 标的
    symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    # 快照时间
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # 价格
    open: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    close: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    pre_close: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))

    # 成交量额
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))

    # 买卖盘一档（简化存储）
    bid_price_1: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    bid_vol_1: Mapped[Optional[int]] = mapped_column(BigInteger)
    ask_price_1: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    ask_vol_1: Mapped[Optional[int]] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    # 复合索引
    __table_args__ = (
        Index("idx_snapshot_symbol_time", "symbol", "snapshot_time"),
    )

    def __init__(
        self,
        symbol: str,
        snapshot_time: datetime,
        open: Optional[Decimal] = None,
        high: Optional[Decimal] = None,
        low: Optional[Decimal] = None,
        close: Optional[Decimal] = None,
        pre_close: Optional[Decimal] = None,
        volume: Optional[int] = None,
        amount: Optional[Decimal] = None,
        bid_price_1: Optional[Decimal] = None,
        bid_vol_1: Optional[int] = None,
        ask_price_1: Optional[Decimal] = None,
        ask_vol_1: Optional[int] = None,
    ):
        self.symbol = symbol
        self.snapshot_time = snapshot_time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.pre_close = pre_close
        self.volume = volume
        self.amount = amount
        self.bid_price_1 = bid_price_1
        self.bid_vol_1 = bid_vol_1
        self.ask_price_1 = ask_price_1
        self.ask_vol_1 = ask_vol_1

    @property
    def change_pct(self) -> Optional[Decimal]:
        """涨跌幅"""
        if self.pre_close and self.pre_close > 0 and self.close:
            return (self.close - self.pre_close) / self.pre_close
        return None

    @property
    def spread(self) -> Optional[Decimal]:
        """买卖价差"""
        if self.ask_price_1 and self.bid_price_1:
            return self.ask_price_1 - self.bid_price_1
        return None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "snapshot_time": self.snapshot_time.isoformat() if self.snapshot_time else None,
            "open": float(self.open) if self.open else None,
            "high": float(self.high) if self.high else None,
            "low": float(self.low) if self.low else None,
            "close": float(self.close) if self.close else None,
            "pre_close": float(self.pre_close) if self.pre_close else None,
            "change_pct": float(self.change_pct) if self.change_pct else None,
            "volume": self.volume,
            "amount": float(self.amount) if self.amount else None,
            "bid_price_1": float(self.bid_price_1) if self.bid_price_1 else None,
            "bid_vol_1": self.bid_vol_1,
            "ask_price_1": float(self.ask_price_1) if self.ask_price_1 else None,
            "ask_vol_1": self.ask_vol_1,
            "spread": float(self.spread) if self.spread else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
