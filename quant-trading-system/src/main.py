"""
量化交易系统 - FastAPI主应用入口

L3级别量化交易系统主入口，集成三省六部架构与金融智能分析
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from src.api.v1.router import router as api_v1_router
from src.common.config import settings
from src.common.logger import logger
from src.market_data.manager import MarketDataManager
from src.market_data.data_service import data_service
from src.market_data.gateway.akshare import AKShareGateway


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    应用生命周期管理

    启动时:
    - 初始化数据库连接
    - 加载策略配置
    - 启动监控服务

    关闭时:
    - 关闭数据库连接
    - 保存运行状态
    - 清理资源
    """
    import os

    logger.info("=" * 60)
    logger.info(f"启动 {settings.app_name}")
    logger.info(f"环境: {settings.app_env}")
    logger.info(f"时间: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # 检测测试模式
    is_testing = os.environ.get("TESTING", "false").lower() == "true"

    # 启动初始化
    try:
        if not is_testing:
            # 初始化数据服务
            logger.info("正在初始化数据服务...")
            await data_service.initialize()

            # 初始化行情数据管理器
            logger.info("正在初始化行情数据管理器...")
            market_manager = MarketDataManager()

            # 注册 AKShare 网关
            akshare_gateway = AKShareGateway()
            market_manager.register_gateway("akshare", akshare_gateway)

            # 启动行情数据服务
            await market_manager.start()
            logger.info("行情数据管理器启动完成")
        else:
            logger.info("测试模式: 跳过行情数据管理器启动")

        logger.info("应用初始化完成")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        raise

    yield

    # 关闭清理
    logger.info("正在关闭应用...")
    try:
        if not is_testing:
            # 关闭行情数据管理器
            market_manager = MarketDataManager()
            await market_manager.stop()
            logger.info("行情数据管理器已关闭")

        # TODO: 关闭数据库连接
        # TODO: 保存运行状态
        logger.info("应用已安全关闭")
    except Exception as e:
        logger.error(f"关闭时出错: {e}")


# 创建FastAPI应用实例
app = FastAPI(
    title="Quant Trading System API",
    description="""
    L3级别量化交易系统API

    ## 功能模块

    ### 核心引擎 (三省六部)
    - **太子院**: 数据前置校验与分发
    - **中书省**: 策略信号生成
    - **门下省**: 风控审核与拦截
    - **尚书省**: 执行调度与资金清算
    - **六部**: 吏(策略)、户(资金)、礼(报表)、兵(交易)、刑(违规)、工(数据)

    ### 智能分析 (L3特性)
    - **基本面分析**: 财报解读、财务指标
    - **宏观分析**: 经济周期、政策方向
    - **行业分析**: 行业研究、产业链分析
    - **股票筛选**: 自然语言选股
    - **资讯搜索**: 金融新闻、公告查询

    ### 交易模式
    - **回测模式**: 历史数据回放、业绩报告
    - **实盘模式**: 实时监控、信号推送、自动交易

    ## 技术栈
    - FastAPI + Python 3.10+
    - 睿之兮三省六部架构
    - 东方财富金融数据API
    - WebSocket实时推送
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 注册中间件
# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    logger.error(f"请求异常: {request.url} - {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": str(exc) if settings.app_debug else "服务器内部错误",
            "timestamp": datetime.now().isoformat()
        }
    )


# 根路由
@app.get("/", tags=["根路由"])
async def root():
    """根路由 - API信息"""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "description": "L3级别量化交易系统",
        "docs": "/docs",
        "api_version": "v1",
        "api_base": "/api/v1",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


# 健康检查
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# 注册API路由
app.include_router(api_v1_router, prefix="/api")


# 主入口
if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=9000,
        reload=settings.app_debug,
        workers=1,
        log_level=settings.monitoring.log_level.lower(),
    )
