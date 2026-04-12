"""
数据质量监控模型
"""
from datetime import datetime
from typing import Optional, Dict, List

from sqlalchemy import String, Numeric, DateTime, BigInteger, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class DataQualityLog(Base):
    """数据质量监控表"""
    __tablename__ = "data_quality_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)

    # 质量评分
    completeness: Mapped[float] = mapped_column(Numeric(4, 3))
    timeliness: Mapped[float] = mapped_column(Numeric(4, 3))
    accuracy: Mapped[float] = mapped_column(Numeric(4, 3))
    overall: Mapped[float] = mapped_column(Numeric(4, 3))

    # 问题记录
    issues: Mapped[List[str]] = mapped_column(JSON)

    # 原始数据
    raw_data: Mapped[Optional[Dict]] = mapped_column(JSON)

    # 时间戳
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    def __init__(
        self,
        symbol: str,
        completeness: float,
        timeliness: float,
        accuracy: float,
        overall: float,
        issues: List[str],
        raw_data: Optional[Dict] = None,
    ):
        self.symbol = symbol
        self.completeness = completeness
        self.timeliness = timeliness
        self.accuracy = accuracy
        self.overall = overall
        self.issues = issues
        self.raw_data = raw_data

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "completeness": float(self.completeness),
            "timeliness": float(self.timeliness),
            "accuracy": float(self.accuracy),
            "overall": float(self.overall),
            "issues": self.issues,
            "raw_data": self.raw_data,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }
