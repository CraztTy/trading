"""
行情数据管理器

中央协调器，负责：
1. 管理多个数据网关
2. K线数据合成
3. 数据缓存
4. WebSocket推送
5. 订阅管理
"""
from typing import Dict, Set, Optional, Callable, Any
from datetime import datetime
import asyncio
import json

from fastapi import WebSocket

from src.market_data.models import TickData, KLineData
from src.market_data.builder import MultiPeriodKLineBuilder
from src.market_data.gateway.base import MarketDataGateway
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)

# 延迟导入太子院（避免循环导入）
_crown_prince = None
_crown_prince_imported = False


def _get_crown_prince():
    """获取太子院实例（延迟加载）"""
    global _crown_prince, _crown_prince_imported
    if not _crown_prince_imported:
        from src.core.crown_prince import crown_prince, DataType
        _crown_prince = crown_prince
        _crown_prince_imported = True
    return _crown_prince


class MarketDataManager:
    """
    行情数据管理器 (单例)

    负责协调整个实时行情系统
    """

    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return

        self._initialized = True

        # 数据网关
        self.gateways: Dict[str, MarketDataGateway] = {}

        # WebSocket订阅者: symbol -> set of websockets
        self.subscribers: Dict[str, Set[WebSocket]] = {}

        # 全局订阅者（订阅所有标的）
        self.global_subscribers: Set[WebSocket] = set()

        # K线合成器: symbol -> MultiPeriodKLineBuilder
        self.kline_builders: Dict[str, MultiPeriodKLineBuilder] = {}

        # 活跃标的集合
        self.active_symbols: Set[str] = set()

        # 最新tick缓存: symbol -> TickData
        self.latest_ticks: Dict[str, TickData] = {}

        # 回调函数
        self.on_tick_callbacks: Set[Callable[[TickData], None]] = set()
        self.on_kline_callbacks: Set[Callable[[KLineData], None]] = set()

        # 运行状态
        self._running = False
        self._tasks: Set[asyncio.Task] = set()

        # 初始化太子院集成
        self._setup_crown_prince()

    async def start(self):
        """启动数据管理器"""
        if self._running:
            return

        self._running = True
        logger.info("行情数据管理器启动")

        # 启动所有网关
        for name, gateway in self.gateways.items():
            try:
                await gateway.connect()
                logger.info(f"网关已连接: {name}")
            except Exception as e:
                logger.error(f"网关连接失败 {name}: {e}")

    async def stop(self):
        """停止数据管理器"""
        self._running = False

        # 取消所有任务
        for task in self._tasks:
            task.cancel()

        # 关闭所有网关
        for name, gateway in self.gateways.items():
            try:
                await gateway.disconnect()
                logger.info(f"网关已断开: {name}")
            except Exception as e:
                logger.error(f"网关断开失败 {name}: {e}")

        logger.info("行情数据管理器已停止")

    def register_gateway(self, name: str, gateway: MarketDataGateway):
        """
        注册数据网关

        Args:
            name: 网关名称
            gateway: 网关实例
        """
        self.gateways[name] = gateway
        gateway.set_tick_handler(self._on_tick_received)
        logger.info(f"注册网关: {name}")

    def _on_tick_received(self, tick: TickData):
        """收到tick数据的回调"""
        # 1. 太子院校验与标准化
        cp = _get_crown_prince()
        if cp:
            result = cp.process_tick(tick)
            if not result.is_valid:
                logger.warning(f"Tick数据校验失败: {result.errors}")
                return
            # 使用标准化后的代码
            tick = result.data

        # 2. 更新最新缓存
        self.latest_ticks[tick.symbol] = tick

        # 3. K线合成
        if tick.symbol in self.kline_builders:
            completed_bars = self.kline_builders[tick.symbol].on_tick(tick)

            # 触发K线完成回调
            for period, bar in completed_bars.items():
                if bar:
                    self._on_kline_completed(bar)

        # 4. 触发tick回调
        self._on_tick_processed(tick)

    def _on_tick_processed(self, tick: TickData):
        """tick处理完成，分发到订阅者"""
        # 执行回调
        for callback in self.on_tick_callbacks:
            try:
                callback(tick)
            except Exception as e:
                logger.error(f"Tick回调执行失败: {e}")

        # WebSocket推送 (异步)
        asyncio.create_task(self._broadcast_tick(tick))

    def _on_kline_completed(self, kline: KLineData):
        """K线完成回调"""
        # 1. 太子院校验与标准化
        cp = _get_crown_prince()
        if cp:
            result = cp.process_kline(kline)
            if not result.is_valid:
                logger.warning(f"K线数据校验失败: {result.errors}")
                return
            # 使用标准化后的数据
            kline = result.data

        # 2. 执行回调
        for callback in self.on_kline_callbacks:
            try:
                callback(kline)
            except Exception as e:
                logger.error(f"K线回调执行失败: {e}")

        # 3. WebSocket推送 (异步)
        asyncio.create_task(self._broadcast_kline(kline))

    async def _broadcast_tick(self, tick: TickData):
        """广播tick到所有订阅者"""
        message = {
            "type": "tick",
            "data": tick.to_dict()
        }

        # 发送给标的特定订阅者
        disconnected = set()
        if tick.symbol in self.subscribers:
            for ws in self.subscribers[tick.symbol]:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.add(ws)

            # 清理断开的连接
            for ws in disconnected:
                self.subscribers[tick.symbol].discard(ws)

        # 发送给全局订阅者
        disconnected = set()
        for ws in self.global_subscribers:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self.global_subscribers.discard(ws)

    async def _broadcast_kline(self, kline: KLineData):
        """广播K线到所有订阅者"""
        message = {
            "type": f"kline_{kline.period}",
            "data": kline.to_dict()
        }

        # 发送给标的特定订阅者
        disconnected = set()
        if kline.symbol in self.subscribers:
            for ws in self.subscribers[kline.symbol]:
                try:
                    await ws.send_json(message)
                except Exception:
                    disconnected.add(ws)

            for ws in disconnected:
                self.subscribers[kline.symbol].discard(ws)

    async def subscribe_symbol(self, symbol: str, websocket: WebSocket):
        """
        订阅标的

        Args:
            symbol: 标的代码
            websocket: WebSocket连接
        """
        if symbol not in self.subscribers:
            self.subscribers[symbol] = set()

            # 首次订阅，需要激活这个标的
            await self._activate_symbol(symbol)

        self.subscribers[symbol].add(websocket)
        logger.debug(f"订阅 {symbol}, 当前订阅者: {len(self.subscribers[symbol])}")

    async def unsubscribe_symbol(self, symbol: str, websocket: WebSocket):
        """取消订阅标的"""
        if symbol in self.subscribers:
            self.subscribers[symbol].discard(websocket)

            # 如果没有订阅者了，可以考虑取消订阅数据源
            if not self.subscribers[symbol]:
                await self._deactivate_symbol(symbol)

    async def subscribe_global(self, websocket: WebSocket):
        """全局订阅（接收所有标的）"""
        self.global_subscribers.add(websocket)

    async def unsubscribe_global(self, websocket: WebSocket):
        """取消全局订阅"""
        self.global_subscribers.discard(websocket)

    async def _activate_symbol(self, symbol: str):
        """激活标的（开始接收数据）"""
        if symbol in self.active_symbols:
            return

        self.active_symbols.add(symbol)

        # 创建K线合成器
        if symbol not in self.kline_builders:
            self.kline_builders[symbol] = MultiPeriodKLineBuilder(symbol)

        # 订阅数据源
        for name, gateway in self.gateways.items():
            try:
                await gateway.subscribe([symbol])
                logger.info(f"已订阅 {symbol} via {name}")
            except Exception as e:
                logger.error(f"订阅失败 {symbol} via {name}: {e}")

    async def _deactivate_symbol(self, symbol: str):
        """取消激活标的"""
        if symbol not in self.active_symbols:
            return

        self.active_symbols.discard(symbol)

        # 取消订阅数据源
        for name, gateway in self.gateways.items():
            try:
                await gateway.unsubscribe([symbol])
                logger.info(f"已取消订阅 {symbol} via {name}")
            except Exception as e:
                logger.error(f"取消订阅失败 {symbol} via {name}: {e}")

    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """获取最新tick"""
        return self.latest_ticks.get(symbol)

    def get_current_klines(self, symbol: str) -> Dict[str, Optional[KLineData]]:
        """获取当前K线数据"""
        if symbol in self.kline_builders:
            return self.kline_builders[symbol].get_current_bars()
        return {}

    def add_tick_callback(self, callback: Callable[[TickData], None]):
        """添加tick回调"""
        self.on_tick_callbacks.add(callback)

    def remove_tick_callback(self, callback: Callable[[TickData], None]):
        """移除tick回调"""
        self.on_tick_callbacks.discard(callback)

    def add_kline_callback(self, callback: Callable[[KLineData], None]):
        """添加K线回调"""
        self.on_kline_callbacks.add(callback)

    def remove_kline_callback(self, callback: Callable[[KLineData], None]):
        """移除K线回调"""
        self.on_kline_callbacks.discard(callback)

    def _setup_crown_prince(self):
        """设置太子院集成 - 将MarketDataManager的回调注册到太子院"""
        cp = _get_crown_prince()
        if not cp:
            logger.warning("太子院未初始化，跳过集成设置")
            return

        from src.core.crown_prince import DataType

        # 注册Tick处理器
        cp.register_handler(DataType.TICK, self._handle_crown_prince_tick)

        # 注册K线处理器
        cp.register_handler(DataType.KLINE, self._handle_crown_prince_kline)

        logger.info("太子院集成已设置")

    def _handle_crown_prince_tick(self, tick: TickData, validation_result):
        """太子院分发的Tick数据处理器"""
        # 这里可以添加额外的处理逻辑
        # 例如：存储到数据库、触发策略计算等
        logger.debug(f"太子院分发Tick: {tick.symbol} @ {tick.price}")

    def _handle_crown_prince_kline(self, kline: KLineData, validation_result):
        """太子院分发的K线数据处理器"""
        logger.debug(f"太子院分发K线: {kline.symbol} [{kline.period}]")

    def add_crown_prince_handler(self, data_type, handler: Callable):
        """
        添加太子院处理器

        用于其他模块（如中书省策略）注册数据处理器
        """
        cp = _get_crown_prince()
        if cp:
            cp.register_handler(data_type, handler)
            logger.info(f"已注册太子院处理器: {handler.__name__}")

    def get_crown_prince_stats(self) -> dict:
        """获取太子院统计信息"""
        cp = _get_crown_prince()
        return cp.get_stats() if cp else {}

    def add_banned_stock(self, code: str, reason: str = ""):
        """添加禁售股票"""
        cp = _get_crown_prince()
        if cp:
            cp.add_banned_stock(code, reason)

    def remove_banned_stock(self, code: str):
        """移除禁售股票"""
        cp = _get_crown_prince()
        if cp:
            cp.remove_banned_stock(code)
