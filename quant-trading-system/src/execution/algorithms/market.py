"""
市价单/限价单直接执行

用于不需要算法拆分的小单直接执行
"""
from datetime import datetime
from decimal import Decimal
from typing import List

from src.execution.algorithms.base import (
    ExecutionAlgorithm, AlgorithmConfig, AlgorithmStatus
)
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class MarketAlgorithm(ExecutionAlgorithm):
    """
    市价/限价单直接执行

    特点：
    1. 不拆分订单
    2. 一次性全部执行
    3. 适用于小单或紧急执行
    """

    def __init__(
        self,
        order,
        config: AlgorithmConfig,
        session,
        algorithm_type: str = "MARKET"
    ):
        """
        初始化直接执行算法

        Args:
            order: 订单
            config: 配置
            session: 数据库会话
            algorithm_type: 算法类型 (MARKET 或 LIMIT)
        """
        super().__init__(order, config, session)
        self.algorithm_type = algorithm_type

        # 直接执行只有一个切片
        remaining_qty = order.qty - order.filled_qty
        self.slice_sizes = [remaining_qty] if remaining_qty > 0 else []

    def _calculate_slice_sizes(self, total_qty: int, num_slices: int) -> List[int]:
        """
        计算切片大小

        直接执行只有一个切片

        Args:
            total_qty: 总数量
            num_slices: 切片数量（忽略）

        Returns:
            List[int]: 切片大小列表
        """
        return self.slice_sizes

    async def execute(self) -> bool:
        """
        执行订单

        一次性执行全部数量

        Returns:
            bool: 执行是否成功
        """
        try:
            self.status = AlgorithmStatus.RUNNING
            self.start_time = datetime.now()

            remaining_qty = self.order.qty - self.order.filled_qty

            if remaining_qty <= 0:
                logger.warning(
                    f"订单已全部成交",
                    order_id=self.order.order_id
                )
                self.status = AlgorithmStatus.COMPLETED
                return True

            logger.info(
                f"开始{self.algorithm_type}直接执行",
                order_id=self.order.order_id,
                qty=remaining_qty
            )

            # 获取执行价格
            execution_price = self._get_execution_price()

            # 执行全部数量
            success = await self._execute_slice(remaining_qty, execution_price)

            self.end_time = datetime.now()

            if success:
                self.completed_slices = 1
                self.status = AlgorithmStatus.COMPLETED
                logger.info(
                    f"{self.algorithm_type}执行完成",
                    order_id=self.order.order_id,
                    qty=remaining_qty,
                    price=execution_price
                )
                return True
            else:
                self.status = AlgorithmStatus.FAILED
                logger.error(
                    f"{self.algorithm_type}执行失败",
                    order_id=self.order.order_id
                )
                return False

        except Exception as e:
            self.status = AlgorithmStatus.FAILED
            self.end_time = datetime.now()
            logger.error(
                f"{self.algorithm_type}执行异常: {e}",
                order_id=self.order.order_id
            )
            return False

    def _get_execution_price(self) -> Decimal:
        """
        获取执行价格

        MARKET: 使用当前市场价
        LIMIT: 使用订单限价

        Returns:
            Decimal: 执行价格
        """
        if self.algorithm_type == "LIMIT" and self.order.price:
            return self.order.price

        # TODO: 从市场数据获取当前价格
        # 暂时使用订单价格或默认价格
        return self.order.price or Decimal("0")
