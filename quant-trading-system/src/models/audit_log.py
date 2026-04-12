"""
风控审核日志模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Dict, List

from sqlalchemy import String, Numeric, DateTime, ForeignKey, BigInteger, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.signal_log import SignalLog


class AuditLog(Base):
    """风控审核日志表"""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    audit_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    signal_id: Mapped[str] = mapped_column(ForeignKey("signal_log.signal_id"), nullable=False, index=True)

    # 审核结果
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rejected_by: Mapped[Optional[str]] = mapped_column(String(16))  # 规则代码
    reject_reason: Mapped[Optional[str]] = mapped_column(String(256))

    # 审核详情
    checks: Mapped[List[Dict]] = mapped_column(JSON)  # [{"rule": "R001", "passed": true, "message": ""}, ...]
    processing_time_ms: Mapped[float] = mapped_column(Numeric(10, 3))

    # 上下文信息
    context: Mapped[Optional[Dict]] = mapped_column(JSON)  # 持仓、账户等信息

    # 时间戳
    audit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # 关系
    signal: Mapped["SignalLog"] = relationship("SignalLog")

    def __init__(
        self,
        audit_id: str,
        signal_id: str,
        approved: bool,
        checks: List[Dict],
        processing_time_ms: float,
        rejected_by: Optional[str] = None,
        reject_reason: Optional[str] = None,
        context: Optional[Dict] = None,
    ):
        self.audit_id = audit_id
        self.signal_id = signal_id
        self.approved = approved
        self.checks = checks
        self.processing_time_ms = processing_time_ms
        self.rejected_by = rejected_by
        self.reject_reason = reject_reason
        self.context = context

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "audit_id": self.audit_id,
            "signal_id": self.signal_id,
            "approved": self.approved,
            "rejected_by": self.rejected_by,
            "reject_reason": self.reject_reason,
            "checks": self.checks,
            "processing_time_ms": float(self.processing_time_ms),
            "context": self.context,
            "audit_time": self.audit_time.isoformat() if self.audit_time else None,
        }
