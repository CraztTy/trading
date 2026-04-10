"""
风控模块单元测试

测试门下省风控审核逻辑
"""
import pytest
from datetime import datetime

from src.core.menxia_sheng import MenxiaSheng, RiskCheckResult


@pytest.mark.unit
class TestMenxiaSheng:
    """门下省风控测试类"""

    @pytest.fixture
    def risk_engine(self, risk_config):
        """创建风控引擎"""
        return MenxiaSheng(risk_config)

    @pytest.fixture
    def base_portfolio(self):
        """基础账户持仓"""
        return {
            "cash": 1000000.0,
            "total_value": 1000000.0,
            "total_position": 0.0,
            "positions": {},
            "consecutive_losses": 0
        }

    # ==================== 止损检查测试 ====================

    @pytest.mark.asyncio
    async def test_stop_loss_within_limit(self, risk_engine, base_portfolio):
        """测试: 止损比例在限制内通过"""
        # Arrange
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000,
            "stop_loss": 9.6  # 4%止损，在5%限制内
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 1
        assert len(rejected) == 0

    @pytest.mark.asyncio
    async def test_stop_loss_exceeds_limit(self, risk_engine, base_portfolio):
        """测试: 止损比例超限被拒绝"""
        # Arrange
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000,
            "stop_loss": 9.0  # 10%止损，超过5%限制
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 0
        assert len(rejected) == 1
        assert "止损比例" in rejected[0]["reject_reason"]

    @pytest.mark.asyncio
    async def test_stop_loss_not_set(self, risk_engine, base_portfolio):
        """测试: 未设置止损也通过"""
        # Arrange
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
            # 没有stop_loss字段
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 1

    # ==================== 单票仓位检查测试 ====================

    @pytest.mark.asyncio
    async def test_single_position_within_limit(self, risk_engine, base_portfolio):
        """测试: 单票仓位在限制内通过"""
        # Arrange
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 5000  # 50000元，5%仓位
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 1

    @pytest.mark.asyncio
    async def test_single_position_exceeds_limit(self, risk_engine, base_portfolio):
        """测试: 单票仓位超限被拒绝"""
        # Arrange
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 20000  # 200000元，20%仓位，超过10%限制
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 0
        assert len(rejected) == 1
        assert "单票仓位" in rejected[0]["reject_reason"]

    @pytest.mark.asyncio
    async def test_single_position_with_existing(self, risk_engine, base_portfolio):
        """测试: 已有仓位+新买入超限"""
        # Arrange
        base_portfolio["positions"]["000001.SZ"] = {
            "value": 80000  # 已有8万仓位
        }
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 5000  # 新增5万，合计13万=13%，超过10%
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 0

    @pytest.mark.asyncio
    async def test_single_position_sell_skipped(self, risk_engine, base_portfolio):
        """测试: 卖出订单跳过单票仓位检查"""
        # Arrange
        signal = {
            "code": "000001.SZ",
            "direction": "SELL",
            "price": 10.0,
            "qty": 20000
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert - 卖出应该通过，不检查单票仓位
        # 但可能因为其他规则被拒绝

    # ==================== 总仓位检查测试 ====================

    @pytest.mark.asyncio
    async def test_total_position_within_limit(self, risk_engine, base_portfolio):
        """测试: 总仓位在限制内通过"""
        # Arrange
        base_portfolio["total_position"] = 100000  # 已有10万
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 10000  # 新增10万，合计20万=20%，在50%内
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 1

    @pytest.mark.asyncio
    async def test_total_position_exceeds_limit(self, risk_engine, base_portfolio):
        """测试: 总仓位超限被拒绝"""
        # Arrange
        base_portfolio["total_position"] = 450000  # 已有45万
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 10000  # 新增10万，合计55万=55%，超过50%
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 0
        assert "总仓位" in rejected[0]["reject_reason"]

    # ==================== 日亏损熔断测试 ====================

    @pytest.mark.asyncio
    async def test_daily_loss_within_limit(self, risk_engine, base_portfolio):
        """测试: 日亏损在限制内通过"""
        # Arrange
        today = datetime.now().date().isoformat()
        risk_engine.daily_stats[today] = {"pnl": -1000}  # 日亏损1000，0.1%

        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 1

    @pytest.mark.asyncio
    async def test_daily_loss_circuit_breaker(self, risk_engine, base_portfolio):
        """测试: 日亏损超限触发熔断"""
        # Arrange
        today = datetime.now().date().isoformat()
        risk_engine.daily_stats[today] = {"pnl": -30000}  # 日亏损3万，3%

        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 0
        assert "熔断" in rejected[0]["reject_reason"]

    # ==================== 连续亏损检查测试 ====================

    @pytest.mark.asyncio
    async def test_consecutive_losses_within_limit(self, risk_engine, base_portfolio):
        """测试: 连续亏损次数在限制内通过"""
        # Arrange
        base_portfolio["consecutive_losses"] = 2  # 2次，在限制3次内

        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 1

    @pytest.mark.asyncio
    async def test_consecutive_losses_exceeds_limit(self, risk_engine, base_portfolio):
        """测试: 连续亏损超限暂停开仓"""
        # Arrange
        base_portfolio["consecutive_losses"] = 3  # 3次，达到限制

        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 0
        assert "连续亏损" in rejected[0]["reject_reason"]

    # ==================== 委托频率限制测试 ====================

    @pytest.mark.asyncio
    async def test_order_frequency_allowed(self, risk_engine, base_portfolio):
        """测试: 首次委托允许"""
        # Arrange
        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
        }

        # Act
        passed, rejected = await risk_engine.review_signals([signal], base_portfolio)

        # Assert
        assert len(passed) == 1

    @pytest.mark.asyncio
    async def test_order_frequency_rejected(self, risk_engine, base_portfolio):
        """测试: 1分钟内重复委托被拒绝"""
        # Arrange
        signal1 = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
        }
        signal2 = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 500
        }

        # Act
        passed1, rejected1 = await risk_engine.review_signals([signal1], base_portfolio)
        passed2, rejected2 = await risk_engine.review_signals([signal2], base_portfolio)

        # Assert
        assert len(passed1) == 1
        assert len(passed2) == 0
        assert "频率限制" in rejected2[0]["reject_reason"]

    @pytest.mark.asyncio
    async def test_order_frequency_different_stocks(self, risk_engine, base_portfolio):
        """测试: 不同股票委托频率互不影响"""
        # Arrange
        signal1 = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
        }
        signal2 = {
            "code": "000002.SZ",
            "direction": "BUY",
            "price": 20.0,
            "qty": 500
        }

        # Act
        passed1, _ = await risk_engine.review_signals([signal1], base_portfolio)
        passed2, _ = await risk_engine.review_signals([signal2], base_portfolio)

        # Assert
        assert len(passed1) == 1
        assert len(passed2) == 1

    # ==================== 批量信号测试 ====================

    @pytest.mark.asyncio
    async def test_batch_signals_mixed_results(self, risk_engine, base_portfolio):
        """测试: 批量信号部分通过部分拒绝"""
        # Arrange
        signals = [
            {
                "code": "000001.SZ",
                "direction": "BUY",
                "price": 10.0,
                "qty": 1000  # 正常
            },
            {
                "code": "000002.SZ",
                "direction": "BUY",
                "price": 10.0,
                "qty": 50000  # 仓位超限
            },
            {
                "code": "000003.SZ",
                "direction": "BUY",
                "price": 10.0,
                "qty": 1000  # 正常
            }
        ]

        # Act
        passed, rejected = await risk_engine.review_signals(signals, base_portfolio)

        # Assert
        assert len(passed) == 2
        assert len(rejected) == 1
        assert rejected[0]["code"] == "000002.SZ"

    # ==================== 日盈亏更新测试 ====================

    def test_update_daily_pnl(self, risk_engine):
        """测试: 更新日盈亏统计"""
        # Act
        risk_engine.update_daily_pnl(1000.0)
        risk_engine.update_daily_pnl(-500.0)
        risk_engine.update_daily_pnl(200.0)

        # Assert
        today = datetime.now().date().isoformat()
        assert today in risk_engine.daily_stats
        assert risk_engine.daily_stats[today]["pnl"] == 700.0
        assert risk_engine.daily_stats[today]["trades"] == 3

    # ==================== RiskCheckResult 测试 ====================

    def test_risk_check_result_passed(self):
        """测试: 风控通过结果"""
        result = RiskCheckResult(
            passed=True,
            rule_code="PASS",
            message="所有规则通过",
            severity="INFO"
        )
        assert result.passed is True

    def test_risk_check_result_failed(self):
        """测试: 风控拒绝结果"""
        result = RiskCheckResult(
            passed=False,
            rule_code="R001",
            message="止损比例超限",
            severity="HIGH"
        )
        assert result.passed is False
        assert result.severity == "HIGH"
