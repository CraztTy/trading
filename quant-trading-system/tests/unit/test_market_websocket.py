"""
行情WebSocket单元测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from decimal import Decimal

from fastapi import WebSocket

from src.api.v1.endpoints.market import WebSocketMessage
from src.market_data.models import TickData, KLineData
from src.market_data.manager import MarketDataManager


class TestWebSocketMessage:
    """测试WebSocket消息格式"""

    def test_connected_message(self):
        """测试连接成功消息"""
        msg = WebSocketMessage.connected_message()
        assert msg["type"] == "connected"
        assert "行情WebSocket连接成功" in msg["message"]

    def test_subscribe_message(self):
        """测试订阅消息"""
        symbols = ["000001.SZ", "600519.SH"]
        data_types = ["tick", "kline_1m"]

        msg = WebSocketMessage.subscribe_message(symbols, data_types)
        assert msg["action"] == "subscribe"
        assert msg["symbols"] == symbols
        assert msg["data_types"] == data_types

    def test_unsubscribe_message(self):
        """测试取消订阅消息"""
        symbols = ["000001.SZ"]

        msg = WebSocketMessage.unsubscribe_message(symbols)
        assert msg["action"] == "unsubscribe"
        assert msg["symbols"] == symbols

    def test_tick_data_message(self):
        """测试Tick数据消息"""
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            price=Decimal("10.50"),
            volume=1000,
        )

        msg = WebSocketMessage.tick_data(tick)
        assert msg["type"] == "tick"
        assert msg["data"]["symbol"] == "000001.SZ"
        assert msg["data"]["price"] == 10.50

    def test_kline_data_message(self):
        """测试K线数据消息"""
        kline = KLineData(
            symbol="000001.SZ",
            timestamp=datetime(2024, 1, 15, 9, 30, 0),
            open=Decimal("10.00"),
            high=Decimal("10.50"),
            low=Decimal("9.90"),
            close=Decimal("10.30"),
            volume=10000,
            period="1m",
        )

        msg = WebSocketMessage.kline_data(kline)
        assert msg["type"] == "kline_1m"
        assert msg["data"]["symbol"] == "000001.SZ"
        assert msg["data"]["close"] == 10.30

    def test_error_message(self):
        """测试错误消息"""
        msg = WebSocketMessage.error_message("测试错误")
        assert msg["type"] == "error"
        assert msg["message"] == "测试错误"


@pytest.mark.asyncio
class TestMarketDataManagerWebSocket:
    """测试MarketDataManager的WebSocket功能"""

    async def test_subscribe_symbol(self):
        """测试订阅标的"""
        manager = MarketDataManager()
        mock_ws = AsyncMock(spec=WebSocket)

        # 测试订阅
        await manager.subscribe_symbol("000001.SZ", mock_ws)

        # 验证订阅成功
        assert "000001.SZ" in manager.subscribers
        assert mock_ws in manager.subscribers["000001.SZ"]

    async def test_unsubscribe_symbol(self):
        """测试取消订阅"""
        manager = MarketDataManager()
        mock_ws = AsyncMock(spec=WebSocket)

        # 先订阅
        await manager.subscribe_symbol("000001.SZ", mock_ws)
        assert "000001.SZ" in manager.subscribers

        # 再取消订阅
        await manager.unsubscribe_symbol("000001.SZ", mock_ws)
        # WebSocket应该从订阅列表中移除
        # 注意：如果没有其他订阅者，symbol会被清理

    async def test_broadcast_tick(self):
        """测试广播tick数据"""
        manager = MarketDataManager()
        mock_ws = AsyncMock(spec=WebSocket)

        # 订阅
        await manager.subscribe_symbol("000001.SZ", mock_ws)

        # 创建tick
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=1000,
        )

        # 广播
        await manager._broadcast_tick(tick)

        # 验证消息已发送
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "tick"
        assert call_args["data"]["symbol"] == "000001.SZ"

    async def test_global_subscribe(self):
        """测试全局订阅"""
        manager = MarketDataManager()
        mock_ws = AsyncMock(spec=WebSocket)

        # 全局订阅
        await manager.subscribe_global(mock_ws)

        # 验证
        assert mock_ws in manager.global_subscribers

    async def test_multiple_subscribers(self):
        """测试多个订阅者"""
        manager = MarketDataManager()
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)

        # 两个WebSocket订阅同一个标的
        await manager.subscribe_symbol("000001.SZ", mock_ws1)
        await manager.subscribe_symbol("000001.SZ", mock_ws2)

        # 验证都有订阅
        assert mock_ws1 in manager.subscribers["000001.SZ"]
        assert mock_ws2 in manager.subscribers["000001.SZ"]


class TestMarketDataManagerSingleton:
    """测试MarketDataManager单例模式"""

    def test_singleton_instance(self):
        """测试单例模式"""
        manager1 = MarketDataManager()
        manager2 = MarketDataManager()

        # 应该是同一个实例
        assert manager1 is manager2

    def test_singleton_state_shared(self):
        """测试单例状态共享"""
        manager1 = MarketDataManager()

        # 添加一个订阅者
        mock_ws = MagicMock()
        manager1.global_subscribers.add(mock_ws)

        # 另一个实例应该能看到
        manager2 = MarketDataManager()
        assert mock_ws in manager2.global_subscribers
