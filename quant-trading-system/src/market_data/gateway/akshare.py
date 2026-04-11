"""
AKShare 数据网关

通过 AKShare 获取 A 股实时和历史行情数据
特点：
- 免费开源
- 数据覆盖 A 股、港股、基金、期货等
- 支持历史 K 线、实时行情、财务数据
- 基于爬虫，需注意请求频率
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Callable
import akshare as ak
import pandas as pd

from src.market_data.gateway.base import MarketDataGateway
from src.market_data.models import TickData, KLineData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class AKShareGateway(MarketDataGateway):
    """
    AKShare 数据网关

    使用 AKShare 获取免费行情数据
    注意：请求频率不要过高，建议 3 秒以上间隔
    """

    def __init__(self):
        super().__init__("akshare")
        self._polling_task: Optional[asyncio.Task] = None
        self._running = False
        self._poll_interval = 3  # 轮询间隔 3 秒
        self._latest_ticks: Dict[str, TickData] = {}
        self._on_tick_callback: Optional[Callable[[TickData], None]] = None

    async def connect(self) -> None:
        """建立连接（启动轮询任务）"""
        self._connected = True
        self._running = True
        self._polling_task = asyncio.create_task(self._polling_loop())
        logger.info("AKShare 网关已连接")

    async def disconnect(self) -> None:
        """断开连接（停止轮询）"""
        self._running = False
        self._connected = False

        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        logger.info("AKShare 网关已断开")

    async def subscribe(self, symbols: List[str]) -> None:
        """订阅标的（添加到轮询列表）"""
        for symbol in symbols:
            self._subscribed_symbols.add(symbol)
            # 立即获取一次数据
            await self._fetch_tick(symbol)

        logger.info(f"AKShare 订阅: {symbols}")

    async def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅（从轮询列表移除）"""
        for symbol in symbols:
            self._subscribed_symbols.discard(symbol)
            self._latest_ticks.pop(symbol, None)

        logger.info(f"AKShare 取消订阅: {symbols}")

    async def _polling_loop(self) -> None:
        """轮询循环 - 定期获取实时行情"""
        try:
            while self._running:
                if self._subscribed_symbols:
                    # 批量获取行情
                    for symbol in list(self._subscribed_symbols):
                        try:
                            await self._fetch_tick(symbol)
                        except Exception as e:
                            logger.error(f"获取 {symbol} 行情失败: {e}")

                        # 短暂延迟，避免请求过快
                        await asyncio.sleep(0.5)

                # 等待下一轮
                await asyncio.sleep(self._poll_interval)

        except asyncio.CancelledError:
            logger.debug("AKShare 轮询任务取消")
        except Exception as e:
            logger.error(f"AKShare 轮询异常: {e}")

    async def _fetch_tick(self, symbol: str) -> Optional[TickData]:
        """
        获取单个标的的实时行情

        Args:
            symbol: 标的代码 (如: 000001.SZ)

        Returns:
            TickData 或 None
        """
        try:
            # 转换代码格式
            code, exchange = self._parse_symbol(symbol)

            # 使用 AKShare 获取实时行情
            # 注意：这里使用 stock_zh_a_spot_em 获取全市场行情，然后筛选
            df = ak.stock_zh_a_spot_em()

            # 筛选指定股票
            # AKShare 的代码格式是 "000001"
            row = df[df['代码'] == code]

            if row.empty:
                logger.warning(f"AKShare 未找到 {symbol} 的数据")
                return None

            data = row.iloc[0]

            # 构建 TickData
            tick = TickData(
                symbol=symbol,
                timestamp=datetime.now(),
                price=Decimal(str(data.get('最新价', 0))),
                volume=int(data.get('成交量', 0) / 100),  # 转换为手
                amount=Decimal(str(data.get('成交额', 0))),
                bid_price=Decimal(str(data.get('买一', 0))),
                bid_volume=int(data.get('买一量', 0)),
                ask_price=Decimal(str(data.get('卖一', 0))),
                ask_volume=int(data.get('卖一量', 0)),
                open=Decimal(str(data.get('今开', 0))),
                high=Decimal(str(data.get('最高', 0))),
                low=Decimal(str(data.get('最低', 0))),
                pre_close=Decimal(str(data.get('昨收', 0))),
                change=Decimal(str(data.get('涨跌额', 0))),
                change_pct=Decimal(str(data.get('涨跌幅', 0))),
                source="akshare",
            )

            self._latest_ticks[symbol] = tick

            # 触发回调
            if self._tick_handler:
                self._tick_handler(tick)

            return tick

        except Exception as e:
            logger.error(f"AKShare 获取 {symbol} 行情失败: {e}")
            return None

    async def get_snapshot(self, symbol: str) -> Optional[TickData]:
        """获取最新快照"""
        # 如果缓存中有数据，直接返回
        if symbol in self._latest_ticks:
            return self._latest_ticks[symbol]

        # 否则实时获取
        return await self._fetch_tick(symbol)

    async def get_kline_history(
        self,
        symbol: str,
        period: str = "daily",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> List[KLineData]:
        """
        获取历史 K 线数据

        Args:
            symbol: 标的代码 (如: 000001.SZ)
            period: 周期 daily/weekly/monthly
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            limit: 最大条数

        Returns:
            KLineData 列表
        """
        try:
            code, exchange = self._parse_symbol(symbol)

            # 设置默认日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=limit)
                start_date = start.strftime('%Y%m%d')

            # 使用 AKShare 获取历史数据
            if period == "daily":
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"  # 前复权
                )
            elif period == "weekly":
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="weekly",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
            elif period == "monthly":
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="monthly",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
            else:
                raise ValueError(f"不支持的周期: {period}")

            # 转换为 KLineData
            klines = []
            for _, row in df.iterrows():
                kline = KLineData(
                    symbol=symbol,
                    timestamp=datetime.strptime(row['日期'], '%Y-%m-%d'),
                    open=Decimal(str(row['开盘'])),
                    high=Decimal(str(row['最高'])),
                    low=Decimal(str(row['最低'])),
                    close=Decimal(str(row['收盘'])),
                    volume=int(row['成交量']),
                    amount=Decimal(str(row['成交额'])),
                    period=period
                )
                klines.append(kline)

            return klines

        except Exception as e:
            logger.error(f"AKShare 获取 {symbol} 历史 K 线失败: {e}")
            return []

    def _parse_symbol(self, symbol: str) -> tuple:
        """
        解析标的代码

        Args:
            symbol: 如 "000001.SZ"

        Returns:
            (code, exchange) 如 ("000001", "SZ")
        """
        if '.' in symbol:
            code, exchange = symbol.split('.')
            return code, exchange
        return symbol, "SZ"  # 默认深圳

    async def get_stock_list(self) -> List[Dict[str, str]]:
        """
        获取 A 股股票列表

        Returns:
            [{"symbol": "000001.SZ", "name": "平安银行"}, ...]
        """
        try:
            df = ak.stock_zh_a_spot_em()

            stocks = []
            for _, row in df.iterrows():
                code = row['代码']
                # 根据代码规则判断交易所
                if code.startswith('6'):
                    symbol = f"{code}.SH"
                else:
                    symbol = f"{code}.SZ"

                stocks.append({
                    "symbol": symbol,
                    "name": row['名称'],
                    "code": code
                })

            return stocks

        except Exception as e:
            logger.error(f"AKShare 获取股票列表失败: {e}")
            return []
