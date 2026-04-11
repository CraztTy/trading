"""
实时监控API

提供交易监控相关的WebSocket和HTTP接口
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import get_db
from src.models.order import Order
from src.models.enums import OrderStatus
from src.services.order_service import OrderService
from src.services.account_service import AccountService
from src.strategy.manager import strategy_manager
from src.common.logger import TradingLogger
from src.market_data.manager import MarketDataManager

logger = TradingLogger(__name__)
router = APIRouter()


class MonitoringManager:
    """
    监控管理器

    管理WebSocket连接和实时数据分发
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._running = False
        self._broadcast_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        """接受新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"监控连接已建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        self.active_connections.discard(websocket)
        logger.info(f"监控连接已断开，当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: Dict):
        """广播消息到所有连接"""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")


# 全局监控管理器实例
monitoring_manager = MonitoringManager()


@router.websocket("/ws")
async def monitoring_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
):
    """
    实时监控WebSocket

    提供实时数据流：
    - 订单状态更新
    - 持仓变化
    - 策略信号
    - 风控告警
    """
    await monitoring_manager.connect(websocket)

    try:
        # 发送初始连接成功消息
        await websocket.send_json({
            "type": "connected",
            "message": "监控连接已建立",
            "timestamp": datetime.now().isoformat()
        })

        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "subscribe":
                # 处理订阅请求
                symbols = data.get("symbols", [])
                await websocket.send_json({
                    "type": "subscribed",
                    "symbols": symbols
                })

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

            elif action == "get_portfolio":
                # 获取组合信息
                account_id = data.get("account_id", 1)
                portfolio = await get_portfolio_summary(db, account_id)
                await websocket.send_json({
                    "type": "portfolio_update",
                    "data": portfolio
                })

            elif action == "get_positions":
                # 获取持仓列表
                account_id = data.get("account_id", 1)
                positions = await get_positions_data(db, account_id)
                await websocket.send_json({
                    "type": "positions_update",
                    "data": positions
                })

            elif action == "get_active_orders":
                # 获取活跃订单
                account_id = data.get("account_id", 1)
                orders = await get_active_orders_data(db, account_id)
                await websocket.send_json({
                    "type": "orders_update",
                    "data": orders
                })

            elif action == "get_strategies":
                # 获取策略状态
                strategies = get_strategies_status()
                await websocket.send_json({
                    "type": "strategies_update",
                    "data": strategies
                })

    except WebSocketDisconnect:
        monitoring_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        monitoring_manager.disconnect(websocket)


async def get_portfolio_summary(db: AsyncSession, account_id: int) -> Dict:
    """获取组合摘要"""
    try:
        account_service = AccountService(db)
        account = await account_service.get_account(account_id)

        if not account:
            return {
                "total_value": 0,
                "cash": 0,
                "position_value": 0,
                "daily_pnl": 0,
                "daily_return": 0
            }

        return {
            "total_value": float(account.total_equity),
            "cash": float(account.available),
            "position_value": float(account.market_value),
            "daily_pnl": float(account.unrealized_pnl),
            "daily_return": float(account.total_return_pct) * 100
        }
    except Exception as e:
        logger.error(f"获取组合摘要失败: {e}")
        return {
            "total_value": 0,
            "cash": 0,
            "position_value": 0,
            "daily_pnl": 0,
            "daily_return": 0
        }


async def get_positions_data(db: AsyncSession, account_id: int) -> List[Dict]:
    """获取持仓数据"""
    try:
        account_service = AccountService(db)
        positions = await account_service.get_positions(account_id)

        result = []
        for pos in positions:
            # 计算盈亏
            pnl_pct = 0
            if pos.avg_price and pos.avg_price > 0:
                pnl_pct = ((pos.current_price - pos.avg_price) / pos.avg_price) * 100

            result.append({
                "symbol": pos.symbol,
                "name": pos.symbol_name or pos.symbol,
                "qty": pos.qty,
                "cost": float(pos.avg_price) if pos.avg_price else 0,
                "price": float(pos.current_price) if pos.current_price else 0,
                "pnl": round(pnl_pct, 2),
                "market_value": float(pos.market_value) if pos.market_value else 0,
                "alerts": []  # 可由风控系统填充
            })

        return result
    except Exception as e:
        logger.error(f"获取持仓数据失败: {e}")
        return []


async def get_active_orders_data(db: AsyncSession, account_id: int) -> List[Dict]:
    """获取活跃订单数据"""
    try:
        order_service = OrderService(db)
        orders = await order_service.get_active_orders(account_id)

        result = []
        for order in orders:
            result.append({
                "order_id": order.order_id,
                "symbol": order.symbol,
                "direction": order.direction.value,
                "qty": order.qty,
                "filled_qty": order.filled_qty,
                "price": float(order.price) if order.price else None,
                "status": order.status.value,
                "created_at": order.created_at.isoformat() if order.created_at else None
            })

        return result
    except Exception as e:
        logger.error(f"获取订单数据失败: {e}")
        return []


def get_strategies_status() -> List[Dict]:
    """获取策略状态"""
    try:
        strategies = []
        for strategy_id in strategy_manager.list_strategies():
            strategy = strategy_manager.get_strategy(strategy_id)
            if strategy:
                stats = strategy.stats
                strategies.append({
                    "id": strategy_id,
                    "name": strategy.name,
                    "type": strategy.__class__.__name__,
                    "status": stats.get("state", "unknown"),
                    "performance": {
                        "return": 0,  # 从策略统计中获取
                        "sharpe": 0
                    }
                })
        return strategies
    except Exception as e:
        logger.error(f"获取策略状态失败: {e}")
        return []


@router.get("/portfolio/{account_id}")
async def get_portfolio(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取账户组合信息"""
    return await get_portfolio_summary(db, account_id)


@router.get("/positions/{account_id}")
async def get_positions(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取持仓列表"""
    return await get_positions_data(db, account_id)


@router.get("/active-orders/{account_id}")
async def get_active_orders(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取活跃订单"""
    return await get_active_orders_data(db, account_id)


@router.get("/strategies")
async def get_strategies():
    """获取策略列表"""
    return get_strategies_status()


@router.get("/risk-metrics/{account_id}")
async def get_risk_metrics(account_id: int):
    """获取风控指标"""
    # 这里可以从风控系统获取实际数据
    return [
        {
            "name": "单票仓位",
            "value": "12.5%",
            "limit": "20%",
            "percent": 62.5,
            "status": "normal"
        },
        {
            "name": "总仓位",
            "value": "45.2%",
            "limit": "60%",
            "percent": 75.3,
            "status": "warning"
        },
        {
            "name": "日亏损",
            "value": "0.8%",
            "limit": "2%",
            "percent": 40,
            "status": "normal"
        }
    ]
