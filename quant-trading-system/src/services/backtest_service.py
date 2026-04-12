"""
回测服务
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.backtest_task import BacktestTask
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class BacktestService:
    """回测服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        task_id: str,
        account_id: int,
        symbols: List[str],
        start_date: str,
        end_date: str,
        strategy_id: str,
        initial_capital: float,
        strategy_params: dict = None
    ) -> BacktestTask:
        """创建回测任务"""
        task = BacktestTask(
            task_id=task_id,
            account_id=account_id,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            strategy_id=strategy_id,
            initial_capital=Decimal(str(initial_capital)),
            strategy_params=strategy_params
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        logger.info(f"创建回测任务: {task_id}")
        return task

    async def get_task(self, task_id: str) -> Optional[BacktestTask]:
        """获取回测任务"""
        result = await self.db.execute(
            select(BacktestTask).where(BacktestTask.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_tasks_by_account(
        self,
        account_id: int,
        status: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[BacktestTask]:
        """获取账户的回测任务列表"""
        query = select(BacktestTask).where(BacktestTask.account_id == account_id)

        if status:
            query = query.where(BacktestTask.status == status)

        query = query.order_by(desc(BacktestTask.created_at)).limit(limit).offset(offset)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_status(
        self,
        task_id: str,
        status: str,
        progress: int = None
    ) -> bool:
        """更新任务状态"""
        task = await self.get_task(task_id)
        if not task:
            return False

        task.status = status

        if progress is not None:
            task.progress = progress

        if status == "running" and not task.started_at:
            task.started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            task.completed_at = datetime.utcnow()

        await self.db.commit()
        return True

    async def save_results(self, task_id: str, results: dict) -> bool:
        """保存回测结果"""
        task = await self.get_task(task_id)
        if not task:
            return False

        task.results = results
        await self.db.commit()
        logger.info(f"保存回测结果: {task_id}")
        return True

    async def save_error(self, task_id: str, error_message: str) -> bool:
        """保存错误信息"""
        task = await self.get_task(task_id)
        if not task:
            return False

        task.error_message = error_message
        await self.db.commit()
        return True

    async def delete_task(self, task_id: str) -> bool:
        """删除回测任务"""
        task = await self.get_task(task_id)
        if not task:
            return False

        await self.db.delete(task)
        await self.db.commit()
        logger.info(f"删除回测任务: {task_id}")
        return True
