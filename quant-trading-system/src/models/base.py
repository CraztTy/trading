"""
数据库模型基类

从 common.database 导入基础组件，保持模型定义简洁
"""

from src.common.database import (
    Base,
    get_db,
    db_manager,
    init_db,
    close_db,
    check_db_connection,
)

# 兼容性导出 - 保持原有导入方式可用
# AsyncSessionLocal 现在通过 db_manager.session_maker 访问
__all__ = [
    "Base",
    "get_db",
    "db_manager",
    "init_db",
    "close_db",
    "check_db_connection",
]
