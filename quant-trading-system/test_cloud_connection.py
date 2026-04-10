#!/usr/bin/env python3
"""
测试云服务器连接
验证 PostgreSQL 和 Redis 是否可连接
"""
import asyncio
import sys
import platform
from pathlib import Path

# Windows 需要设置事件循环策略
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.common.config import settings
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


async def test_postgres():
    """测试 PostgreSQL 连接"""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        engine = create_async_engine(
            settings.database.url,
            echo=False,
            pool_size=1,
            max_overflow=0,
        )

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✓ PostgreSQL 连接成功")
            logger.info(f"  地址: {settings.database.host}:{settings.database.port}")
            logger.info(f"  数据库: {settings.database.name}")
            logger.info(f"  版本: {version}")

        await engine.dispose()
        return True

    except Exception as e:
        logger.error(f"✗ PostgreSQL 连接失败: {e}")
        logger.error(f"  地址: {settings.database.host}:{settings.database.port}")
        return False


async def test_redis():
    """测试 Redis 连接"""
    try:
        import redis.asyncio as redis

        client = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            password=settings.redis.password,
            db=settings.redis.db,
            socket_connect_timeout=5,
            decode_responses=True,
        )

        pong = await client.ping()
        if pong:
            info = await client.info()
            logger.info(f"✓ Redis 连接成功")
            logger.info(f"  地址: {settings.redis.host}:{settings.redis.port}")
            logger.info(f"  版本: {info.get('redis_version', 'unknown')}")

        await client.close()
        return True

    except Exception as e:
        logger.error(f"✗ Redis 连接失败: {e}")
        logger.error(f"  地址: {settings.redis.host}:{settings.redis.port}")
        return False


async def main():
    """主入口"""
    logger.info("=" * 50)
    logger.info("测试云服务器连接")
    logger.info("=" * 50)

    pg_ok = await test_postgres()
    redis_ok = await test_redis()

    logger.info("=" * 50)
    if pg_ok and redis_ok:
        logger.info("✓ 所有连接测试通过")
        return 0
    else:
        logger.error("✗ 部分连接测试失败")
        if not pg_ok:
            logger.error("  - PostgreSQL 连接有问题")
        if not redis_ok:
            logger.error("  - Redis 连接有问题")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
