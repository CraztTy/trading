"""
实盘监控API
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional

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
