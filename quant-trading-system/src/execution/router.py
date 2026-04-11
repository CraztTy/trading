"""
智能订单路由器

职责：
- 根据账户类型、订单特征决定执行渠道
- 选择执行算法
- 支持自定义路由规则
- 提供路由决策信息
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Callable, List, Dict, Any
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.order import Order
from src.models.account import Account
from src.models.enums import AccountType, OrderType, AccountStatus
from src.services.account_service import AccountService
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class RouteTarget(str, Enum):
    """路由目标"""
    SIMULATED = "simulated"      # 模拟撮合
    REAL_EXCHANGE = "real_exchange"  # 真实交易所
    PAPER_TRADING = "paper_trading"  # 纸交易（仿真）


@dataclass
class RoutingDecision:
    """路由决策结果"""
    target: RouteTarget
    algorithm: str
    reason: str
    priority: int = 0
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoutingRule:
    """路由规则"""
    name: str
    condition: Callable[[Order, Account], bool]
    target: RouteTarget
    algorithm: str = "MARKET"
    priority: int = 0
    description: str = ""


@dataclass
class AccountRoutingInfo:
    """账户路由信息"""
    account_id: int
    account_type: AccountType
    available_targets: List[RouteTarget]
    default_algorithm: str
    restrictions: List[str] = field(default_factory=list)


class OrderRouter:
    """
    智能订单路由器

    根据订单特征和账户类型智能选择执行渠道：
    1. 模拟账户 -> 模拟撮合
    2. 实盘账户 -> 真实交易所
    3. 大单 -> TWAP/VWAP算法
    4. 市价单 -> 直接执行
    """

    # 大单阈值（金额）
    LARGE_ORDER_THRESHOLD = Decimal("100000")
    # 超大单阈值
    VERY_LARGE_ORDER_THRESHOLD = Decimal("1000000")

    def __init__(self):
        """初始化路由器"""
        self._rules: List[RoutingRule] = []
        self._default_algorithm = "MARKET"
        self._account_service: Optional[AccountService] = None

    def _get_account_service(self, session: Optional[AsyncSession] = None) -> AccountService:
        """获取账户服务"""
        if self._account_service is None:
            if session is None:
                raise ValueError("需要数据库会话来初始化AccountService")
            self._account_service = AccountService(session)
        return self._account_service

    def add_rule(self, rule: RoutingRule) -> None:
        """
        添加自定义路由规则

        Args:
            rule: 路由规则
        """
        self._rules.append(rule)
        # 按优先级排序（高优先级在前）
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"添加路由规则: {rule.name}, 优先级: {rule.priority}")

    def remove_rule(self, rule_name: str) -> bool:
        """
        移除路由规则

        Args:
            rule_name: 规则名称

        Returns:
            bool: 是否成功移除
        """
        for i, rule in enumerate(self._rules):
            if rule.name == rule_name:
                self._rules.pop(i)
                logger.info(f"移除路由规则: {rule_name}")
                return True
        return False

    def clear_rules(self) -> None:
        """清除所有自定义规则"""
        self._rules.clear()
        logger.info("清除所有路由规则")

    async def route_order(
        self,
        order: Order,
        session: Optional[AsyncSession] = None
    ) -> RouteTarget:
        """
        路由订单

        Args:
            order: 订单
            session: 数据库会话

        Returns:
            RouteTarget: 路由目标
        """
        decision = await self.get_routing_decision(order, session)
        return decision.target

    async def get_routing_decision(
        self,
        order: Order,
        session: Optional[AsyncSession] = None
    ) -> RoutingDecision:
        """
        获取路由决策

        Args:
            order: 订单
            session: 数据库会话

        Returns:
            RoutingDecision: 路由决策
        """
        # 获取账户信息
        account = await self._get_account(session).get_account(order.account_id)

        if not account:
            raise ValueError(f"账户不存在: {order.account_id}")

        # 检查账户状态
        if account.status != AccountStatus.ACTIVE:
            raise ValueError(f"账户状态异常: {account.status.value}")

        # 1. 先检查自定义规则
        for rule in self._rules:
            if rule.condition(order, account):
                logger.info(
                    f"自定义规则匹配: {rule.name}",
                    order_id=order.order_id,
                    target=rule.target.value
                )
                return RoutingDecision(
                    target=rule.target,
                    algorithm=rule.algorithm,
                    reason=f"匹配规则: {rule.name}",
                    priority=rule.priority
                )

        # 2. 默认路由逻辑
        return self._default_routing(order, account)

    def _get_account(self, session: Optional[AsyncSession] = None):
        """获取账户服务"""
        if session:
            return AccountService(session)
        # 如果没有session，尝试使用缓存的service
        if self._account_service:
            return self._account_service
        raise ValueError("需要数据库会话来获取账户信息")

    def _default_routing(self, order: Order, account: Account) -> RoutingDecision:
        """
        默认路由逻辑

        策略：
        1. 模拟账户 -> 模拟撮合
        2. 实盘账户 -> 真实交易所
        3. 大单 -> 算法执行
        4. 市价单 -> 直接执行
        """
        order_value = (order.price or Decimal("0")) * order.qty

        # 根据账户类型选择目标
        if account.account_type == AccountType.SIMULATE:
            target = RouteTarget.SIMULATED
        elif account.account_type == AccountType.REAL:
            target = RouteTarget.REAL_EXCHANGE
        else:
            target = RouteTarget.PAPER_TRADING

        # 选择算法
        algorithm = self._select_algorithm(order, order_value)

        return RoutingDecision(
            target=target,
            algorithm=algorithm,
            reason=f"账户类型: {account.account_type.value}, 订单金额: {order_value}"
        )

    def _select_algorithm(self, order: Order, order_value: Decimal) -> str:
        """
        选择执行算法

        Args:
            order: 订单
            order_value: 订单金额

        Returns:
            str: 算法名称
        """
        # 市价单直接执行
        if order.order_type == OrderType.MARKET:
            return "MARKET"

        # 超大单使用VWAP
        if order_value >= self.VERY_LARGE_ORDER_THRESHOLD:
            return "VWAP"

        # 大单使用TWAP
        if order_value >= self.LARGE_ORDER_THRESHOLD:
            return "TWAP"

        # 小单直接限价执行
        return "LIMIT"

    async def get_account_routing_info(
        self,
        account_id: int,
        session: Optional[AsyncSession] = None
    ) -> AccountRoutingInfo:
        """
        获取账户路由信息

        Args:
            account_id: 账户ID
            session: 数据库会话

        Returns:
            AccountRoutingInfo: 路由信息
        """
        account = await self._get_account(session).get_account(account_id)

        if not account:
            raise ValueError(f"账户不存在: {account_id}")

        # 确定可用目标
        available_targets = []
        if account.account_type == AccountType.SIMULATE:
            available_targets = [RouteTarget.SIMULATED]
        elif account.account_type == AccountType.REAL:
            available_targets = [RouteTarget.REAL_EXCHANGE, RouteTarget.PAPER_TRADING]
        else:
            available_targets = [RouteTarget.PAPER_TRADING]

        # 确定默认算法
        default_algorithm = "MARKET"

        # 确定限制
        restrictions = []
        if account.status != AccountStatus.ACTIVE:
            restrictions.append(f"账户状态: {account.status.value}")

        return AccountRoutingInfo(
            account_id=account_id,
            account_type=account.account_type,
            available_targets=available_targets,
            default_algorithm=default_algorithm,
            restrictions=restrictions
        )

    def get_routing_rules(self) -> List[Dict[str, Any]]:
        """
        获取所有路由规则

        Returns:
            List[Dict]: 规则列表
        """
        return [
            {
                "name": rule.name,
                "target": rule.target.value,
                "algorithm": rule.algorithm,
                "priority": rule.priority,
                "description": rule.description
            }
            for rule in self._rules
        ]
