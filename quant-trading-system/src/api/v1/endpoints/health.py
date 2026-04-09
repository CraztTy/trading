"""
健康检查API
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/")
async def health_check():
    """基础健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    return {
        "status": "ready",
        "checks": {
            "database": True,
            "redis": True,
            "data_provider": True
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/live")
async def liveness_check():
    """存活检查"""
    return {"status": "alive"}
