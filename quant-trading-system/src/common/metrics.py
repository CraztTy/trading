"""
指标收集模块 - 提供系统性能指标收集和监控

功能：
- 计数器（Counter）：累计值，如请求总数、错误数
- 仪表盘（Gauge）：瞬时值，如当前连接数、队列长度
- 直方图（Histogram）：分布统计，如请求延迟、响应时间
- 计时器（Timer）：自动记录代码块执行时间

使用示例：
    from src.common.metrics import metrics

    # 计数器
    metrics.record("signals.generated", 1)

    # 仪表盘
    metrics.record("queue.size", queue.qsize(), "gauge")

    # 计时器
    with metrics.timer("risk.audit_duration"):
        result = await audit_signal(signal)

    # 获取所有指标
    all_metrics = metrics.get_metrics()
"""

import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class HistogramStats:
    """直方图统计结果"""
    count: int = 0
    sum_val: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    avg: float = 0.0
    p50: float = 0.0  # 中位数
    p95: float = 0.0  # 95分位数
    p99: float = 0.0  # 99分位数


class Timer:
    """
    计时器上下文管理器

    用法:
        with metrics.timer("operation.duration"):
            do_something()

    支持嵌套和异常处理，即使发生异常也会记录已执行的时间
    """

    def __init__(self, collector: 'MetricsCollector', metric_name: str,
                 tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time: Optional[float] = None
        self.duration_ms: Optional[float] = None

    def __enter__(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            end_time = time.perf_counter()
            self.duration_ms = (end_time - self.start_time) * 1000
            self.collector.record(
                self.metric_name,
                self.duration_ms,
                "histogram",
                tags=self.tags
            )

    def elapsed_ms(self) -> Optional[float]:
        """获取已过去的时间（毫秒），仅在计时器运行中或结束后有效"""
        if self.duration_ms is not None:
            return self.duration_ms
        if self.start_time is not None:
            return (time.perf_counter() - self.start_time) * 1000
        return None


class MetricsCollector:
    """
    指标收集器（线程安全的单例）

    支持多线程环境下的指标收集，提供：
    - Counter: 单调递增的计数器
    - Gauge: 可增可减的仪表盘值
    - Histogram: 数值分布统计

    所有指标可以带标签（tags）进行多维度统计
    """

    _instance: Optional['MetricsCollector'] = None
    _lock = threading.Lock()

    def __new__(cls) -> 'MetricsCollector':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # 计数器: {metric_name: {tag_key: value}}
        self._counters: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # 仪表盘: {metric_name: {tag_key: value}}
        self._gauges: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # 直方图: {metric_name: {tag_key: [values]}}
        self._histograms: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

        # 保护指标存储的锁
        self._metrics_lock = threading.RLock()

        # 最大直方图样本数（防止内存无限增长）
        self._max_histogram_samples = 10000

    def _make_tag_key(self, tags: Optional[Dict[str, str]]) -> str:
        """将标签字典转换为排序后的字符串键"""
        if not tags:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(tags.items()))

    def record(self, metric_name: str, value: float,
               metric_type: str = "counter",
               tags: Optional[Dict[str, str]] = None):
        """
        记录指标

        Args:
            metric_name: 指标名称，建议使用点号分隔的命名空间
                         如: "signals.generated", "risk.audit_duration"
            value: 指标值
            metric_type: 指标类型 ("counter", "gauge", "histogram")
            tags: 可选的标签字典，用于多维度统计
                  如: {"strategy": "momentum", "symbol": "000001.SZ"}

        Examples:
            # 计数器 - 自动累加
            metrics.record("signals.generated", 1)
            metrics.record("signals.generated", 1, tags={"type": "buy"})

            # 仪表盘 - 覆盖当前值
            metrics.record("queue.size", 100, "gauge")

            # 直方图 - 记录分布
            metrics.record("api.latency", 45.2, "histogram", tags={"endpoint": "/trade"})
        """
        tag_key = self._make_tag_key(tags)

        with self._metrics_lock:
            if metric_type == "counter":
                self._counters[metric_name][tag_key] += value

            elif metric_type == "gauge":
                self._gauges[metric_name][tag_key] = value

            elif metric_type == "histogram":
                values = self._histograms[metric_name][tag_key]
                values.append(value)
                # 限制样本数量，防止内存无限增长
                if len(values) > self._max_histogram_samples:
                    # 保留最近的 75% 数据
                    self._histograms[metric_name][tag_key] = values[len(values)//4:]

            else:
                raise ValueError(f"Unknown metric type: {metric_type}")

    def increment(self, metric_name: str, value: float = 1.0,
                  tags: Optional[Dict[str, str]] = None):
        """
        计数器递增的便捷方法

        Args:
            metric_name: 指标名称
            value: 递增值，默认为1
            tags: 可选的标签
        """
        self.record(metric_name, value, "counter", tags)

    def decrement(self, metric_name: str, value: float = 1.0,
                  tags: Optional[Dict[str, str]] = None):
        """
        计数器递减的便捷方法（用于gauge类型更合适）

        Args:
            metric_name: 指标名称
            value: 递减值，默认为1
            tags: 可选的标签
        """
        self.record(metric_name, -value, "counter", tags)

    def gauge(self, metric_name: str, value: float,
              tags: Optional[Dict[str, str]] = None):
        """
        设置仪表盘值的便捷方法

        Args:
            metric_name: 指标名称
            value: 当前值
            tags: 可选的标签
        """
        self.record(metric_name, value, "gauge", tags)

    def timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> Timer:
        """
        创建计时器上下文管理器

        Args:
            metric_name: 指标名称，建议以 _duration 或 _latency 结尾
            tags: 可选的标签

        Returns:
            Timer: 计时器上下文管理器

        Example:
            with metrics.timer("risk.audit_duration"):
                result = await audit_signal(signal)

            with metrics.timer("db.query_latency", tags={"table": "orders"}):
                results = await db.execute(query)
        """
        return Timer(self, metric_name, tags)

    def _calculate_histogram_stats(self, values: List[float]) -> HistogramStats:
        """计算直方图统计值"""
        if not values:
            return HistogramStats()

        sorted_values = sorted(values)
        count = len(sorted_values)
        sum_val = sum(sorted_values)
        avg = sum_val / count

        def percentile(p: float) -> float:
            """计算百分位数"""
            if not sorted_values:
                return 0.0
            k = (len(sorted_values) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(sorted_values) else f
            if f == c:
                return sorted_values[f]
            return sorted_values[f] * (c - k) + sorted_values[c] * (k - f)

        return HistogramStats(
            count=count,
            sum_val=sum_val,
            min_val=sorted_values[0],
            max_val=sorted_values[-1],
            avg=avg,
            p50=percentile(50),
            p95=percentile(95),
            p99=percentile(99)
        )

    def get_metric(self, metric_name: str, metric_type: Optional[str] = None) -> Dict[str, Any]:
        """
        获取指定指标的当前值

        Args:
            metric_name: 指标名称
            metric_type: 可选的指标类型过滤

        Returns:
            指标值的字典，包含所有标签维度的数据
        """
        result: Dict[str, Any] = {}

        with self._metrics_lock:
            # 检查计数器
            if metric_name in self._counters and metric_type in (None, "counter"):
                result["counter"] = dict(self._counters[metric_name])

            # 检查仪表盘
            if metric_name in self._gauges and metric_type in (None, "gauge"):
                result["gauge"] = dict(self._gauges[metric_name])

            # 检查直方图
            if metric_name in self._histograms and metric_type in (None, "histogram"):
                histogram_data = {}
                for tag_key, values in self._histograms[metric_name].items():
                    stats = self._calculate_histogram_stats(values)
                    histogram_data[tag_key] = {
                        "count": stats.count,
                        "sum": stats.sum_val,
                        "avg": round(stats.avg, 3),
                        "min": round(stats.min_val, 3),
                        "max": round(stats.max_val, 3),
                        "p50": round(stats.p50, 3),
                        "p95": round(stats.p95, 3),
                        "p99": round(stats.p99, 3),
                    }
                result["histogram"] = histogram_data

        return result

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取所有指标的汇总数据

        Returns:
            包含所有指标的字典，格式如下:
            {
                "counters": {"metric_name": {"tag_key": value, ...}, ...},
                "gauges": {"metric_name": {"tag_key": value, ...}, ...},
                "histograms": {"metric_name": {"tag_key": stats_dict, ...}, ...}
            }
        """
        with self._metrics_lock:
            return {
                "counters": {
                    name: dict(values)
                    for name, values in self._counters.items()
                },
                "gauges": {
                    name: dict(values)
                    for name, values in self._gauges.items()
                },
                "histograms": {
                    name: {
                        tag_key: {
                            "count": len(vals),
                            "sum": sum(vals),
                            "avg": round(sum(vals) / len(vals), 3) if vals else 0,
                            "min": round(min(vals), 3) if vals else 0,
                            "max": round(max(vals), 3) if vals else 0,
                        }
                        for tag_key, vals in tag_values.items()
                    }
                    for name, tag_values in self._histograms.items()
                }
            }

    def get_metric_names(self) -> Dict[str, List[str]]:
        """
        获取所有注册的指标名称

        Returns:
            {"counters": [...], "gauges": [...], "histograms": [...]}
        """
        with self._metrics_lock:
            return {
                "counters": list(self._counters.keys()),
                "gauges": list(self._gauges.keys()),
                "histograms": list(self._histograms.keys())
            }

    def reset(self, metric_name: Optional[str] = None):
        """
        重置指标

        Args:
            metric_name: 要重置的指标名称，如果为None则重置所有指标
        """
        with self._metrics_lock:
            if metric_name is None:
                self._counters.clear()
                self._gauges.clear()
                self._histograms.clear()
            else:
                self._counters.pop(metric_name, None)
                self._gauges.pop(metric_name, None)
                self._histograms.pop(metric_name, None)

    def snapshot(self) -> Dict[str, Any]:
        """
        创建指标快照（用于导出或持久化）

        Returns:
            包含时间戳和所有指标数据的字典
        """
        import time
        return {
            "timestamp": time.time(),
            "metrics": self.get_metrics()
        }


# 全局指标收集器实例
metrics = MetricsCollector()


# 便捷函数，用于快速记录常见指标
def record_signal_generated(strategy_type: str = "", symbol: str = ""):
    """记录信号生成指标"""
    tags = {}
    if strategy_type:
        tags["strategy"] = strategy_type
    if symbol:
        tags["symbol"] = symbol
    metrics.increment("signals.generated", tags=tags if tags else None)


def record_signal_deduplicated(strategy_type: str = ""):
    """记录信号去重指标"""
    tags = {"strategy": strategy_type} if strategy_type else None
    metrics.increment("signals.deduplicated", tags=tags)


def record_risk_audit(duration_ms: float, approved: bool):
    """记录风控审核指标"""
    metrics.record("risk.audit_duration", duration_ms, "histogram",
                   tags={"result": "approved" if approved else "rejected"})
    if approved:
        metrics.increment("risk.approved")
    else:
        metrics.increment("risk.rejected")


def record_order_submitted(order_type: str = ""):
    """记录订单提交指标"""
    tags = {"type": order_type} if order_type else None
    metrics.increment("orders.submitted", tags=tags)


def record_order_executed(order_type: str = ""):
    """记录订单执行指标"""
    tags = {"type": order_type} if order_type else None
    metrics.increment("orders.executed", tags=tags)


def record_order_cancelled(reason: str = ""):
    """记录订单取消指标"""
    tags = {"reason": reason} if reason else None
    metrics.increment("orders.cancelled", tags=tags)


def record_data_quality_score(symbol: str, score: float):
    """记录数据质量评分指标"""
    metrics.gauge("data.quality_score", score, tags={"symbol": symbol})


def record_data_validation_result(data_type: str, is_valid: bool):
    """记录数据校验结果指标"""
    metrics.increment(
        "data.validation",
        tags={"type": data_type, "result": "valid" if is_valid else "invalid"}
    )
