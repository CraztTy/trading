"""
策略模型
"""
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import (
    BigInteger, String, Numeric, DateTime, ForeignKey,
    Integer, JSON, Text, Index, Boolean, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.backtest_task import BacktestTask


class StrategyStatus(str, enum.Enum):
    """策略状态"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 运行中
    PAUSED = "paused"         # 暂停
    STOPPED = "stopped"       # 停止
    ERROR = "error"           # 错误


class StrategyType(str, enum.Enum):
    """策略类型"""
    TECHNICAL = "technical"   # 技术分析
    FUNDAMENTAL = "fundamental"  # 基本面
    QUANT = "quant"           # 量化
    ML = "ml"                 # 机器学习
    CUSTOM = "custom"         # 自定义


class Strategy(Base):
    """策略表"""
    __tablename__ = "strategy"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    # 关联
    account_id: Mapped[int] = mapped_column(ForeignKey("account.id"), nullable=False, index=True)

    # 基本信息
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    strategy_type: Mapped[str] = mapped_column(String(16), default=StrategyType.CUSTOM)

    # 策略代码（当前版本）
    code: Mapped[str] = mapped_column(Text, nullable=False)  # Python代码

    # 参数定义（JSON Schema格式）
    # {
    #   "fast_period": {"type": "int", "default": 5, "min": 1, "max": 100, "description": "快速均线周期"},
    #   "slow_period": {"type": "int", "default": 10, "min": 1, "max": 200, "description": "慢速均线周期"}
    # }
    parameters_schema: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # 默认参数值
    default_parameters: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # 状态
    status: Mapped[str] = mapped_column(String(16), default=StrategyStatus.DRAFT, index=True)

    # 运行配置
    symbols: Mapped[List[str]] = mapped_column(JSON, default=list)  # 监控的股票列表

    # 性能统计（运行时更新）
    total_return: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    sharpe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    max_drawdown: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    win_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    total_trades: Mapped[int] = mapped_column(Integer, default=0)

    # 当前版本号
    current_version: Mapped[int] = mapped_column(Integer, default=1)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 关系
    versions: Mapped[List["StrategyVersion"]] = relationship("StrategyVersion", back_populates="strategy", cascade="all, delete-orphan")
    backtests: Mapped[List["StrategyBacktest"]] = relationship("StrategyBacktest", back_populates="strategy", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index("idx_strategy_account_status", "account_id", "status"),
        Index("idx_strategy_type", "strategy_type"),
    )

    def __init__(
        self,
        strategy_id: str,
        account_id: int,
        name: str,
        code: str,
        description: str = "",
        strategy_type: str = StrategyType.CUSTOM,
        parameters_schema: dict = None,
        default_parameters: dict = None,
        symbols: list = None
    ):
        self.strategy_id = strategy_id
        self.account_id = account_id
        self.name = name
        self.code = code
        self.description = description
        self.strategy_type = strategy_type
        self.parameters_schema = parameters_schema or {}
        self.default_parameters = default_parameters or {}
        self.symbols = symbols or []

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "account_id": self.account_id,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type,
            "parameters_schema": self.parameters_schema,
            "default_parameters": self.default_parameters,
            "status": self.status,
            "symbols": self.symbols,
            "total_return": float(self.total_return) if self.total_return else None,
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            "win_rate": float(self.win_rate) if self.win_rate else None,
            "total_trades": self.total_trades,
            "current_version": self.current_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
        }
