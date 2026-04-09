"""
异常定义模块 - 量化交易系统专用异常类
"""

from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
import json


@dataclass
class ErrorDetail:
    """错误详情"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class TradingException(Exception):
    """量化交易系统基础异常"""

    def __init__(
        self,
        message: str,
        code: str = "TRADING_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }

    def __str__(self) -> str:
        """字符串表示"""
        base = f"{self.code}: {self.message}"
        if self.details:
            return f"{base} | Details: {json.dumps(self.details, ensure_ascii=False)}"
        return base


class ValidationError(TradingException):
    """数据验证错误"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = value

        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details,
        )


class DataSourceError(TradingException):
    """数据源错误"""

    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        url: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if source is not None:
            details["source"] = source
        if url is not None:
            details["url"] = url

        super().__init__(
            message=message,
            code="DATA_SOURCE_ERROR",
            details=details,
        )


class DatabaseError(TradingException):
    """数据库错误"""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if operation is not None:
            details["operation"] = operation
        if table is not None:
            details["table"] = table

        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            details=details,
        )


class StrategyError(TradingException):
    """策略错误"""

    def __init__(
        self,
        message: str,
        strategy_id: Optional[str] = None,
        signal: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if strategy_id is not None:
            details["strategy_id"] = strategy_id
        if signal is not None:
            details["signal"] = signal

        super().__init__(
            message=message,
            code="STRATEGY_ERROR",
            details=details,
        )


class RiskControlError(TradingException):
    """风控错误"""

    def __init__(
        self,
        message: str,
        rule_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if rule_id is not None:
            details["rule_id"] = rule_id
        if risk_level is not None:
            details["risk_level"] = risk_level

        super().__init__(
            message=message,
            code="RISK_CONTROL_ERROR",
            details=details,
        )


class OrderExecutionError(TradingException):
    """订单执行错误"""

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        broker: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if order_id is not None:
            details["order_id"] = order_id
        if broker is not None:
            details["broker"] = broker
        if status is not None:
            details["status"] = status

        super().__init__(
            message=message,
            code="ORDER_EXECUTION_ERROR",
            details=details,
        )


class AuthenticationError(TradingException):
    """认证错误"""

    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        token_type: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if user_id is not None:
            details["user_id"] = user_id
        if token_type is not None:
            details["token_type"] = token_type

        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(TradingException):
    """授权错误"""

    def __init__(
        self,
        message: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if user_id is not None:
            details["user_id"] = user_id
        if resource is not None:
            details["resource"] = resource
        if action is not None:
            details["action"] = action

        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            details=details,
        )


class RateLimitError(TradingException):
    """速率限制错误"""

    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        remaining: Optional[int] = None,
        reset_time: Optional[int] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if limit is not None:
            details["limit"] = limit
        if remaining is not None:
            details["remaining"] = remaining
        if reset_time is not None:
            details["reset_time"] = reset_time

        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            details=details,
        )


class CircuitBreakerError(TradingException):
    """熔断器错误"""

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        state: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if service is not None:
            details["service"] = service
        if state is not None:
            details["state"] = state

        super().__init__(
            message=message,
            code="CIRCUIT_BREAKER_ERROR",
            details=details,
        )


class ConfigurationError(TradingException):
    """配置错误"""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if config_key is not None:
            details["config_key"] = config_key
        if config_value is not None:
            details["config_value"] = config_value

        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details=details,
        )


class BusinessLogicError(TradingException):
    """业务逻辑错误"""

    def __init__(
        self,
        message: str,
        business_rule: Optional[str] = None,
        entity_id: Optional[str] = None,
        **kwargs,
    ):
        details = kwargs.get("details", {})
        if business_rule is not None:
            details["business_rule"] = business_rule
        if entity_id is not None:
            details["entity_id"] = entity_id

        super().__init__(
            message=message,
            code="BUSINESS_LOGIC_ERROR",
            details=details,
        )


# 错误码映射表
ERROR_CODES = {
    "VALIDATION_ERROR": {"http_status": 400, "description": "请求数据验证失败"},
    "AUTHENTICATION_ERROR": {"http_status": 401, "description": "认证失败"},
    "AUTHORIZATION_ERROR": {"http_status": 403, "description": "权限不足"},
    "DATA_SOURCE_ERROR": {"http_status": 502, "description": "数据源服务异常"},
    "DATABASE_ERROR": {"http_status": 500, "description": "数据库操作异常"},
    "STRATEGY_ERROR": {"http_status": 422, "description": "策略执行错误"},
    "RISK_CONTROL_ERROR": {"http_status": 403, "description": "风控规则触发"},
    "ORDER_EXECUTION_ERROR": {"http_status": 422, "description": "订单执行失败"},
    "RATE_LIMIT_ERROR": {"http_status": 429, "description": "请求频率超限"},
    "CIRCUIT_BREAKER_ERROR": {"http_status": 503, "description": "服务熔断中"},
    "CONFIGURATION_ERROR": {"http_status": 500, "description": "配置错误"},
    "BUSINESS_LOGIC_ERROR": {"http_status": 422, "description": "业务逻辑错误"},
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