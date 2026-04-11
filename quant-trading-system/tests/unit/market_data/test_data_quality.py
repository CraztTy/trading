"""
数据质量监控测试

测试覆盖：
1. 数据完整性检查
2. 数据准确性验证
3. 异常数据检测
4. 质量指标统计
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock

from src.market_data.quality import (
    DataQualityMonitor, QualityCheck, QualityLevel,
    DataValidator, AnomalyDetector, QualityMetrics
)
from src.market_data.models import TickData, KLineData


class TestQualityLevel:
    """质量级别测试"""

    def test_level_values(self):
        """测试级别值"""
        assert QualityLevel.EXCELLENT.value == "excellent"
        assert QualityLevel.GOOD.value == "good"
        assert QualityLevel.FAIR.value == "fair"
        assert QualityLevel.POOR.value == "poor"
        assert QualityLevel.CRITICAL.value == "critical"


class TestQualityCheck:
    """质量检查测试"""

    def test_check_creation(self):
        """测试检查项创建"""
        check = QualityCheck(
            name="price_range_check",
            passed=True,
            message="价格范围检查通过",
            level=QualityLevel.GOOD
        )
        assert check.name == "price_range_check"
        assert check.passed is True
        assert check.level == QualityLevel.GOOD


class TestDataValidator:
    """数据验证器测试"""

    @pytest.fixture
    def validator(self):
        return DataValidator()

    def test_validate_valid_tick(self, validator):
        """测试验证有效tick"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=1000,
            bid_price=Decimal("10.48"),
            ask_price=Decimal("10.52"),
            source="test"
        )

        result = validator.validate_tick(tick)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_missing_symbol(self, validator):
        """测试验证缺失股票代码"""
        tick = TickData(
            symbol="",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=1000,
        )

        result = validator.validate_tick(tick)
        assert result.is_valid is False
        assert any("symbol" in e.lower() for e in result.errors)

    def test_validate_negative_price(self, validator):
        """测试验证负价格"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("-10.50"),
            volume=1000,
        )

        result = validator.validate_tick(tick)
        assert result.is_valid is False

    def test_validate_zero_volume(self, validator):
        """测试验证零成交量"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=0,
        )

        result = validator.validate_tick(tick)
        # 零成交量是允许的，只是警告
        assert len(result.warnings) > 0

    def test_validate_bid_ask_spread(self, validator):
        """测试验证买卖价差"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=1000,
            bid_price=Decimal("12.00"),  # 买价 > 卖价
            ask_price=Decimal("10.00"),
        )

        result = validator.validate_tick(tick)
        assert result.is_valid is False
        assert any("spread" in e.lower() for e in result.errors)

    def test_validate_price_precision(self, validator):
        """测试验证价格精度"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50123"),  # 超过2位小数
            volume=1000,
        )

        result = validator.validate_tick(tick)
        assert len(result.warnings) > 0

    def test_validate_kline_ohlc(self, validator):
        """测试验证K线OHLC关系"""
        kline = KLineData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10"),
            high=Decimal("8"),   # 最高价 < 开盘价
            low=Decimal("12"),   # 最低价 > 开盘价
            close=Decimal("11"),
            volume=10000,
            period="1d"
        )

        result = validator.validate_kline(kline)
        assert result.is_valid is False

    def test_validate_kline_positive_prices(self, validator):
        """测试验证K线正价格"""
        kline = KLineData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("-10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
            volume=10000,
            period="1d"
        )

        result = validator.validate_kline(kline)
        assert result.is_valid is False

    def test_validate_kline_volume(self, validator):
        """测试验证K线成交量"""
        kline = KLineData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10"),
            volume=-1000,  # 负成交量
            period="1d"
        )

        result = validator.validate_kline(kline)
        assert result.is_valid is False


class TestAnomalyDetector:
    """异常检测器测试"""

    @pytest.fixture
    def detector(self):
        return AnomalyDetector(
            price_change_threshold=0.1,  # 10%
            volume_spike_threshold=5.0    # 5倍
        )

    def test_detect_price_spike(self, detector):
        """测试检测价格暴涨"""
        ticks = [
            TickData(symbol="000001.SZ", timestamp=datetime.now(), price=Decimal("10"), volume=1000),
            TickData(symbol="000001.SZ", timestamp=datetime.now(), price=Decimal("12"), volume=1000),  # +20%
        ]

        anomalies = detector.detect_price_anomaly(ticks)
        assert len(anomalies) > 0

    def test_detect_volume_spike(self, detector):
        """测试检测成交量激增"""
        ticks = [
            TickData(symbol="000001.SZ", timestamp=datetime.now(), price=Decimal("10"), volume=1000),
            TickData(symbol="000001.SZ", timestamp=datetime.now(), price=Decimal("10"), volume=10000),  # 10倍
        ]

        anomalies = detector.detect_volume_anomaly(ticks)
        assert len(anomalies) > 0

    def test_detect_missing_data(self, detector):
        """测试检测数据缺失"""
        # 应该有数据的时间点
        expected_times = [datetime(2024, 1, 1, i) for i in range(10)]
        # 实际只有部分数据
        actual_data = [
            TickData(symbol="000001.SZ", timestamp=datetime(2024, 1, 1, 0), price=Decimal("10"), volume=1000),
            TickData(symbol="000001.SZ", timestamp=datetime(2024, 1, 1, 5), price=Decimal("10"), volume=1000),
            TickData(symbol="000001.SZ", timestamp=datetime(2024, 1, 1, 9), price=Decimal("10"), volume=1000),
        ]

        missing = detector.detect_missing_data(expected_times, actual_data)
        assert len(missing) == 7  # 缺失7个时间点

    def test_detect_stale_data(self, detector):
        """测试检测数据过期"""
        old_time = datetime.now() - timedelta(minutes=10)
        tick = TickData(symbol="000001.SZ", timestamp=old_time, price=Decimal("10"), volume=1000)

        is_stale = detector.is_stale(tick, max_age_seconds=300)  # 5分钟
        assert is_stale is True

    def test_detect_flat_line(self, detector):
        """测试检测价格横盘"""
        ticks = [
            TickData(symbol="000001.SZ", timestamp=datetime.now(), price=Decimal("10"), volume=1000)
            for _ in range(100)
        ]

        is_flat = detector.detect_flat_line(ticks, min_ticks=10)
        assert is_flat is True


class TestQualityMetrics:
    """质量指标测试"""

    def test_metrics_calculation(self):
        """测试指标计算"""
        checks = [
            QualityCheck("check1", True, "通过", QualityLevel.EXCELLENT),
            QualityCheck("check2", True, "通过", QualityLevel.GOOD),
            QualityCheck("check3", False, "失败", QualityLevel.POOR),
        ]

        metrics = QualityMetrics.calculate(checks)

        assert metrics["total_checks"] == 3
        assert metrics["passed_checks"] == 2
        assert metrics["failed_checks"] == 1
        assert metrics["pass_rate"] == 2/3

    def test_overall_quality_level(self):
        """测试整体质量级别"""
        checks = [
            QualityCheck("check1", True, "通过", QualityLevel.EXCELLENT),
            QualityCheck("check2", True, "通过", QualityLevel.EXCELLENT),
            QualityCheck("check3", True, "通过", QualityLevel.GOOD),
        ]

        metrics = QualityMetrics.calculate(checks)
        level = QualityMetrics.get_overall_level(metrics)

        assert level == QualityLevel.GOOD  # 最低的是GOOD


class TestDataQualityMonitor:
    """数据质量监控器测试"""

    @pytest.fixture
    def monitor(self):
        return DataQualityMonitor()

    def test_monitor_initialization(self, monitor):
        """测试监控器初始化"""
        assert monitor.validator is not None
        assert monitor.detector is not None
        assert len(monitor.quality_history) == 0

    def test_check_tick_quality(self, monitor):
        """测试检查tick质量"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=1000,
            bid_price=Decimal("10.48"),
            ask_price=Decimal("10.52"),
            source="test"
        )

        result = monitor.check_tick_quality(tick)

        assert result.symbol == "000001.SZ"
        assert result.overall_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]

    def test_check_tick_quality_with_anomaly(self, monitor):
        """测试检查异常tick质量"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("-10.50"),  # 负价格
            volume=1000,
        )

        result = monitor.check_tick_quality(tick)

        assert result.overall_level == QualityLevel.CRITICAL
        assert result.passed is False

    def test_check_kline_quality(self, monitor):
        """测试检查K线质量"""
        kline = KLineData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10"),
            high=Decimal("11"),
            low=Decimal("9"),
            close=Decimal("10.5"),
            volume=10000,
            period="1d"
        )

        result = monitor.check_kline_quality(kline)

        assert result.symbol == "000001.SZ"
        assert result.passed is True

    def test_record_quality_result(self, monitor):
        """测试记录质量结果"""
        from src.market_data.quality import QualityResult

        result = QualityResult(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            checks=[],
            overall_level=QualityLevel.GOOD,
            passed=True
        )

        monitor.record_result(result)

        assert len(monitor.quality_history) == 1
        assert "000001.SZ" in monitor.quality_history

    def test_get_symbol_quality_history(self, monitor):
        """测试获取标的质量历史"""
        from src.market_data.quality import QualityResult

        # 添加一些历史记录
        for i in range(5):
            result = QualityResult(
                symbol="000001.SZ",
                timestamp=datetime.now() - timedelta(minutes=i),
                checks=[],
                overall_level=QualityLevel.GOOD,
                passed=True
            )
            monitor.record_result(result)

        history = monitor.get_symbol_quality_history("000001.SZ")
        assert len(history) == 5

    def test_get_quality_summary(self, monitor):
        """测试获取质量摘要"""
        from src.market_data.quality import QualityResult

        # 添加混合质量记录
        for i in range(10):
            result = QualityResult(
                symbol="000001.SZ" if i < 5 else "000002.SZ",
                timestamp=datetime.now(),
                checks=[],
                overall_level=QualityLevel.GOOD if i % 2 == 0 else QualityLevel.FAIR,
                passed=i % 2 == 0
            )
            monitor.record_result(result)

        summary = monitor.get_quality_summary()

        assert summary["total_records"] == 10
        assert summary["symbols_checked"] == 2
        assert summary["overall_pass_rate"] == 0.5

    def test_clear_old_records(self, monitor):
        """测试清理旧记录"""
        from src.market_data.quality import QualityResult

        # 添加新旧记录
        old_result = QualityResult(
            symbol="000001.SZ",
            timestamp=datetime.now() - timedelta(days=10),
            checks=[],
            overall_level=QualityLevel.GOOD,
            passed=True
        )
        new_result = QualityResult(
            symbol="000002.SZ",
            timestamp=datetime.now(),
            checks=[],
            overall_level=QualityLevel.GOOD,
            passed=True
        )

        monitor.record_result(old_result)
        monitor.record_result(new_result)

        cleared = monitor.clear_old_records(days=7)

        assert cleared == 1
        assert len(monitor.quality_history.get("000001.SZ", [])) == 0

    def test_generate_quality_report(self, monitor):
        """测试生成质量报告"""
        from src.market_data.quality import QualityResult

        result = QualityResult(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            checks=[
                QualityCheck("completeness", True, "数据完整", QualityLevel.EXCELLENT),
                QualityCheck("accuracy", True, "数据准确", QualityLevel.GOOD),
                QualityCheck("timeliness", False, "数据延迟", QualityLevel.FAIR),
            ],
            overall_level=QualityLevel.GOOD,
            passed=True
        )
        monitor.record_result(result)

        report = monitor.generate_report()

        assert "summary" in report
        assert "symbol_reports" in report
        assert "recommendations" in report
