"""
VWAP (Volume Weighted Average Price) 算法

成交量加权平均价格算法：
- 按预测的成交量分布执行
- 目标是接近市场VWAP
- 适用于希望跟随市场节奏的大单执行
"""
import asyncio
import random
from datetime import datetime
from decimal import Decimal
from typing import List

from src.execution.algorithms.base import (
    ExecutionAlgorithm, AlgorithmConfig, AlgorithmStatus
)
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class VWAPAlgorithm(ExecutionAlgorithm):
    """
    VWAP算法实现

    特点：
    1. 根据历史成交量分布确定切片大小
    2. 在成交量大的时段执行更多
    3. 更紧密跟踪市场VWAP
    """

    def __init__(self, order, config: AlgorithmConfig, session):
        """初始化VWAP算法"""
        super().__init__(order, config, session)
        self.volume_profile = config.volume_profile
        self.total_slices = config.num_slices
        self.slice_interval = config.duration_seconds / config.num_slices

        # 计算成交量分布
        remaining_qty = order.qty - order.filled_qty
        profile = self._calculate_volume_profile(
            config.num_slices, config.volume_profile
        )
        self.slice_sizes = self._apply_volume_profile(remaining_qty, profile)

    def _calculate_volume_profile(self, num_slices: int, profile_type: str) -> List[float]:
        """
        计算成交量分布

        Args:
            num_slices: 切片数量
            profile_type: 分布类型 (flat, U, increasing, decreasing)

        Returns:
            List[float]: 各切片占比列表（总和为1）
        """
        if profile_type == "flat":
            # 均匀分布
            return [1.0 / num_slices] * num_slices

        elif profile_type == "U":
            # U型分布（两头大中间小，模拟开盘收盘高峰）
            weights = []
            for i in range(num_slices):
                # 使用抛物线模拟U型
                x = (i / (num_slices - 1)) * 2 - 1  # 映射到[-1, 1]
                weight = x * x  # 抛物线
                weights.append(weight)

            # 归一化
            total = sum(weights)
            return [w / total for w in weights]

        elif profile_type == "increasing":
            # 递增分布（尾盘大）
            weights = list(range(1, num_slices + 1))
            total = sum(weights)
            return [w / total for w in weights]

        elif profile_type == "decreasing":
            # 递减分布（开盘大）
            weights = list(range(num_slices, 0, -1))
            total = sum(weights)
            return [w / total for w in weights]

        else:
            # 默认均匀分布
            return [1.0 / num_slices] * num_slices

    def _apply_volume_profile(
        self,
        total_qty: int,
        profile: List[float]
    ) -> List[int]:
        """
        应用成交量分布到切片大小

        Args:
            total_qty: 总数量
            profile: 成交量分布

        Returns:
            List[int]: 切片大小列表
        """
        if total_qty <= 0:
            return []

        slices = []
        remaining = total_qty

        for i, ratio in enumerate(profile[:-1]):  # 最后一个单独处理
            # 计算切片大小
            size = int(total_qty * ratio)
            size = self._align_to_lot(size)

            # 确保至少min_slice_size
            if size < self.config.min_slice_size:
                size = 0

            if size > remaining:
                size = self._align_to_lot(remaining)

            if size > 0:
                slices.append(size)
                remaining -= size

        # 最后一个切片包含剩余所有
        if remaining > 0:
            final_slice = self._align_to_lot(remaining)
            if final_slice > 0:
                slices.append(final_slice)

        return slices

    def _calculate_slice_sizes(self, total_qty: int, num_slices: int) -> List[int]:
        """
        计算VWAP切片大小（已预计算）

        Args:
            total_qty: 总数量
            num_slices: 切片数量

        Returns:
            List[int]: 切片大小列表
        """
        # VWAP使用预计算的slice_sizes
        return self.slice_sizes

    async def execute(self) -> bool:
        """
        执行VWAP算法

        按照成交量分布执行各个切片

        Returns:
            bool: 执行是否成功
        """
        try:
            self.status = AlgorithmStatus.RUNNING
            self.start_time = datetime.now()

            logger.info(
                f"开始VWAP执行",
                order_id=self.order.order_id,
                total_slices=len(self.slice_sizes),
                volume_profile=self.volume_profile
            )

            for i, slice_size in enumerate(self.slice_sizes):
                # 检查是否被取消
                if self._cancelled:
                    logger.info(f"VWAP执行被取消", order_id=self.order.order_id)
                    return False

                # 检查是否暂停
                while self._paused:
                    await asyncio.sleep(0.1)

                # 获取执行价格（加入随机性模拟市场波动）
                execution_price = self._get_execution_price()

                # 执行切片
                success = await self._execute_slice(slice_size, execution_price)

                if success:
                    self.completed_slices += 1
                    logger.debug(
                        f"VWAP切片 {i+1}/{len(self.slice_sizes)} 完成",
                        order_id=self.order.order_id,
                        qty=slice_size
                    )
                else:
                    logger.warning(
                        f"VWAP切片执行失败",
                        order_id=self.order.order_id,
                        slice_index=i
                    )

                # 等待到下一个切片时间
                if i < len(self.slice_sizes) - 1:
                    await asyncio.sleep(self.slice_interval)

            # 执行完成
            self.end_time = datetime.now()

            if self.completed_slices == len(self.slice_sizes):
                self.status = AlgorithmStatus.COMPLETED
                logger.info(
                    f"VWAP执行完成",
                    order_id=self.order.order_id,
                    completed_slices=self.completed_slices
                )
                return True
            else:
                if self._cancelled:
                    self.status = AlgorithmStatus.CANCELLED
                else:
                    self.status = AlgorithmStatus.FAILED
                return False

        except Exception as e:
            self.status = AlgorithmStatus.FAILED
            self.end_time = datetime.now()
            logger.error(f"VWAP执行异常: {e}", order_id=self.order.order_id)
            return False

    def _get_execution_price(self) -> Decimal:
        """
        获取执行价格

        VWAP算法中加入随机性模拟市场波动

        Returns:
            Decimal: 执行价格
        """
        base_price = self.order.price
        if not base_price:
            return Decimal("0")

        # 添加随机波动（模拟滑点）
        volatility = Decimal(str(random.uniform(-0.001, 0.001)))  # ±0.1%
        adjusted_price = base_price * (Decimal("1") + volatility)

        return Decimal(str(round(adjusted_price, 2)))
