"""
TWAP (Time Weighted Average Price) 算法

时间加权平均价格算法：
- 将订单分成多个小单
- 在时间区间内均匀执行
- 目标是接近时间加权平均价格
"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import List

from src.execution.algorithms.base import (
    ExecutionAlgorithm, AlgorithmConfig, AlgorithmStatus
)
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class TWAPAlgorithm(ExecutionAlgorithm):
    """
    TWAP算法实现

    特点：
    1. 将大单分成多个等份（或近似等份）
    2. 按固定时间间隔执行
    3. 适用于需要平滑执行、减少市场冲击的场景
    """

    def __init__(self, order, config: AlgorithmConfig, session):
        """初始化TWAP算法"""
        super().__init__(order, config, session)
        self.total_slices = config.num_slices
        self.slice_interval = config.duration_seconds / config.num_slices

        # 预计算切片大小
        remaining_qty = order.qty - order.filled_qty
        self.slice_sizes = self._calculate_slice_sizes(
            remaining_qty, config.num_slices
        )

    def _calculate_slice_sizes(self, total_qty: int, num_slices: int) -> List[int]:
        """
        计算TWAP切片大小

        策略：
        1. 基础等分
        2. 余数分配到最后一个切片
        3. 每个切片至少min_slice_size
        4. 对齐到100股（A股）

        Args:
            total_qty: 总数量
            num_slices: 切片数量

        Returns:
            List[int]: 切片大小列表
        """
        if total_qty <= 0:
            return []

        # 计算基础切片大小
        base_size = total_qty // num_slices
        remainder = total_qty % num_slices

        slices = []
        for i in range(num_slices):
            # 基础大小 + 余数分配
            size = base_size + (1 if i < remainder else 0)

            # 对齐到100股
            size = self._align_to_lot(size)

            # 确保至少min_slice_size
            if size < self.config.min_slice_size:
                # 如果太小，尝试合并
                continue

            slices.append(size)

        # 处理合并后剩下的数量
        assigned = sum(slices)
        remaining = total_qty - assigned

        if remaining > 0:
            # 将剩余数量加到最后一个切片
            if slices:
                slices[-1] += self._align_to_lot(remaining)
            else:
                # 如果所有切片都太小，创建一个大的
                slices = [self._align_to_lot(total_qty)]

        return slices

    async def execute(self) -> bool:
        """
        执行TWAP算法

        按时间间隔依次执行各个切片

        Returns:
            bool: 执行是否成功
        """
        try:
            self.status = AlgorithmStatus.RUNNING
            self.start_time = datetime.now()

            logger.info(
                f"开始TWAP执行",
                order_id=self.order.order_id,
                total_slices=len(self.slice_sizes),
                slice_interval=self.slice_interval
            )

            for i, slice_size in enumerate(self.slice_sizes):
                # 检查是否被取消
                if self._cancelled:
                    logger.info(f"TWAP执行被取消", order_id=self.order.order_id)
                    return False

                # 检查是否暂停
                while self._paused:
                    await asyncio.sleep(0.1)

                # 获取当前价格（使用订单价格或市场价）
                execution_price = self._get_execution_price()

                # 执行切片
                success = await self._execute_slice(slice_size, execution_price)

                if success:
                    self.completed_slices += 1
                    logger.debug(
                        f"TWAP切片 {i+1}/{len(self.slice_sizes)} 完成",
                        order_id=self.order.order_id,
                        qty=slice_size
                    )
                else:
                    logger.warning(
                        f"TWAP切片执行失败",
                        order_id=self.order.order_id,
                        slice_index=i
                    )

                # 等待到下一个切片时间（最后一个切片不需要等待）
                if i < len(self.slice_sizes) - 1:
                    await asyncio.sleep(self.slice_interval)

            # 执行完成
            self.end_time = datetime.now()

            if self.completed_slices == len(self.slice_sizes):
                self.status = AlgorithmStatus.COMPLETED
                logger.info(
                    f"TWAP执行完成",
                    order_id=self.order.order_id,
                    completed_slices=self.completed_slices
                )
                return True
            else:
                # 部分完成
                if self._cancelled:
                    self.status = AlgorithmStatus.CANCELLED
                else:
                    self.status = AlgorithmStatus.FAILED
                return False

        except Exception as e:
            self.status = AlgorithmStatus.FAILED
            self.end_time = datetime.now()
            logger.error(f"TWAP执行异常: {e}", order_id=self.order.order_id)
            return False

    def _get_execution_price(self) -> Decimal:
        """
        获取执行价格

        对于TWAP，使用订单限价或当前市场价

        Returns:
            Decimal: 执行价格
        """
        if self.order.price:
            return self.order.price
        # TODO: 从市场数据获取当前价格
        return Decimal("0")
