"""
数据库初始化脚本

创建所有表并初始化超级用户
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from src.common.database import init_db, close_db, db_manager
from src.common.config import settings
from src.common.logger import logger
from src.models.user import User
from src.models.signal_log import SignalLog
from src.models.audit_log import AuditLog
from src.models.data_quality_log import DataQualityLog
from src.models.backtest_task import BacktestTask
from src.models.strategy_version import StrategyVersion
from src.models.strategy_backtest import StrategyBacktest
from src.common.auth import get_password_hash


async def create_superuser():
    """创建超级用户（如果不存在）"""
    async with db_manager.session_maker() as session:
        # 检查是否已存在超级用户
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.info("超级用户 'admin' 已存在，跳过创建")
            return

        # 创建超级用户
        superuser = User(
            username="admin",
            email="admin@quantpro.com",
            hashed_password=get_password_hash("Admin@123456"),
            nickname="系统管理员",
            is_active=True,
            is_superuser=True,
            is_verified=True,
        )

        session.add(superuser)
        await session.commit()
        logger.info("超级用户 'admin' 创建成功")
        logger.info("默认密码: Admin@123456")
        logger.info("请登录后立即修改密码！")


async def create_demo_user():
    """创建演示用户（可选）"""
    async with db_manager.session_maker() as session:
        # 检查是否已存在演示用户
        result = await session.execute(
            select(User).where(User.username == "demo")
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.info("演示用户 'demo' 已存在，跳过创建")
            return

        # 创建演示用户
        demo_user = User(
            username="demo",
            email="demo@quantpro.com",
            hashed_password=get_password_hash("Demo@123456"),
            nickname="演示用户",
            is_active=True,
            is_superuser=False,
            is_verified=True,
        )

        session.add(demo_user)
        await session.commit()
        logger.info("演示用户 'demo' 创建成功")
        logger.info("用户名: demo")
        logger.info("密码: Demo@123456")


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始初始化数据库")
    logger.info("=" * 60)

    try:
        # 初始化数据库（创建所有表）
        logger.info("正在创建数据库表...")
        await init_db()
        logger.info("数据库表创建完成")

        # 创建超级用户
        logger.info("正在创建超级用户...")
        await create_superuser()

        # 创建演示用户（仅在开发环境）
        if settings.app_env == "development":
            logger.info("正在创建演示用户...")
            await create_demo_user()

        logger.info("=" * 60)
        logger.info("数据库初始化完成")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
