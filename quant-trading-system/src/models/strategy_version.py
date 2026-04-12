"""
策略版本模型
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, String, DateTime, ForeignKey, Integer, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.strategy import Strategy


class StrategyVersion(Base):
    """策略版本表"""
    __tablename__ = "strategy_version"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # 关联
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategy.id"), nullable=False, index=True)
    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="versions")

    # 版本信息
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # 代码
    code: Mapped[str] = mapped_column(Text, nullable=False)

    # 变更说明
    changelog: Mapped[Optional[str]] = mapped_column(Text)

    # 参数定义
    parameters_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    default_parameters: Mapped[dict] = mapped_column(JSON, default=dict)

    # 创建信息
    created_by: Mapped[Optional[str]] = mapped_column(String(32))  # user/system
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # 唯一约束：策略+版本号
    __table_args__ = (
        Index("idx_strategy_version", "strategy_id", "version", unique=True),
    )

    def __init__(
        self,
        strategy_id: int,
        version: int,
        code: str,
        changelog: str = "",
        parameters_schema: dict = None,
        default_parameters: dict = None,
        created_by: str = "user"
    ):
        self.strategy_id = strategy_id
        self.version = version
        self.code = code
        self.changelog = changelog
        self.parameters_schema = parameters_schema or {}
        self.default_parameters = default_parameters or {}
        self.created_by = created_by

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "version": self.version,
            "changelog": self.changelog,
            "parameters_schema": self.parameters_schema,
            "default_parameters": self.default_parameters,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
