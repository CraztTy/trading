"""
Day 7 联调测试 - 完整交易链路测试

测试场景：
1. 正常下单 → 成交 → 持仓更新
2. 信号生成 → 风控通过 → 自动下单
3. 风控拦截 → 订单拒绝
4. 资金不足 → 下单失败
"""

import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.core.crown_prince import CrownPrince, crown_prince, DataType
from src.core.zhongshu_sheng import ZhongshuSheng, zhongshu_sheng, SignalEvent, SignalStatus
from src.core.menxia_sheng import MenxiaSheng, menxia_sheng, AuditResult, RiskLevel
from src.core.shangshu_sheng import ShangshuSheng, shangshu_sheng, OrderPriority
from src.strategy.base import (
    StrategyBase, StrategyContext, Signal, SignalType,
    TickData, BarData
)
from src.market_data.models import TickData as MDTickData
from src.models.order import Order
from src.models.trade import Trade
from src.models.position import Position
from src.models.enums import OrderDirection, OrderType, OrderStatus


# ============== 测试用简单策略 ==============

class SimpleMAStrategy(StrategyBase):
    """简单的均线策略，用于测试"""

    def __init__(self, strategy_id: str, name: str, symbols: list, params: dict = None):
        super().__init__(strategy_id, name, symbols, params)
        self.prices = []
        self.signal_count = 0

    def on_init(self, context: StrategyContext):
        """初始化"""
        print(f"[{self.strategy_id}] 策略初始化完成")

    def on_bar(self, bar: BarData):
        """K线触发"""
        self.prices.append(bar.close)

        # 简单逻辑：价格高于前一根K线就买入
        if len(self.prices) >= 2:
            if self.prices[-1] > self.prices[-2]:
                signal = Signal(
                    type=SignalType.BUY,
                    symbol=bar.symbol,
                    timestamp=bar.timestamp,
                    price=bar.close,
                    volume=100,
                    confidence=0.7,
                    reason="价格突破"
                )
                self.emit_signal(signal)
                return signal
        return None

    def on_tick(self, tick: TickData):
        """Tick触发"""
        pass

    async def on_bar_async(self, bar: BarData) -> Optional[Signal]:
        """异步K线处理"""
        self._bar_count += 1
        signal = self.on_bar(bar)
        return signal


# ============== 测试辅助函数 ==============

def reset_singletons():
    """重置所有单例状态"""
    # 重置太子院
    crown_prince.reset_stats()
    crown_prince.banned_stocks.clear()

    # 重置中书省
    zhongshu_sheng._stats = {
        "signals_generated": 0,
        "signals_deduplicated": 0,
        "strategies_active": 0,
    }
    zhongshu_sheng.signal_cache.clear()
    zhongshu_sheng._account_strategies.clear()
    zhongshu_sheng.strategy_loader._instances.clear()

    # 重置门下省
    menxia_sheng._stats = {
        "total_audits": 0,
        "approved": 0,
        "rejected": 0,
        "circuit_breaker_count": 0,
    }
    menxia_sheng._audit_log.clear()
    if menxia_sheng.is_circuit_breaker_active():
        menxia_sheng.reset_circuit_breaker()

    # 重置尚书省
    shangshu_sheng._stats = {
        "orders_submitted": 0,
        "orders_executed": 0,
        "orders_rejected": 0,
        "trades_completed": 0,
    }


def create_sample_tick():
    """创建样本Tick数据"""
    return MDTickData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        price=Decimal("10.50"),
        volume=1000,
        bid_price=Decimal("10.48"),
        ask_price=Decimal("10.52"),
        bid_volume=500,
        ask_volume=600
    )


def create_sample_bar(close_price: Decimal = Decimal("10.50")):
    """创建样本K线数据"""
    return BarData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        open=Decimal("10.30"),
        high=Decimal("10.60"),
        low=Decimal("10.20"),
        close=close_price,
        volume=10000,
        amount=Decimal("105000"),
        period="1d"
    )


def create_sample_signal():
    """创建样本交易信号"""
    return Signal(
        type=SignalType.BUY,
        symbol="000001.SZ",
        timestamp=datetime.now(),
        price=Decimal("10.50"),
        volume=100,
        confidence=0.8,
        reason="测试信号"
    )


# ============== 测试用例 ==============

async def test_tick_validation():
    """测试Tick数据校验"""
    print("\n[测试] Tick数据校验...")

    tick = create_sample_tick()
    result = crown_prince.process_tick(tick)

    assert result.is_valid is True, f"期望校验通过，但失败: {result.errors}"
    assert result.normalized_symbol == "000001.SZ"
    print("   ✓ Tick数据校验通过")


async def test_symbol_normalization():
    """测试代码标准化"""
    print("\n[测试] 代码标准化...")

    test_cases = [
        ("000001.SZ", "000001.SZ"),
        ("000001.sz", "000001.SZ"),
        ("sz000001", "000001.SZ"),
        ("000001", "000001.SZ"),
        ("600000.SH", "600000.SH"),
        ("sh600000", "600000.SH"),
    ]

    for input_symbol, expected in test_cases:
        result = crown_prince.normalizer.normalize(input_symbol)
        assert result == expected, f"标准化失败: {input_symbol} -> {result}, 期望 {expected}"
        print(f"   ✓ {input_symbol} -> {result}")


async def test_banned_stock():
    """测试禁售股票"""
    print("\n[测试] 禁售股票拦截...")

    crown_prince.add_banned_stock("000001.SZ", "测试禁售")

    tick = create_sample_tick()
    result = crown_prince.process_tick(tick)

    assert result.is_valid is False, "期望校验失败"
    assert "禁售" in result.errors[0], f"期望禁售错误，但得到: {result.errors}"
    print("   ✓ 禁售股票被正确拦截")

    crown_prince.remove_banned_stock("000001.SZ")


async def test_strategy_registration():
    """测试策略注册和激活"""
    print("\n[测试] 策略注册和激活...")

    zhongshu_sheng.register_strategy_class("simple_ma", SimpleMAStrategy)

    registered = zhongshu_sheng.strategy_loader.list_registered()
    assert "simple_ma" in registered, "策略注册失败"
    print("   ✓ 策略类注册成功")

    success = zhongshu_sheng.activate_strategy(
        account_id=1,
        strategy_id="test_strategy_1",
        name="测试策略",
        symbols=["000001.SZ"],
        params={"period": 20}
    )

    assert success is True, "策略激活失败"
    assert "test_strategy_1" in zhongshu_sheng.strategy_loader.list_active()
    print("   ✓ 策略激活成功")


async def test_signal_generation():
    """测试信号生成"""
    print("\n[测试] 信号生成...")

    reset_singletons()
    zhongshu_sheng.register_strategy_class("simple_ma", SimpleMAStrategy)
    zhongshu_sheng.activate_strategy(
        account_id=1,
        strategy_id="test_strategy_1",
        name="测试策略",
        symbols=["000001.SZ"]
    )

    # 添加第一根K线
    bar1 = BarData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        open=Decimal("10.00"),
        high=Decimal("10.20"),
        low=Decimal("9.90"),
        close=Decimal("10.10"),
        volume=10000,
        amount=Decimal("101000"),
        period="1d"
    )

    # 添加第二根K线（价格上涨）
    bar2 = BarData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        open=Decimal("10.20"),
        high=Decimal("10.60"),
        low=Decimal("10.10"),
        close=Decimal("10.50"),  # 价格高于10.10
        volume=15000,
        amount=Decimal("157500"),
        period="1d"
    )

    await zhongshu_sheng._process_kline_strategy(
        zhongshu_sheng.strategy_loader.get_instance("test_strategy_1"),
        bar1
    )

    await zhongshu_sheng._process_kline_strategy(
        zhongshu_sheng.strategy_loader.get_instance("test_strategy_1"),
        bar2
    )

    assert zhongshu_sheng._stats["signals_generated"] > 0, "信号生成失败"
    print(f"   ✓ 信号生成成功 ({zhongshu_sheng._stats['signals_generated']}个)")


async def test_signal_deduplication():
    """测试信号去重"""
    print("\n[测试] 信号去重...")

    signal = create_sample_signal()
    event1 = SignalEvent(signal=signal, strategy_id="test_strategy")
    event2 = SignalEvent(signal=signal, strategy_id="test_strategy")

    # 第一次添加应该成功
    assert zhongshu_sheng.signal_cache.add(event1) is True, "首次添加应该成功"
    # 重复添加应该失败
    assert zhongshu_sheng.signal_cache.add(event2) is False, "重复添加应该失败"

    print("   ✓ 信号去重正常工作")


async def test_risk_audit_pass():
    """测试风控审核通过"""
    print("\n[测试] 风控审核通过...")

    signal = create_sample_signal()
    context = {
        "positions": {},
        "total_value": Decimal("100000"),
        "stop_loss": Decimal("10.00")
    }

    result = await menxia_sheng.audit_signal(signal, context)

    assert result.approved is True, f"期望审核通过，但被拒绝: {result.reject_reason}"
    assert len(result.checks) > 0, "应该有检查记录"
    print(f"   ✓ 风控审核通过 ({len(result.checks)}项检查)")


async def test_risk_position_limit_rejection():
    """测试仓位限制拒绝"""
    print("\n[测试] 仓位限制拒绝...")

    signal = create_sample_signal()
    # 模拟已经有大仓位
    context = {
        "positions": {
            "000001.SZ": {"market_value": Decimal("50000")}
        },
        "total_value": Decimal("100000"),
        "stop_loss": Decimal("10.00")
    }

    result = await menxia_sheng.audit_signal(signal, context)

    assert result.approved is False, "期望审核被拒绝"
    assert "仓位" in result.reject_reason, f"期望仓位限制错误，但得到: {result.reject_reason}"
    print(f"   ✓ 仓位限制正确触发: {result.reject_reason}")


async def test_risk_stop_loss_required():
    """测试止损设置检查"""
    print("\n[测试] 止损设置检查...")

    signal = create_sample_signal()
    context = {
        "positions": {},
        "total_value": Decimal("100000"),
        # 不设置止损
    }

    result = await menxia_sheng.audit_signal(signal, context)

    assert result.approved is False, "期望审核被拒绝"
    assert "止损" in result.reject_reason, f"期望止损错误，但得到: {result.reject_reason}"
    print(f"   ✓ 止损检查正确触发: {result.reject_reason}")


async def test_capital_freeze():
    """测试资金冻结"""
    print("\n[测试] 资金冻结...")

    frozen = await shangshu_sheng.capital_manager.freeze_for_order(
        account_id=1,
        order_id="TEST001",
        amount=Decimal("10000")
    )

    assert frozen is True, "资金冻结失败"
    assert shangshu_sheng.capital_manager.get_frozen_amount(1) == Decimal("10000")
    print("   ✓ 资金冻结成功")


async def test_position_update_buy():
    """测试买入持仓更新"""
    print("\n[测试] 买入持仓更新...")

    trade = Trade(
        trade_id="T001",
        order_id=1,
        account_id=1,
        symbol="000001.SZ",
        direction=OrderDirection.BUY,
        qty=100,
        price=Decimal("10.50"),
        trade_time=datetime.now()
    )

    position = await shangshu_sheng.position_manager.update_position(trade)

    assert position is not None, "持仓更新失败"
    assert position.total_qty == 100, f"期望持仓100，但得到{position.total_qty}"
    assert position.symbol == "000001.SZ"
    print(f"   ✓ 持仓更新成功: {position.total_qty}股 @ {position.cost_price}")


async def test_position_update_sell():
    """测试卖出持仓更新"""
    print("\n[测试] 卖出持仓更新...")

    # 先买入
    buy_trade = Trade(
        trade_id="T001",
        order_id=1,
        account_id=1,
        symbol="000001.SZ",
        direction=OrderDirection.BUY,
        qty=100,
        price=Decimal("10.50"),
        trade_time=datetime.now()
    )
    await shangshu_sheng.position_manager.update_position(buy_trade)

    # 再卖出
    sell_trade = Trade(
        trade_id="T002",
        order_id=2,
        account_id=1,
        symbol="000001.SZ",
        direction=OrderDirection.SELL,
        qty=100,
        price=Decimal("11.00"),
        trade_time=datetime.now()
    )
    position = await shangshu_sheng.position_manager.update_position(sell_trade)

    # 持仓应该被清空
    assert position is None or position.total_qty == 0, "期望持仓被清空"
    print("   ✓ 卖出后持仓清空成功")


async def test_full_flow_signal_to_execution():
    """测试完整链路：信号生成 → 风控 → 执行"""
    print("\n" + "=" * 50)
    print("[完整链路测试] 信号生成 → 风控 → 执行")
    print("=" * 50)

    reset_singletons()

    # 1. 注册并激活策略
    print("\n1. 注册策略...")
    zhongshu_sheng.register_strategy_class("simple_ma", SimpleMAStrategy)
    zhongshu_sheng.activate_strategy(
        account_id=1,
        strategy_id="test_strategy_1",
        name="测试均线策略",
        symbols=["000001.SZ"]
    )

    # 2. 设置风控回调
    print("2. 设置风控回调...")
    async def risk_handler(signal, audit_result):
        """风控通过后发送到尚书省"""
        if audit_result.approved:
            print(f"   → 风控通过，发送到尚书省: {signal.symbol}")
            await shangshu_sheng.submit_signal(signal, account_id=1)
        else:
            print(f"   → 风控拒绝: {audit_result.reject_reason}")

    menxia_sheng.on_approval(risk_handler)

    # 3. 设置信号处理器链
    print("3. 设置信号处理器链...")
    async def signal_handler(event: SignalEvent):
        """信号处理器：发送到门下省风控"""
        print(f"   → 信号处理器收到: {event.signal_id[:8]}...")
        context = {
            "positions": {},
            "total_value": Decimal("100000"),
            "stop_loss": Decimal("10.00")
        }
        await menxia_sheng.audit_signal(event.signal, context)

    zhongshu_sheng.add_signal_handler(signal_handler)

    # 4. 启动尚书省
    print("4. 启动尚书省...")
    await shangshu_sheng.start()

    # 5. 模拟K线数据驱动策略
    print("5. 模拟K线数据...")
    bar1 = BarData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        open=Decimal("10.00"),
        high=Decimal("10.20"),
        low=Decimal("9.90"),
        close=Decimal("10.10"),
        volume=10000,
        amount=Decimal("101000"),
        period="1d"
    )

    bar2 = BarData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        open=Decimal("10.20"),
        high=Decimal("10.60"),
        low=Decimal("10.10"),
        close=Decimal("10.50"),  # 价格上涨
        volume=15000,
        amount=Decimal("157500"),
        period="1d"
    )

    # 先处理第一根K线
    await zhongshu_sheng._process_kline_strategy(
        zhongshu_sheng.strategy_loader.get_instance("test_strategy_1"),
        bar1
    )

    # 再处理第二根K线（应该生成信号）
    await zhongshu_sheng._process_kline_strategy(
        zhongshu_sheng.strategy_loader.get_instance("test_strategy_1"),
        bar2
    )

    # 等待订单处理
    await asyncio.sleep(0.5)

    # 6. 验证结果
    print("\n6. 验证结果...")
    print(f"   中书省信号生成: {zhongshu_sheng._stats['signals_generated']}")
    print(f"   门下省审核通过: {menxia_sheng._stats['approved']}")
    print(f"   门下省审核拒绝: {menxia_sheng._stats['rejected']}")
    print(f"   尚书省订单提交: {shangshu_sheng._stats['orders_submitted']}")

    # 停止尚书省
    await shangshu_sheng.stop()

    # 验证
    assert zhongshu_sheng._stats["signals_generated"] > 0, "信号生成失败"
    assert menxia_sheng._stats["total_audits"] > 0, "风控审核未执行"
    assert shangshu_sheng._stats["orders_submitted"] > 0, "订单未提交"

    print("\n   ✓ 完整链路测试通过!")


async def test_risk_rejection_flow():
    """测试风控拦截链路"""
    print("\n" + "=" * 50)
    print("[风控拦截测试] 信号 → 风控拒绝")
    print("=" * 50)

    reset_singletons()

    # 1. 注册策略
    print("\n1. 注册策略...")
    zhongshu_sheng.register_strategy_class("simple_ma", SimpleMAStrategy)
    zhongshu_sheng.activate_strategy(
        account_id=1,
        strategy_id="test_strategy_1",
        name="测试策略",
        symbols=["000001.SZ"]
    )

    # 2. 设置风控回调
    async def risk_handler(signal, audit_result):
        if audit_result.approved:
            await shangshu_sheng.submit_signal(signal, account_id=1)
        else:
            print(f"   → 风控拦截: {audit_result.reject_reason}")

    menxia_sheng.on_approval(risk_handler)

    # 3. 设置信号处理器（带大仓位的上下文）
    async def signal_handler(event: SignalEvent):
        context = {
            "positions": {
                "000001.SZ": {"market_value": Decimal("50000")}  # 已有大仓位
            },
            "total_value": Decimal("100000"),
            "stop_loss": Decimal("10.00")
        }
        await menxia_sheng.audit_signal(event.signal, context)

    zhongshu_sheng.add_signal_handler(signal_handler)

    # 4. 触发信号
    print("2. 触发信号...")
    bar1 = BarData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        open=Decimal("10.00"),
        high=Decimal("10.20"),
        low=Decimal("9.90"),
        close=Decimal("10.10"),
        volume=10000,
        amount=Decimal("101000"),
        period="1d"
    )

    bar2 = BarData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        open=Decimal("10.20"),
        high=Decimal("10.60"),
        low=Decimal("10.10"),
        close=Decimal("10.50"),
        volume=15000,
        amount=Decimal("157500"),
        period="1d"
    )

    await zhongshu_sheng._process_kline_strategy(
        zhongshu_sheng.strategy_loader.get_instance("test_strategy_1"),
        bar1
    )

    await zhongshu_sheng._process_kline_strategy(
        zhongshu_sheng.strategy_loader.get_instance("test_strategy_1"),
        bar2
    )

    await asyncio.sleep(0.2)

    # 验证
    print("\n3. 验证结果...")
    print(f"   信号生成: {zhongshu_sheng._stats['signals_generated']}")
    print(f"   风控拒绝: {menxia_sheng._stats['rejected']}")
    print(f"   订单提交: {shangshu_sheng._stats['orders_submitted']}")

    assert zhongshu_sheng._stats["signals_generated"] > 0, "信号生成失败"
    assert menxia_sheng._stats["rejected"] > 0, "风控未拒绝"
    assert shangshu_sheng._stats["orders_submitted"] == 0, "订单应该被拒绝"

    print("\n   ✓ 风控拦截测试通过!")


async def run_all_tests():
    """运行所有测试"""
    tests = [
        ("Tick数据校验", test_tick_validation),
        ("代码标准化", test_symbol_normalization),
        ("禁售股票拦截", test_banned_stock),
        ("策略注册激活", test_strategy_registration),
        ("信号生成", test_signal_generation),
        ("信号去重", test_signal_deduplication),
        ("风控审核通过", test_risk_audit_pass),
        ("仓位限制拒绝", test_risk_position_limit_rejection),
        ("止损设置检查", test_risk_stop_loss_required),
        ("资金冻结", test_capital_freeze),
        ("买入持仓更新", test_position_update_buy),
        ("卖出持仓更新", test_position_update_sell),
        ("完整链路测试", test_full_flow_signal_to_execution),
        ("风控拦截测试", test_risk_rejection_flow),
    ]

    passed = 0
    failed = 0
    errors = []

    for name, test_func in tests:
        try:
            reset_singletons()
            await test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append(f"[失败] {name}: {e}")
            print(f"   ✗ 失败: {e}")
        except Exception as e:
            failed += 1
            errors.append(f"[错误] {name}: {e}")
            print(f"   ✗ 错误: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"总计: {len(tests)}")
    print(f"通过: {passed}")
    print(f"失败: {failed}")

    if errors:
        print("\n错误详情:")
        for error in errors:
            print(f"  {error}")

    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("Day 7 联调测试 - 完整交易链路")
    print("=" * 60)

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
