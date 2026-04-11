"""
订单执行引擎测试

测试覆盖：
1. 执行引擎初始化
2. 订单提交执行
3. 订单状态跟踪
4. 执行报告生成
"""
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from src.execution.engine import ExecutionEngine, ExecutionConfig
from src.execution.router import OrderRouter, RouteTarget
from src.execution.monitor import ExecutionMonitor
from src.models.order import Order
from src.models.enums import OrderDirection, OrderType, OrderStatus


@pytest.fixture
def execution_config():
    """执行引擎配置"""
    return ExecutionConfig(
        default_algorithm="MARKET",
        enable_smart_routing=True,
        max_order_value=Decimal("1000000"),
        partial_fill_threshold=100000,
    )


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
    order.remaining_qty = 1000
    order.status = OrderStatus.CREATED
    order.filled_avg_price = Decimal("0")
    order.filled_amount = Decimal("0")
    return order


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    return session


class TestExecutionConfig:
    """执行配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = ExecutionConfig()
        assert config.default_algorithm == "MARKET"
        assert config.enable_smart_routing is True
        assert config.max_order_value == Decimal("1000000")

    def test_custom_config(self):
        """测试自定义配置"""
        config = ExecutionConfig(
            default_algorithm="TWAP",
            enable_smart_routing=False,
            max_order_value=Decimal("500000"),
        )
        assert config.default_algorithm == "TWAP"
        assert config.enable_smart_routing is False
        assert config.max_order_value == Decimal("500000")


class TestExecutionEngine:
    """执行引擎测试"""

    @pytest.fixture
    async def engine(self, execution_config, mock_db_session):
        """创建执行引擎实例"""
        router = Mock(spec=OrderRouter)
        monitor = Mock(spec=ExecutionMonitor)
        engine = ExecutionEngine(
            config=execution_config,
            session=mock_db_session,
            router=router,
            monitor=monitor
        )
        return engine

    @pytest.mark.asyncio
    async def test_engine_initialization(self, execution_config, mock_db_session):
        """测试引擎初始化"""
        router = Mock(spec=OrderRouter)
        monitor = Mock(spec=ExecutionMonitor)

        engine = ExecutionEngine(
            config=execution_config,
            session=mock_db_session,
            router=router,
            monitor=monitor
        )

        assert engine.config == execution_config
        assert engine.session == mock_db_session
        assert engine.router == router
        assert engine.monitor == monitor

    @pytest.mark.asyncio
    async def test_validate_order_valid(self, engine, mock_order):
        """测试订单验证 - 有效订单"""
        engine = await engine
        # 订单金额 = 1000 * 10.50 = 10500 < 1000000 (max_order_value)
        result = await engine.validate_order(mock_order)
        assert result.is_valid is True
        assert result.error_msg is None

    @pytest.mark.asyncio
    async def test_validate_order_exceed_max_value(self, engine, mock_order):
        """测试订单验证 - 超过最大金额限制"""
        engine = await engine
        mock_order.qty = 10000000  # 非常大的数量
        mock_order.price = Decimal("1000")

        result = await engine.validate_order(mock_order)
        assert result.is_valid is False
        assert "超过最大金额限制" in result.error_msg

    @pytest.mark.asyncio
    async def test_validate_order_zero_price(self, engine, mock_order):
        """测试订单验证 - 限价为0"""
        engine = await engine
        mock_order.order_type = OrderType.LIMIT
        mock_order.price = Decimal("0")

        result = await engine.validate_order(mock_order)
        assert result.is_valid is False
        assert "价格必须大于0" in result.error_msg

    @pytest.mark.asyncio
    async def test_validate_order_invalid_symbol(self, engine, mock_order):
        """测试订单验证 - 无效股票代码"""
        engine = await engine
        mock_order.symbol = ""

        result = await engine.validate_order(mock_order)
        assert result.is_valid is False
        assert "股票代码不能为空" in result.error_msg

    @pytest.mark.asyncio
    async def test_execute_order_success(self, engine, mock_order, mock_db_session):
        """测试执行订单 - 成功"""
        engine = await engine

        # 模拟路由决策
        engine.router.route_order = AsyncMock(return_value=RouteTarget.SIMULATED)

        # 模拟订单服务
        with patch('src.execution.engine.OrderService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.submit_order = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            result = await engine.execute_order(mock_order)

            assert result.success is True
            assert result.order_id == mock_order.order_id
            assert result.execution_target == RouteTarget.SIMULATED
            mock_service.submit_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_order_validation_failed(self, engine, mock_order):
        """测试执行订单 - 验证失败"""
        engine = await engine
        mock_order.qty = 100000000  # 超大数量导致验证失败
        mock_order.price = Decimal("100000")

        result = await engine.execute_order(mock_order)

        assert result.success is False
        assert "超过最大金额限制" in result.error_msg

    @pytest.mark.asyncio
    async def test_execute_order_routing_failed(self, engine, mock_order):
        """测试执行订单 - 路由失败"""
        engine = await engine
        engine.router.route_order = AsyncMock(side_effect=Exception("路由错误"))

        result = await engine.execute_order(mock_order)

        assert result.success is False
        assert "路由失败" in result.error_msg

    @pytest.mark.asyncio
    async def test_get_execution_status(self, engine, mock_order):
        """测试获取执行状态"""
        engine = await engine

        # 模拟订单服务
        with patch('src.execution.engine.OrderService') as mock_service_class:
            mock_service = AsyncMock()
            mock_order.status = OrderStatus.PENDING
            mock_order.filled_qty = 500
            mock_order.qty = 1000
            mock_service.get_order = AsyncMock(return_value=mock_order)
            mock_service_class.return_value = mock_service

            status = await engine.get_execution_status("ORD202401011200001")

            assert status is not None
            assert status.order_id == "ORD202401011200001"
            assert status.status == OrderStatus.PENDING
            assert status.fill_rate == 0.5

    @pytest.mark.asyncio
    async def test_cancel_execution(self, engine, mock_order):
        """测试取消执行"""
        engine = await engine

        with patch('src.execution.engine.OrderService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_order = AsyncMock(return_value=mock_order)
            mock_service.cancel_order = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            result = await engine.cancel_execution("ORD202401011200001")

            assert result.success is True
            mock_service.cancel_order.assert_called_once_with(mock_order)

    @pytest.mark.asyncio
    async def test_get_execution_report(self, engine, mock_order):
        """测试获取执行报告"""
        engine = await engine

        with patch('src.execution.engine.OrderService') as mock_service_class:
            mock_service = AsyncMock()
            mock_order.status = OrderStatus.FILLED
            mock_order.filled_qty = 1000
            mock_order.filled_avg_price = Decimal("10.50")
            mock_order.filled_amount = Decimal("10500")
            mock_order.created_at = datetime.now()
            mock_order.filled_at = datetime.now()
            mock_service.get_order = AsyncMock(return_value=mock_order)
            mock_service_class.return_value = mock_service

            report = await engine.get_execution_report("ORD202401011200001")

            assert report is not None
            assert report.order_id == "ORD202401011200001"
            assert report.execution_time_ms > 0
            assert report.slippage_bps >= 0


class TestExecutionResult:
    """执行结果测试"""

    def test_success_result(self):
        """测试成功结果"""
        from src.execution.engine import ExecutionResult

        result = ExecutionResult.success(
            order_id="ORD001",
            target=RouteTarget.SIMULATED,
            message="执行成功"
        )

        assert result.success is True
        assert result.order_id == "ORD001"
        assert result.execution_target == RouteTarget.SIMULATED
        assert result.error_msg is None

    def test_failure_result(self):
        """测试失败结果"""
        from src.execution.engine import ExecutionResult

        result = ExecutionResult.failure(
            order_id="ORD001",
            error_msg="余额不足"
        )

        assert result.success is False
        assert result.order_id == "ORD001"
        assert result.error_msg == "余额不足"


class TestValidationResult:
    """验证结果测试"""

    def test_valid_result(self):
        """测试验证通过"""
        from src.execution.engine import ValidationResult

        result = ValidationResult.valid()
        assert result.is_valid is True
        assert result.error_msg is None

    def test_invalid_result(self):
        """测试验证失败"""
        from src.execution.engine import ValidationResult

        result = ValidationResult.invalid("价格错误")
        assert result.is_valid is False
        assert result.error_msg == "价格错误"
