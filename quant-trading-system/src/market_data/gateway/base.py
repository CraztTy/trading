"""
行情网关基类

定义所有行情网关的统一接口
"""
from abc import ABC, abstractmethod
from typing import List, Callable, Optional
import asyncio

from src.market_data.models import TickData


class MarketDataGateway(ABC):
    """
    行情网关抽象基类

    所有具体数据源网关都应继承此类
    """

    def __init__(self, name: str):
        """
        初始化网关

        Args:
            name: 网关名称
        """
        self.name = name
        self._connected = False
        self._tick_handler: Optional[Callable[[TickData], None]] = None
        self._subscribed_symbols: set = set()

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    def set_tick_handler(self, handler: Callable[[TickData], None]):
        """
        设置tick数据处理回调

        Args:
            handler: 回调函数，接收TickData参数
        """
        self._tick_handler = handler

    def _on_tick(self, tick: TickData):
        """
        内部方法：收到tick数据时调用

        Args:
            tick: tick数据
        """
        if self._tick_handler:
            self._tick_handler(tick)

    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> None:
        """
        订阅标的

        Args:
            symbols: 标的代码列表
        """
        pass

    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> None:
        """
        取消订阅

        Args:
            symbols: 标的代码列表
        """
        pass

    @abstractmethod
    async def get_snapshot(self, symbol: str) -> Optional[TickData]:
        """
        获取标的快照

        Args:
            symbol: 标的代码

        Returns:
            TickData或None
        """
        pass

    def get_subscribed_symbols(self) -> List[str]:
        """获取已订阅的标的列表"""
        return list(self._subscribed_symbols)
