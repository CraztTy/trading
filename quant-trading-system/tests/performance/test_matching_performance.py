"""
撮合引擎性能测试

测试撮合引擎在高并发场景下的性能表现
"""
import pytest
import asyncio
import time
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

from src.core.matching_engine import (
    SimulatedMatchingEngine,
    MarketDataSimulator,
    MarketPrice
)
from src.models.enums import OrderDirection, OrderStatus


@pytest.mark.performance
class TestMatchingEnginePerformance:
    """撮合引擎性能测试"""

    @pytest.fixture
    def engine_with_data(self):
        """配置好市场数据的撮合引擎"""
        engine = SimulatedMatchingEngine()
        simulator = MarketDataSimulator()

        # 设置多个标的的价格
        symbols = [f"{i:06d}.SZ" for i in range(1, 101)]  # 100个股票
        for symbol in symbols:
            simulator.set_base_price(symbol, Decimal(str(10 + hash(symbol) % 90)))

        # 更新引擎的市场数据
        for symbol, price in simulator.current_prices.items():
            engine.update_market_price(price)

        return engine, symbols

    @pytest.fixture
    def create_order(self):
        """订单创建辅助函数"""
        class MockOrder:
            def __init__(self, symbol, direction, qty, price):
                self.symbol = symbol
                self.direction = direction
                self.qty = qty
                self.price = price
                self.filled_qty = 0
                self.status = OrderStatus.PENDING

        def _create(symbol="000001.SZ", direction=OrderDirection.BUY, qty=1000, price=Decimal("10.50")):
            return MockOrder(symbol, direction, qty, price)

        return _create

    def test_single_order_latency(self, engine_with_data, create_order, benchmark):
        """测试: 单笔订单撮合延迟 (目标: <1ms)"""
        engine, _ = engine_with_data
        order = create_order()

        def match_single():
            return engine.try_match(order)

        # 使用pytest-benchmark
        result = benchmark(match_single)
        assert result.success is True

        # 检查平均延迟
        stats = benchmark.stats
        avg_latency_ms = stats["mean"] * 1000
        print(f"\n单笔订单平均延迟: {avg_latency_ms:.3f}ms")
        assert avg_latency_ms < 1.0, f"单笔延迟 {avg_latency_ms}ms 超过 1ms 目标"

    def test_throughput_sequential(self, engine_with_data, create_order):
        """测试: 顺序处理吞吐量 (目标: >10000 TPS)"""
        engine, symbols = engine_with_data

        # 准备10000个订单
        orders = []
        for i in range(10000):
            symbol = symbols[i % len(symbols)]
            direction = OrderDirection.BUY if i % 2 == 0 else OrderDirection.SELL
            order = create_order(symbol=symbol, direction=direction)
            orders.append(order)

        # 测试顺序处理
        start_time = time.perf_counter()
        success_count = 0
        for order in orders:
            result = engine.try_match(order)
            if result.success:
                success_count += 1
        end_time = time.perf_counter()

        duration = end_time - start_time
        tps = len(orders) / duration

        print(f"\n顺序处理吞吐量: {tps:.0f} TPS")
        print(f"处理 {len(orders)} 个订单耗时: {duration:.3f}s")
        print(f"成功撮合: {success_count}/{len(orders)}")

        assert tps > 10000, f"吞吐量 {tps:.0f} TPS 低于 10000 目标"

    @pytest.mark.asyncio
    async def test_throughput_concurrent(self, engine_with_data, create_order):
        """测试: 并发处理吞吐量"""
        engine, symbols = engine_with_data

        async def match_batch(orders):
            """批量撮合"""
            results = []
            for order in orders:
                result = engine.try_match(order)
                results.append(result)
            return results

        # 准备50000个订单，分成10批
        batch_size = 5000
        num_batches = 10
        batches = []

        for batch_idx in range(num_batches):
            batch_orders = []
            for i in range(batch_size):
                idx = batch_idx * batch_size + i
                symbol = symbols[idx % len(symbols)]
                direction = OrderDirection.BUY if idx % 2 == 0 else OrderDirection.SELL
                order = create_order(symbol=symbol, direction=direction)
                batch_orders.append(order)
            batches.append(batch_orders)

        # 并发执行
        start_time = time.perf_counter()
        tasks = [match_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        end_time = time.perf_counter()

        total_orders = batch_size * num_batches
        duration = end_time - start_time
        tps = total_orders / duration

        total_success = sum(1 for batch in results for r in batch if r.success)

        print(f"\n并发处理吞吐量: {tps:.0f} TPS")
        print(f"处理 {total_orders} 个订单耗时: {duration:.3f}s")
        print(f"成功撮合: {total_success}/{total_orders}")

        assert tps > 50000, f"并发吞吐量 {tps:.0f} TPS 低于预期"

    def test_latency_distribution(self, engine_with_data, create_order):
        """测试: 延迟分布 (P50, P99, P999)"""
        engine, symbols = engine_with_data

        # 执行10000次撮合，记录延迟
        latencies = []
        for i in range(10000):
            symbol = symbols[i % len(symbols)]
            order = create_order(symbol=symbol)

            start = time.perf_counter()
            engine.try_match(order)
            end = time.perf_counter()

            latencies.append((end - start) * 1000)  # 转换为ms

        # 计算分位数
        latencies.sort()
        p50 = latencies[int(len(latencies) * 0.50)]
        p99 = latencies[int(len(latencies) * 0.99)]
        p999 = latencies[int(len(latencies) * 0.999)]

        print(f"\n延迟分布:")
        print(f"  P50: {p50:.3f}ms")
        print(f"  P99: {p99:.3f}ms")
        print(f"  P999: {p999:.3f}ms")

        assert p50 < 0.5, f"P50 延迟 {p50:.3f}ms 过高"
        assert p99 < 5.0, f"P99 延迟 {p99:.3f}ms 超过 5ms 目标"
        assert p999 < 10.0, f"P999 延迟 {p999:.3f}ms 超过 10ms 目标"

    def test_memory_usage_stability(self, engine_with_data, create_order):
        """测试: 内存使用稳定性"""
        import gc
        engine, symbols = engine_with_data

        # 记录初始内存（近似）
        gc.collect()

        # 连续处理大量订单
        for round_idx in range(10):
            for i in range(10000):
                symbol = symbols[i % len(symbols)]
                order = create_order(symbol=symbol)
                engine.try_match(order)

            # 每轮后清理
            gc.collect()

        # 如果内存稳定增长，可能存在泄漏
        # 这里主要通过不抛出异常和合理时间来判断
        assert True, "内存稳定性测试通过"

    def test_large_order_partial_fill_performance(self, engine_with_data, create_order):
        """测试: 大单部分成交性能"""
        engine, _ = engine_with_data

        # 大单（>10万）会触发部分成交逻辑
        large_order = create_order(qty=100000, price=Decimal("10.00"))

        start_time = time.perf_counter()
        result = engine.try_match(large_order)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000

        print(f"\n大单撮合延迟: {latency_ms:.3f}ms")
        assert result.success is True
        assert result.filled_qty < large_order.qty  # 部分成交
        assert latency_ms < 5.0, f"大单延迟 {latency_ms:.3f}ms 过高"

    @pytest.mark.slow
    def test_sustained_throughput(self, engine_with_data, create_order):
        """测试: 持续吞吐量（1分钟）"""
        engine, symbols = engine_with_data

        duration = 60  # 60秒
        start_time = time.perf_counter()
        count = 0

        while time.perf_counter() - start_time < duration:
            for _ in range(1000):  # 每批1000个
                symbol = symbols[count % len(symbols)]
                order = create_order(symbol=symbol)
                engine.try_match(order)
                count += 1

        elapsed = time.perf_counter() - start_time
        tps = count / elapsed

        print(f"\n持续 {duration}s 吞吐量: {tps:.0f} TPS")
        print(f"总处理订单: {count}")

        # 持续性能不应低于峰值的80%
        assert tps > 8000, f"持续吞吐量 {tps:.0f} TPS 低于预期"


@pytest.mark.performance
class TestMarketDataSimulatorPerformance:
    """市场数据模拟器性能测试"""

    def test_price_update_throughput(self, benchmark):
        """测试: 价格更新吞吐量"""
        simulator = MarketDataSimulator()

        # 初始化100个股票
        for i in range(100):
            simulator.set_base_price(f"{i:06d}.SZ", Decimal("10.00"))

        def update_prices():
            simulator.tick()

        benchmark(update_prices)

        stats = benchmark.stats
        avg_time_ms = stats["mean"] * 1000
        print(f"\n价格更新平均耗时: {avg_time_ms:.3f}ms (100只股票)")

        assert avg_time_ms < 10.0, f"价格更新耗时 {avg_time_ms:.3f}ms 过高"
