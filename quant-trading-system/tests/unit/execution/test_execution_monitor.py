"""
订单执行监控测试

测试覆盖：
1. 监控器初始化
2. 执行事件跟踪
3. 统计信息收集
4. 告警触发
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.execution.monitor import (
    ExecutionMonitor, ExecutionMetrics, ExecutionEvent,
    ExecutionStatistics, AlertRule, AlertLevel
)
from src.models.order import Order
from src.models.enums import OrderDirection, OrderType, OrderStatus


@pytest.fixture
def monitor():
    """创建监控器实例"""
    return ExecutionMonitor()


@pytest.fixture
def mock_order():
    """模拟订单"""
    order = Mock(spec=Order)
    order.order_id = "ORD202401011200001"
    order.account_id = 1
    order.symbol = "000001.SZ"
    order.direction = OrderDirection.BUY
    order.order_type = OrderType.LIMIT
    order.qty = 1000
    order.price = Decimal("10.50")
    order.filled_qty = 0
    order.status = OrderStatus.CREATED
    return order


class TestAlertLevel:
    """告警级别测试"""

    def test_level_values(self):
        """测试级别值"""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"


class TestExecutionEvent:
    """执行事件测试"""

    def test_event_creation(self):
        """测试事件创建"""
        event = ExecutionEvent(
            event_type="ORDER_CREATED",
            order_id="ORD001",
            timestamp=datetime.now(),
            details={"symbol": "000001.SZ", "qty": 1000}
        )
        assert event.event_type == "ORDER_CREATED"
        assert event.order_id == "ORD001"
        assert event.details["symbol"] == "000001.SZ"


class TestExecutionMetrics:
    """执行指标测试"""

    def test_metrics_creation(self):
        """测试指标创建"""
        metrics = ExecutionMetrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=1000,
            filled_qty=500,
            avg_fill_price=Decimal("10.50"),
            start_time=datetime.now()
        )
        assert metrics.fill_rate == 0.5
        assert metrics.remaining_qty == 500

    def test_fill_rate_calculation(self):
        """测试填充率计算"""
        metrics = ExecutionMetrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=1000,
            filled_qty=750,
            avg_fill_price=Decimal("10.50"),
            start_time=datetime.now()
        )
        assert metrics.fill_rate == 0.75

    def test_fill_rate_zero_total(self):
        """测试总数为0时的填充率"""
        metrics = ExecutionMetrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=0,
            filled_qty=0,
            avg_fill_price=Decimal("0"),
            start_time=datetime.now()
        )
        assert metrics.fill_rate == 0.0


class TestExecutionMonitor:
    """执行监控器测试"""

    def test_monitor_initialization(self, monitor):
        """测试监控器初始化"""
        assert monitor is not None
        assert len(monitor._events) == 0
        assert len(monitor._metrics) == 0
        assert len(monitor._alert_rules) == 0

    def test_record_event(self, monitor):
        """测试记录事件"""
        monitor.record_event(
            event_type="ORDER_SUBMITTED",
            order_id="ORD001",
            details={"symbol": "000001.SZ"}
        )

        assert len(monitor._events) == 1
        assert monitor._events[0].event_type == "ORDER_SUBMITTED"
        assert monitor._events[0].order_id == "ORD001"

    def test_update_metrics(self, monitor):
        """测试更新指标"""
        monitor.update_metrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=1000,
            filled_qty=100,
            avg_fill_price=Decimal("10.50")
        )

        metrics = monitor.get_metrics("ORD001")
        assert metrics is not None
        assert metrics.total_qty == 1000
        assert metrics.filled_qty == 100

    def test_update_metrics_incremental(self, monitor):
        """测试增量更新指标"""
        monitor.update_metrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=1000,
            filled_qty=100,
            avg_fill_price=Decimal("10.50")
        )

        # 再次更新
        monitor.update_metrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=1000,
            filled_qty=300,  # 增加了200
            avg_fill_price=Decimal("10.48")
        )

        metrics = monitor.get_metrics("ORD001")
        assert metrics.filled_qty == 300
        assert metrics.fill_rate == 0.3

    def test_get_nonexistent_metrics(self, monitor):
        """测试获取不存在的指标"""
        metrics = monitor.get_metrics("NONEXISTENT")
        assert metrics is None

    def test_add_alert_rule(self, monitor):
        """测试添加告警规则"""
        rule = AlertRule(
            name="low_fill_rate",
            condition=lambda metrics: metrics.fill_rate < 0.1,
            level=AlertLevel.WARNING,
            message="填充率过低"
        )
        monitor.add_alert_rule(rule)

        assert len(monitor._alert_rules) == 1

    def test_check_alerts_triggered(self, monitor):
        """测试告警触发"""
        # 添加告警规则
        rule = AlertRule(
            name="low_fill_rate",
            condition=lambda metrics: metrics.fill_rate < 0.1,
            level=AlertLevel.WARNING,
            message="填充率过低"
        )
        monitor.add_alert_rule(rule)

        # 创建低填充率指标
        metrics = ExecutionMetrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=1000,
            filled_qty=50,  # 只有5%填充率
            avg_fill_price=Decimal("10.50"),
            start_time=datetime.now()
        )

        alerts = monitor.check_alerts(metrics)

        assert len(alerts) == 1
        assert alerts[0].rule_name == "low_fill_rate"
        assert alerts[0].level == AlertLevel.WARNING

    def test_check_alerts_not_triggered(self, monitor):
        """测试告警未触发"""
        rule = AlertRule(
            name="low_fill_rate",
            condition=lambda metrics: metrics.fill_rate < 0.1,
            level=AlertLevel.WARNING,
            message="填充率过低"
        )
        monitor.add_alert_rule(rule)

        # 创建正常填充率指标
        metrics = ExecutionMetrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=1000,
            filled_qty=500,  # 50%填充率
            avg_fill_price=Decimal("10.50"),
            start_time=datetime.now()
        )

        alerts = monitor.check_alerts(metrics)

        assert len(alerts) == 0

    def test_get_order_events(self, monitor):
        """测试获取订单事件"""
        # 记录多个事件
        monitor.record_event("ORDER_CREATED", "ORD001", {})
        monitor.record_event("ORDER_SUBMITTED", "ORD001", {})
        monitor.record_event("ORDER_FILLED", "ORD001", {})
        monitor.record_event("ORDER_CREATED", "ORD002", {})  # 其他订单

        events = monitor.get_order_events("ORD001")

        assert len(events) == 3
        for event in events:
            assert event.order_id == "ORD001"

    def test_get_execution_statistics(self, monitor):
        """测试获取执行统计"""
        # 记录一些执行数据
        for i in range(10):
            monitor.update_metrics(
                order_id=f"ORD{i:03d}",
                symbol="000001.SZ",
                total_qty=1000,
                filled_qty=1000 if i < 8 else 500,  # 80%完全成交
                avg_fill_price=Decimal("10.50")
            )

        stats = monitor.get_execution_statistics()

        assert stats.total_orders == 10
        assert stats.completed_orders == 8
        assert stats.completion_rate == 0.8

    def test_clear_old_events(self, monitor):
        """测试清理旧事件"""
        old_time = datetime.now() - timedelta(days=10)
        new_time = datetime.now()

        # 添加旧事件
        monitor._events.append(ExecutionEvent(
            event_type="OLD_EVENT",
            order_id="ORD001",
            timestamp=old_time,
            details={}
        ))

        # 添加新事件
        monitor._events.append(ExecutionEvent(
            event_type="NEW_EVENT",
            order_id="ORD002",
            timestamp=new_time,
            details={}
        ))

        # 清理7天前的事件
        cleared = monitor.clear_old_events(days=7)

        assert cleared == 1
        assert len(monitor._events) == 1
        assert monitor._events[0].event_type == "NEW_EVENT"

    def test_export_metrics(self, monitor):
        """测试导出指标"""
        monitor.update_metrics(
            order_id="ORD001",
            symbol="000001.SZ",
            total_qty=1000,
            filled_qty=500,
            avg_fill_price=Decimal("10.50")
        )

        exported = monitor.export_metrics()

        assert "ORD001" in exported
        assert exported["ORD001"]["total_qty"] == 1000
        assert exported["ORD001"]["filled_qty"] == 500

    @pytest.mark.asyncio
    async def test_start_monitoring(self, monitor):
        """测试启动监控"""
        monitor._monitoring_loop = AsyncMock()

        await monitor.start()

        assert monitor._running is True

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, monitor):
        """测试停止监控"""
        monitor._running = True

        await monitor.stop()

        assert monitor._running is False

    def test_slippage_calculation(self, monitor):
        """测试滑点计算"""
        expected_price = Decimal("10.50")
        actual_price = Decimal("10.53")

        slippage_bps = monitor.calculate_slippage(expected_price, actual_price)

        # (10.53 - 10.50) / 10.50 * 10000 = ~28.57 bps
        assert slippage_bps > 28
        assert slippage_bps < 29

    def test_execution_time_calculation(self, monitor):
        """测试执行时间计算"""
        start_time = datetime.now() - timedelta(seconds=5)
        end_time = datetime.now()

        execution_time_ms = monitor.calculate_execution_time(start_time, end_time)

        # 应该大约是5000ms
        assert execution_time_ms >= 5000
        assert execution_time_ms < 6000

    def test_market_impact_estimation(self, monitor):
        """测试市场冲击估算"""
        order_value = Decimal("100000")  # 10万订单
        avg_daily_volume = Decimal("10000000")  # 日成交额1000万

        impact = monitor.estimate_market_impact(order_value, avg_daily_volume)

        # 10万/1000万 = 1%，冲击应该与这个比例相关
        assert impact > 0
        assert impact < 1
