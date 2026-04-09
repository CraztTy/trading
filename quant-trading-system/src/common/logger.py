"""
日志管理模块 - 基于structlog的结构化日志
"""

import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

import structlog
from structlog.types import Processor, EventDict
from opentelemetry import trace

from .config import settings


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


# 全局日志实例
logger = setup_logging(
    level=settings.monitoring.log_level,
    log_file=settings.monitoring.log_file,
    log_format=settings.monitoring.log_format,
)


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