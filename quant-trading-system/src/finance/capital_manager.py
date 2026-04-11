"""
资金管理器

职责：
- 出入金管理
- 资金冻结/解冻
- 资金流水记录
- 资金查询统计
- 资金快照
"""
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.account import Account
from src.models.balance_flow import BalanceFlow
from src.models.enums import FlowType
from src.services.account_service import AccountService
from src.common.logger import TradingLogger
from src.common.exceptions import BusinessLogicError

logger = TradingLogger(__name__)


class CapitalOperationType(Enum):
    """资金操作类型"""
    DEPOSIT = "deposit"           # 入金
    WITHDRAW = "withdraw"         # 出金
    FREEZE = "freeze"             # 冻结
    UNFREEZE = "unfreeze"         # 解冻
    TRANSFER = "transfer"         # 转账


@dataclass
class CapitalOperationResult:
    """资金操作结果"""
    success: bool
    operation_type: CapitalOperationType
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    flow_id: Optional[int] = None
    error_msg: Optional[str] = None


@dataclass
class CapitalSnapshot:
    """资金快照"""
    account_id: int
    total_balance: Decimal
    available: Decimal
    frozen: Decimal
    position_value: Decimal
    timestamp: datetime

    @property
    def net_asset(self) -> Decimal:
        """净资产 = 总资产 + 持仓市值"""
        return self.total_balance + self.position_value


@dataclass
class FlowStatistics:
    """流水统计"""
    total_deposit: Decimal
    total_withdraw: Decimal
    total_buy: Decimal
    total_sell: Decimal
    total_fee: Decimal
    net_flow: Decimal


def validate_amount(amount: Decimal) -> bool:
    """
    验证金额有效性

    规则：
    1. 必须大于0
    2. 不能超过10亿
    3. 最多2位小数
    """
    if amount <= 0:
        return False
    if amount > Decimal("1000000000"):
        return False
    if amount != amount.quantize(Decimal("0.01")):
        return False
    return True


def calculate_buying_power(account: Account, positions: List) -> Dict[str, Decimal]:
    """
    计算购买力

    Returns:
        Dict包含：
        - available_cash: 可用现金
        - position_value: 持仓市值
        - total_buying_power: 总购买力
    """
    position_value = sum(
        pos.market_value for pos in positions
        if hasattr(pos, 'market_value') and pos.market_value
    )

    return {
        "available_cash": account.available,
        "position_value": position_value,
        "total_buying_power": account.available + position_value
    }


class CapitalManager:
    """
    资金管理器

    处理所有资金相关的业务逻辑
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._account_service: Optional[AccountService] = None

    def _get_account_service(self) -> AccountService:
        """获取账户服务（懒加载）"""
        if self._account_service is None:
            self._account_service = AccountService(self.session)
        return self._account_service

    async def deposit(
        self,
        account_id: int,
        amount: Decimal,
        remark: str = ""
    ) -> CapitalOperationResult:
        """
        入金

        Args:
            account_id: 账户ID
            amount: 入金金额
            remark: 备注

        Returns:
            CapitalOperationResult: 操作结果
        """
        # 验证金额
        if not validate_amount(amount):
            return CapitalOperationResult(
                success=False,
                operation_type=CapitalOperationType.DEPOSIT,
                amount=amount,
                balance_before=Decimal("0"),
                balance_after=Decimal("0"),
                error_msg="金额无效（必须大于0，最多2位小数）"
            )

        try:
            # 获取账户
            account = await self._get_account_service().get_account(account_id)
            if not account:
                raise BusinessLogicError(f"账户不存在: {account_id}")

            if account.status.value != "ACTIVE":
                raise BusinessLogicError(f"账户状态异常: {account.status.value}")

            # 记录操作前余额
            balance_before = account.total_balance

            # 更新账户余额
            account.total_balance += amount
            account.available += amount

            # 创建流水记录
            flow = BalanceFlow(
                account_id=account_id,
                flow_type=FlowType.DEPOSIT,
                amount=amount,
                balance_before=balance_before,
                balance_after=account.total_balance,
                description=f"入金: {amount}",
                remark=remark
            )
            self.session.add(flow)
            await self.session.flush()

            logger.info(
                "入金成功",
                account_id=account_id,
                amount=float(amount),
                balance=float(account.total_balance)
            )

            return CapitalOperationResult(
                success=True,
                operation_type=CapitalOperationType.DEPOSIT,
                amount=amount,
                balance_before=balance_before,
                balance_after=account.total_balance,
                flow_id=flow.id
            )

        except Exception as e:
            logger.error(f"入金失败: {e}", account_id=account_id)
            return CapitalOperationResult(
                success=False,
                operation_type=CapitalOperationType.DEPOSIT,
                amount=amount,
                balance_before=Decimal("0"),
                balance_after=Decimal("0"),
                error_msg=str(e)
            )

    async def withdraw(
        self,
        account_id: int,
        amount: Decimal,
        remark: str = ""
    ) -> CapitalOperationResult:
        """
        出金

        Args:
            account_id: 账户ID
            amount: 出金金额
            remark: 备注

        Returns:
            CapitalOperationResult: 操作结果
        """
        # 验证金额
        if not validate_amount(amount):
            return CapitalOperationResult(
                success=False,
                operation_type=CapitalOperationType.WITHDRAW,
                amount=amount,
                balance_before=Decimal("0"),
                balance_after=Decimal("0"),
                error_msg="金额无效"
            )

        try:
            # 获取账户
            account = await self._get_account_service().get_account(account_id)
            if not account:
                raise BusinessLogicError(f"账户不存在: {account_id}")

            # 检查可用资金
            if account.available < amount:
                raise BusinessLogicError(
                    f"可用资金不足: 需要 {amount}, 可用 {account.available}"
                )

            # 记录操作前余额
            balance_before = account.total_balance

            # 更新账户余额
            account.total_balance -= amount
            account.available -= amount

            # 创建流水记录
            flow = BalanceFlow(
                account_id=account_id,
                flow_type=FlowType.WITHDRAW,
                amount=-amount,  # 出金是负向
                balance_before=balance_before,
                balance_after=account.total_balance,
                description=f"出金: {amount}",
                remark=remark
            )
            self.session.add(flow)
            await self.session.flush()

            logger.info(
                "出金成功",
                account_id=account_id,
                amount=float(amount),
                balance=float(account.total_balance)
            )

            return CapitalOperationResult(
                success=True,
                operation_type=CapitalOperationType.WITHDRAW,
                amount=amount,
                balance_before=balance_before,
                balance_after=account.total_balance,
                flow_id=flow.id
            )

        except Exception as e:
            logger.error(f"出金失败: {e}", account_id=account_id)
            return CapitalOperationResult(
                success=False,
                operation_type=CapitalOperationType.WITHDRAW,
                amount=amount,
                balance_before=Decimal("0"),
                balance_after=Decimal("0"),
                error_msg=str(e)
            )

    async def freeze_for_order(
        self,
        account_id: int,
        order_id: int,
        amount: Decimal
    ) -> CapitalOperationResult:
        """
        委托冻结资金

        Args:
            account_id: 账户ID
            order_id: 订单ID
            amount: 冻结金额

        Returns:
            CapitalOperationResult: 操作结果
        """
        try:
            account = await self._get_account_service().get_account(account_id)
            if not account:
                raise BusinessLogicError(f"账户不存在: {account_id}")

            # 检查可用资金
            if account.available < amount:
                raise BusinessLogicError(
                    f"可用资金不足: 需要 {amount}, 可用 {account.available}"
                )

            balance_before = account.total_balance

            # 冻结资金
            account.available -= amount
            account.frozen += amount

            # 创建流水
            flow = BalanceFlow.create_order_frozen(
                account_id=account_id,
                order_id=order_id,
                amount=amount,
                balance_before=balance_before
            )
            self.session.add(flow)
            await self.session.flush()

            logger.info(
                "委托冻结成功",
                account_id=account_id,
                order_id=order_id,
                amount=float(amount)
            )

            return CapitalOperationResult(
                success=True,
                operation_type=CapitalOperationType.FREEZE,
                amount=amount,
                balance_before=balance_before,
                balance_after=account.total_balance,
                flow_id=flow.id
            )

        except Exception as e:
            logger.error(f"委托冻结失败: {e}", account_id=account_id, order_id=order_id)
            return CapitalOperationResult(
                success=False,
                operation_type=CapitalOperationType.FREEZE,
                amount=amount,
                balance_before=Decimal("0"),
                balance_after=Decimal("0"),
                error_msg=str(e)
            )

    async def unfreeze_for_order(
        self,
        account_id: int,
        order_id: int,
        amount: Decimal
    ) -> CapitalOperationResult:
        """
        委托解冻资金

        Args:
            account_id: 账户ID
            order_id: 订单ID
            amount: 解冻金额

        Returns:
            CapitalOperationResult: 操作结果
        """
        try:
            account = await self._get_account_service().get_account(account_id)
            if not account:
                raise BusinessLogicError(f"账户不存在: {account_id}")

            # 检查冻结资金
            if account.frozen < amount:
                raise BusinessLogicError(
                    f"冻结资金不足: 需要解冻 {amount}, 已冻结 {account.frozen}"
                )

            balance_before = account.total_balance

            # 解冻资金
            account.available += amount
            account.frozen -= amount

            # 创建流水
            flow = BalanceFlow.create_order_unfrozen(
                account_id=account_id,
                order_id=order_id,
                amount=amount,
                balance_before=balance_before
            )
            self.session.add(flow)
            await self.session.flush()

            logger.info(
                "委托解冻成功",
                account_id=account_id,
                order_id=order_id,
                amount=float(amount)
            )

            return CapitalOperationResult(
                success=True,
                operation_type=CapitalOperationType.UNFREEZE,
                amount=amount,
                balance_before=balance_before,
                balance_after=account.total_balance,
                flow_id=flow.id
            )

        except Exception as e:
            logger.error(f"委托解冻失败: {e}", account_id=account_id, order_id=order_id)
            return CapitalOperationResult(
                success=False,
                operation_type=CapitalOperationType.UNFREEZE,
                amount=amount,
                balance_before=Decimal("0"),
                balance_after=Decimal("0"),
                error_msg=str(e)
            )

    async def transfer(
        self,
        from_account_id: int,
        to_account_id: int,
        amount: Decimal,
        remark: str = ""
    ) -> CapitalOperationResult:
        """
        账户间转账

        Args:
            from_account_id: 转出账户ID
            to_account_id: 转入账户ID
            amount: 转账金额
            remark: 备注

        Returns:
            CapitalOperationResult: 操作结果
        """
        try:
            if not validate_amount(amount):
                raise BusinessLogicError("金额无效")

            # 获取两个账户
            from_account = await self._get_account_service().get_account(from_account_id)
            to_account = await self._get_account_service().get_account(to_account_id)

            if not from_account:
                raise BusinessLogicError(f"转出账户不存在: {from_account_id}")
            if not to_account:
                raise BusinessLogicError(f"转入账户不存在: {to_account_id}")

            # 检查转出账户余额
            if from_account.available < amount:
                raise BusinessLogicError(
                    f"转出账户余额不足: 可用 {from_account.available}"
                )

            # 记录转出前余额
            from_balance_before = from_account.total_balance
            to_balance_before = to_account.total_balance

            # 执行转账
            from_account.total_balance -= amount
            from_account.available -= amount
            to_account.total_balance += amount
            to_account.available += amount

            # 创建流水记录
            from_flow = BalanceFlow(
                account_id=from_account_id,
                flow_type=FlowType.WITHDRAW,
                amount=-amount,
                balance_before=from_balance_before,
                balance_after=from_account.total_balance,
                description=f"转账至 {to_account_id}: {amount}",
                remark=remark
            )

            to_flow = BalanceFlow(
                account_id=to_account_id,
                flow_type=FlowType.DEPOSIT,
                amount=amount,
                balance_before=to_balance_before,
                balance_after=to_account.total_balance,
                description=f"转账来自 {from_account_id}: {amount}",
                remark=remark
            )

            self.session.add(from_flow)
            self.session.add(to_flow)
            await self.session.flush()

            logger.info(
                "转账成功",
                from_account=from_account_id,
                to_account=to_account_id,
                amount=float(amount)
            )

            return CapitalOperationResult(
                success=True,
                operation_type=CapitalOperationType.TRANSFER,
                amount=amount,
                balance_before=from_balance_before,
                balance_after=from_account.total_balance
            )

        except Exception as e:
            logger.error(
                f"转账失败: {e}",
                from_account=from_account_id,
                to_account=to_account_id
            )
            return CapitalOperationResult(
                success=False,
                operation_type=CapitalOperationType.TRANSFER,
                amount=amount,
                balance_before=Decimal("0"),
                balance_after=Decimal("0"),
                error_msg=str(e)
            )

    async def get_balance_flows(
        self,
        account_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        flow_type: Optional[FlowType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[BalanceFlow]:
        """
        获取资金流水

        Args:
            account_id: 账户ID
            start_date: 开始日期
            end_date: 结束日期
            flow_type: 流水类型过滤
            limit: 数量限制
            offset: 偏移量

        Returns:
            List[BalanceFlow]: 流水列表
        """
        query = select(BalanceFlow).where(BalanceFlow.account_id == account_id)

        if start_date:
            query = query.where(BalanceFlow.created_at >= start_date)
        if end_date:
            query = query.where(BalanceFlow.created_at <= end_date)
        if flow_type:
            query = query.where(BalanceFlow.flow_type == flow_type)

        query = query.order_by(BalanceFlow.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_flow_statistics(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> FlowStatistics:
        """
        获取流水统计

        Args:
            account_id: 账户ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            FlowStatistics: 统计结果
        """
        query = select(
            BalanceFlow.flow_type,
            func.sum(BalanceFlow.amount).label("total")
        ).where(
            and_(
                BalanceFlow.account_id == account_id,
                BalanceFlow.created_at >= start_date,
                BalanceFlow.created_at <= end_date
            )
        ).group_by(BalanceFlow.flow_type)

        result = await self.session.execute(query)
        rows = result.all()

        # 初始化统计
        stats = {
            FlowType.DEPOSIT: Decimal("0"),
            FlowType.WITHDRAW: Decimal("0"),
            FlowType.TRADE_BUY: Decimal("0"),
            FlowType.TRADE_SELL: Decimal("0"),
            FlowType.COMMISSION: Decimal("0"),
            FlowType.STAMP_TAX: Decimal("0"),
            FlowType.TRANSFER_FEE: Decimal("0"),
        }

        for row in rows:
            stats[row.flow_type] = row.total or Decimal("0")

        total_fee = (
            stats[FlowType.COMMISSION] +
            stats[FlowType.STAMP_TAX] +
            stats[FlowType.TRANSFER_FEE]
        )

        net_flow = (
            stats[FlowType.DEPOSIT] +
            stats[FlowType.WITHDRAW] +
            stats[FlowType.TRADE_BUY] +
            stats[FlowType.TRADE_SELL]
        )

        return FlowStatistics(
            total_deposit=stats[FlowType.DEPOSIT],
            total_withdraw=stats[FlowType.WITHDRAW],
            total_buy=stats[FlowType.TRADE_BUY],
            total_sell=stats[FlowType.TRADE_SELL],
            total_fee=total_fee,
            net_flow=net_flow
        )

    async def create_snapshot(self, account_id: int) -> CapitalSnapshot:
        """
        创建资金快照

        Args:
            account_id: 账户ID

        Returns:
            CapitalSnapshot: 资金快照
        """
        account = await self._get_account_service().get_account(account_id)
        positions = await self._get_account_service().get_positions(account_id)

        position_value = sum(
            pos.market_value for pos in positions
            if hasattr(pos, 'market_value') and pos.market_value
        )

        return CapitalSnapshot(
            account_id=account_id,
            total_balance=account.total_balance,
            available=account.available,
            frozen=account.frozen,
            position_value=position_value,
            timestamp=datetime.now()
        )
