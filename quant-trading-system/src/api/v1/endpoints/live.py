"""
实盘监控API
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional

from src.core.auto_trader import auto_trader, TradeMode
from src.core.signal_publisher import signal_publisher
from src.api.v1.exceptions import ValidationError, NotFoundError

router = APIRouter()

# 模拟实盘监控状态
live_status = {
    'running': False,
    'watch_list': [],
    'active_strategies': [],
    'portfolio': {
        'cash': 1000000,
        'total_value': 1000000,
        'positions': {}
    }
}

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


@router.get("/status")
async def get_live_status():
    """获取实盘监控状态"""
    return live_status


@router.post("/start")
async def start_live_monitoring(request: dict):
    """
    启动实盘监控

    请求体示例:
    {
        "symbols": ["000001.SZ", "600036.SH"],
        "strategies": ["strategy_01"],
        "auto_trade": false
    }
    """
    live_status['running'] = True
    live_status['watch_list'] = request.get('symbols', [])
    live_status['active_strategies'] = request.get('strategies', [])

    return {
        'status': 'started',
        'watch_list': live_status['watch_list'],
        'active_strategies': live_status['active_strategies']
    }


@router.post("/stop")
async def stop_live_monitoring():
    """停止实盘监控"""
    live_status['running'] = False
    return {'status': 'stopped'}


@router.post("/symbols/add")
async def add_symbol(request: dict):
    """添加监控股票"""
    symbol = request.get('symbol')
    if symbol and symbol not in live_status['watch_list']:
        live_status['watch_list'].append(symbol)
    return {'watch_list': live_status['watch_list']}


@router.post("/symbols/remove")
async def remove_symbol(request: dict):
    """移除监控股票"""
    symbol = request.get('symbol')
    if symbol and symbol in live_status['watch_list']:
        live_status['watch_list'].remove(symbol)
    return {'watch_list': live_status['watch_list']}


@router.post("/strategies/add")
async def add_strategy(request: dict):
    """添加策略"""
    strategy_id = request.get('strategy_id')
    if strategy_id and strategy_id not in live_status['active_strategies']:
        live_status['active_strategies'].append(strategy_id)
    return {'active_strategies': live_status['active_strategies']}


@router.post("/strategies/remove")
async def remove_strategy(request: dict):
    """移除策略"""
    strategy_id = request.get('strategy_id')
    if strategy_id and strategy_id in live_status['active_strategies']:
        live_status['active_strategies'].remove(strategy_id)
    return {'active_strategies': live_status['active_strategies']}


@router.get("/portfolio")
async def get_portfolio():
    """获取账户状态"""
    return live_status['portfolio']


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket实时数据推送

    推送消息类型:
    - signal: 交易信号
    - trade: 成交通知
    - market: 行情数据
    - error: 错误信息
    """
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            # 处理订阅请求
            if data.get('action') == 'subscribe':
                await websocket.send_json({
                    'type': 'subscribed',
                    'symbols': data.get('symbols', [])
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# 切换交易模式
@router.post("/mode")
async def set_trade_mode(request: dict):
    """设置交易模式"""
    mode = request.get("mode")
    if mode not in ["auto", "manual", "simulate", "pause"]:
        raise ValidationError("Invalid trade mode", field="mode", value=mode)

    auto_trader.set_mode(TradeMode(mode))
    return {"success": True, "mode": mode}


# 获取信号历史
@router.get("/signals")
async def get_signal_history(
    strategy_id: str = None,
    symbol: str = None,
    status: str = None,
    limit: int = 100
):
    """获取信号历史"""
    signals = signal_publisher.get_signal_history(
        strategy_id=strategy_id,
        symbol=symbol,
        status=status,
        limit=limit
    )
    return [s.to_dict() for s in signals]


# 确认信号（手动模式）
@router.post("/signals/{signal_id}/confirm")
async def confirm_signal(signal_id: str):
    """确认信号并下单"""
    result = await auto_trader.confirm_signal(signal_id)
    return {
        "success": result.success,
        "order_id": result.order_id,
        "message": result.message
    }


# 忽略信号
@router.post("/signals/{signal_id}/ignore")
async def ignore_signal(signal_id: str):
    """忽略信号"""
    success = auto_trader.ignore_signal(signal_id)
    return {"success": success}


# 获取待确认信号
@router.get("/signals/pending")
async def get_pending_signals():
    """获取待手动确认的信号"""
    signals = auto_trader.get_pending_signals()
    return {sid: s.to_dict() for sid, s in signals.items()}


# 获取模拟交易记录
@router.get("/simulated-trades")
async def get_simulated_trades():
    """获取模拟交易记录"""
    trades = auto_trader.get_simulated_trades()
    return trades


# 获取绩效统计
@router.get("/performance")
async def get_performance():
    """获取实盘绩效"""
    stats = signal_publisher.get_stats()
    return {
        "signals": stats,
        "mode": auto_trader.get_mode().value
    }
