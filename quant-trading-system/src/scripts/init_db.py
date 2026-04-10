"""
数据库初始化脚本
创建默认账户和策略
"""
import asyncio
from decimal import Decimal

from sqlalchemy import select

from src.models.base import AsyncSessionLocal, init_db
from src.models.account import Account, AccountType
from src.models.strategy import Strategy, RunMode
from src.models.enums import StrategyStatus
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


async def create_default_account(session) -> Account:
    """创建默认模拟账户"""
    # 检查是否已存在
    result = await session.execute(
        select(Account).where(Account.account_no == "SIM001")
    )
    account = result.scalar_one_or_none()

    if account:
        logger.info(f"默认账户已存在: {account.account_no}")
        return account

    # 创建新账户
    account = Account(
        account_no="SIM001",
        name="模拟账户",
        account_type=AccountType.SIMULATE,
        initial_capital=Decimal("1000000"),
    )
    session.add(account)
    await session.flush()

    logger.info(f"创建默认模拟账户: {account.account_no}, 初始资金: {account.initial_capital}")
    return account


async def create_sample_strategies(session, account_id: int):
    """创建示例策略"""
    sample_strategies = [
        {
            "strategy_id": "MA_CROSS",
            "name": "双均线突破",
            "description": "MA5/MA20金叉买入，死叉卖出",
            "category": "趋势",
            "style": "趋势跟踪",
            "params": {"fast_ma": 5, "slow_ma": 20},
            "max_position": Decimal("0.20"),
            "stop_loss": Decimal("0.03"),
            "take_profit": Decimal("0.06"),
        },
        {
            "strategy_id": "MACD_MOM",
            "name": "MACD动量",
            "description": "MACD柱状图转正买入，转负卖出",
            "category": "动量",
            "style": "动量策略",
            "params": {"fast": 12, "slow": 26, "signal": 9},
            "max_position": Decimal("0.15"),
            "stop_loss": Decimal("0.02"),
            "take_profit": Decimal("0.05"),
        },
        {
            "strategy_id": "BOLL_MEAN",
            "name": "布林带均值回归",
            "description": "触及下轨买入，触及上轨卖出",
            "category": "均值回归",
            "style": "统计套利",
            "params": {"period": 20, "std": 2},
            "max_position": Decimal("0.15"),
            "stop_loss": Decimal("0.02"),
            "take_profit": Decimal("0.04"),
        },
    ]

    for data in sample_strategies:
        result = await session.execute(
            select(Strategy).where(Strategy.strategy_id == data["strategy_id"])
        )
        if result.scalar_one_or_none():
            logger.info(f"策略已存在: {data['strategy_id']}")
            continue

        strategy = Strategy(
            strategy_id=data["strategy_id"],
            name=data["name"],
            description=data["description"],
            account_id=account_id,
            params=data["params"],
            run_mode=RunMode.SIMULATE,
        )
        strategy.category = data["category"]
        strategy.style = data["style"]
        strategy.max_position = data["max_position"]
        strategy.stop_loss = data["stop_loss"]
        strategy.take_profit = data["take_profit"]
        session.add(strategy)
        logger.info(f"创建策略: {data['strategy_id']} - {data['name']}")


async def init_data():
    """初始化数据"""
    async with AsyncSessionLocal() as session:
        try:
            # 创建默认账户
            account = await create_default_account(session)

            # 创建示例策略
            await create_sample_strategies(session, account.id)

            await session.commit()
            logger.info("数据库初始化完成")

        except Exception as e:
            await session.rollback()
            logger.error(f"数据库初始化失败: {e}")
            raise


async def main():
    """主入口"""
    logger.info("开始初始化数据库...")

    # 初始化表结构（开发环境）
    await init_db()

    # 初始化数据
    await init_data()

    logger.info("数据库初始化全部完成")


if __name__ == "__main__":
    asyncio.run(main())
