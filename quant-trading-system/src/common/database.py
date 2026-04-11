"""
数据库连接管理模块

提供异步数据库连接池、会话管理和依赖注入
"""

import asyncio
import platform
from typing import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase

from src.common.config import settings
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)

# Windows 需要设置事件循环策略
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# 命名约定（统一约束命名规范）
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """SQLAlchemy声明式基类"""

    metadata = MetaData(naming_convention=convention)

    def __repr__(self) -> str:
        columns = []
        for col in self.__table__.columns.keys():
            val = getattr(self, col)
            if val is not None:
                columns.append(f"{col}={val!r}")
        return f"<{self.__class__.__name__}({', '.join(columns)})>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            col: getattr(self, col)
            for col in self.__table__.columns.keys()
        }


# ============================================================================
# 数据库引擎和会话管理
# ============================================================================

class DatabaseManager:
    """数据库连接管理器（单例模式）"""

    _instance = None
    _engine: AsyncEngine | None = None
    _session_maker: async_sessionmaker | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def engine(self) -> AsyncEngine:
        """获取数据库引擎（懒加载）"""
        if self._engine is None:
            self._engine = create_async_engine(
                settings.database.url,
                echo=settings.app_debug,
                pool_size=settings.database.pool_size,
                max_overflow=settings.database.max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            logger.info(f"数据库引擎初始化完成: {settings.database.host}:{settings.database.port}")
        return self._engine

    @property
    def session_maker(self) -> async_sessionmaker:
        """获取会话工厂（懒加载）"""
        if self._session_maker is None:
            self._session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            logger.info("数据库会话工厂初始化完成")
        return self._session_maker

    async def close(self):
        """关闭数据库连接"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None
            logger.info("数据库连接已关闭")

    async def init_tables(self, drop_all: bool = False):
        """初始化数据库表"""
        async with self.engine.begin() as conn:
            if drop_all:
                logger.warning("正在删除所有表...")
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("正在创建所有表...")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库表初始化完成")


# 全局数据库管理器实例
db_manager = DatabaseManager()


# ============================================================================
# FastAPI依赖注入
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依赖注入用的数据库会话生成器

    使用方式:
        from fastapi import Depends
        from src.common.database import get_db

        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with db_manager.session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"数据库事务回滚: {e}")
            raise
        finally:
            await session.close()


# 兼容性导出（保持与原有代码兼容）
engine = property(lambda self: db_manager.engine)
AsyncSessionLocal = property(lambda self: db_manager.session_maker)


# ============================================================================
# 工具函数
# ============================================================================

async def init_db(drop_all: bool = False):
    """
    初始化数据库（创建所有表）

    Args:
        drop_all: 是否先删除所有表（开发环境使用）
    """
    if settings.app_env == "development" and drop_all:
        logger.warning("开发模式：重建所有表")
        await db_manager.init_tables(drop_all=True)
    else:
        await db_manager.init_tables(drop_all=False)


async def close_db():
    """关闭数据库连接"""
    await db_manager.close()


async def check_db_connection() -> bool:
    """检查数据库连接是否正常"""
    try:
        from sqlalchemy import text
        async with db_manager.session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            await result.scalar()
        logger.info("数据库连接检查通过")
        return True
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        return False
