"""
API中间件模块

提供错误处理、请求日志、响应格式化等中间件功能
"""
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.v1.exceptions import TradingAPIException
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """错误处理中间件

    捕获所有未处理的异常，统一返回标准错误格式
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except TradingAPIException as exc:
            # 处理自定义API异常
            logger.warning(
                f"API异常: {exc.error_code}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_code": exc.error_code,
                    "message": exc.message
                }
            )
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.to_dict()
            )
        except Exception as exc:
            # 处理未预期的异常
            logger.error(
                f"未预期的异常: {exc}",
                extra={
                    "path": request.url.path,
                    "method": request.method
                },
                exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件

    记录所有API请求和响应信息
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = datetime.utcnow()

        # 记录请求开始
        logger.info(
            f"请求开始: {request.method} {request.url.path}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )

        try:
            response = await call_next(request)

            # 计算处理时间
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            # 记录请求完成
            logger.info(
                f"请求完成: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2)
                }
            )

            return response

        except Exception as exc:
            # 记录请求失败
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(
                f"请求失败: {request.method} {request.url.path} - {exc}",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc)
                }
            )
            raise


class ResponseFormatMiddleware(BaseHTTPMiddleware):
    """响应格式化中间件

    统一成功响应格式
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # 只处理JSON响应
        if (response.status_code < 400 and
            isinstance(response, JSONResponse) and
            not request.url.path.startswith("/docs") and
            not request.url.path.startswith("/redoc") and
            not request.url.path.startswith("/openapi")):

            content = response.body
            if content:
                import json
                try:
                    data = json.loads(content)
                    # 如果响应不是标准格式，包装为标准格式
                    if isinstance(data, dict) and "success" not in data:
                        formatted_data = {
                            "success": True,
                            "data": data,
                            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                        }
                        return JSONResponse(
                            status_code=response.status_code,
                            content=formatted_data
                        )
                except json.JSONDecodeError:
                    pass

        return response


def setup_exception_handlers(app):
    """设置全局异常处理器

    在FastAPI应用上注册自定义异常处理器
    """

    @app.exception_handler(TradingAPIException)
    async def trading_api_exception_handler(request: Request, exc: TradingAPIException):
        """处理TradingAPIException及其子类"""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """处理ValueError，转换为标准格式"""
        from src.api.v1.exceptions import ValidationError
        validation_error = ValidationError(message=str(exc))
        return JSONResponse(
            status_code=400,
            content=validation_error.to_dict()
        )

    logger.info("异常处理器已注册")
