"""
日志管理模块 - 基于structlog的结构化日志

功能：
- 结构化JSON日志输出
- 支持业务上下文绑定（trace_id, user_id等）
- 动态日志级别调整
- OpenTelemetry追踪集成
- 敏感信息自动过滤

使用示例：
    from src.common.logger import StructuredLogger, set_log_level, get_logger

    # 创建结构化日志器
    logger = StructuredLogger("my_module")

    # 绑定业务上下文
    logger.bind(trace_id="abc123", user_id=1001)
    logger.info("用户操作", action="buy", symbol="000001.SZ")

    # 动态调整日志级别
    set_log_level("DEBUG")
"""

import sys
import json
import logging
import threading
from typing import Dict, Any, Optional, Union
from datetime import datetime
from contextvars import ContextVar

import structlog
from structlog.types import Processor, EventDict
from opentelemetry import trace

from .config import settings

# 上下文变量，用于存储当前请求的上下文信息
_log_context: ContextVar[Dict[str, Any]] = ContextVar('log_context', default={})


def add_trace_info(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """添加OpenTelemetry追踪信息到日志"""
    span = trace.get_current_span()
    if span.is_recording():
        event_dict["trace_id"] = format(span.get_span_context().trace_id, "032x")
        event_dict["span_id"] = format(span.get_span_context().span_id, "016x")
    return event_dict


def add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """添加时间戳"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def filter_secrets(
    logger: logging.Logger, method_name: str, event_dict: EventDict
) -> EventDict:
    """过滤敏感信息"""
    sensitive_fields = [
        "password",
        "token",
        "secret",
        "key",
        "authorization",
        "api_key",
        "access_key",
        "secret_key",
    ]

    for key in list(event_dict.keys()):
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_fields):
            event_dict[key] = "[FILTERED]"

    return event_dict


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "json",
) -> structlog.BoundLogger:
    """
    配置结构化日志

    Args:
        level: 日志级别
        log_file: 日志文件路径
        log_format: 日志格式 (json, console)

    Returns:
        structlog.BoundLogger: 配置好的日志记录器
    """
    # 配置基础日志
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )

    # 配置处理器
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)

    # 配置structlog处理器
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_timestamp,
        add_trace_info,
        filter_secrets,
        structlog.stdlib.ExtraAdder(),
    ]

    # 根据格式添加渲染器
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    # 配置structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        wrapper_class=structlog.stdlib.BoundLogger,
    )

    # 返回根日志记录器
    return structlog.get_logger()


# 全局日志级别锁
_log_level_lock = threading.Lock()


def set_log_level(level: Union[str, int]):
    """
    动态设置全局日志级别

    Args:
        level: 日志级别，可以是字符串 ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
               或 logging 模块的级别常量

    Example:
        set_log_level("DEBUG")  # 开启调试日志
        set_log_level(logging.WARNING)  # 只显示警告及以上
    """
    with _log_level_lock:
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)

        # 设置根日志记录器级别
        logging.getLogger().setLevel(level)

        # 设置structlog使用的日志记录器级别
        for logger_name in ['', 'src', 'src.common', 'src.core', 'src.strategy']:
            logging.getLogger(logger_name).setLevel(level)

        # 记录级别变更
        root_logger = structlog.get_logger()
        root_logger.info("log_level_changed", new_level=logging.getLevelName(level))


def get_log_level() -> str:
    """获取当前日志级别"""
    return logging.getLevelName(logging.getLogger().level)


class StructuredLogger:
    """
    结构化日志记录器

    提供业务上下文绑定、结构化JSON输出和动态日志级别支持。
    所有日志方法都支持额外的关键字参数，这些参数会被序列化为JSON字段。

    Example:
        logger = StructuredLogger("my_module")

        # 绑定上下文（会附加到后续所有日志）
        logger.bind(trace_id="abc123", user_id=1001)

        # 记录日志
        logger.info("操作成功", action="buy", symbol="000001.SZ", qty=100)

        # 取消绑定
        logger.unbind("trace_id")

        # 临时绑定（只影响单次日志）
        logger.info("单次日志", **{"extra_field": "value"})
    """

    def __init__(self, name: str):
        self._logger = structlog.get_logger(name)
        self._name = name
        self._context: Dict[str, Any] = {}
        self._context_lock = threading.Lock()

    def bind(self, **kwargs) -> 'StructuredLogger':
        """
        绑定业务上下文

        绑定的上下文会自动附加到后续所有日志记录中。
        常用上下文字段：trace_id, user_id, account_id, request_id, session_id

        Args:
            **kwargs: 要绑定的键值对

        Returns:
            self，支持链式调用
        """
        with self._context_lock:
            self._context.update(kwargs)
        return self

    def unbind(self, *keys) -> 'StructuredLogger':
        """
        移除绑定的上下文

        Args:
            *keys: 要移除的键名

        Returns:
            self，支持链式调用
        """
        with self._context_lock:
            for key in keys:
                self._context.pop(key, None)
        return self

    def clear_context(self) -> 'StructuredLogger':
        """清除所有绑定的上下文"""
        with self._context_lock:
            self._context.clear()
        return self

    def get_context(self) -> Dict[str, Any]:
        """获取当前绑定的上下文副本"""
        with self._context_lock:
            return self._context.copy()

    def _log(self, level: str, message: str, **kwargs):
        """
        内部日志记录方法

        合并绑定的上下文和临时参数，输出结构化JSON日志
        """
        with self._context_lock:
            context = self._context.copy()

        # 合并上下文和临时参数（临时参数优先级更高）
        log_data = {**context, **kwargs}

        # 添加时间戳（如果structlog没有添加）
        if "timestamp" not in log_data:
            log_data["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # 获取对应的日志方法
        log_method = getattr(self._logger, level.lower(), self._logger.info)

        # 记录日志
        log_method(message, **log_data)

    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._log("debug", message, **kwargs)

    def info(self, message: str, **kwargs):
        """信息日志"""
        self._log("info", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._log("warning", message, **kwargs)

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """
        错误日志

        Args:
            message: 错误消息
            error: 异常对象，会自动提取错误类型和消息
            **kwargs: 其他上下文信息
        """
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
        self._log("error", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._log("critical", message, **kwargs)

    def audit(self, action: str, user: str, resource: str, details: Optional[Dict[str, Any]] = None):
        """
        审计日志

        用于记录重要的业务操作，如交易执行、资金变动、配置变更等

        Args:
            action: 操作类型，如 "trade.execute", "config.update", "user.login"
            user: 操作用户标识
            resource: 被操作的资源
            details: 操作详情
        """
        log_data = {
            "audit_action": action,
            "audit_user": user,
            "audit_resource": resource,
            "log_type": "audit"
        }
        if details:
            log_data["audit_details"] = details
        self._log("info", "audit_event", **log_data)

    def metrics(self, metric_name: str, value: float, tags: Optional[Dict[str, Any]] = None):
        """
        指标日志

        用于记录可聚合的指标数据，便于后续分析和监控

        Args:
            metric_name: 指标名称
            value: 指标值
            tags: 指标标签
        """
        log_data = {
            "metric_name": metric_name,
            "metric_value": value,
            "log_type": "metric"
        }
        if tags:
            log_data["metric_tags"] = tags
        self._log("info", "metric_recorded", **log_data)


# 全局日志实例（向后兼容）
logger = setup_logging(
    level=settings.monitoring.log_level,
    log_file=settings.monitoring.log_file,
    log_format=settings.monitoring.log_format,
)


def get_logger(name: str) -> StructuredLogger:
    """
    获取结构化日志记录器

    Args:
        name: 日志记录器名称，通常使用模块名 __name__

    Returns:
        StructuredLogger: 结构化日志记录器实例

    Example:
        logger = get_logger(__name__)
        logger.info("服务启动", port=8080)
    """
    return StructuredLogger(name)


class TradingLogger:
    """量化交易专用日志记录器"""

    def __init__(self, name: str):
        self.logger = structlog.get_logger(name)

    def info(self, event: str, **kwargs):
        """信息日志"""
        self.logger.info(event, **kwargs)

    def warning(self, event: str, **kwargs):
        """警告日志"""
        self.logger.warning(event, **kwargs)

    def error(self, event: str, error: Optional[Exception] = None, **kwargs):
        """错误日志"""
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
        self.logger.error(event, **kwargs)

    def debug(self, event: str, **kwargs):
        """调试日志"""
        self.logger.debug(event, **kwargs)

    def critical(self, event: str, **kwargs):
        """严重错误日志"""
        self.logger.critical(event, **kwargs)

    def metrics(self, metric_name: str, value: float, tags: Optional[Dict[str, Any]] = None):
        """指标日志"""
        log_data = {"metric": metric_name, "value": value}
        if tags:
            log_data.update(tags)
        self.logger.info("metric_recorded", **log_data)

    def audit(self, action: str, user: str, resource: str, details: Optional[Dict[str, Any]] = None):
        """审计日志"""
        log_data = {
            "audit_action": action,
            "audit_user": user,
            "audit_resource": resource,
        }
        if details:
            log_data.update({"audit_details": details})
        self.logger.info("audit_event", **log_data)


# 模块特定日志记录器
data_logger = TradingLogger("data")
strategy_logger = TradingLogger("strategy")
risk_logger = TradingLogger("risk")
execution_logger = TradingLogger("execution")
monitoring_logger = TradingLogger("monitoring")