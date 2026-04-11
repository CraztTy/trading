"""
撮合引擎单元测试

测试撮合逻辑、涨跌停限制、滑点计算等
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from src.core.matching_engine import (
    SimulatedMatchingEngine,
    MarketDataSimulator,
    MarketPrice,
    MatchResult
)
from src.models.enums import OrderDirection, OrderStatus


@pytest.mark.unit
class TestSimulatedMatchingEngine:
    """撮合引擎测试类"""

    @pytest.fixture
    def engine(self):
        """创建撮合引擎实例"""
        return SimulatedMatchingEngine()

    @pytest.fixture
    def sample_buy_order(self):
        """样本买入订单"""
        order = MagicMock()
        order.symbol = "000001.SZ"
        order.direction = OrderDirection.BUY
        order.price = Decimal("10.50")
        order.qty = 1000
        order.filled_qty = 0
        order.status = OrderStatus.PENDING
        return order

    @pytest.fixture
    def sample_sell_order(self):
        """样本卖出订单"""
        order = MagicMock()
        order.symbol = "000001.SZ"
        order.direction = OrderDirection.SELL
        order.price = Decimal("10.50")
        order.qty = 1000
        order.filled_qty = 0
        order.status = OrderStatus.PENDING
        return order

    @pytest.fixture
    def market_price_normal(self):
        """正常市场价格"""
        return MarketPrice(
            symbol="000001.SZ",
            last_price=Decimal("10.50"),
            bid_price=Decimal("10.49"),
            ask_price=Decimal("10.51"),
            bid_volume=5000,
            ask_volume=5000,
            high_limit=Decimal("11.55"),  # +10%
            low_limit=Decimal("9.45")     # -10%
        )

    @pytest.fixture
    def market_price_uplimit(self):
        """涨停价格"""
        return MarketPrice(
            symbol="000001.SZ",
            last_price=Decimal("11.55"),  # 涨停价
            bid_price=Decimal("11.55"),
            ask_price=Decimal("11.55"),
            high_limit=Decimal("11.55"),
            low_limit=Decimal("9.45")
        )

    @pytest.fixture
    def market_price_downlimit(self):
        """跌停价格"""
        return MarketPrice(
            symbol="000001.SZ",
            last_price=Decimal("9.45"),   # 跌停价
            bid_price=Decimal("9.45"),
            ask_price=Decimal("9.45"),
            high_limit=Decimal("11.55"),
            low_limit=Decimal("9.45")
        )

    # ==================== 基本撮合测试 ====================

    def test_try_match_success_buy(self, engine, sample_buy_order, market_price_normal):
        """测试: 买入订单成功撮合"""
        # Arrange
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True
        assert result.filled_qty == 1000  # 小单全额成交
        assert result.filled_price > Decimal("0")
        assert result.remaining_qty == 0

    def test_try_match_success_sell(self, engine, sample_sell_order, market_price_normal):
        """测试: 卖出订单成功撮合"""
        # Arrange
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_sell_order)

        # Assert
        assert result.success is True
        assert result.filled_qty == 1000
        assert result.filled_price > Decimal("0")

    def test_try_match_no_market_data(self, engine, sample_buy_order):
        """测试: 无市场数据时撮合失败"""
        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is False
        assert "无市场数据" in result.message

    # ==================== 涨跌停限制测试 ====================

    def test_buy_at_uplimit_rejected(self, engine, sample_buy_order, market_price_uplimit):
        """测试: 涨停时买入被拒绝"""
        # Arrange
        engine.update_market_price(market_price_uplimit)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is False
        assert "涨停" in result.message
        assert "无法买入" in result.message

    def test_sell_at_downlimit_rejected(self, engine, sample_sell_order, market_price_downlimit):
        """测试: 跌停时卖出被拒绝"""
        # Arrange
        engine.update_market_price(market_price_downlimit)

        # Act
        result = engine.try_match(sample_sell_order)

        # Assert
        assert result.success is False
        assert "跌停" in result.message
        assert "无法卖出" in result.message

    def test_buy_price_exceeds_uplimit(self, engine, sample_buy_order, market_price_normal):
        """测试: 买入价格超过涨停价被拒绝"""
        # Arrange
        sample_buy_order.price = Decimal("12.00")  # 超过涨停价11.55
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is False
        assert "超过涨停价" in result.message

    def test_sell_price_below_downlimit(self, engine, sample_sell_order, market_price_normal):
        """测试: 卖出价格低于跌停价被拒绝"""
        # Arrange
        sample_sell_order.price = Decimal("9.00")  # 低于跌停价9.45
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_sell_order)

        # Assert
        assert result.success is False
        assert "低于跌停价" in result.message

    def test_sell_at_uplimit_allowed(self, engine, sample_sell_order, market_price_uplimit):
        """测试: 涨停时可以卖出"""
        # Arrange
        engine.update_market_price(market_price_uplimit)

        # Act
        result = engine.try_match(sample_sell_order)

        # Assert
        assert result.success is True

    def test_buy_at_downlimit_allowed(self, engine, sample_buy_order, market_price_downlimit):
        """测试: 跌停时可以买入"""
        # Arrange
        engine.update_market_price(market_price_downlimit)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True

    # ==================== 成交数量计算测试 ====================

    def test_small_order_full_fill(self, engine, sample_buy_order, market_price_normal):
        """测试: 小单（<10万）全额成交"""
        # Arrange
        sample_buy_order.qty = 500  # 500 * 10.50 = 5250 < 100000
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True
        assert result.filled_qty == 500

    def test_large_order_partial_fill(self, engine, sample_buy_order, market_price_normal):
        """测试: 大单（>10万）部分成交"""
        # Arrange
        sample_buy_order.qty = 20000  # 20000 * 10.50 = 210000 > 100000
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True
        assert result.filled_qty >= 6000  # 至少成交30% (20000 * 0.3 = 6000)
        assert result.filled_qty <= 20000  # 不超过订单量
        assert result.filled_qty % 100 == 0  # 对齐到100股

    def test_fill_qty_rounding(self, engine, sample_buy_order, market_price_normal):
        """测试: 成交数量对齐到100股（A股最小单位）"""
        # Arrange - 创建一个会产生非100倍数的场景
        sample_buy_order.qty = 150  # 很小的单，但测试对齐逻辑
        engine.update_market_price(market_price_normal)
        engine.partial_fill_threshold = 0  # 强制进入部分成交逻辑
        engine.min_fill_ratio = 0.99  # 几乎全额成交

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert - 即使没有进入部分成交逻辑，也应该对齐到100股
        if result.success:
            assert result.filled_qty % 100 == 0, f"成交数量{result.filled_qty}未对齐到100股"

    def test_fill_not_exceed_remaining(self, engine, sample_buy_order, market_price_normal):
        """测试: 成交数量不超过剩余数量"""
        # Arrange
        sample_buy_order.qty = 1000
        sample_buy_order.filled_qty = 800  # 已成交800
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True
        assert result.filled_qty <= 200  # 不能超过剩余200

    # ==================== 滑点计算测试 ====================

    def test_buy_slippage_upward(self, engine, sample_buy_order, market_price_normal):
        """测试: 买入滑点向上（成交价 >= 委托价）"""
        # Arrange
        sample_buy_order.price = Decimal("10.50")
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True
        assert result.filled_price >= sample_buy_order.price
        # 滑点不超过0.1%
        max_slippage = sample_buy_order.price * Decimal("1.001")
        assert result.filled_price <= max_slippage

    def test_sell_slippage_downward(self, engine, sample_sell_order, market_price_normal):
        """测试: 卖出滑点向下（成交价 <= 委托价）"""
        # Arrange
        sample_sell_order.price = Decimal("10.50")
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_sell_order)

        # Assert
        assert result.success is True
        assert result.filled_price <= sample_sell_order.price
        # 滑点不超过0.1%
        min_slippage = sample_sell_order.price * Decimal("0.999")
        assert result.filled_price >= min_slippage

    def test_fill_price_two_decimals(self, engine, sample_buy_order, market_price_normal):
        """测试: 成交价格保留两位小数"""
        # Arrange
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True
        price_str = str(result.filled_price)
        if '.' in price_str:
            assert len(price_str.split('.')[1]) <= 2

    # ==================== 订单簿测试 ====================

    def test_register_fill_callback(self, engine, sample_buy_order, market_price_normal):
        """测试: 成交回调注册"""
        # Arrange
        callback_called = []

        def test_callback(order, fill_qty, fill_price):
            callback_called.append((order, fill_qty, fill_price))

        engine.register_fill_callback(test_callback)
        engine.update_market_price(market_price_normal)

        # Act
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True
        assert len(callback_called) == 1
        assert callback_called[0][0] == sample_buy_order

    def test_callback_exception_not_blocking(self, engine, sample_buy_order, market_price_normal):
        """测试: 回调异常不阻塞主流程"""
        # Arrange
        def failing_callback(order, fill_qty, fill_price):
            raise ValueError("回调错误")

        engine.register_fill_callback(failing_callback)
        engine.update_market_price(market_price_normal)

        # Act - 不应抛出异常
        result = engine.try_match(sample_buy_order)

        # Assert
        assert result.success is True

    # ==================== can_match 测试 ====================

    def test_can_match_pending_order(self, engine, sample_buy_order, market_price_normal):
        """测试: PENDING状态可以撮合"""
        # Arrange
        sample_buy_order.status = OrderStatus.PENDING
        engine.update_market_price(market_price_normal)

        # Act & Assert
        assert engine.can_match(sample_buy_order) is True

    def test_can_match_partial_order(self, engine, sample_buy_order, market_price_normal):
        """测试: PARTIAL状态可以撮合"""
        # Arrange
        sample_buy_order.status = OrderStatus.PARTIAL
        engine.update_market_price(market_price_normal)

        # Act & Assert
        assert engine.can_match(sample_buy_order) is True

    def test_can_match_filled_order(self, engine, sample_buy_order, market_price_normal):
        """测试: FILLED状态不可以撮合"""
        # Arrange
        sample_buy_order.status = OrderStatus.FILLED
        engine.update_market_price(market_price_normal)

        # Act & Assert
        assert engine.can_match(sample_buy_order) is False

    def test_can_match_no_market_data(self, engine, sample_buy_order):
        """测试: 无市场数据时不可以撮合"""
        # Arrange
        sample_buy_order.status = OrderStatus.PENDING

        # Act & Assert
        assert engine.can_match(sample_buy_order) is False


@pytest.mark.unit
class TestMarketDataSimulator:
    """市场数据模拟器测试"""

    @pytest.fixture
    def simulator(self):
        """创建市场数据模拟器"""
        return MarketDataSimulator()

    def test_set_base_price(self, simulator):
        """测试: 设置基准价格"""
        # Act
        simulator.set_base_price("000001.SZ", Decimal("10.50"))

        # Assert
        price = simulator.get_price("000001.SZ")
        assert price is not None
        assert price.last_price == Decimal("10.50")
        assert price.high_limit == Decimal("11.55")  # +10%
        assert price.low_limit == Decimal("9.45")    # -10%

    def test_tick_price_change(self, simulator):
        """测试: 价格变动模拟"""
        # Arrange
        simulator.set_base_price("000001.SZ", Decimal("10.50"))
        initial_price = simulator.get_price("000001.SZ").last_price

        # Act
        simulator.tick("000001.SZ")
        new_price = simulator.get_price("000001.SZ").last_price

        # Assert
        assert new_price != initial_price  # 价格应该变动
        # 变动范围在 ±1% 内
        assert Decimal("10.395") <= new_price <= Decimal("10.605")

    def test_tick_respects_price_limits(self, simulator):
        """测试: 价格变动不超过涨跌停限制"""
        # Arrange - 设置价格在涨停边缘
        simulator.set_base_price("000001.SZ", Decimal("11.50"))
        # 多次tick，验证价格不超过涨停
        for _ in range(100):
            simulator.tick("000001.SZ")
            price = simulator.get_price("000001.SZ")
            assert price.last_price <= price.high_limit
            assert price.last_price >= price.low_limit

    def test_tick_all_symbols(self, simulator):
        """测试: 同时更新所有标的价格"""
        # Arrange
        simulator.set_base_price("000001.SZ", Decimal("10.50"))
        simulator.set_base_price("000002.SZ", Decimal("20.00"))

        # Act
        simulator.tick()

        # Assert
        price1 = simulator.get_price("000001.SZ")
        price2 = simulator.get_price("000002.SZ")
        assert price1.last_price != Decimal("10.50")  # 应该变动了
        assert price2.last_price != Decimal("20.00")

    def test_get_price_nonexistent(self, simulator):
        """测试: 获取不存在的价格返回None"""
        # Act
        price = simulator.get_price("999999.SZ")

        # Assert
        assert price is None
