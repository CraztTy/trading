"""
数据质量监控

职责：
- 数据完整性检查
- 数据准确性验证
- 异常数据检测
- 质量指标统计和报告
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict

from src.market_data.models import TickData, KLineData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class QualityLevel(str, Enum):
    """数据质量级别"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"            # 良好
    FAIR = "fair"            # 一般
    POOR = "poor"            # 较差
    CRITICAL = "critical"    # 严重


@dataclass
class QualityCheck:
    """质量检查项"""
    name: str
    passed: bool
    message: str
    level: QualityLevel = QualityLevel.GOOD


@dataclass
class QualityResult:
    """质量检查结果"""
    symbol: str
    timestamp: datetime
    checks: List[QualityCheck]
    overall_level: QualityLevel
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class DataValidator:
    """
    数据验证器

    验证数据的完整性和准确性
    """

    def __init__(self):
        self.max_price = Decimal("99999.99")
        self.max_volume = 10**12
        self.price_precision = 2

    def validate_tick(self, tick: TickData) -> ValidationResult:
        """
        验证Tick数据

        Args:
            tick: Tick数据

        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []

        # 检查必填字段
        if not tick.symbol:
            errors.append("Missing symbol")

        if tick.price is None:
            errors.append("Missing price")
        else:
            # 检查价格范围
            if tick.price <= 0:
                errors.append(f"Invalid price: {tick.price} (must be positive)")
            elif tick.price > self.max_price:
                errors.append(f"Price exceeds max: {tick.price}")

            # 检查价格精度
            if tick.price != tick.price.quantize(Decimal(f"0.{('0'*self.price_precision)}")):
                warnings.append(f"Price precision exceeds {self.price_precision} decimal places")

        # 检查成交量
        if tick.volume is None:
            warnings.append("Missing volume")
        elif tick.volume < 0:
            errors.append(f"Invalid volume: {tick.volume}")
        elif tick.volume == 0:
            warnings.append("Zero volume")

        # 检查买卖盘
        if tick.bid_price and tick.ask_price:
            if tick.bid_price > tick.ask_price:
                errors.append(f"Invalid spread: bid({tick.bid_price}) > ask({tick.ask_price})")

        # 检查时间戳
        if tick.timestamp is None:
            warnings.append("Missing timestamp")
        else:
            # 检查时间是否在未来
            if tick.timestamp > datetime.now() + timedelta(minutes=1):
                errors.append(f"Future timestamp: {tick.timestamp}")
            # 检查时间是否太旧
            if tick.timestamp < datetime.now() - timedelta(days=1):
                warnings.append(f"Stale timestamp: {tick.timestamp}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def validate_kline(self, kline: KLineData) -> ValidationResult:
        """
        验证K线数据

        Args:
            kline: K线数据

        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []

        # 检查必填字段
        if not kline.symbol:
            errors.append("Missing symbol")

        if kline.timestamp is None:
            errors.append("Missing timestamp")

        # 检查价格
        prices = [
            ("open", kline.open),
            ("high", kline.high),
            ("low", kline.low),
            ("close", kline.close)
        ]

        for name, price in prices:
            if price is None:
                errors.append(f"Missing {name} price")
            elif price < 0:
                errors.append(f"Negative {name} price: {price}")
            elif price > self.max_price:
                errors.append(f"{name} price exceeds max: {price}")

        # 检查OHLC关系
        if kline.high and kline.low:
            if kline.high < kline.low:
                errors.append(f"High({kline.high}) < Low({kline.low})")

            if kline.open and kline.open > kline.high:
                errors.append(f"Open({kline.open}) > High({kline.high})")
            if kline.open and kline.open < kline.low:
                errors.append(f"Open({kline.open}) < Low({kline.low})")

            if kline.close and kline.close > kline.high:
                errors.append(f"Close({kline.close}) > High({kline.high})")
            if kline.close and kline.close < kline.low:
                errors.append(f"Close({kline.close}) < Low({kline.low})")

        # 检查成交量
        if kline.volume is None:
            warnings.append("Missing volume")
        elif kline.volume < 0:
            errors.append(f"Negative volume: {kline.volume}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class AnomalyDetector:
    """
    异常检测器

    检测数据中的异常模式
    """

    def __init__(
        self,
        price_change_threshold: float = 0.1,      # 价格变动阈值 10%
        volume_spike_threshold: float = 5.0,      # 成交量激增阈值 5倍
        stale_data_seconds: int = 300             # 数据过期阈值 5分钟
    ):
        self.price_change_threshold = price_change_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.stale_data_seconds = stale_data_seconds

    def detect_price_anomaly(self, ticks: List[TickData]) -> List[Dict[str, Any]]:
        """
        检测价格异常

        Args:
            ticks: Tick数据列表

        Returns:
            异常列表
        """
        anomalies = []

        for i in range(1, len(ticks)):
            prev_tick = ticks[i-1]
            curr_tick = ticks[i]

            if prev_tick.price > 0:
                change_pct = abs(curr_tick.price - prev_tick.price) / prev_tick.price

                if change_pct > Decimal(str(self.price_change_threshold)):
                    anomalies.append({
                        "type": "price_spike",
                        "timestamp": curr_tick.timestamp,
                        "symbol": curr_tick.symbol,
                        "change_pct": float(change_pct),
                        "from_price": float(prev_tick.price),
                        "to_price": float(curr_tick.price)
                    })

        return anomalies

    def detect_volume_anomaly(self, ticks: List[TickData]) -> List[Dict[str, Any]]:
        """
        检测成交量异常

        Args:
            ticks: Tick数据列表

        Returns:
            异常列表
        """
        anomalies = []

        if len(ticks) < 2:
            return anomalies

        # 计算平均成交量
        avg_volume = sum(t.volume for t in ticks[:-1]) / len(ticks[:-1])

        if avg_volume > 0:
            latest = ticks[-1]
            volume_ratio = latest.volume / avg_volume

            if volume_ratio > self.volume_spike_threshold:
                anomalies.append({
                    "type": "volume_spike",
                    "timestamp": latest.timestamp,
                    "symbol": latest.symbol,
                    "volume_ratio": float(volume_ratio),
                    "volume": latest.volume,
                    "avg_volume": avg_volume
                })

        return anomalies

    def detect_missing_data(
        self,
        expected_times: List[datetime],
        actual_data: List[TickData]
    ) -> List[datetime]:
        """
        检测数据缺失

        Args:
            expected_times: 预期的时间点列表
            actual_data: 实际的数据

        Returns:
            缺失的时间点列表
        """
        actual_times = {d.timestamp for d in actual_data}
        missing = [t for t in expected_times if t not in actual_times]
        return missing

    def is_stale(self, tick: TickData, max_age_seconds: Optional[int] = None) -> bool:
        """
        检查数据是否过期

        Args:
            tick: Tick数据
            max_age_seconds: 最大年龄（秒）

        Returns:
            是否过期
        """
        if tick.timestamp is None:
            return True

        age = datetime.now() - tick.timestamp
        threshold = max_age_seconds or self.stale_data_seconds

        return age.total_seconds() > threshold

    def detect_flat_line(self, ticks: List[TickData], min_ticks: int = 10) -> bool:
        """
        检测价格横盘（可能是数据 stale）

        Args:
            ticks: Tick数据列表
            min_ticks: 最小检查条数

        Returns:
            是否横盘
        """
        if len(ticks) < min_ticks:
            return False

        recent_ticks = ticks[-min_ticks:]
        prices = [t.price for t in recent_ticks]

        # 检查是否所有价格都相同
        return len(set(prices)) == 1


class QualityMetrics:
    """质量指标计算"""

    @staticmethod
    def calculate(checks: List[QualityCheck]) -> Dict[str, Any]:
        """
        计算质量指标

        Args:
            checks: 检查项列表

        Returns:
            指标字典
        """
        total = len(checks)
        passed = sum(1 for c in checks if c.passed)
        failed = total - passed

        # 统计各级别的数量
        level_counts = defaultdict(int)
        for check in checks:
            level_counts[check.level] += 1

        # 计算通过率
        pass_rate = passed / total if total > 0 else 0.0

        return {
            "total_checks": total,
            "passed_checks": passed,
            "failed_checks": failed,
            "pass_rate": pass_rate,
            "level_counts": dict(level_counts)
        }

    @staticmethod
    def get_overall_level(metrics: Dict[str, Any]) -> QualityLevel:
        """获取整体质量级别"""
        pass_rate = metrics.get("pass_rate", 0)
        level_counts = metrics.get("level_counts", {})

        # 如果有任何critical级别的问题，整体为critical
        if level_counts.get(QualityLevel.CRITICAL, 0) > 0:
            return QualityLevel.CRITICAL

        # 根据通过率判断
        if pass_rate >= 0.95:
            return QualityLevel.EXCELLENT
        elif pass_rate >= 0.85:
            return QualityLevel.GOOD
        elif pass_rate >= 0.70:
            return QualityLevel.FAIR
        else:
            return QualityLevel.POOR


class DataQualityMonitor:
    """
    数据质量监控器

    持续监控数据质量并生成报告
    """

    def __init__(self):
        self.validator = DataValidator()
        self.detector = AnomalyDetector()
        self.quality_history: Dict[str, List[QualityResult]] = defaultdict(list)

    def check_tick_quality(self, tick: TickData) -> QualityResult:
        """
        检查Tick数据质量

        Args:
            tick: Tick数据

        Returns:
            QualityResult: 质量结果
        """
        checks = []

        # 完整性检查
        validation = self.validator.validate_tick(tick)
        if validation.is_valid:
            checks.append(QualityCheck(
                name="completeness",
                passed=True,
                message="Data is complete",
                level=QualityLevel.EXCELLENT
            ))
        else:
            checks.append(QualityCheck(
                name="completeness",
                passed=False,
                message=f"Data incomplete: {', '.join(validation.errors)}",
                level=QualityLevel.CRITICAL if validation.errors else QualityLevel.FAIR
            ))

        # 时效性检查
        if self.detector.is_stale(tick):
            checks.append(QualityCheck(
                name="timeliness",
                passed=False,
                message="Data is stale",
                level=QualityLevel.POOR
            ))
        else:
            checks.append(QualityCheck(
                name="timeliness",
                passed=True,
                message="Data is fresh",
                level=QualityLevel.GOOD
            ))

        # 准确性检查
        if tick.price and tick.price > 0:
            checks.append(QualityCheck(
                name="accuracy",
                passed=True,
                message="Price is valid",
                level=QualityLevel.GOOD
            ))
        else:
            checks.append(QualityCheck(
                name="accuracy",
                passed=False,
                message="Price is invalid",
                level=QualityLevel.CRITICAL
            ))

        # 计算质量指标
        metrics = QualityMetrics.calculate(checks)
        overall_level = QualityMetrics.get_overall_level(metrics)

        result = QualityResult(
            symbol=tick.symbol,
            timestamp=datetime.now(),
            checks=checks,
            overall_level=overall_level,
            passed=metrics["pass_rate"] >= 0.8
        )

        self.record_result(result)
        return result

    def check_kline_quality(self, kline: KLineData) -> QualityResult:
        """
        检查K线数据质量

        Args:
            kline: K线数据

        Returns:
            QualityResult: 质量结果
        """
        checks = []

        validation = self.validator.validate_kline(kline)

        # OHLC关系检查
        if validation.is_valid:
            checks.append(QualityCheck(
                name="ohlc_relationship",
                passed=True,
                message="OHLC relationship is valid",
                level=QualityLevel.EXCELLENT
            ))
        else:
            level = QualityLevel.CRITICAL if validation.errors else QualityLevel.FAIR
            checks.append(QualityCheck(
                name="ohlc_relationship",
                passed=False,
                message=f"OHLC invalid: {', '.join(validation.errors)}",
                level=level
            ))

        # 成交量检查
        if kline.volume and kline.volume > 0:
            checks.append(QualityCheck(
                name="volume",
                passed=True,
                message="Volume is valid",
                level=QualityLevel.GOOD
            ))
        else:
            checks.append(QualityCheck(
                name="volume",
                passed=False,
                message="Volume is zero or missing",
                level=QualityLevel.FAIR
            ))

        metrics = QualityMetrics.calculate(checks)
        overall_level = QualityMetrics.get_overall_level(metrics)

        result = QualityResult(
            symbol=kline.symbol,
            timestamp=datetime.now(),
            checks=checks,
            overall_level=overall_level,
            passed=validation.is_valid
        )

        self.record_result(result)
        return result

    def record_result(self, result: QualityResult) -> None:
        """记录质量结果"""
        self.quality_history[result.symbol].append(result)

        # 限制历史记录数量
        max_history = 1000
        if len(self.quality_history[result.symbol]) > max_history:
            self.quality_history[result.symbol] = self.quality_history[result.symbol][-max_history:]

    def get_symbol_quality_history(self, symbol: str) -> List[QualityResult]:
        """获取标的质量历史"""
        return self.quality_history.get(symbol, [])

    def get_quality_summary(self) -> Dict[str, Any]:
        """获取质量摘要"""
        total_records = sum(len(h) for h in self.quality_history.values())
        symbols_checked = len(self.quality_history)

        # 计算整体通过率
        passed_count = sum(
            sum(1 for r in h if r.passed)
            for h in self.quality_history.values()
        )
        overall_pass_rate = passed_count / total_records if total_records > 0 else 0.0

        return {
            "total_records": total_records,
            "symbols_checked": symbols_checked,
            "overall_pass_rate": overall_pass_rate,
            "timestamp": datetime.now()
        }

    def clear_old_records(self, days: int = 7) -> int:
        """
        清理旧记录

        Args:
            days: 保留天数

        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(days=days)
        cleared = 0

        for symbol in list(self.quality_history.keys()):
            original_len = len(self.quality_history[symbol])
            self.quality_history[symbol] = [
                r for r in self.quality_history[symbol]
                if r.timestamp > cutoff
            ]
            cleared += original_len - len(self.quality_history[symbol])

        return cleared

    def generate_report(self) -> Dict[str, Any]:
        """生成质量报告"""
        summary = self.get_quality_summary()

        # 按标的质量报告
        symbol_reports = {}
        for symbol, history in self.quality_history.items():
            if not history:
                continue

            latest = history[-1]
            pass_count = sum(1 for r in history if r.passed)

            symbol_reports[symbol] = {
                "latest_quality": latest.overall_level.value,
                "latest_timestamp": latest.timestamp,
                "check_count": len(history),
                "pass_rate": pass_count / len(history),
                "recent_issues": [
                    {
                        "check": c.name,
                        "message": c.message
                    }
                    for c in latest.checks if not c.passed
                ]
            }

        # 生成建议
        recommendations = []
        for symbol, report in symbol_reports.items():
            if report["pass_rate"] < 0.8:
                recommendations.append({
                    "type": "data_quality",
                    "symbol": symbol,
                    "message": f"{symbol} 数据质量较差，建议检查数据源"
                })

        return {
            "summary": summary,
            "symbol_reports": symbol_reports,
            "recommendations": recommendations,
            "generated_at": datetime.now()
        }
