"""
行情数据 API

提供实时行情数据接口：
- REST API: 历史数据查询
- WebSocket: 实时数据推送
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from src.models.base import get_db
from src.market_data.manager import MarketDataManager
from src.market_data.data_service import data_service
from src.market_data.models import TickData, KLineData
from src.market_data.gateway.akshare import AKShareGateway
from src.market_data.mock_provider import MockDataProvider
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()


# ============ 响应模型 ============

class TickResponse(BaseModel):
    """Tick数据响应"""
    symbol: str
    timestamp: str
    price: float
    volume: int
    bid_price: Optional[float] = None
    bid_volume: Optional[int] = None
    ask_price: Optional[float] = None
    ask_volume: Optional[int] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None


class KLineResponse(BaseModel):
    """K线数据响应"""
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: Optional[float] = None
    period: str


class MarketSnapshotResponse(BaseModel):
    """市场快照响应"""
    symbol: str
    price: float
    open: float
    high: float
    low: float
    pre_close: float
    volume: int
    change: float
    change_pct: float
    bid_price_1: Optional[float] = None
    ask_price_1: Optional[float] = None
    timestamp: str


class StockInfoResponse(BaseModel):
    """股票信息响应"""
    symbol: str
    name: str
    code: Optional[str] = None


# ============ REST API ============

@router.get("/tick/{symbol}", response_model=TickResponse)
async def get_latest_tick(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取最新Tick数据

    Args:
        symbol: 标的代码 (如: 000001.SZ)
    """
    tick = await data_service.get_tick(symbol)

    if not tick:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的行情数据")

    return tick.to_dict()


@router.get("/kline/{symbol}", response_model=List[KLineResponse])
async def get_kline_history(
    symbol: str,
    period: str = Query("daily", description="周期: daily, weekly, monthly"),
    start: Optional[datetime] = Query(None, description="开始时间"),
    end: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取K线历史数据

    Args:
        symbol: 标的代码
        period: K线周期 (daily/weekly/monthly)
        start: 开始时间 (ISO格式)
        end: 结束时间 (ISO格式)
        limit: 最大返回条数
    """
    # 转换日期格式
    start_date = start.strftime('%Y%m%d') if start else None
    end_date = end.strftime('%Y%m%d') if end else None

    klines = await data_service.get_kline(
        symbol=symbol,
        period=period,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    return [k.to_dict() for k in klines]


@router.get("/snapshot/{symbol}", response_model=MarketSnapshotResponse)
async def get_market_snapshot(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取市场快照

    包含完整的市场数据：价格、成交量、买卖盘等
    """
    tick = await data_service.get_tick(symbol)

    if not tick:
        raise HTTPException(status_code=404, detail=f"未找到 {symbol} 的快照数据")

    # 构建快照响应
    change = tick.change or Decimal("0")
    pre_close = tick.pre_close or (tick.price - change)
    change_pct = (change / pre_close * 100) if pre_close else Decimal("0")

    return {
        "symbol": tick.symbol,
        "price": float(tick.price),
        "open": float(tick.open) if tick.open else float(tick.price),
        "high": float(tick.high) if tick.high else float(tick.price),
        "low": float(tick.low) if tick.low else float(tick.price),
        "pre_close": float(pre_close),
        "volume": tick.volume,
        "change": float(change),
        "change_pct": float(change_pct),
        "bid_price_1": float(tick.bid_price) if tick.bid_price else None,
        "ask_price_1": float(tick.ask_price) if tick.ask_price else None,
        "timestamp": tick.timestamp.isoformat() if tick.timestamp else datetime.now().isoformat(),
    }


@router.get("/symbols", response_model=List[str])
async def get_active_symbols(
    db: AsyncSession = Depends(get_db)
):
    """获取当前活跃的标的列表"""
    manager = MarketDataManager()
    return list(manager.active_symbols)


@router.get("/stocks/search", response_model=List[StockInfoResponse])
async def search_stocks(
    keyword: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=100, description="返回条数")
):
    """
    搜索股票

    根据关键词搜索A股股票
    """
    results = await data_service.search_stocks(keyword, limit)
    return results


@router.get("/stocks/list", response_model=List[StockInfoResponse])
async def get_stock_list(
    limit: int = Query(100, ge=1, le=1000, description="返回条数")
):
    """
    获取A股股票列表

    返回A股所有股票的基本信息
    """
    stocks = await data_service.get_stock_list(limit=limit)
    return stocks


@router.get("/batch/ticks")
async def get_batch_ticks(
    symbols: str = Query(..., description="标的代码，逗号分隔，如: 000001.SZ,600519.SH"),
    db: AsyncSession = Depends(get_db)
):
    """
    批量获取Tick数据

    Args:
        symbols: 逗号分隔的标的代码
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    results = await data_service.get_batch_ticks(symbol_list)

    return {
        "data": {symbol: tick.to_dict() for symbol, tick in results.items()},
        "count": len(results),
        "requested": len(symbol_list)
    }


@router.get("/service/status")
async def get_data_service_status():
    """获取数据服务状态"""
    return data_service.get_cache_stats()


@router.post("/service/clear-cache")
async def clear_data_cache():
    """清除数据缓存"""
    data_service.clear_cache()
    return {"message": "缓存已清除"}


# ============ WebSocket API ============

class WebSocketMessage:
    """WebSocket消息格式"""

    @staticmethod
    def subscribe_message(symbols: List[str], data_types: List[str] = None) -> Dict[str, Any]:
        """订阅消息"""
        return {
            "action": "subscribe",
            "symbols": symbols,
            "data_types": data_types or ["tick"]
        }

    @staticmethod
    def unsubscribe_message(symbols: List[str]) -> Dict[str, Any]:
        """取消订阅消息"""
        return {
            "action": "unsubscribe",
            "symbols": symbols
        }

    @staticmethod
    def tick_data(tick: TickData) -> Dict[str, Any]:
        """Tick数据消息"""
        return {
            "type": "tick",
            "data": tick.to_dict()
        }

    @staticmethod
    def kline_data(kline: KLineData) -> Dict[str, Any]:
        """K线数据消息"""
        return {
            "type": f"kline_{kline.period}",
            "data": kline.to_dict()
        }

    @staticmethod
    def error_message(message: str) -> Dict[str, Any]:
        """错误消息"""
        return {
            "type": "error",
            "message": message
        }

    @staticmethod
    def connected_message() -> Dict[str, Any]:
        """连接成功消息"""
        return {
            "type": "connected",
            "message": "行情WebSocket连接成功"
        }


@router.websocket("/ws")
async def market_websocket(websocket: WebSocket):
    """
    行情WebSocket接口

    提供实时行情数据推送服务
    """
    await websocket.accept()

    # 获取数据管理器
    manager = MarketDataManager()

    # 当前订阅的标的
    subscribed_symbols: set = set()

    try:
        # 发送连接成功消息
        await websocket.send_json(WebSocketMessage.connected_message())
        logger.info(f"行情WebSocket连接建立: {websocket.client}")

        # 消息处理循环
        while True:
            try:
                # 接收消息
                message = await websocket.receive_json()

                action = message.get("action")
                symbols = message.get("symbols", [])
                data_types = message.get("data_types", ["tick"])

                if action == "subscribe":
                    # 处理订阅请求
                    for symbol in symbols:
                        await manager.subscribe_symbol(symbol, websocket)
                        subscribed_symbols.add(symbol)

                    await websocket.send_json({
                        "type": "subscribed",
                        "symbols": symbols
                    })
                    logger.debug(f"WebSocket订阅: {symbols}")

                elif action == "unsubscribe":
                    # 处理取消订阅
                    for symbol in symbols:
                        await manager.unsubscribe_symbol(symbol, websocket)
                        subscribed_symbols.discard(symbol)

                    await websocket.send_json({
                        "type": "unsubscribed",
                        "symbols": symbols
                    })
                    logger.debug(f"WebSocket取消订阅: {symbols}")

                elif action == "ping":
                    # 心跳响应
                    await websocket.send_json({"type": "pong"})

                else:
                    # 未知动作
                    await websocket.send_json(
                        WebSocketMessage.error_message(f"未知动作: {action}")
                    )

            except WebSocketDisconnect:
                logger.info(f"WebSocket断开连接: {websocket.client}")
                break

            except Exception as e:
                logger.error(f"WebSocket消息处理错误: {e}")
                await websocket.send_json(
                    WebSocketMessage.error_message(f"处理错误: {str(e)}")
                )

    except Exception as e:
        logger.error(f"WebSocket异常: {e}")

    finally:
        # 清理订阅
        for symbol in subscribed_symbols:
            await manager.unsubscribe_symbol(symbol, websocket)

        logger.info(f"WebSocket连接清理完成: {websocket.client}")
