"""
数据库基础配置
SQLAlchemy 2.0 + 异步支持
"""

import asyncio
import platform
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

from src.common.config import settings
from src.common.logger import TradingLogger

# Windows 需要设置事件循环策略
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = TradingLogger(__name__)


# 命名约定
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """声明式基类"""
    metadata = MetaData(naming_convention=convention)

    def __repr__(self) -> str:
        columns = []
        for col in self.__table__.columns.keys():
            val = getattr(self, col)
            if val is not None:
                columns.append(f"{col}={val!r}")
        return f"<{self.__class__.__name__}({', '.join(columns)})>"


# 异步数据库引擎配置
# 使用 psycopg 驱动（支持 Python 3.11+）
engine = create_async_engine(
    settings.database.url,
    echo=settings.app_debug,  # 调试模式打印SQL
    pool_size=10,             # 连接池大小
    max_overflow=20,          # 最大溢出连接
    pool_pre_ping=True,       # 连接前ping检测
    pool_recycle=3600,        # 连接回收时间（秒）
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,   # 提交后不过期，避免懒加载问题
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依赖注入用的数据库会话生成器

    使用方式:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库事务回滚: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        # 生产环境不要这样做，应该用Alembic迁移
        # 开发环境方便快速重建
        if settings.app_env == "development":
            logger.warning("开发模式：重建所有表")
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库初始化完成")


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
    logger.info("数据库连接已关闭")
