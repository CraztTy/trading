"""
订单状态历史模型

用于持久化存储订单状态变更历史，支持审计和查询。
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Any
import json

from sqlalchemy import String, DateTime, ForeignKey, Index, text, BigInteger, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base
from src.models.enums import OrderStatus

if TYPE_CHECKING:
    from src.models.order import Order


class OrderStateHistory(Base):
    """订单状态历史表"""
    __tablename__ = "order_state_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 关联订单
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    order: Mapped["Order"] = relationship("Order", back_populates="state_history")

    # 状态信息
    from_status: Mapped[str] = mapped_column(String(16), nullable=False)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)

    # 变更原因
    reason: Mapped[Optional[str]] = mapped_column(String(256))

    # 附加元数据（JSON格式存储）
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("NOW()"),
        nullable=False,
        index=True
    )

    # 表级索引
    __table_args__ = (
        Index(
            "idx_order_state_history_order_created",
            "order_id",
            "created_at"
        ),
    )

    def __init__(
        self,
        order_id: int,
        from_status: OrderStatus | str,
        to_status: OrderStatus | str,
        reason: str = "",
        metadata: Optional[dict] = None
    ):
        self.order_id = order_id
        self.from_status = from_status.value if isinstance(from_status, OrderStatus) else from_status
        self.to_status = to_status.value if isinstance(to_status, OrderStatus) else to_status
        self.reason = reason
        if metadata:
            self.metadata_json = json.dumps(metadata, ensure_ascii=False)

    def get_metadata(self) -> Optional[dict]:
        """获取元数据字典"""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError:
                return None
        return None

    def set_metadata(self, value: Optional[dict]):
        """设置元数据字典"""
        if value:
            self.metadata_json = json.dumps(value, ensure_ascii=False)
        else:
            self.metadata_json = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "reason": self.reason,
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"OrderStateHistory("
            f"order_id={self.order_id}, "
            f"{self.from_status} -> {self.to_status}, "
            f"created_at={self.created_at}"
            f")"
        )
