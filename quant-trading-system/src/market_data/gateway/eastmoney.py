"""
东方财富行情网关

通过WebSocket接入东方财富实时行情
"""
import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Callable, Dict, Any
import aiohttp

from src.market_data.gateway.base import MarketDataGateway
from src.market_data.models import TickData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class EastmoneyGateway(MarketDataGateway):
    """
    东方财富行情网关

    特点:
    - 免费数据源
    - A股全市场覆盖
    - 支持tick级数据
    - WebSocket推送
    """

    # 东方财富WebSocket地址
    WS_URL = "wss://push2.eastmoney.com/ws"

    # 股票代码格式转换
    @staticmethod
    def symbol_to_em_code(symbol: str) -> str:
        """
        将标准代码转换为东方财富代码

        Examples:
            000001.SZ -> 0.000001
            600519.SH -> 1.600519
            300750.SZ -> 0.300750
        """
        if "." not in symbol:
            # 默认深圳
            return f"0.{symbol}"

        code, exchange = symbol.split(".")
        if exchange == "SH":
            return f"1.{code}"
        else:
            return f"0.{code}"

    @staticmethod
    def em_code_to_symbol(em_code: str) -> str:
        """将东方财富代码转换为标准代码"""
        prefix, code = em_code.split(".")
        if prefix == "1":
            return f"{code}.SH"
        else:
            return f"{code}.SZ"

    def __init__(self):
        super().__init__("eastmoney")
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._latest_ticks: Dict[str, TickData] = {}

    async def connect(self) -> None:
        """建立WebSocket连接"""
        try:
            self._session = aiohttp.ClientSession()
            self._ws = await self._session.ws_connect(self.WS_URL)
            self._connected = True

            # 启动接收任务
            self._receive_task = asyncio.create_task(self._receive_loop())
            # 启动心跳任务
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            logger.info("东方财富网关已连接")

        except Exception as e:
            logger.error(f"东方财富网关连接失败: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        self._connected = False

        # 取消任务
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # 关闭WebSocket
        if self._ws:
            await self._ws.close()

        # 关闭session
        if self._session:
            await self._session.close()

        logger.info("东方财富网关已断开")

    async def subscribe(self, symbols: List[str]) -> None:
        """订阅标的"""
        if not self._connected or not self._ws:
            raise RuntimeError("网关未连接")

        for symbol in symbols:
            em_code = self.symbol_to_em_code(symbol)
            # 东方财富订阅格式
            subscribe_msg = {
                "cmd": "subscribe",
                "codes": [em_code],
            }
            await self._ws.send_json(subscribe_msg)
            self._subscribed_symbols.add(symbol)

        logger.info(f"东方财富订阅: {symbols}")

    async def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
        if not self._connected or not self._ws:
            return

        for symbol in symbols:
            em_code = self.symbol_to_em_code(symbol)
            unsubscribe_msg = {
                "cmd": "unsubscribe",
                "codes": [em_code],
            }
            await self._ws.send_json(unsubscribe_msg)
            self._subscribed_symbols.discard(symbol)

        logger.info(f"东方财富取消订阅: {symbols}")

    async def _receive_loop(self) -> None:
        """接收消息循环"""
        try:
            while self._connected and self._ws:
                msg = await self._ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    logger.warning("东方财富WebSocket连接断开")
                    break

        except asyncio.CancelledError:
            logger.debug("接收任务取消")
        except Exception as e:
            logger.error(f"接收循环异常: {e}")
        finally:
            self._connected = False

    async def _handle_message(self, data: str) -> None:
        """处理收到的消息"""
        try:
            msg = json.loads(data)

            # 根据消息类型处理
            if "data" in msg:
                tick = self._parse_tick(msg["data"])
                if tick:
                    self._latest_ticks[tick.symbol] = tick
                    self._on_tick(tick)

        except json.JSONDecodeError:
            logger.warning(f"收到非JSON消息: {data[:100]}")
        except Exception as e:
            logger.error(f"处理消息失败: {e}")

    def _parse_tick(self, data: Dict[str, Any]) -> Optional[TickData]:
        """解析tick数据"""
        try:
            # 东方财富数据格式解析
            em_code = data.get("code", "")
            if not em_code:
                return None

            symbol = self.em_code_to_symbol(em_code)

            # 提取价格信息
            price = Decimal(str(data.get("price", 0)))
            if price == 0:
                price = Decimal(str(data.get("last_price", 0)))

            tick = TickData(
                symbol=symbol,
                timestamp=datetime.now(),
                price=price,
                volume=int(data.get("volume", 0)),
                amount=Decimal(str(data.get("amount", 0))) if data.get("amount") else None,
                bid_price=Decimal(str(data.get("bid1", 0))) if data.get("bid1") else None,
                bid_volume=int(data.get("bid1_volume", 0)) if data.get("bid1_volume") else None,
                ask_price=Decimal(str(data.get("ask1", 0))) if data.get("ask1") else None,
                ask_volume=int(data.get("ask1_volume", 0)) if data.get("ask1_volume") else None,
                open=Decimal(str(data.get("open", 0))) if data.get("open") else None,
                high=Decimal(str(data.get("high", 0))) if data.get("high") else None,
                low=Decimal(str(data.get("low", 0))) if data.get("low") else None,
                pre_close=Decimal(str(data.get("pre_close", 0))) if data.get("pre_close") else None,
                source="eastmoney",
                raw_data=data,
            )

            return tick

        except Exception as e:
            logger.error(f"解析tick数据失败: {e}, data: {data}")
            return None

    async def _heartbeat_loop(self) -> None:
        """心跳保持循环"""
        try:
            while self._connected and self._ws:
                await asyncio.sleep(30)  # 每30秒发送心跳

                if self._ws and not self._ws.closed:
                    try:
                        await self._ws.send_json({"cmd": "ping"})
                    except Exception as e:
                        logger.error(f"心跳发送失败: {e}")
                        break

        except asyncio.CancelledError:
            logger.debug("心跳任务取消")
        except Exception as e:
            logger.error(f"心跳循环异常: {e}")

    async def get_snapshot(self, symbol: str) -> Optional[TickData]:
        """获取最新快照"""
        return self._latest_ticks.get(symbol)
