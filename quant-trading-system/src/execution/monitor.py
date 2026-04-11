"""
订单执行监控

职责：
- 跟踪执行事件
- 收集执行指标
- 触发告警
- 生成执行统计
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import asyncio

from src.models.order import Order
from src.models.enums import OrderStatus
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ExecutionEvent:
    """执行事件"""
    event_type: str
    order_id: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionMetrics:
    """执行指标"""
    order_id: str
    symbol: str
    total_qty: int
    filled_qty: int
    avg_fill_price: Decimal
    start_time: datetime
    end_time: Optional[datetime] = None
    status: OrderStatus = OrderStatus.CREATED

    @property
    def fill_rate(self) -> float:
        """填充率"""
        if self.total_qty == 0:
            return 0.0
        return self.filled_qty / self.total_qty

    @property
    def remaining_qty(self) -> int:
        """剩余数量"""
        return self.total_qty - self.filled_qty


@dataclass
class ExecutionStatistics:
    """执行统计"""
    total_orders: int = 0
    completed_orders: int = 0
    cancelled_orders: int = 0
    failed_orders: int = 0
    avg_execution_time_ms: float = 0.0
    avg_slippage_bps: float = 0.0
    total_volume: Decimal = Decimal("0")
    total_value: Decimal = Decimal("0")

    @property
    def completion_rate(self) -> float:
        """完成率"""
        if self.total_orders == 0:
            return 0.0
        return self.completed_orders / self.total_orders


@dataclass
class Alert:
    """告警"""
    rule_name: str
    level: AlertLevel
    message: str
    order_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: Callable[[ExecutionMetrics], bool]
    level: AlertLevel
    message: str
    enabled: bool = True


class ExecutionMonitor:
    """
    订单执行监控器

    跟踪订单执行过程，收集指标，触发告警
    """

    def __init__(self):
        """初始化监控器"""
        self._events: List[ExecutionEvent] = []
        self._metrics: Dict[str, ExecutionMetrics] = {}
        self._alert_rules: List[AlertRule] = []
        self._alerts: List[Alert] = []
        self._running = False
        self._cancelled = False

    def record_event(
        self,
        event_type: str,
        order_id: str,
        details: Dict[str, Any] = None
    ) -> None:
        """
        记录执行事件

        Args:
            event_type: 事件类型
            order_id: 订单号
            details: 事件详情
        """
        event = ExecutionEvent(
            event_type=event_type,
            order_id=order_id,
            timestamp=datetime.now(),
            details=details or {}
        )
        self._events.append(event)
        logger.debug(
            f"执行事件: {event_type}",
            order_id=order_id,
            details=details
        )

    def update_metrics(
        self,
        order_id: str,
        symbol: str,
        total_qty: int,
        filled_qty: int,
        avg_fill_price: Decimal,
        status: OrderStatus = None,
        end_time: datetime = None
    ) -> None:
        """
        更新执行指标

        Args:
            order_id: 订单号
            symbol: 股票代码
            total_qty: 总数量
            filled_qty: 已成交数量
            avg_fill_price: 成交均价
            status: 订单状态
            end_time: 结束时间
        """
        if order_id in self._metrics:
            # 更新现有指标
            existing = self._metrics[order_id]
            existing.filled_qty = filled_qty
            existing.avg_fill_price = avg_fill_price
            if status:
                existing.status = status
            if end_time:
                existing.end_time = end_time
        else:
            # 创建新指标
            self._metrics[order_id] = ExecutionMetrics(
                order_id=order_id,
                symbol=symbol,
                total_qty=total_qty,
                filled_qty=filled_qty,
                avg_fill_price=avg_fill_price,
                start_time=datetime.now(),
                status=status or OrderStatus.CREATED,
                end_time=end_time
            )

        # 检查告警
        self._check_alerts_for_order(order_id)

    def get_metrics(self, order_id: str) -> Optional[ExecutionMetrics]:
        """
        获取订单指标

        Args:
            order_id: 订单号

        Returns:
            ExecutionMetrics: 指标，不存在返回None
        """
        return self._metrics.get(order_id)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """
        添加告警规则

        Args:
            rule: 告警规则
        """
        self._alert_rules.append(rule)
        logger.info(f"添加告警规则: {rule.name}")

    def remove_alert_rule(self, rule_name: str) -> bool:
        """
        移除告警规则

        Args:
            rule_name: 规则名称

        Returns:
            bool: 是否成功移除
        """
        for i, rule in enumerate(self._alert_rules):
            if rule.name == rule_name:
                self._alert_rules.pop(i)
                logger.info(f"移除告警规则: {rule_name}")
                return True
        return False

    def _check_alerts_for_order(self, order_id: str) -> None:
        """检查订单告警"""
        metrics = self._metrics.get(order_id)
        if not metrics:
            return

        alerts = self.check_alerts(metrics)
        for alert in alerts:
            self._alerts.append(alert)
            logger.warning(
                f"执行告警: {alert.message}",
                order_id=order_id,
                level=alert.level.value
            )

    def check_alerts(self, metrics: ExecutionMetrics) -> List[Alert]:
        """
        检查告警

        Args:
            metrics: 执行指标

        Returns:
            List[Alert]: 触发的告警列表
        """
        triggered = []

        for rule in self._alert_rules:
            if not rule.enabled:
                continue

            try:
                if rule.condition(metrics):
                    alert = Alert(
                        rule_name=rule.name,
                        level=rule.level,
                        message=rule.message,
                        order_id=metrics.order_id
                    )
                    triggered.append(alert)
            except Exception as e:
                logger.error(f"告警规则执行失败: {rule.name}, 错误: {e}")

        return triggered

    def get_order_events(self, order_id: str) -> List[ExecutionEvent]:
        """
        获取订单事件

        Args:
            order_id: 订单号

        Returns:
            List[ExecutionEvent]: 事件列表
        """
        return [e for e in self._events if e.order_id == order_id]

    def get_execution_statistics(self) -> ExecutionStatistics:
        """
        获取执行统计

        Returns:
            ExecutionStatistics: 统计信息
        """
        stats = ExecutionStatistics()
        stats.total_orders = len(self._metrics)

        total_execution_time = 0.0
        execution_time_count = 0

        for metrics in self._metrics.values():
            if metrics.status == OrderStatus.FILLED:
                stats.completed_orders += 1
            elif metrics.status == OrderStatus.CANCELLED:
                stats.cancelled_orders += 1
            elif metrics.status == OrderStatus.REJECTED:
                stats.failed_orders += 1

            # 计算执行时间
            if metrics.end_time and metrics.start_time:
                exec_time = (metrics.end_time - metrics.start_time).total_seconds() * 1000
                total_execution_time += exec_time
                execution_time_count += 1

            stats.total_volume += Decimal(metrics.filled_qty)
            stats.total_value += metrics.avg_fill_price * metrics.filled_qty

        if execution_time_count > 0:
            stats.avg_execution_time_ms = total_execution_time / execution_time_count

        return stats

    def clear_old_events(self, days: int = 7) -> int:
        """
        清理旧事件

        Args:
            days: 保留天数

        Returns:
            int: 清理的事件数量
        """
        cutoff = datetime.now() - timedelta(days=days)
        original_count = len(self._events)

        self._events = [e for e in self._events if e.timestamp > cutoff]

        cleared = original_count - len(self._events)
        if cleared > 0:
            logger.info(f"清理 {cleared} 个旧事件")

        return cleared

    def export_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        导出指标

        Returns:
            Dict: 指标字典
        """
        return {
            order_id: {
                "symbol": m.symbol,
                "total_qty": m.total_qty,
                "filled_qty": m.filled_qty,
                "fill_rate": m.fill_rate,
                "avg_fill_price": float(m.avg_fill_price),
                "status": m.status.value,
                "start_time": m.start_time.isoformat(),
                "end_time": m.end_time.isoformat() if m.end_time else None
            }
            for order_id, m in self._metrics.items()
        }

    async def start(self) -> None:
        """启动监控"""
        self._running = True
        logger.info("执行监控已启动")

    async def stop(self) -> None:
        """停止监控"""
        self._running = False
        logger.info("执行监控已停止")

    @staticmethod
    def calculate_slippage(expected_price: Decimal, actual_price: Decimal) -> float:
        """
        计算滑点

        Args:
            expected_price: 预期价格
            actual_price: 实际价格

        Returns:
            float: 滑点（基点）
        """
        if expected_price == 0:
            return 0.0

        diff = abs(actual_price - expected_price)
        bps = float(diff / expected_price * 10000)
        return bps

    @staticmethod
    def calculate_execution_time(start_time: datetime, end_time: datetime) -> int:
        """
        计算执行时间

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            int: 执行时间（毫秒）
        """
        return int((end_time - start_time).total_seconds() * 1000)

    @staticmethod
    def estimate_market_impact(order_value: Decimal, avg_daily_volume: Decimal) -> float:
        """
        估算市场冲击

        Args:
            order_value: 订单金额
            avg_daily_volume: 日均成交额

        Returns:
            float: 估算的市场冲击（0-1）
        """
        if avg_daily_volume == 0:
            return 0.0

        participation_rate = float(order_value / avg_daily_volume)

        # 简化的市场冲击模型
        # 实际模型会更复杂，考虑流动性、波动性等因素
        impact = min(participation_rate * 0.1, 0.5)  # 最高50%

        return impact
