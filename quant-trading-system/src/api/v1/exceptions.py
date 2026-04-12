"""
API异常定义模块

统一API错误响应格式，提供结构化的异常类
"""
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class TradingAPIException(Exception):
    """API异常基类"""

    def __init__(
        self,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 400
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": False,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }


class OrderException(TradingAPIException):
    """订单相关异常基类"""
    pass


class InsufficientFundsError(OrderException):
    """资金不足错误"""

    def __init__(self, required: Decimal, available: Decimal):
        super().__init__(
            error_code="ORDER_INSUFFICIENT_FUNDS",
            message=f"Insufficient funds. Required: {required}, Available: {available}",
            details={"required": float(required), "available": float(available)},
            status_code=400
        )


class RiskCheckFailedError(OrderException):
    """风控检查失败错误"""

    def __init__(self, rule_code: str, reason: str):
        super().__init__(
            error_code="RISK_CHECK_FAILED",
            message=f"Risk check failed: {reason}",
            details={"rule_code": rule_code, "reason": reason},
            status_code=403
        )


class OrderNotFoundError(OrderException):
    """订单不存在错误"""

    def __init__(self, order_id: str):
        super().__init__(
            error_code="ORDER_NOT_FOUND",
            message=f"Order not found: {order_id}",
            details={"order_id": order_id},
            status_code=404
        )


class InvalidOrderStateError(OrderException):
    """订单状态无效错误"""

    def __init__(self, order_id: str, current_status: str, expected_status: str):
        super().__init__(
            error_code="INVALID_ORDER_STATE",
            message=f"Order {order_id} is in {current_status} status, expected {expected_status}",
            details={
                "order_id": order_id,
                "current_status": current_status,
                "expected_status": expected_status
            },
            status_code=400
        )


class ValidationError(TradingAPIException):
    """参数校验错误"""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            details=details,
            status_code=400
        )


class NotFoundError(TradingAPIException):
    """资源不存在错误"""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            error_code="NOT_FOUND",
            message=f"{resource_type} not found: {resource_id}",
            details={"resource_type": resource_type, "resource_id": resource_id},
            status_code=404
        )


class AccountNotFoundError(NotFoundError):
    """账户不存在错误"""

    def __init__(self, account_id: int):
        super().__init__("Account", str(account_id))
        self.error_code = "ACCOUNT_NOT_FOUND"
        self.message = f"Account not found: {account_id}"
        self.details = {"account_id": account_id}


class InvalidAmountError(ValidationError):
    """金额无效错误"""

    def __init__(self, amount: Any, reason: str = ""):
        message = f"Invalid amount: {amount}"
        if reason:
            message = f"{message}. {reason}"
        super().__init__(
            message=message,
            field="amount",
            value=str(amount) if amount is not None else None
        )
        self.error_code = "INVALID_AMOUNT"


class FlowTypeError(ValidationError):
    """流水类型错误"""

    def __init__(self, flow_type: str):
        super().__init__(
            message=f"Invalid flow type: {flow_type}",
            field="flow_type",
            value=flow_type
        )
        self.error_code = "INVALID_FLOW_TYPE"


class BusinessLogicError(TradingAPIException):
    """业务逻辑错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="BUSINESS_LOGIC_ERROR",
            message=message,
            details=details,
            status_code=422
        )


class AuthenticationError(TradingAPIException):
    """认证错误"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            error_code="AUTHENTICATION_ERROR",
            message=message,
            status_code=401
        )


class AuthorizationError(TradingAPIException):
    """授权错误"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            error_code="AUTHORIZATION_ERROR",
            message=message,
            status_code=403
        )


class RateLimitError(TradingAPIException):
    """速率限制错误"""

    def __init__(self, limit: int, remaining: int, reset_time: int):
        super().__init__(
            error_code="RATE_LIMIT_ERROR",
            message=f"Rate limit exceeded. Limit: {limit}, Remaining: {remaining}",
            details={
                "limit": limit,
                "remaining": remaining,
                "reset_time": reset_time
            },
            status_code=429
        )


# 错误码到HTTP状态码的映射
ERROR_CODE_MAPPING = {
    "ORDER_INSUFFICIENT_FUNDS": 400,
    "RISK_CHECK_FAILED": 403,
    "ORDER_NOT_FOUND": 404,
    "INVALID_ORDER_STATE": 400,
    "VALIDATION_ERROR": 400,
    "NOT_FOUND": 404,
    "ACCOUNT_NOT_FOUND": 404,
    "INVALID_AMOUNT": 400,
    "INVALID_FLOW_TYPE": 400,
    "BUSINESS_LOGIC_ERROR": 422,
    "AUTHENTICATION_ERROR": 401,
    "AUTHORIZATION_ERROR": 403,
    "RATE_LIMIT_ERROR": 429,
}
