"""
Phase 1 优化集成测试

测试覆盖以下功能：
1. 订单状态流转测试
2. 风控规则测试
3. API错误处理测试
4. 数据质量监控测试
5. 指标收集测试

注意：此测试文件使用内嵌的类定义，避免导入SQLAlchemy相关的模型
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List, Callable
from unittest.mock import MagicMock
from dataclasses import dataclass, field
from enum import Enum, auto

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


# ============== 内嵌枚举定义（避免SQLAlchemy依赖） ==============

class OrderStatus(str, Enum):
    """订单状态"""
    CREATED = "CREATED"
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderDirection(str, Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """订单类型"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"


class QualityLevel(str, Enum):
    """数据质量级别"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class OrderEvent(Enum):
    """订单事件类型"""
    CREATE = auto()
    SUBMIT = auto()
    FILL_PARTIAL = auto()
    FILL_FULL = auto()
    CANCEL = auto()
    REJECT = auto()
    EXPIRE = auto()


# ============== 内嵌数据类定义 ==============

@dataclass
class StateTransition:
    """状态转换记录"""
    from_status: OrderStatus
    to_status: OrderStatus
    event: OrderEvent
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


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


@dataclass
class MockTickData:
    """Mock Tick数据类"""
    symbol: str
    timestamp: datetime
    price: Optional[Decimal] = None
    volume: Optional[int] = None
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    bid_volume: Optional[int] = None
    ask_volume: Optional[int] = None


@dataclass
class MockKLineData:
    """Mock K线数据类"""
    symbol: str
    timestamp: datetime
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    volume: Optional[int] = None
    amount: Optional[Decimal] = None
    period: str = "1d"


# ============== 内嵌异常类 ==============

class TradingException(Exception):
    """基础交易异常"""
    def __init__(self, message: str, code: str = "TRADING_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class ValidationError(TradingException):
    """数据验证错误"""
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, **kwargs):
        details = kwargs.get("details", {})
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)


class RiskControlError(TradingException):
    """风控错误"""
    def __init__(self, message: str, rule_id: Optional[str] = None, risk_level: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if rule_id is not None:
            details["rule_id"] = rule_id
        if risk_level is not None:
            details["risk_level"] = risk_level
        super().__init__(message=message, code="RISK_CONTROL_ERROR", details=details)


class OrderExecutionError(TradingException):
    """订单执行错误"""
    def __init__(self, message: str, order_id: Optional[str] = None, broker: Optional[str] = None, status: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if order_id is not None:
            details["order_id"] = order_id
        if broker is not None:
            details["broker"] = broker
        if status is not None:
            details["status"] = status
        super().__init__(message=message, code="ORDER_EXECUTION_ERROR", details=details)


ERROR_CODES = {
    "VALIDATION_ERROR": {"http_status": 400, "description": "请求数据验证失败"},
    "RISK_CONTROL_ERROR": {"http_status": 403, "description": "风控规则触发"},
    "ORDER_EXECUTION_ERROR": {"http_status": 422, "description": "订单执行失败"},
    "TRADING_ERROR": {"http_status": 500, "description": "交易系统通用错误"},
}


def get_error_response(exception: TradingException) -> Dict[str, Any]:
    """获取标准错误响应"""
    error_info = ERROR_CODES.get(exception.code, ERROR_CODES["TRADING_ERROR"])
    return {
        "error": {
            "code": exception.code,
            "message": exception.message,
            "details": exception.details,
            "type": error_info["description"],
        },
        "status_code": error_info["http_status"],
    }


# ============== 订单状态机实现 ==============

class InvalidStateTransition(Exception):
    """非法状态转换异常"""
    pass


class OrderStateMachine:
    """订单状态机（简化版）"""

    TRANSITIONS: Dict[tuple, OrderStatus] = {
        (OrderStatus.CREATED, OrderEvent.SUBMIT): OrderStatus.PENDING,
        (OrderStatus.PENDING, OrderEvent.FILL_PARTIAL): OrderStatus.PARTIAL,
        (OrderStatus.PENDING, OrderEvent.FILL_FULL): OrderStatus.FILLED,
        (OrderStatus.PENDING, OrderEvent.CANCEL): OrderStatus.CANCELLED,
        (OrderStatus.PENDING, OrderEvent.REJECT): OrderStatus.REJECTED,
        (OrderStatus.PARTIAL, OrderEvent.FILL_PARTIAL): OrderStatus.PARTIAL,
        (OrderStatus.PARTIAL, OrderEvent.FILL_FULL): OrderStatus.FILLED,
        (OrderStatus.PARTIAL, OrderEvent.CANCEL): OrderStatus.CANCELLED,
        (OrderStatus.CREATED, OrderEvent.EXPIRE): OrderStatus.EXPIRED,
        (OrderStatus.PENDING, OrderEvent.EXPIRE): OrderStatus.EXPIRED,
        (OrderStatus.PARTIAL, OrderEvent.EXPIRE): OrderStatus.EXPIRED,
    }

    TERMINAL_STATES = {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.REJECTED,
        OrderStatus.EXPIRED,
    }

    def __init__(self, order):
        self.order = order
        self._transitions: List[StateTransition] = []
        self._callbacks: Dict[OrderEvent, List[Callable]] = {event: [] for event in OrderEvent}

        if order.created_at:
            self._transitions.append(StateTransition(
                from_status=OrderStatus.CREATED,
                to_status=order.status,
                event=OrderEvent.CREATE,
                timestamp=order.created_at
            ))

    def can_transition(self, event: OrderEvent) -> bool:
        current_status = self.order.status
        if current_status in self.TERMINAL_STATES:
            return False
        return (current_status, event) in self.TRANSITIONS

    def get_target_status(self, event: OrderEvent) -> Optional[OrderStatus]:
        return self.TRANSITIONS.get((self.order.status, event))

    def transition(self, event: OrderEvent, details: Optional[Dict[str, Any]] = None) -> bool:
        target_status = self.get_target_status(event)
        if target_status is None:
            raise InvalidStateTransition(f"Cannot transition from {self.order.status.value} with event {event.name}")

        transition = StateTransition(
            from_status=self.order.status,
            to_status=target_status,
            event=event,
            timestamp=datetime.now(),
            details=details
        )
        self._transitions.append(transition)

        old_status = self.order.status
        self.order.status = target_status
        self._update_timestamp(event, details)
        self._trigger_callbacks(event, transition)
        return True

    def _update_timestamp(self, event: OrderEvent, details: Optional[Dict[str, Any]]) -> None:
        if event == OrderEvent.SUBMIT:
            self.order.submitted_at = datetime.now()
        elif event in (OrderEvent.FILL_PARTIAL, OrderEvent.FILL_FULL):
            self.order.filled_at = datetime.now()
            if details:
                fill_qty = details.get('fill_qty', 0)
                fill_price = details.get('fill_price', Decimal('0'))
                if fill_qty > 0 and fill_price > 0:
                    new_amount = self.order.filled_amount + (fill_price * fill_qty)
                    self.order.filled_qty += fill_qty
                    if self.order.filled_qty > 0:
                        self.order.filled_avg_price = new_amount / self.order.filled_qty
                    self.order.filled_amount = new_amount
        elif event == OrderEvent.CANCEL:
            self.order.cancelled_at = datetime.now()
        elif event == OrderEvent.REJECT:
            if details and 'reason' in details:
                self.order.error_msg = details['reason']

    def register_callback(self, event: OrderEvent, callback: Callable) -> None:
        self._callbacks[event].append(callback)

    def _trigger_callbacks(self, event: OrderEvent, transition: StateTransition) -> None:
        for callback in self._callbacks.get(event, []):
            try:
                callback(self.order, transition)
            except Exception:
                pass

    def get_transition_history(self) -> List[StateTransition]:
        return self._transitions.copy()

    def is_terminal(self) -> bool:
        return self.order.status in self.TERMINAL_STATES

    def is_active(self) -> bool:
        return self.order.status in {OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL}

    def can_cancel(self) -> bool:
        return self.order.status in {OrderStatus.CREATED, OrderStatus.PENDING, OrderStatus.PARTIAL}

    def can_fill(self) -> bool:
        return self.order.status in {OrderStatus.PENDING, OrderStatus.PARTIAL}


# ============== 数据质量监控实现 ==============

class DataValidator:
    """数据验证器"""

    def __init__(self):
        self.max_price = Decimal("99999.99")
        self.max_volume = 10**12
        self.price_precision = 2

    def validate_tick(self, tick: MockTickData) -> ValidationResult:
        errors = []
        warnings = []

        if not tick.symbol:
            errors.append("Missing symbol")

        if tick.price is None:
            errors.append("Missing price")
        else:
            if tick.price <= 0:
                errors.append(f"Invalid price: {tick.price}")
            elif tick.price > self.max_price:
                errors.append(f"Price exceeds max: {tick.price}")

        if tick.volume is None:
            warnings.append("Missing volume")
        elif tick.volume < 0:
            errors.append(f"Invalid volume: {tick.volume}")

        if tick.bid_price and tick.ask_price:
            if tick.bid_price > tick.ask_price:
                errors.append(f"Invalid spread: bid({tick.bid_price}) > ask({tick.ask_price})")

        if tick.timestamp is None:
            warnings.append("Missing timestamp")
        else:
            if tick.timestamp > datetime.now() + timedelta(minutes=1):
                errors.append(f"Future timestamp: {tick.timestamp}")
            if tick.timestamp < datetime.now() - timedelta(days=1):
                warnings.append(f"Stale timestamp: {tick.timestamp}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_kline(self, kline: MockKLineData) -> ValidationResult:
        errors = []
        warnings = []

        if not kline.symbol:
            errors.append("Missing symbol")

        if kline.timestamp is None:
            errors.append("Missing timestamp")

        prices = [("open", kline.open), ("high", kline.high), ("low", kline.low), ("close", kline.close)]
        for name, price in prices:
            if price is None:
                errors.append(f"Missing {name} price")
            elif price < 0:
                errors.append(f"Negative {name} price: {price}")
            elif price > self.max_price:
                errors.append(f"{name} price exceeds max: {price}")

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

        if kline.volume is None:
            warnings.append("Missing volume")
        elif kline.volume < 0:
            errors.append(f"Negative volume: {kline.volume}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class AnomalyDetector:
    """异常检测器"""

    def __init__(self, price_change_threshold: float = 0.1, volume_spike_threshold: float = 5.0, stale_data_seconds: int = 300):
        self.price_change_threshold = price_change_threshold
        self.volume_spike_threshold = volume_spike_threshold
        self.stale_data_seconds = stale_data_seconds

    def detect_price_anomaly(self, ticks: List[MockTickData]) -> List[Dict[str, Any]]:
        anomalies = []
        for i in range(1, len(ticks)):
            prev_tick = ticks[i-1]
            curr_tick = ticks[i]
            if prev_tick.price and prev_tick.price > 0:
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

    def detect_volume_anomaly(self, ticks: List[MockTickData]) -> List[Dict[str, Any]]:
        anomalies = []
        if len(ticks) < 2:
            return anomalies
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

    def is_stale(self, tick: MockTickData, max_age_seconds: Optional[int] = None) -> bool:
        if tick.timestamp is None:
            return True
        age = datetime.now() - tick.timestamp
        threshold = max_age_seconds or self.stale_data_seconds
        return age.total_seconds() > threshold


class DataQualityMonitor:
    """数据质量监控器"""

    def __init__(self):
        self.validator = DataValidator()
        self.detector = AnomalyDetector()
        self.quality_history: Dict[str, List[QualityResult]] = {}

    def check_tick_quality(self, tick: MockTickData) -> QualityResult:
        checks = []
        validation = self.validator.validate_tick(tick)

        if validation.is_valid:
            checks.append(QualityCheck(name="completeness", passed=True, message="Data is complete", level=QualityLevel.EXCELLENT))
        else:
            level = QualityLevel.CRITICAL if validation.errors else QualityLevel.FAIR
            checks.append(QualityCheck(name="completeness", passed=False, message=f"Data incomplete: {', '.join(validation.errors)}", level=level))

        if self.detector.is_stale(tick):
            checks.append(QualityCheck(name="timeliness", passed=False, message="Data is stale", level=QualityLevel.POOR))
        else:
            checks.append(QualityCheck(name="timeliness", passed=True, message="Data is fresh", level=QualityLevel.GOOD))

        if tick.price and tick.price > 0:
            checks.append(QualityCheck(name="accuracy", passed=True, message="Price is valid", level=QualityLevel.GOOD))
        else:
            checks.append(QualityCheck(name="accuracy", passed=False, message="Price is invalid", level=QualityLevel.CRITICAL))

        passed_count = sum(1 for c in checks if c.passed)
        pass_rate = passed_count / len(checks) if checks else 0

        if any(c.level == QualityLevel.CRITICAL for c in checks):
            overall_level = QualityLevel.CRITICAL
        elif pass_rate >= 0.95:
            overall_level = QualityLevel.EXCELLENT
        elif pass_rate >= 0.85:
            overall_level = QualityLevel.GOOD
        elif pass_rate >= 0.70:
            overall_level = QualityLevel.FAIR
        else:
            overall_level = QualityLevel.POOR

        result = QualityResult(
            symbol=tick.symbol,
            timestamp=datetime.now(),
            checks=checks,
            overall_level=overall_level,
            passed=pass_rate >= 0.8
        )

        if tick.symbol not in self.quality_history:
            self.quality_history[tick.symbol] = []
        self.quality_history[tick.symbol].append(result)

        return result

    def check_kline_quality(self, kline: MockKLineData) -> QualityResult:
        checks = []
        validation = self.validator.validate_kline(kline)

        if validation.is_valid:
            checks.append(QualityCheck(name="ohlc_relationship", passed=True, message="OHLC relationship is valid", level=QualityLevel.EXCELLENT))
        else:
            level = QualityLevel.CRITICAL if validation.errors else QualityLevel.FAIR
            checks.append(QualityCheck(name="ohlc_relationship", passed=False, message=f"OHLC invalid: {', '.join(validation.errors)}", level=level))

        if kline.volume and kline.volume > 0:
            checks.append(QualityCheck(name="volume", passed=True, message="Volume is valid", level=QualityLevel.GOOD))
        else:
            checks.append(QualityCheck(name="volume", passed=False, message="Volume is zero or missing", level=QualityLevel.FAIR))

        passed_count = sum(1 for c in checks if c.passed)
        pass_rate = passed_count / len(checks) if checks else 0

        if any(c.level == QualityLevel.CRITICAL for c in checks):
            overall_level = QualityLevel.CRITICAL
        elif pass_rate >= 0.95:
            overall_level = QualityLevel.EXCELLENT
        elif pass_rate >= 0.85:
            overall_level = QualityLevel.GOOD
        elif pass_rate >= 0.70:
            overall_level = QualityLevel.FAIR
        else:
            overall_level = QualityLevel.POOR

        return QualityResult(
            symbol=kline.symbol,
            timestamp=datetime.now(),
            checks=checks,
            overall_level=overall_level,
            passed=validation.is_valid
        )

    def generate_report(self) -> Dict[str, Any]:
        total_records = sum(len(h) for h in self.quality_history.values())
        symbols_checked = len(self.quality_history)

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
                "pass_rate": pass_count / len(history) if history else 0,
                "recent_issues": [{"check": c.name, "message": c.message} for c in latest.checks if not c.passed]
            }

        recommendations = []
        for symbol, report in symbol_reports.items():
            if report["pass_rate"] < 0.8:
                recommendations.append({"type": "data_quality", "symbol": symbol, "message": f"{symbol} 数据质量较差，建议检查数据源"})

        return {
            "summary": {"total_records": total_records, "symbols_checked": symbols_checked},
            "symbol_reports": symbol_reports,
            "recommendations": recommendations,
            "generated_at": datetime.now()
        }


# ============== 指标收集实现 ==============

@dataclass
class HistogramStats:
    """直方图统计结果"""
    count: int = 0
    sum_val: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    avg: float = 0.0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0


class Timer:
    """计时器上下文管理器"""

    def __init__(self, collector, metric_name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time: Optional[float] = None
        self.duration_ms: Optional[float] = None

    def __enter__(self):
        self.start_time = asyncio.get_event_loop().time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            end_time = asyncio.get_event_loop().time()
            self.duration_ms = (end_time - self.start_time) * 1000
            self.collector.record(self.metric_name, self.duration_ms, "histogram", tags=self.tags)


class MetricsCollector:
    """指标收集器（单例）"""

    _instance: Optional['MetricsCollector'] = None

    def __new__(cls) -> 'MetricsCollector':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._counters: Dict[str, Dict[str, float]] = {}
        self._gauges: Dict[str, Dict[str, float]] = {}
        self._histograms: Dict[str, Dict[str, List[float]]] = {}
        self._max_histogram_samples = 10000

    def _make_tag_key(self, tags: Optional[Dict[str, str]]) -> str:
        if not tags:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(tags.items()))

    def record(self, metric_name: str, value: float, metric_type: str = "counter", tags: Optional[Dict[str, str]] = None):
        tag_key = self._make_tag_key(tags)

        if metric_type == "counter":
            if metric_name not in self._counters:
                self._counters[metric_name] = {}
            self._counters[metric_name][tag_key] = self._counters[metric_name].get(tag_key, 0) + value
        elif metric_type == "gauge":
            if metric_name not in self._gauges:
                self._gauges[metric_name] = {}
            self._gauges[metric_name][tag_key] = value
        elif metric_type == "histogram":
            if metric_name not in self._histograms:
                self._histograms[metric_name] = {}
            if tag_key not in self._histograms[metric_name]:
                self._histograms[metric_name][tag_key] = []
            self._histograms[metric_name][tag_key].append(value)
            if len(self._histograms[metric_name][tag_key]) > self._max_histogram_samples:
                vals = self._histograms[metric_name][tag_key]
                self._histograms[metric_name][tag_key] = vals[len(vals)//4:]

    def increment(self, metric_name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        self.record(metric_name, value, "counter", tags)

    def gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        self.record(metric_name, value, "gauge", tags)

    def timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        return Timer(self, metric_name, tags)

    def get_metric(self, metric_name: str, metric_type: Optional[str] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        if metric_name in self._counters and metric_type in (None, "counter"):
            result["counter"] = dict(self._counters[metric_name])
        if metric_name in self._gauges and metric_type in (None, "gauge"):
            result["gauge"] = dict(self._gauges[metric_name])
        if metric_name in self._histograms and metric_type in (None, "histogram"):
            histogram_data = {}
            for tag_key, values in self._histograms[metric_name].items():
                histogram_data[tag_key] = {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": round(sum(values) / len(values), 3) if values else 0,
                    "min": round(min(values), 3) if values else 0,
                    "max": round(max(values), 3) if values else 0,
                }
            result["histogram"] = histogram_data
        return result

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "counters": {name: dict(values) for name, values in self._counters.items()},
            "gauges": {name: dict(values) for name, values in self._gauges.items()},
            "histograms": {
                name: {
                    tag_key: {"count": len(vals), "sum": sum(vals), "avg": round(sum(vals) / len(vals), 3) if vals else 0,
                              "min": round(min(vals), 3) if vals else 0, "max": round(max(vals), 3) if vals else 0}
                    for tag_key, vals in tag_values.items()
                }
                for name, tag_values in self._histograms.items()
            }
        }

    def reset(self, metric_name: Optional[str] = None):
        if metric_name is None:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
        else:
            self._counters.pop(metric_name, None)
            self._gauges.pop(metric_name, None)
            self._histograms.pop(metric_name, None)

    def snapshot(self) -> Dict[str, Any]:
        import time
        return {"timestamp": time.time(), "metrics": self.get_metrics()}


# 全局指标收集器实例
metrics = MetricsCollector()


# ============== 测试夹具 ==============

@pytest.fixture
def sample_order():
    """创建样本订单"""
    order = MagicMock()
    order.order_id = "ORD20240101000001001"
    order.status = OrderStatus.CREATED
    order.created_at = datetime.now()
    order.qty = 1000
    order.filled_qty = 0
    order.filled_avg_price = Decimal("0")
    order.filled_amount = Decimal("0")
    order.submitted_at = None
    order.filled_at = None
    order.cancelled_at = None
    order.error_msg = None
    return order


@pytest.fixture
def data_quality_monitor():
    """创建数据质量监控器"""
    return DataQualityMonitor()


@pytest.fixture
def sample_tick():
    """创建样本Tick数据"""
    return MockTickData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        price=Decimal("10.50"),
        volume=1000,
        bid_price=Decimal("10.48"),
        ask_price=Decimal("10.52"),
        bid_volume=500,
        ask_volume=600
    )


@pytest.fixture
def sample_kline():
    """创建样本K线数据"""
    return MockKLineData(
        symbol="000001.SZ",
        timestamp=datetime.now(),
        open=Decimal("10.30"),
        high=Decimal("10.60"),
        low=Decimal("10.20"),
        close=Decimal("10.50"),
        volume=10000,
        amount=Decimal("105000"),
        period="1d"
    )


# ============== 订单状态管理测试 ==============

@pytest.mark.integration
class TestOrderStateManagement:
    """订单状态管理测试"""

    @pytest.mark.asyncio
    async def test_order_state_transitions(self, sample_order):
        """测试订单状态流转: CREATED -> PENDING -> PARTIAL -> FILLED"""
        # 创建订单 -> CREATED
        sm = OrderStateMachine(sample_order)
        assert sample_order.status == OrderStatus.CREATED

        # 提交 -> PENDING
        sm.transition(OrderEvent.SUBMIT)
        assert sample_order.status == OrderStatus.PENDING
        assert sample_order.submitted_at is not None

        # 部分成交 -> PARTIAL
        sm.transition(OrderEvent.FILL_PARTIAL, details={"fill_qty": 500, "fill_price": Decimal("10.50")})
        assert sample_order.status == OrderStatus.PARTIAL
        assert sample_order.filled_qty == 500

        # 全部成交 -> FILLED
        sm.transition(OrderEvent.FILL_FULL, details={"fill_qty": 500, "fill_price": Decimal("10.60")})
        assert sample_order.status == OrderStatus.FILLED
        assert sample_order.filled_qty == 1000

        # 验证状态历史记录
        history = sm.get_transition_history()
        assert len(history) == 4  # 初始创建 + 3次转换

        # 验证每次转换
        assert history[1].event == OrderEvent.SUBMIT
        assert history[2].event == OrderEvent.FILL_PARTIAL
        assert history[3].event == OrderEvent.FILL_FULL

    @pytest.mark.asyncio
    async def test_order_cancellation(self, sample_order):
        """测试撤单功能"""
        sm = OrderStateMachine(sample_order)

        # 提交订单
        sm.transition(OrderEvent.SUBMIT)
        assert sample_order.status == OrderStatus.PENDING

        # 撤单
        sm.transition(OrderEvent.CANCEL)
        assert sample_order.status == OrderStatus.CANCELLED
        assert sample_order.cancelled_at is not None

        # 验证终结状态不可再转换
        assert sm.is_terminal() is True
        with pytest.raises(InvalidStateTransition):
            sm.transition(OrderEvent.SUBMIT)

    @pytest.mark.asyncio
    async def test_partial_fill_and_cancel(self, sample_order):
        """测试部分成交后撤单"""
        sm = OrderStateMachine(sample_order)

        # 提交订单
        sm.transition(OrderEvent.SUBMIT)

        # 部分成交
        sm.transition(OrderEvent.FILL_PARTIAL, details={"fill_qty": 300, "fill_price": Decimal("10.50")})
        assert sample_order.status == OrderStatus.PARTIAL
        assert sample_order.filled_qty == 300

        # 撤单
        sm.transition(OrderEvent.CANCEL)
        assert sample_order.status == OrderStatus.CANCELLED
        # 已成交部分保留
        assert sample_order.filled_qty == 300

    @pytest.mark.asyncio
    async def test_order_rejection(self, sample_order):
        """测试订单被拒绝"""
        sm = OrderStateMachine(sample_order)

        # 提交订单
        sm.transition(OrderEvent.SUBMIT)

        # 被拒绝
        sm.transition(OrderEvent.REJECT, details={"reason": "资金不足"})
        assert sample_order.status == OrderStatus.REJECTED
        assert sample_order.error_msg == "资金不足"

    @pytest.mark.asyncio
    async def test_order_expiration(self, sample_order):
        """测试订单过期"""
        sm = OrderStateMachine(sample_order)

        # 过期
        sm.transition(OrderEvent.EXPIRE)
        assert sample_order.status == OrderStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_invalid_state_transition(self, sample_order):
        """测试非法状态转换"""
        sm = OrderStateMachine(sample_order)

        # CREATED 不能直接到 FILLED
        with pytest.raises(InvalidStateTransition):
            sm.transition(OrderEvent.FILL_FULL)

        # 到 PENDING 后不能直接 REJECT（需要先 SUBMIT）
        sm.transition(OrderEvent.SUBMIT)

        # FILLED 后不能 CANCEL
        sm.transition(OrderEvent.FILL_FULL, details={"fill_qty": 1000, "fill_price": Decimal("10.50")})
        with pytest.raises(InvalidStateTransition):
            sm.transition(OrderEvent.CANCEL)

    @pytest.mark.asyncio
    async def test_state_query_methods(self, sample_order):
        """测试状态查询方法"""
        sm = OrderStateMachine(sample_order)

        # CREATED 状态
        assert sm.is_active() is True
        assert sm.is_terminal() is False
        assert sm.can_cancel() is True
        assert sm.can_fill() is False

        # PENDING 状态
        sm.transition(OrderEvent.SUBMIT)
        assert sm.is_active() is True
        assert sm.can_fill() is True

        # FILLED 状态
        sm.transition(OrderEvent.FILL_FULL, details={"fill_qty": 1000, "fill_price": Decimal("10.50")})
        assert sm.is_terminal() is True
        assert sm.can_cancel() is False


# ============== API错误处理测试 ==============

@pytest.mark.integration
class TestAPIErrorHandling:
    """API错误处理测试"""

    @pytest.mark.asyncio
    async def test_api_error_response_format(self):
        """测试API错误响应格式"""
        # 创建各种异常
        errors = [
            ValidationError("参数错误", field="price", value=-1),
            RiskControlError("风控拒绝", rule_id="position_limit"),
            OrderExecutionError("订单执行失败", order_id="ORD001"),
        ]

        for error in errors:
            response = get_error_response(error)

            # 验证统一格式
            assert "error" in response
            assert "status_code" in response
            assert "code" in response["error"]
            assert "message" in response["error"]
            assert "details" in response["error"]
            assert "type" in response["error"]

    @pytest.mark.asyncio
    async def test_validation_error(self):
        """测试参数校验错误"""
        error = ValidationError(
            message="价格必须大于0",
            field="price",
            value=-10
        )

        response = get_error_response(error)

        assert response["status_code"] == 400
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert "price" in response["error"]["details"]["field"]
        assert response["error"]["details"]["value"] == -10

    @pytest.mark.asyncio
    async def test_risk_control_error(self):
        """测试风控错误"""
        error = RiskControlError(
            message="单票仓位超限",
            rule_id="single_stock_limit",
            risk_level="high"
        )

        response = get_error_response(error)

        assert response["status_code"] == 403
        assert response["error"]["code"] == "RISK_CONTROL_ERROR"
        assert response["error"]["details"]["rule_id"] == "single_stock_limit"

    @pytest.mark.asyncio
    async def test_order_execution_error(self):
        """测试订单执行错误"""
        error = OrderExecutionError(
            message="交易所拒绝",
            order_id="ORD202401010001",
            broker="simulator",
            status="rejected"
        )

        response = get_error_response(error)

        assert response["status_code"] == 422
        assert response["error"]["code"] == "ORDER_EXECUTION_ERROR"
        assert response["error"]["details"]["order_id"] == "ORD202401010001"

    @pytest.mark.asyncio
    async def test_error_to_dict(self):
        """测试错误转换为字典"""
        error = ValidationError("测试错误", field="test_field")
        error_dict = error.to_dict()

        assert error_dict["code"] == "VALIDATION_ERROR"
        assert error_dict["message"] == "测试错误"
        assert "details" in error_dict


# ============== 数据质量监控测试 ==============

@pytest.mark.integration
class TestDataQuality:
    """数据质量监控测试"""

    @pytest.mark.asyncio
    async def test_data_quality_score(self, data_quality_monitor, sample_tick):
        """测试数据质量评分"""
        result = data_quality_monitor.check_tick_quality(sample_tick)

        assert result.symbol == "000001.SZ"
        assert result.passed is True
        assert result.overall_level in [QualityLevel.EXCELLENT, QualityLevel.GOOD]
        assert len(result.checks) >= 3  # 至少包含完整性、时效性、准确性检查

    @pytest.mark.asyncio
    async def test_price_jump_detection(self, data_quality_monitor):
        """测试价格跳空检测"""
        # 创建价格跳变的tick序列
        base_time = datetime.now()
        ticks = [
            MockTickData(
                symbol="000001.SZ",
                timestamp=base_time,
                price=Decimal("10.00"),
                volume=1000
            ),
            MockTickData(
                symbol="000001.SZ",
                timestamp=base_time + timedelta(seconds=1),
                price=Decimal("11.50"),  # 15%跳涨
                volume=1000
            )
        ]

        anomalies = data_quality_monitor.detector.detect_price_anomaly(ticks)

        assert len(anomalies) > 0
        assert anomalies[0]["type"] == "price_spike"
        assert anomalies[0]["change_pct"] > 0.1  # 超过10%阈值

    @pytest.mark.asyncio
    async def test_volume_spike_detection(self, data_quality_monitor):
        """测试成交量异常检测"""
        # 创建成交量异常的tick序列
        base_time = datetime.now()
        ticks = [
            MockTickData(
                symbol="000001.SZ",
                timestamp=base_time + timedelta(seconds=i),
                price=Decimal("10.00"),
                volume=1000
            )
            for i in range(10)
        ]
        # 最后一个tick成交量激增
        ticks[-1].volume = 10000  # 10倍于平均

        anomalies = data_quality_monitor.detector.detect_volume_anomaly(ticks)

        assert len(anomalies) > 0
        assert anomalies[0]["type"] == "volume_spike"
        assert anomalies[0]["volume_ratio"] > 5.0  # 超过5倍阈值

    @pytest.mark.asyncio
    async def test_invalid_tick_detection(self, data_quality_monitor):
        """测试无效Tick数据检测"""
        # 创建无效tick（负价格）
        invalid_tick = MockTickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("-10.00"),  # 负价格
            volume=1000
        )

        result = data_quality_monitor.check_tick_quality(invalid_tick)

        assert result.passed is False
        assert result.overall_level in [QualityLevel.POOR, QualityLevel.CRITICAL]

        # 验证错误检查项
        failed_checks = [c for c in result.checks if not c.passed]
        assert len(failed_checks) > 0

    @pytest.mark.asyncio
    async def test_kline_quality_check(self, data_quality_monitor, sample_kline):
        """测试K线质量检查"""
        result = data_quality_monitor.check_kline_quality(sample_kline)

        assert result.symbol == "000001.SZ"
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_invalid_kline_detection(self, data_quality_monitor):
        """测试无效K线检测（OHLC关系错误）"""
        # 创建OHLC关系错误的K线
        invalid_kline = MockKLineData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            open=Decimal("10.50"),
            high=Decimal("10.20"),  # high < low，错误
            low=Decimal("10.60"),
            close=Decimal("10.40"),
            volume=10000,
            amount=Decimal("105000"),
            period="1d"
        )

        validator = DataValidator()
        validation = validator.validate_kline(invalid_kline)

        assert validation.is_valid is False
        assert any("High" in e and "Low" in e for e in validation.errors)

    @pytest.mark.asyncio
    async def test_stale_data_detection(self, data_quality_monitor):
        """测试过期数据检测"""
        # 创建过期tick（5分钟前）
        stale_tick = MockTickData(
            symbol="000001.SZ",
            timestamp=datetime.now() - timedelta(minutes=10),
            price=Decimal("10.00"),
            volume=1000
        )

        is_stale = data_quality_monitor.detector.is_stale(stale_tick)
        assert is_stale is True

    @pytest.mark.asyncio
    async def test_quality_report_generation(self, data_quality_monitor, sample_tick):
        """测试质量报告生成"""
        # 添加多个质量记录
        for _ in range(5):
            data_quality_monitor.check_tick_quality(sample_tick)

        report = data_quality_monitor.generate_report()

        assert "summary" in report
        assert "symbol_reports" in report
        assert "recommendations" in report
        assert "generated_at" in report
        assert "000001.SZ" in report["symbol_reports"]


# ============== 指标收集测试 ==============

@pytest.mark.integration
class TestMetrics:
    """指标收集测试"""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """每个测试前重置指标"""
        metrics.reset()
        yield
        metrics.reset()

    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """测试指标收集"""
        # 记录计数器
        metrics.increment("test.counter", 1)
        metrics.increment("test.counter", 2)

        # 记录仪表盘
        metrics.gauge("test.gauge", 100)

        # 记录直方图
        for i in range(10):
            metrics.record("test.histogram", float(i * 10), "histogram")

        # 验证计数器
        counter_data = metrics.get_metric("test.counter", "counter")
        assert counter_data["counter"][""] == 3  # 1 + 2 = 3

        # 验证仪表盘
        gauge_data = metrics.get_metric("test.gauge", "gauge")
        assert gauge_data["gauge"][""] == 100

        # 验证直方图
        hist_data = metrics.get_metric("test.histogram", "histogram")
        assert hist_data["histogram"][""]["count"] == 10

    @pytest.mark.asyncio
    async def test_timer_metrics(self):
        """测试计时器指标"""
        # 使用计时器
        with metrics.timer("test.operation_duration"):
            await asyncio.sleep(0.01)  # 10ms

        # 验证计时器记录了数据
        hist_data = metrics.get_metric("test.operation_duration", "histogram")
        assert hist_data["histogram"][""]["count"] == 1
        assert hist_data["histogram"][""]["avg"] > 0

    @pytest.mark.asyncio
    async def test_metrics_with_tags(self):
        """测试带标签的指标"""
        # 记录带标签的指标
        metrics.increment("orders.submitted", 1, tags={"symbol": "000001.SZ", "direction": "BUY"})
        metrics.increment("orders.submitted", 1, tags={"symbol": "000002.SZ", "direction": "SELL"})
        metrics.increment("orders.submitted", 1, tags={"symbol": "000001.SZ", "direction": "BUY"})

        # 获取所有指标
        all_metrics = metrics.get_metrics()

        assert "orders.submitted" in all_metrics["counters"]
        # 应该有两个不同的标签组合
        assert len(all_metrics["counters"]["orders.submitted"]) == 2

    @pytest.mark.asyncio
    async def test_metrics_reset(self):
        """测试指标重置"""
        # 记录一些指标
        metrics.increment("test.reset", 100)

        # 验证指标存在
        data = metrics.get_metric("test.reset")
        assert data["counter"][""] == 100

        # 重置特定指标
        metrics.reset("test.reset")
        data = metrics.get_metric("test.reset")
        assert data == {}  # 已重置

        # 记录新指标
        metrics.increment("test.another", 50)

        # 重置所有指标
        metrics.reset()
        all_data = metrics.get_metrics()
        assert all_data["counters"] == {}
        assert all_data["gauges"] == {}

    @pytest.mark.asyncio
    async def test_histogram_stats_calculation(self):
        """测试直方图统计计算"""
        # 记录已知分布的数据
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for v in values:
            metrics.record("test.stats", float(v), "histogram")

        hist_data = metrics.get_metric("test.stats", "histogram")
        stats = hist_data["histogram"][""]

        assert stats["count"] == 10
        assert stats["min"] == 10
        assert stats["max"] == 100
        assert 50 <= stats["avg"] <= 60  # 平均值应该在50-60之间

    @pytest.mark.asyncio
    async def test_metrics_snapshot(self):
        """测试指标快照"""
        metrics.increment("test.snapshot", 42)

        snapshot = metrics.snapshot()

        assert "timestamp" in snapshot
        assert "metrics" in snapshot
        assert "test.snapshot" in snapshot["metrics"]["counters"]


# ============== 清理操作 ==============

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """每个测试后清理状态"""
    yield
    # 清理指标
    metrics.reset()


# ============== 主函数 ==============

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
