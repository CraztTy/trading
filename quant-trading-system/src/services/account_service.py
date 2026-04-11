"""
账户服务

提供账户相关的业务操作：
- 账户查询
- 持仓查询
- 资金操作
- 账户统计
"""
from typing import Optional, List
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.account import Account
from src.models.position import Position
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class AccountService:
    """
    账户服务

    处理账户相关的业务逻辑
    """

    def __init__(self, session: AsyncSession):
        """
        初始化账户服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def get_account(self, account_id: int) -> Optional[Account]:
        """
        根据ID获取账户

        Args:
            account_id: 账户ID

        Returns:
            Account: 账户，不存在返回None
        """
        result = await self.session.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_account_by_no(self, account_no: str) -> Optional[Account]:
        """
        根据账号获取账户

        Args:
            account_no: 账号

        Returns:
            Account: 账户，不存在返回None
        """
        result = await self.session.execute(
            select(Account).where(Account.account_no == account_no)
        )
        return result.scalar_one_or_none()

    async def get_position(
        self,
        account_id: int,
        symbol: str
    ) -> Optional[Position]:
        """
        获取账户的某个持仓

        Args:
            account_id: 账户ID
            symbol: 股票代码

        Returns:
            Position: 持仓，不存在返回None
        """
        result = await self.session.execute(
            select(Position).where(
                Position.account_id == account_id,
                Position.symbol == symbol
            )
        )
        return result.scalar_one_or_none()

    async def get_positions(self, account_id: int) -> List[Position]:
        """
        获取账户的所有持仓

        Args:
            account_id: 账户ID

        Returns:
            List[Position]: 持仓列表
        """
        result = await self.session.execute(
            select(Position).where(Position.account_id == account_id)
        )
        return result.scalars().all()

    async def get_account_summary(self, account_id: int) -> Optional[dict]:
        """
        获取账户摘要

        Args:
            account_id: 账户ID

        Returns:
            dict: 账户摘要
        """
        account = await self.get_account(account_id)
        if not account:
            return None

        positions = await self.get_positions(account_id)

        return {
            "account_id": account.id,
            "account_no": account.account_no,
            "name": account.name,
            "account_type": account.account_type.value,
            "total_balance": float(account.total_balance),
            "available": float(account.available),
            "frozen": float(account.frozen),
            "market_value": float(account.market_value),
            "total_equity": float(account.total_equity),
            "realized_pnl": float(account.realized_pnl),
            "unrealized_pnl": float(account.unrealized_pnl),
            "total_return_pct": float(account.total_return_pct),
            "position_count": len(positions),
            "status": account.status.value,
        }
