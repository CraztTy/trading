"""
订单流程测试
验证订单状态机和完整下单流程
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from src.models.base import AsyncSessionLocal, init_db
from src.models.account import Account
from src.models.order import Order
from src.models.enums import OrderDirection, OrderStatus, OrderType
from src.services.order_service import OrderService
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


async def test_order_flow():
    """测试完整订单流程"""
    async with AsyncSessionLocal() as session:
        try:
            service = OrderService(session)

            # 1. 获取测试账户
            result = await session.execute(
                select(Account).where(Account.account_no == "SIM001")
            )
            account = result.scalar_one_or_none()

            if not account:
                logger.error("测试账户不存在，请先运行 init_db")
                return False

            logger.info(f"测试账户: {account.account_no}, 可用资金: {account.available}")

            # 2. 创建买入订单
            logger.info("\n=== 测试1: 创建买入订单 ===")
            order = await service.create_order(
                account_id=account.id,
                symbol="600519.SH",
                direction=OrderDirection.BUY,
                qty=100,
                price=Decimal("1500.00"),
                order_type=OrderType.LIMIT,
                symbol_name="贵州茅台"
            )
            logger.info(f"订单创建: {order.order_id}, 状态: {order.status.value}")

            # 3. 提交订单
            success = await service.submit_order(order)
            logger.info(f"订单提交: {'成功' if success else '失败'}, 状态: {order.status.value}")
            logger.info(f"冻结资金后可用: {account.available}")

            # 4. 部分成交
            logger.info("\n=== 测试2: 部分成交 ===")
            success = await service.fill_order(order, 30, Decimal("1498.50"))
            logger.info(f"部分成交: {'成功' if success else '失败'}, 状态: {order.status.value}")
            logger.info(f"已成交: {order.filled_qty}/{order.qty}, 均价: {order.filled_avg_price}")

            # 5. 继续成交
            logger.info("\n=== 测试3: 继续成交 ===")
            success = await service.fill_order(order, 70, Decimal("1499.00"))
            logger.info(f"全部成交: {'成功' if success else '失败'}, 状态: {order.status.value}")
            logger.info(f"已成交: {order.filled_qty}/{order.qty}, 均价: {order.filled_avg_price}")

            await session.commit()

            # 6. 创建卖出订单并撤单
            logger.info("\n=== 测试4: 创建卖出订单并撤单 ===")
            sell_order = await service.create_order(
                account_id=account.id,
                symbol="600519.SH",
                direction=OrderDirection.SELL,
                qty=50,
                price=Decimal("1600.00"),
                order_type=OrderType.LIMIT
            )
            logger.info(f"卖出订单创建: {sell_order.order_id}")

            success = await service.submit_order(sell_order)
            logger.info(f"卖出订单提交: {'成功' if success else '失败'}")

            success = await service.cancel_order(sell_order)
            logger.info(f"卖出订单撤单: {'成功' if success else '失败'}, 状态: {sell_order.status.value}")

            await session.commit()

            # 7. 查询订单
            logger.info("\n=== 测试5: 查询订单 ===")
            orders = await service.get_account_orders(account.id)
            logger.info(f"账户订单总数: {len(orders)}")

            active_orders = await service.get_active_orders(account.id)
            logger.info(f"活跃订单数: {len(active_orders)}")

            await session.commit()

            logger.info("\n=== 所有测试通过! ===")
            return True

        except Exception as e:
            await session.rollback()
            logger.error(f"测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主入口"""
    logger.info("=" * 50)
    logger.info("订单状态机测试")
    logger.info("=" * 50)

    success = await test_order_flow()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
