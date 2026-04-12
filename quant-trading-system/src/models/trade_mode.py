"""
交易模式配置模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class TradeModeConfig(Base):
    """交易模式配置表"""
    __tablename__ = "trade_mode_config"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 关联
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False, index=True)

    # 模式
    mode: Mapped[str] = mapped_column(String(16), default="manual")  # auto/manual/simulate/pause

    # 自动模式配置
    enable_risk_check: Mapped[bool] = mapped_column(default=True)
    enable_capital_check: Mapped[bool] = mapped_column(default=True)
    max_orders_per_day: Mapped[int] = mapped_column(default=100)

    # 时间戳
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_trade_mode_account", "account_id"),
    )
