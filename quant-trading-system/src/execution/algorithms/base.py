"""
算法执行基类

定义算法执行的标准接口和通用功能
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.order import Order
from src.models.enums import OrderStatus
from src.services.order_service import OrderService
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class AlgorithmStatus(str, Enum):
    """算法执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class AlgorithmConfig:
    """算法配置"""
    duration_seconds: int = 300  # 执行时长（秒）
    num_slices: int = 5          # 切片数量
    min_slice_size: int = 100    # 最小切片大小（股）
    max_participation_rate: float = 0.1  # 最大参与率（占市场成交量比例）
    volume_profile: str = "flat"  # 成交量分布 (flat, U, increasing, decreasing)
    price_limit_pct: Optional[float] = None  # 价格限制百分比

    def __post_init__(self):
        """验证配置"""
        if self.duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        if self.num_slices <= 0:
            raise ValueError("num_slices must be positive")
        if self.min_slice_size <= 0:
            raise ValueError("min_slice_size must be positive")


@dataclass
class AlgorithmProgress:
    """算法执行进度"""
    status: AlgorithmStatus
    completed_slices: int
    total_slices: int
    filled_qty: int
    total_qty: int
    completion_pct: float
    estimated_completion_time: Optional[int] = None  # 预计剩余时间（秒）


@dataclass
class AlgorithmMetrics:
    """算法执行指标"""
    total_volume: int
    vwap_price: Decimal
    min_price: Decimal
    max_price: Decimal
    avg_slice_time_ms: int


class ExecutionAlgorithm(ABC):
    """
    算法执行基类

    所有执行算法的抽象基类，定义标准接口
    """

    def __init__(
        self,
        order: Order,
        config: AlgorithmConfig,
        session: AsyncSession
    ):
        """
        初始化算法

        Args:
            order: 订单
            config: 算法配置
            session: 数据库会话
        """
        self.order = order
        self.config = config
        self.session = session
        self.status = AlgorithmStatus.PENDING
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._cancelled = False
        self._paused = False
        self._order_service: Optional[OrderService] = None

        # 执行记录
        self.slice_sizes: list = []
        self.completed_slices = 0
        self.executed_prices: list[tuple[int, Decimal]] = []

    def _get_order_service(self) -> OrderService:
        """获取订单服务（懒加载）"""
        if self._order_service is None:
            self._order_service = OrderService(self.session)
        return self._order_service

    @abstractmethod
    async def execute(self) -> bool:
        """
        执行算法

        Returns:
            bool: 执行是否成功
        """
        pass

    @abstractmethod
    def _calculate_slice_sizes(self, total_qty: int, num_slices: int) -> list[int]:
        """
        计算切片大小

        Args:
            total_qty: 总数量
            num_slices: 切片数量

        Returns:
            list[int]: 切片大小列表
        """
        pass

    async def pause(self) -> None:
        """暂停执行"""
        if self.status == AlgorithmStatus.RUNNING:
            self._paused = True
            self.status = AlgorithmStatus.PAUSED
            logger.info(f"算法已暂停: {self.order.order_id}")

    async def resume(self) -> None:
        """恢复执行"""
        if self.status == AlgorithmStatus.PAUSED:
            self._paused = False
            self.status = AlgorithmStatus.RUNNING
            logger.info(f"算法已恢复: {self.order.order_id}")

    async def cancel(self) -> None:
        """取消执行"""
        self._cancelled = True
        self.status = AlgorithmStatus.CANCELLED
        logger.info(f"算法已取消: {self.order.order_id}")

    def get_progress(self) -> AlgorithmProgress:
        """
        获取执行进度

        Returns:
            AlgorithmProgress: 进度信息
        """
        completion_pct = (
            self.completed_slices / len(self.slice_sizes)
            if self.slice_sizes else 0.0
        )

        filled_qty = sum(qty for qty, _ in self.executed_prices)

        eta = None
        if self.status == AlgorithmStatus.RUNNING and self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if self.completed_slices > 0:
                avg_time_per_slice = elapsed / self.completed_slices
                remaining_slices = len(self.slice_sizes) - self.completed_slices
                eta = int(avg_time_per_slice * remaining_slices)

        return AlgorithmProgress(
            status=self.status,
            completed_slices=self.completed_slices,
            total_slices=len(self.slice_sizes),
            filled_qty=filled_qty,
            total_qty=self.order.qty,
            completion_pct=completion_pct,
            estimated_completion_time=eta
        )

    def get_metrics(self) -> AlgorithmMetrics:
        """
        获取执行指标

        Returns:
            AlgorithmMetrics: 指标信息
        """
        total_volume = sum(qty for qty, _ in self.executed_prices)

        if total_volume > 0:
            vwap = sum(
                qty * price for qty, price in self.executed_prices
            ) / total_volume
        else:
            vwap = Decimal("0")

        prices = [price for _, price in self.executed_prices]
        min_price = min(prices) if prices else Decimal("0")
        max_price = max(prices) if prices else Decimal("0")

        # 计算平均切片执行时间
        avg_slice_time = 0
        if self.start_time and self.end_time and self.completed_slices > 0:
            total_time = (self.end_time - self.start_time).total_seconds() * 1000
            avg_slice_time = int(total_time / self.completed_slices)

        return AlgorithmMetrics(
            total_volume=total_volume,
            vwap_price=vwap,
            min_price=min_price,
            max_price=max_price,
            avg_slice_time_ms=avg_slice_time
        )

    async def _execute_slice(self, qty: int, price: Decimal) -> bool:
        """
        执行单个切片

        Args:
            qty: 数量
            price: 价格

        Returns:
            bool: 是否成功
        """
        try:
            order_service = self._get_order_service()

            success = await order_service.fill_order(
                self.order,
                fill_qty=qty,
                fill_price=price
            )

            if success:
                self.executed_prices.append((qty, price))
                logger.debug(
                    f"切片执行成功: {qty} @ {price}",
                    order_id=self.order.order_id
                )

            return success

        except Exception as e:
            logger.error(f"切片执行失败: {e}", order_id=self.order.order_id)
            return False

    def _align_to_lot(self, qty: int, lot_size: int = 100) -> int:
        """
        对齐到最小交易单位

        Args:
            qty: 数量
            lot_size: 每手股数

        Returns:
            int: 对齐后的数量
        """
        return (qty // lot_size) * lot_size

    def estimate_completion_time(self) -> int:
        """
        估算完成时间

        Returns:
            int: 预计剩余时间（秒）
        """
        if self.status != AlgorithmStatus.RUNNING or not self.start_time:
            return 0

        elapsed = (datetime.now() - self.start_time).total_seconds()
        if self.completed_slices == 0:
            return self.config.duration_seconds

        avg_time_per_slice = elapsed / self.completed_slices
        remaining_slices = len(self.slice_sizes) - self.completed_slices

        return int(avg_time_per_slice * remaining_slices)
