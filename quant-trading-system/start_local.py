#!/usr/bin/env python3
"""
本地开发启动脚本
一键启动后端服务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.base import init_db, close_db
from src.scripts.init_db import init_data
from src.main import app
from src.common.logger import TradingLogger
import uvicorn

logger = TradingLogger(__name__)


async def setup():
    """初始化数据库"""
    logger.info("=" * 50)
    logger.info("启动本地开发环境")
    logger.info("=" * 50)

    try:
        # 初始化数据库表结构
        logger.info("初始化数据库...")
        await init_db()

        # 初始化默认数据
        logger.info("初始化默认数据...")
        await init_data()

        logger.info("初始化完成，启动服务...")
        return True

    except Exception as e:
        logger.error(f"初始化失败: {e}")
        return False


def main():
    """主入口"""
    # 先异步初始化数据库
    success = asyncio.run(setup())

    if not success:
        logger.error("服务启动失败")
        sys.exit(1)

    # 启动 uvicorn 服务
    logger.info("启动 Uvicorn 服务...")
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
