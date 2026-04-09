#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import asyncio
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.common.config import settings
from src.common.logger import setup_logging

logger = setup_logging(__name__)


async def execute_sql_file(engine, filepath: Path):
    """执行SQL文件"""
    if not filepath.exists():
        logger.error(f"SQL文件不存在: {filepath}")
        return False

    try:
        async with engine.begin() as conn:
            # 读取SQL文件
            sql_content = filepath.read_text(encoding='utf-8')

            # 分割SQL语句
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

            # 执行每个语句
            for i, statement in enumerate(statements, 1):
                if statement:
                    logger.info(f"执行语句 {i}/{len(statements)}")
                    await conn.execute(text(statement))

            logger.info(f"成功执行SQL文件: {filepath.name}")
            return True

    except Exception as e:
        logger.error(f"执行SQL文件失败: {filepath.name}", error=e)
        return False


async def create_database():
    """创建数据库（如果不存在）"""
    try:
        # 使用无数据库的连接
        base_url = f"mysql+aiomysql://{settings.database.user}:{settings.database.password}@{settings.database.host}:{settings.database.port}/"
        engine = create_async_engine(base_url, echo=False)

        async with engine.begin() as conn:
            # 检查数据库是否存在
            result = await conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{settings.database.name}'")
            )
            db_exists = result.fetchone()

            if not db_exists:
                logger.info(f"创建数据库: {settings.database.name}")
                await conn.execute(text(f"CREATE DATABASE {settings.database.name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                logger.info(f"数据库创建成功: {settings.database.name}")
            else:
                logger.info(f"数据库已存在: {settings.database.name}")

        await engine.dispose()
        return True

    except Exception as e:
        logger.error("创建数据库失败", error=e)
        return False


async def create_tables():
    """创建表结构"""
    try:
        # 创建数据库引擎
        engine = create_async_engine(settings.database.url, echo=False)

        # 执行初始化SQL
        sql_dir = Path("scripts/sql")
        if not sql_dir.exists():
            logger.error(f"SQL目录不存在: {sql_dir}")
            return False

        # 按顺序执行SQL文件
        sql_files = [
            "00_schema.sql",      # 基础表结构
            "01_stock_info.sql",  # 股票信息表
            "02_kline.sql",       # K线表
            "03_sector.sql",      # 板块表
            "04_index_data.sql",  # 指数数据表
            "05_functions.sql",   # 存储函数
            "06_procedures.sql",  # 存储过程
            "07_triggers.sql",    # 触发器
            "08_views.sql",       # 视图
            "09_data.sql",        # 基础数据
            "10_indexes.sql",     # 索引
        ]

        success_count = 0
        for sql_file in sql_files:
            filepath = sql_dir / sql_file
            if filepath.exists():
                success = await execute_sql_file(engine, filepath)
                if success:
                    success_count += 1
            else:
                logger.warning(f"SQL文件不存在: {sql_file}")

        await engine.dispose()

        logger.info(f"表创建完成: {success_count}/{len(sql_files)} 个文件成功执行")
        return success_count > 0

    except Exception as e:
        logger.error("创建表结构失败", error=e)
        return False


async def create_test_data():
    """创建测试数据"""
    try:
        engine = create_async_engine(settings.database.url, echo=False)

        # 检查是否有测试数据
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) as count FROM stock_info")
            )
            count = result.scalar()

        if count > 0:
            logger.info(f"数据库中已有 {count} 条股票记录，跳过测试数据创建")
            await engine.dispose()
            return True

        # 执行测试数据SQL
        test_data_file = Path("scripts/sql/99_test_data.sql")
        if test_data_file.exists():
            success = await execute_sql_file(engine, test_data_file)
            if success:
                logger.info("测试数据创建成功")
            else:
                logger.warning("测试数据创建失败")
        else:
            logger.warning("测试数据SQL文件不存在")

        await engine.dispose()
        return True

    except Exception as e:
        logger.error("创建测试数据失败", error=e)
        return False


async def verify_database():
    """验证数据库状态"""
    try:
        engine = create_async_engine(settings.database.url, echo=False)

        async with engine.begin() as conn:
            # 检查核心表
            tables_to_check = [
                "stock_info",
                "daily_kline",
                "minute_kline",
                "sector_info",
                "sector_daily"
            ]

            for table in tables_to_check:
                result = await conn.execute(
                    text(f"SHOW TABLES LIKE '{table}'")
                )
                if not result.fetchone():
                    logger.error(f"表不存在: {table}")
                    await engine.dispose()
                    return False
                logger.info(f"表存在: {table}")

            # 检查表结构
            result = await conn.execute(
                text("""
                    SELECT
                        TABLE_NAME,
                        TABLE_ROWS,
                        DATA_LENGTH,
                        INDEX_LENGTH
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = :db_name
                    ORDER BY TABLE_NAME
                """),
                {"db_name": settings.database.name}
            )

            tables_info = result.fetchall()
            logger.info("数据库表信息:")
            for table in tables_info:
                logger.info(f"  {table.TABLE_NAME}: {table.TABLE_ROWS or 0} 行, {table.DATA_LENGTH or 0} 字节")

        await engine.dispose()
        logger.info("数据库验证通过")
        return True

    except Exception as e:
        logger.error("数据库验证失败", error=e)
        return False


async def main():
    """主函数"""
    logger.info("开始初始化数据库...")

    # 步骤1: 创建数据库
    logger.info("步骤1: 创建数据库")
    if not await create_database():
        logger.error("创建数据库失败，终止初始化")
        return False

    # 步骤2: 创建表结构
    logger.info("步骤2: 创建表结构")
    if not await create_tables():
        logger.error("创建表结构失败")
        # 继续执行，可能部分表已存在

    # 步骤3: 创建测试数据
    logger.info("步骤3: 创建测试数据")
    await create_test_data()

    # 步骤4: 验证数据库
    logger.info("步骤4: 验证数据库")
    if not await verify_database():
        logger.warning("数据库验证未通过")
        return False

    logger.info("数据库初始化完成")
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("用户中断初始化")
        exit(1)
    except Exception as e:
        logger.error("初始化过程发生异常", error=e)
        exit(1)