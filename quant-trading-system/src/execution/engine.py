"""
订单执行引擎

职责：
- 统一管理订单执行流程
- 订单验证和预处理
- 路由决策
- 执行跟踪
- 执行报告生成
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.order import Order
from src.models.enums import OrderStatus, AccountType
from src.execution.router import OrderRouter, RouteTarget, RoutingDecision
from src.execution.monitor import ExecutionMonitor, ExecutionMetrics
from src.services.order_service import OrderService
from src.services.account_service import AccountService
from src.common.logger import TradingLogger
from src.common.exceptions import OrderExecutionError

logger = TradingLogger(__name__)


@dataclass
class ExecutionConfig:
    """执行引擎配置"""
    default_algorithm: str = "MARKET"
    enable_smart_routing: bool = True
    max_order_value: Decimal = Decimal("10000000")  # 最大订单金额1000万
    partial_fill_threshold: int = 100000  # 部分成交阈值（金额）
    max_execution_time: int = 300  # 最大执行时间（秒）
    auto_cancel_on_timeout: bool = True


@dataclass
class ValidationResult:
    """订单验证结果"""
    is_valid: bool
    error_msg: Optional[str] = None
    warnings: list = field(default_factory=list)

    @classmethod
    def valid(cls, warnings: list = None):
        """创建验证通过的结果"""
        return cls(is_valid=True, warnings=warnings or [])

    @classmethod
    def invalid(cls, error_msg: str):
        """创建验证失败的结果"""
        return cls(is_valid=False, error_msg=error_msg)


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    order_id: str
    execution_target: Optional[RouteTarget] = None
    algorithm: Optional[str] = None
    error_msg: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success_result(
        cls,
        order_id: str,
        target: RouteTarget,
        algorithm: str = "MARKET",
        details: Dict[str, Any] = None
    ):
        """创建成功结果"""
        return cls(
            success=True,
            order_id=order_id,
            execution_target=target,
            algorithm=algorithm,
            details=details or {}
        )

    @classmethod
    def failure_result(cls, order_id: str, error_msg: str):
        """创建失败结果"""
        return cls(
            success=False,
            order_id=order_id,
            error_msg=error_msg
        )


@dataclass
class ExecutionStatus:
    """执行状态"""
    order_id: str
    status: OrderStatus
    filled_qty: int
    remaining_qty: int
    fill_rate: float
    avg_fill_price: Decimal
    execution_time_ms: int
    target: Optional[RouteTarget] = None


@dataclass
class ExecutionReport:
    """执行报告"""
    order_id: str
    symbol: str
    direction: str
    total_qty: int
    filled_qty: int
    avg_fill_price: Decimal
    total_amount: Decimal
    start_time: datetime
    end_time: Optional[datetime]
    execution_time_ms: int
    slippage_bps: float
    target: RouteTarget
    algorithm: str


class ExecutionEngine:
    """
    订单执行引擎

    负责订单的完整执行流程：
    1. 订单验证
    2. 路由决策
    3. 执行订单
    4. 跟踪状态
    5. 生成报告
    """

    def __init__(
        self,
        config: ExecutionConfig,
        session: AsyncSession,
        router: Optional[OrderRouter] = None,
        monitor: Optional[ExecutionMonitor] = None
    ):
        """
        初始化执行引擎

        Args:
            config: 执行配置
            session: 数据库会话
            router: 订单路由器（可选）
            monitor: 执行监控器（可选）
        """
        self.config = config
        self.session = session
        self.router = router or OrderRouter()
        self.monitor = monitor or ExecutionMonitor()
        self._order_service: Optional[OrderService] = None
        self._account_service: Optional[AccountService] = None

    def _get_order_service(self) -> OrderService:
        """获取订单服务（懒加载）"""
        if self._order_service is None:
            self._order_service = OrderService(self.session)
        return self._order_service

    def _get_account_service(self) -> AccountService:
        """获取账户服务（懒加载）"""
        if self._account_service is None:
            self._account_service = AccountService(self.session)
        return self._account_service

    async def validate_order(self, order: Order) -> ValidationResult:
        """
        验证订单

        Args:
            order: 待验证订单

        Returns:
            ValidationResult: 验证结果
        """
        warnings = []

        # 检查股票代码
        if not order.symbol:
            return ValidationResult.invalid("股票代码不能为空")

        # 检查数量
        if order.qty <= 0:
            return ValidationResult.invalid("订单数量必须大于0")

        # 检查价格（限价单）
        if order.order_type.value == "LIMIT":
            if order.price is None or order.price <= 0:
                return ValidationResult.invalid("限价单价格必须大于0")

            # 检查价格精度
            if order.price != order.price.quantize(Decimal("0.01")):
                return ValidationResult.invalid("价格最多支持2位小数")

            # 检查价格范围
            if order.price > Decimal("99999.99"):
                return ValidationResult.invalid("价格超出有效范围")

        # 检查订单金额
        order_value = (order.price or Decimal("0")) * order.qty
        if order_value > self.config.max_order_value:
            return ValidationResult.invalid(
                f"订单金额 {order_value} 超过最大限制 {self.config.max_order_value}"
            )

        # 检查账户状态
        account = await self._get_account_service().get_account(order.account_id)
        if not account:
            return ValidationResult.invalid(f"账户 {order.account_id} 不存在")

        if account.status.value != "ACTIVE":
            return ValidationResult.invalid(f"账户状态异常: {account.status.value}")

        # 检查余额/持仓
        if order.direction.value == "BUY":
            required_amount = (order.price or Decimal("0")) * order.qty
            if account.balance < required_amount:
                return ValidationResult.invalid("账户余额不足")
        else:
            # 卖出检查持仓
            position = await self._get_account_service().get_position(
                order.account_id, order.symbol
            )
            if not position or position.qty < order.qty:
                return ValidationResult.invalid("持仓数量不足")

        # 大额订单警告
        if order_value > self.config.partial_fill_threshold * 10:
            warnings.append(f"大额订单，建议使用TWAP/VWAP算法执行")

        return ValidationResult.valid(warnings)

    async def execute_order(self, order: Order) -> ExecutionResult:
        """
        执行订单

        Args:
            order: 待执行订单

        Returns:
            ExecutionResult: 执行结果
        """
        try:
            # 1. 订单验证
            validation = await self.validate_order(order)
            if not validation.is_valid:
                logger.warning(
                    "订单验证失败",
                    order_id=order.order_id,
                    error=validation.error_msg
                )
                return ExecutionResult.failure_result(
                    order.order_id, validation.error_msg
                )

            # 记录警告
            for warning in validation.warnings:
                logger.warning("订单警告", order_id=order.order_id, warning=warning)

            # 2. 路由决策
            try:
                decision = await self.router.get_routing_decision(order)
                target = decision.target
                algorithm = decision.algorithm
            except Exception as e:
                logger.error(f"路由失败: {e}", order_id=order.order_id)
                return ExecutionResult.failure_result(
                    order.order_id, f"路由失败: {str(e)}"
                )

            # 3. 记录执行事件
            self.monitor.record_event(
                event_type="EXECUTION_STARTED",
                order_id=order.order_id,
                details={
                    "target": target.value,
                    "algorithm": algorithm,
                    "symbol": order.symbol,
                    "qty": order.qty
                }
            )

            # 4. 执行订单
            if target == RouteTarget.SIMULATED:
                success = await self._execute_simulated(order, algorithm)
            elif target == RouteTarget.REAL_EXCHANGE:
                success = await self._execute_real(order, algorithm)
            elif target == RouteTarget.PAPER_TRADING:
                success = await self._execute_paper(order, algorithm)
            else:
                return ExecutionResult.failure_result(
                    order.order_id, f"未知执行目标: {target}"
                )

            if not success:
                return ExecutionResult.failure_result(
                    order.order_id, "订单执行失败"
                )

            # 5. 记录成功事件
            self.monitor.record_event(
                event_type="EXECUTION_COMPLETED",
                order_id=order.order_id,
                details={"target": target.value, "algorithm": algorithm}
            )

            return ExecutionResult.success_result(
                order_id=order.order_id,
                target=target,
                algorithm=algorithm,
                details={"warnings": validation.warnings}
            )

        except Exception as e:
            logger.error(f"执行异常: {e}", order_id=order.order_id)
            return ExecutionResult.failure_result(
                order.order_id, f"执行异常: {str(e)}"
            )

    async def _execute_simulated(self, order: Order, algorithm: str) -> bool:
        """执行模拟交易"""
        try:
            order_service = self._get_order_service()

            # 提交订单
            success = await order_service.submit_order(order)

            if success and algorithm in ["TWAP", "VWAP"]:
                # 启动算法执行
                from src.execution.algorithms import create_algorithm, AlgorithmConfig
                config = AlgorithmConfig()
                algo = create_algorithm(algorithm, order, config, self.session)
                await algo.execute()

            return success

        except Exception as e:
            logger.error(f"模拟执行失败: {e}", order_id=order.order_id)
            return False

    async def _execute_real(self, order: Order, algorithm: str) -> bool:
        """执行实盘交易"""
        # TODO: 接入真实交易API
        logger.warning("实盘交易尚未实现，使用模拟执行", order_id=order.order_id)
        return await self._execute_simulated(order, algorithm)

    async def _execute_paper(self, order: Order, algorithm: str) -> bool:
        """执行纸交易（仿真交易）"""
        # 纸交易使用模拟执行，但记录到专门的数据表
        return await self._execute_simulated(order, algorithm)

    async def get_execution_status(self, order_id: str) -> Optional[ExecutionStatus]:
        """
        获取执行状态

        Args:
            order_id: 订单号

        Returns:
            ExecutionStatus: 执行状态，不存在返回None
        """
        order = await self._get_order_service().get_order(order_id)

        if not order:
            return None

        # 计算执行时间
        execution_time_ms = 0
        if order.created_at:
            end_time = order.filled_at or datetime.now()
            execution_time_ms = int((end_time - order.created_at).total_seconds() * 1000)

        return ExecutionStatus(
            order_id=order.order_id,
            status=order.status,
            filled_qty=order.filled_qty,
            remaining_qty=order.remaining_qty,
            fill_rate=order.filled_qty / order.qty if order.qty > 0 else 0,
            avg_fill_price=order.filled_avg_price,
            execution_time_ms=execution_time_ms,
            target=None  # TODO: 从订单记录中获取
        )

    async def cancel_execution(self, order_id: str) -> ExecutionResult:
        """
        取消执行

        Args:
            order_id: 订单号

        Returns:
            ExecutionResult: 取消结果
        """
        try:
            order_service = self._get_order_service()
            order = await order_service.get_order(order_id)

            if not order:
                return ExecutionResult.failure_result(order_id, "订单不存在")

            success = await order_service.cancel_order(order)

            if success:
                self.monitor.record_event(
                    event_type="EXECUTION_CANCELLED",
                    order_id=order_id,
                    details={}
                )
                return ExecutionResult.success_result(
                    order_id, RouteTarget.SIMULATED, "CANCEL"
                )
            else:
                return ExecutionResult.failure_result(order_id, "撤单失败")

        except Exception as e:
            return ExecutionResult.failure_result(order_id, f"撤单异常: {str(e)}")

    async def get_execution_report(self, order_id: str) -> Optional[ExecutionReport]:
        """
        获取执行报告

        Args:
            order_id: 订单号

        Returns:
            ExecutionReport: 执行报告，不存在返回None
        """
        order = await self._get_order_service().get_order(order_id)

        if not order:
            return None

        # 计算执行时间
        execution_time_ms = 0
        if order.created_at:
            end_time = order.filled_at or datetime.now()
            execution_time_ms = int((end_time - order.created_at).total_seconds() * 1000)

        # 计算滑点
        slippage_bps = 0.0
        if order.price and order.filled_avg_price > 0:
            price_diff = abs(order.filled_avg_price - order.price)
            slippage_bps = float(price_diff / order.price * 10000)

        return ExecutionReport(
            order_id=order.order_id,
            symbol=order.symbol,
            direction=order.direction.value,
            total_qty=order.qty,
            filled_qty=order.filled_qty,
            avg_fill_price=order.filled_avg_price,
            total_amount=order.filled_amount,
            start_time=order.created_at,
            end_time=order.filled_at,
            execution_time_ms=execution_time_ms,
            slippage_bps=slippage_bps,
            target=RouteTarget.SIMULATED,  # TODO: 从记录获取
            algorithm="MARKET"  # TODO: 从记录获取
        )

    async def batch_execute(
        self,
        orders: list[Order],
        continue_on_error: bool = True
    ) -> list[ExecutionResult]:
        """
        批量执行订单

        Args:
            orders: 订单列表
            continue_on_error: 错误时是否继续

        Returns:
            list[ExecutionResult]: 执行结果列表
        """
        results = []

        for order in orders:
            result = await self.execute_order(order)
            results.append(result)

            if not result.success and not continue_on_error:
                break

        return results
