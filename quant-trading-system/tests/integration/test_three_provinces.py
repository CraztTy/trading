"""
三省协同集成测试

测试中书省 → 门下省 → 尚书省的完整流程
"""
import pytest
import pandas as pd
from datetime import datetime
from decimal import Decimal

from src.core.zhongshu_sheng import ZhongshuSheng
from src.core.menxia_sheng import MenxiaSheng
from src.core.shangshu_sheng import ShangshuSheng


@pytest.mark.integration
class TestThreeProvincesWorkflow:
    """三省协同工作流测试"""

    @pytest.fixture
    def three_provinces(self, risk_config, clearing_config):
        """创建三省实例"""
        zhongshu = ZhongshuSheng({})
        menxia = MenxiaSheng(risk_config)
        shangshu = ShangshuSheng(clearing_config)
        return zhongshu, menxia, shangshu

    @pytest.fixture
    def sample_strategy(self):
        """样本策略"""
        class TestStrategy:
            def on_bar(self, klines, context):
                # 简单的均线策略
                if len(klines) < 5:
                    return None

                ma5 = klines['close'].rolling(window=5).mean().iloc[-1]
                current = klines['close'].iloc[-1]

                if current > ma5:
                    return {
                        "direction": "BUY",
                        "price": float(current),
                        "qty": 1000,
                        "stop_loss": float(current) * 0.95
                    }
                elif current < ma5:
                    return {
                        "direction": "SELL",
                        "price": float(current),
                        "qty": 1000
                    }
                return None

        return TestStrategy()

    @pytest.fixture
    def sample_klines(self):
        """样本K线数据"""
        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        return pd.DataFrame({
            "open": [10.0, 10.2, 10.1, 10.5, 10.6, 10.8, 11.0, 10.9, 11.2, 11.5],
            "high": [10.3, 10.4, 10.5, 10.8, 11.0, 11.2, 11.3, 11.1, 11.5, 11.8],
            "low": [9.9, 10.0, 10.0, 10.3, 10.5, 10.6, 10.8, 10.7, 10.9, 11.2],
            "close": [10.2, 10.1, 10.5, 10.6, 10.8, 11.0, 10.9, 11.2, 11.5, 11.8],
            "volume": [10000] * 10
        }, index=dates)

    @pytest.mark.asyncio
    async def test_full_workflow_success(self, three_provinces, sample_strategy, sample_klines):
        """测试: 完整流程 - 生成信号 -> 风控通过 -> 执行成交"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces
        zhongshu.register_strategy("test_strategy", sample_strategy)

        portfolio = shangshu.get_portfolio_state()

        market_data = {
            "000001.SZ": {"close": 11.8}
        }

        # Act - Step 1: 中书省生成信号
        signals = await zhongshu.generate_signals(sample_klines, "000001.SZ")
        assert len(signals) > 0

        # Act - Step 2: 门下省风控审核
        passed, rejected = await menxia.review_signals(signals, portfolio)

        # Assert - 风控通过
        assert len(passed) > 0
        assert len(rejected) == 0

        # Act - Step 3: 尚书省执行
        executed = await shangshu.execute_orders(passed, market_data)

        # Assert - 执行成功
        assert len(executed) > 0
        assert shangshu.cash < 1000000  # 资金减少
        assert "000001.SZ" in shangshu.positions  # 有持仓

    @pytest.mark.asyncio
    async def test_workflow_risk_rejected(self, three_provinces, sample_strategy, sample_klines):
        """测试: 风控拦截流程"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces
        zhongshu.register_strategy("test_strategy", sample_strategy)

        # 设置一个导致风控拒绝的信号（大仓位）
        large_signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 100.0,
            "qty": 50000,  # 500万，超过单票限制
            "strategy_id": "manual"
        }

        portfolio = shangshu.get_portfolio_state()

        # Act
        passed, rejected = await menxia.review_signals([large_signal], portfolio)

        # Assert - 被风控拒绝
        assert len(passed) == 0
        assert len(rejected) == 1
        assert "仓位" in rejected[0]["reject_reason"]

        # 不应执行
        executed = await shangshu.execute_orders(passed, {})
        assert len(executed) == 0

    @pytest.mark.asyncio
    async def test_workflow_insufficient_cash(self, three_provinces):
        """测试: 资金不足拒绝"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces

        # 模拟资金不足
        shangshu.cash = 1000  # 只有1000元

        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000  # 需要1万+，超过可用资金
        }

        market_data = {"000001.SZ": {"close": 10.0}}

        # Act
        executed = await shangshu.execute_orders([signal], market_data)

        # Assert
        assert len(executed) == 0
        assert shangshu.cash == 1000  # 资金未变

    @pytest.mark.asyncio
    async def test_workflow_insufficient_position(self, three_provinces):
        """测试: 持仓不足拒绝卖出"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces

        signal = {
            "code": "000001.SZ",
            "direction": "SELL",
            "price": 10.0,
            "qty": 1000  # 没有持仓
        }

        market_data = {"000001.SZ": {"close": 10.0}}

        # Act
        executed = await shangshu.execute_orders([signal], market_data)

        # Assert
        assert len(executed) == 0

    @pytest.mark.asyncio
    async def test_batch_signals_processing(self, three_provinces, sample_klines):
        """测试: 批量信号处理"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces

        # 创建多个策略
        class BuyStrategy:
            def on_bar(self, klines, context):
                return {"direction": "BUY", "price": 10.0, "qty": 1000}

        class SellStrategy:
            def on_bar(self, klines, context):
                return {"direction": "SELL", "price": 10.0, "qty": 500}

        zhongshu.register_strategy("buy_strat", BuyStrategy())
        zhongshu.register_strategy("sell_strat", SellStrategy())

        # 先买入一些持仓
        shangshu.positions["000001.SZ"] = {
            "qty": 2000,
            "cost": 10.0,
            "frozen": 0
        }

        portfolio = shangshu.get_portfolio_state()

        # Act
        signals = await zhongshu.generate_signals(sample_klines, "000001.SZ")
        assert len(signals) == 2

        passed, rejected = await menxia.review_signals(signals, portfolio)
        # 都应该是合法信号

        # Assert
        assert len(passed) + len(rejected) == 2

    @pytest.mark.asyncio
    async def test_strategy_context_update(self, three_provinces, sample_klines):
        """测试: 策略上下文更新和传递"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces

        context_updates = []

        class ContextTrackingStrategy:
            def on_bar(self, klines, context):
                context_updates.append(context.copy())
                # 更新上下文
                return {"direction": "BUY", "price": 10.0, "qty": 100}

        zhongshu.register_strategy("context_strat", ContextTrackingStrategy())

        # 设置初始上下文
        zhongshu.update_strategy_context("context_strat", "000001.SZ", {"position": 0, "trades": 0})

        # Act - 多次调用，验证上下文传递
        await zhongshu.generate_signals(sample_klines, "000001.SZ")
        await zhongshu.generate_signals(sample_klines, "000001.SZ")

        # Assert
        assert len(context_updates) == 2
        assert "position" in context_updates[0]
        assert "trades" in context_updates[0]

    @pytest.mark.asyncio
    async def test_stop_loss_triggered(self, three_provinces):
        """测试: 止损触发"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces

        # 设置持仓和止损
        shangshu.positions["000001.SZ"] = {
            "qty": 1000,
            "cost": 10.0,
            "frozen": 0,
            "stop_loss": 9.50  # 止损价
        }

        # 市场价格跌破止损
        market_data = {
            "000001.SZ": {"close": 9.40}
        }

        # Act
        stop_signals = await shangshu.check_stops(market_data)

        # Assert
        assert len(stop_signals) == 1
        assert stop_signals[0]["code"] == "000001.SZ"
        assert stop_signals[0]["direction"] == "SELL"
        assert stop_signals[0]["reason"] == "STOP_LOSS"

    @pytest.mark.asyncio
    async def test_take_profit_triggered(self, three_provinces):
        """测试: 止盈触发"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces

        # 设置持仓和止盈
        shangshu.positions["000001.SZ"] = {
            "qty": 1000,
            "cost": 10.0,
            "frozen": 0,
            "take_profit": 12.00
        }

        # 市场价格超过止盈
        market_data = {
            "000001.SZ": {"close": 12.50}
        }

        # Act
        stop_signals = await shangshu.check_stops(market_data)

        # Assert
        assert len(stop_signals) == 1
        assert stop_signals[0]["reason"] == "TAKE_PROFIT"

    @pytest.mark.asyncio
    async def test_trading_fees_calculation(self, three_provinces):
        """测试: 交易费用计算"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces

        signal = {
            "code": "000001.SZ",
            "direction": "BUY",
            "price": 10.0,
            "qty": 1000
        }

        market_data = {"000001.SZ": {"close": 10.0}}

        initial_cash = shangshu.cash

        # Act
        executed = await shangshu.execute_orders([signal], market_data)

        # Assert
        assert len(executed) == 1
        result = executed[0]

        # 验证费用
        assert result["commission"] >= 5.0  # 最低佣金
        assert result["stamp_tax"] == 0  # 买入无印花税
        assert result["total_cost"] > 0

        # 验证资金变化 = 成交金额 + 总费用
        expected_deduction = 10000 + result["total_cost"]
        actual_deduction = initial_cash - result["cash_after"]
        assert abs(actual_deduction - expected_deduction) < 0.01

    @pytest.mark.asyncio
    async def test_sell_stamp_tax(self, three_provinces):
        """测试: 卖出印花税"""
        # Arrange
        zhongshu, menxia, shangshu = three_provinces

        # 设置持仓
        shangshu.positions["000001.SZ"] = {
            "qty": 1000,
            "cost": 10.0,
            "frozen": 0
        }

        signal = {
            "code": "000001.SZ",
            "direction": "SELL",
            "price": 11.0,
            "qty": 1000
        }

        market_data = {"000001.SZ": {"close": 11.0}}

        # Act
        executed = await shangshu.execute_orders([signal], market_data)

        # Assert
        assert len(executed) == 1
        # 卖出有印花税 0.1%
        expected_tax = 11000 * 0.001  # 11元
        assert abs(executed[0]["stamp_tax"] - expected_tax) < 0.01
