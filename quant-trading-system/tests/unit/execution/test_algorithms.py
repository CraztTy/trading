"""
算法执行测试

测试覆盖：
1. TWAP算法执行
2. VWAP算法执行
3. 算法参数验证
4. 执行进度跟踪
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.execution.algorithms.base import AlgorithmConfig, AlgorithmStatus
from src.execution.algorithms.twap import TWAPAlgorithm
from src.execution.algorithms.vwap import VWAPAlgorithm
from src.models.order import Order
from src.models.enums import OrderDirection, OrderType, OrderStatus


@pytest.fixture
def mock_order():
    """模拟订单"""
    order = Mock(spec=Order)
    order.order_id = "ORD202401011200001"
    order.account_id = 1
    order.symbol = "000001.SZ"
    order.direction = OrderDirection.BUY
    order.order_type = OrderType.LIMIT
    order.qty = 10000
    order.price = Decimal("10.50")
    order.filled_qty = 0
    order.remaining_qty = 10000
    order.status = OrderStatus.PENDING
    return order


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    return session


class TestAlgorithmConfig:
    """算法配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = AlgorithmConfig()
        assert config.duration_seconds == 300
        assert config.num_slices == 5
        assert config.min_slice_size == 100

    def test_custom_config(self):
        """测试自定义配置"""
        config = AlgorithmConfig(
            duration_seconds=600,
            num_slices=10,
            min_slice_size=200,
            max_participation_rate=0.3
        )
        assert config.duration_seconds == 600
        assert config.num_slices == 10
        assert config.min_slice_size == 200
        assert config.max_participation_rate == 0.3

    def test_invalid_config(self):
        """测试无效配置"""
        with pytest.raises(ValueError):
            AlgorithmConfig(duration_seconds=0)

        with pytest.raises(ValueError):
            AlgorithmConfig(num_slices=0)


class TestAlgorithmStatus:
    """算法状态测试"""

    def test_status_values(self):
        """测试状态值"""
        assert AlgorithmStatus.PENDING.value == "pending"
        assert AlgorithmStatus.RUNNING.value == "running"
        assert AlgorithmStatus.PAUSED.value == "paused"
        assert AlgorithmStatus.COMPLETED.value == "completed"
        assert AlgorithmStatus.CANCELLED.value == "cancelled"
        assert AlgorithmStatus.FAILED.value == "failed"


class TestTWAPAlgorithm:
    """TWAP算法测试"""

    @pytest.fixture
    def twap(self, mock_order, mock_db_session):
        """创建TWAP算法实例"""
        config = AlgorithmConfig(
            duration_seconds=60,  # 短时长便于测试
            num_slices=5,
            min_slice_size=100
        )
        return TWAPAlgorithm(
            order=mock_order,
            config=config,
            session=mock_db_session
        )

    def test_twap_initialization(self, twap, mock_order):
        """测试TWAP初始化"""
        assert twap.order == mock_order
        assert twap.status == AlgorithmStatus.PENDING
        assert twap.total_slices == 5
        assert twap.completed_slices == 0

    def test_calculate_slice_sizes(self, twap):
        """测试切片大小计算"""
        slices = twap._calculate_slice_sizes(1000, 5)
        assert len(slices) == 5
        assert sum(slices) == 1000
        # 每个切片应该是100的整数倍
        for size in slices:
            assert size % 100 == 0

    def test_calculate_slice_sizes_with_min_size(self, twap):
        """测试带最小大小的切片计算"""
        slices = twap._calculate_slice_sizes(550, 5)
        assert len(slices) <= 5  # 可能少于5个切片
        assert sum(slices) == 550
        # 每个切片至少100
        for size in slices:
            assert size >= 100

    @pytest.mark.asyncio
    async def test_execute_single_slice(self, twap):
        """测试执行单个切片"""
        with patch('src.execution.algorithms.twap.OrderService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.fill_order = AsyncMock(return_value=True)
            mock_service_class.return_value = mock_service

            result = await twap._execute_slice(100, Decimal("10.50"))

            assert result is True
            mock_service.fill_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_all_slices(self, twap):
        """测试执行所有切片"""
        executed_slices = []

        async def mock_execute_slice(qty, price):
            executed_slices.append(qty)
            return True

        twap._execute_slice = mock_execute_slice

        # 设置切片
        twap.slice_sizes = [2000, 2000, 2000, 2000, 2000]
        twap.slice_interval = 0.01  # 短时间隔

        await twap.execute()

        assert twap.status == AlgorithmStatus.COMPLETED
        assert sum(executed_slices) == 10000

    @pytest.mark.asyncio
    async def test_pause_and_resume(self, twap):
        """测试暂停和恢复"""
        twap.status = AlgorithmStatus.RUNNING

        await twap.pause()
        assert twap.status == AlgorithmStatus.PAUSED

        await twap.resume()
        assert twap.status == AlgorithmStatus.RUNNING

    @pytest.mark.asyncio
    async def test_cancel(self, twap):
        """测试取消"""
        twap.status = AlgorithmStatus.RUNNING

        await twap.cancel()
        assert twap.status == AlgorithmStatus.CANCELLED
        assert twap._cancelled is True

    def test_get_progress_pending(self, twap):
        """测试获取进度 - 待执行"""
        progress = twap.get_progress()
        assert progress.status == AlgorithmStatus.PENDING
        assert progress.completion_pct == 0.0

    def test_get_progress_running(self, twap):
        """测试获取进度 - 执行中"""
        twap.status = AlgorithmStatus.RUNNING
        twap.completed_slices = 2
        twap.total_slices = 5

        progress = twap.get_progress()
        assert progress.status == AlgorithmStatus.RUNNING
        assert progress.completion_pct == 0.4

    def test_estimate_completion_time(self, twap):
        """测试估算完成时间"""
        twap.start_time = datetime.now()
        twap.completed_slices = 2
        twap.total_slices = 5
        twap.slice_interval = 10

        eta = twap.estimate_completion_time()
        # 还剩3个切片，每个间隔10秒
        expected_seconds = 3 * 10
        assert abs(eta - expected_seconds) < 1


class TestVWAPAlgorithm:
    """VWAP算法测试"""

    @pytest.fixture
    def vwap(self, mock_order, mock_db_session):
        """创建VWAP算法实例"""
        config = AlgorithmConfig(
            duration_seconds=60,
            num_slices=5,
            min_slice_size=100,
            volume_profile="U"  # U型分布
        )
        return VWAPAlgorithm(
            order=mock_order,
            config=config,
            session=mock_db_session
        )

    def test_vwap_initialization(self, vwap, mock_order):
        """测试VWAP初始化"""
        assert vwap.order == mock_order
        assert vwap.status == AlgorithmStatus.PENDING
        assert vwap.volume_profile == "U"

    def test_calculate_volume_profile_u_shape(self, vwap):
        """测试U型成交量分布"""
        profile = vwap._calculate_volume_profile(5, "U")
        assert len(profile) == 5
        assert abs(sum(profile) - 1.0) < 0.001  # 总和应为1
        # U型：两头大中间小
        assert profile[0] > profile[2]
        assert profile[4] > profile[2]

    def test_calculate_volume_profile_uniform(self, vwap):
        """测试均匀成交量分布"""
        profile = vwap._calculate_volume_profile(5, "flat")
        assert len(profile) == 5
        # 均匀分布每个相等
        for p in profile:
            assert abs(p - 0.2) < 0.001

    def test_calculate_volume_profile_increasing(self, vwap):
        """测试递增成交量分布"""
        profile = vwap._calculate_volume_profile(5, "increasing")
        assert len(profile) == 5
        assert abs(sum(profile) - 1.0) < 0.001
        # 递增分布
        assert profile[0] < profile[1] < profile[2] < profile[3] < profile[4]

    def test_apply_volume_profile_to_slices(self, vwap):
        """测试应用成交量分布到切片"""
        profile = [0.3, 0.2, 0.2, 0.2, 0.1]
        slices = vwap._apply_volume_profile(10000, profile)

        assert len(slices) == 5
        # 检查大致比例（考虑整数取整）
        assert slices[0] > slices[4]  # 第一个应该最大

    @pytest.mark.asyncio
    async def test_vwap_execute(self, vwap):
        """测试VWAP执行"""
        executed_slices = []

        async def mock_execute_slice(qty, price):
            executed_slices.append(qty)
            return True

        vwap._execute_slice = mock_execute_slice
        vwap.slice_interval = 0.01

        await vwap.execute()

        assert vwap.status == AlgorithmStatus.COMPLETED
        assert sum(executed_slices) == 10000

    def test_get_vwap_metrics(self, vwap):
        """测试获取VWAP指标"""
        vwap.executed_prices = [
            (1000, Decimal("10.50")),
            (2000, Decimal("10.48")),
            (3000, Decimal("10.52")),
        ]

        metrics = vwap.get_metrics()

        assert metrics.total_volume == 6000
        assert metrics.vwap_price > Decimal("10.48")
        assert metrics.vwap_price < Decimal("10.52")


class TestAlgorithmFactory:
    """算法工厂测试"""

    def test_create_twap_algorithm(self, mock_order, mock_db_session):
        """测试创建TWAP算法"""
        from src.execution.algorithms import create_algorithm

        config = AlgorithmConfig()
        algo = create_algorithm("TWAP", mock_order, config, mock_db_session)

        assert isinstance(algo, TWAPAlgorithm)

    def test_create_vwap_algorithm(self, mock_order, mock_db_session):
        """测试创建VWAP算法"""
        from src.execution.algorithms import create_algorithm

        config = AlgorithmConfig()
        algo = create_algorithm("VWAP", mock_order, config, mock_db_session)

        assert isinstance(algo, VWAPAlgorithm)

    def test_create_unknown_algorithm(self, mock_order, mock_db_session):
        """测试创建未知算法"""
        from src.execution.algorithms import create_algorithm

        config = AlgorithmConfig()

        with pytest.raises(ValueError) as exc_info:
            create_algorithm("UNKNOWN", mock_order, config, mock_db_session)

        assert "未知算法类型" in str(exc_info.value)

    def test_create_market_algorithm(self, mock_order, mock_db_session):
        """测试创建MARKET算法（默认）"""
        from src.execution.algorithms import create_algorithm

        config = AlgorithmConfig()
        algo = create_algorithm("MARKET", mock_order, config, mock_db_session)

        # MARKET应该使用默认实现
        assert algo is not None
