"""
API模块

提供RESTful API和WebSocket接口
"""

from .v1.router import router as v1_router

__all__ = ['v1_router']
