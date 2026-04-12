"""
实盘监控集成测试 (Live Monitoring Integration Tests)
"""

import asyncio
try:
    import pytest
except ImportError:
    pytest = None
from datetime import datetime
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.live_cabinet import LiveCabinet
from src.core.auto_trader import auto_trader, TradeMode
from src.core.signal_publisher import signal_publisher, SignalEvent
from src.strategy.base import Signal, SignalType


class MockWebSocket:
    """模拟WebSocket连接"""
    def __init__(self):
        self.messages = []

    async def send_json(self, data):
        self.messages.append(data)


class TestLiveMonitoring:
    """实盘监控测试"""

    (pytest.mark.asyncio if pytest else lambda x: x)
    async def test_trade_mode_switch(self):
        """测试交易模式切换"""
        print("\n[TEST] Trade Mode Switch...")

        # 初始模式
        assert auto_trader.get_mode() == TradeMode.MANUAL

        # 切换到自动模式
        auto_trader.set_mode(TradeMode.AUTO)
        assert auto_trader.get_mode() == TradeMode.AUTO

        # 切换到模拟模式
        auto_trader.set_mode(TradeMode.SIMULATE)
        assert auto_trader.get_mode() == TradeMode.SIMULATE

        # 切换到暂停模式
        auto_trader.set_mode(TradeMode.PAUSE)
        assert auto_trader.get_mode() == TradeMode.PAUSE

        # 恢复手动模式
        auto_trader.set_mode(TradeMode.MANUAL)
        print("   [OK] Mode switch passed")

    (pytest.mark.asyncio if pytest else lambda x: x)
    async def test_signal_publish(self):
        """测试信号发布"""
        print("\n[TEST] Signal Publish...")

        received_signals = []

        def on_signal(event):
            received_signals.append(event)

        # Subscribe to signals
        signal_publisher.subscribe(on_signal)

        # Create test signal
        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=100,
            confidence=0.85,
            reason="Test signal"
        )

        # Publish signal
        event = await signal_publisher.publish(
            signal=signal,
            strategy_id="test_strategy",
            strategy_name="Test Strategy"
        )

        assert event is not None
        assert event.symbol == "000001.SZ"
        assert event.signal_type == "buy"

        # Verify subscriber received signal
        await asyncio.sleep(0.1)
        assert len(received_signals) == 1

        # Unsubscribe
        signal_publisher.unsubscribe(on_signal)

        print(f"   Signal ID: {event.id}")
        print("   [OK] Signal publish passed")

    (pytest.mark.asyncio if pytest else lambda x: x)
    async def test_signal_deduplication(self):
        """Test signal deduplication"""
        print("\n[TEST] Signal Deduplication...")

        # Get current dedup count
        stats_before = signal_publisher.get_stats()
        dedup_before = stats_before["deduplicated_signals"]

        # Use new symbol to avoid conflict with previous tests
        signal = Signal(
            type=SignalType.BUY,
            symbol="000002.SZ",  # Use different symbol
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=100
        )

        # First publish
        event1 = await signal_publisher.publish(
            signal=signal,
            strategy_id="test_strategy"
        )
        assert event1 is not None

        # Duplicate publish (should be deduplicated)
        event2 = await signal_publisher.publish(
            signal=signal,
            strategy_id="test_strategy"
        )
        assert event2 is None  # Deduplicated

        stats = signal_publisher.get_stats()
        assert stats["deduplicated_signals"] == dedup_before + 1

        print("   [OK] Signal deduplication passed")

    (pytest.mark.asyncio if pytest else lambda x: x)
    async def test_manual_mode(self):
        """Test manual mode"""
        print("\n[TEST] Manual Mode...")

        # Set to manual mode and disable risk check (not needed in tests)
        auto_trader.set_mode(TradeMode.MANUAL)
        auto_trader.enable_risk_check = False

        # Create signal event (use unique ID to avoid conflict with previous tests)
        import time
        event = SignalEvent(
            id=f"test_signal_{int(time.time()*1000)}",
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            strategy_name="Test",
            symbol="000001.SZ",
            signal_type="buy",
            price=Decimal("10.50"),
            volume=100,
            confidence=0.8,
            reason="Test"
        )

        # Process signal
        result = await auto_trader.process_signal(event)

        # In manual mode, signal should be added to pending list (success=False means waiting for confirmation)
        assert not result.success

        # Check pending list
        pending = auto_trader.get_pending_signals()
        signal_id = event.id
        print(f"   Signal ID: {signal_id}")
        print(f"   Pending signals: {list(pending.keys())}")
        assert signal_id in pending, f"Signal {signal_id} not found in pending list: {list(pending.keys())}"

        # Ignore signal
        success = auto_trader.ignore_signal(signal_id)
        assert success

        pending = auto_trader.get_pending_signals()
        assert signal_id not in pending

        print("   [OK] Manual mode passed")

    (pytest.mark.asyncio if pytest else lambda x: x)
    async def test_simulate_mode(self):
        """Test simulate mode"""
        print("\n[TEST] Simulate Mode...")

        # Set to simulate mode and disable risk check (not needed in tests)
        auto_trader.set_mode(TradeMode.SIMULATE)
        auto_trader.enable_risk_check = False

        import time
        event = SignalEvent(
            id=f"test_signal_{int(time.time()*1000)}",
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            strategy_name="Test",
            symbol="000001.SZ",
            signal_type="buy",
            price=Decimal("10.50"),
            volume=100,
            confidence=0.8,
            reason="Test"
        )

        # Process signal
        result = await auto_trader.process_signal(event)

        # Simulate mode should succeed
        assert result.success
        assert result.simulated
        assert result.order_id.startswith("SIM_")

        # Check simulated trade records
        trades = auto_trader.get_simulated_trades()
        assert len(trades) >= 1

        print(f"   Simulated order: {result.order_id}")
        print("   [OK] Simulate mode passed")

    (pytest.mark.asyncio if pytest else lambda x: x)
    async def test_pause_mode(self):
        """Test pause mode"""
        print("\n[TEST] Pause Mode...")

        # Set to pause mode (pause mode rejects directly without risk check)
        auto_trader.set_mode(TradeMode.PAUSE)

        import time
        event = SignalEvent(
            id=f"test_signal_{int(time.time()*1000)}",
            timestamp=datetime.now(),
            strategy_id="test_strategy",
            strategy_name="Test",
            symbol="000001.SZ",
            signal_type="buy",
            price=Decimal("10.50"),
            volume=100,
            confidence=0.8,
            reason="Test"
        )

        # Process signal
        result = await auto_trader.process_signal(event)

        # Pause mode should reject (success=False means trade rejected)
        assert not result.success

        print("   [OK] Pause mode passed")

    def test_signal_history(self):
        """Test signal history query"""
        print("\n[TEST] Signal History Query...")

        # Query history
        history = signal_publisher.get_signal_history(limit=10)

        # Verify return is list
        assert isinstance(history, list)

        print(f"   History records: {len(history)}")
        print("   [OK] Signal history query passed")

    def test_signal_stats(self):
        """Test signal statistics"""
        print("\n[TEST] Signal Statistics...")

        stats = signal_publisher.get_stats()

        assert "total_signals" in stats
        assert "published_signals" in stats
        assert "deduplicated_signals" in stats

        print(f"   Total signals: {stats['total_signals']}")
        print(f"   Published: {stats['published_signals']}")
        print(f"   Deduplicated: {stats['deduplicated_signals']}")
        print("   [OK] Signal statistics passed")


async def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Live Monitoring Integration Tests")
    print("=" * 60)

    tests = TestLiveMonitoring()

    await tests.test_trade_mode_switch()
    await tests.test_signal_publish()
    await tests.test_signal_deduplication()
    await tests.test_manual_mode()
    await tests.test_simulate_mode()
    await tests.test_pause_mode()
    tests.test_signal_history()
    tests.test_signal_stats()

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
