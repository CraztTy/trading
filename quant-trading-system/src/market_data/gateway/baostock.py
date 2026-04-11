"""
Baostock 数据网关

通过 Baostock 获取 A 股历史行情数据
特点：
- 完全免费，无需注册
- 数据稳定，官方维护
- A股历史数据完整（2000年至今）
- 支持复权数据
- 注意：实时数据有15分钟延迟
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Callable
from src.market_data.gateway.base import MarketDataGateway
from src.market_data.models import TickData, KLineData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class BaostockGateway(MarketDataGateway):
    """
    Baostock 数据网关

    使用 Baostock 获取免费历史行情数据
    注意：实时数据有15分钟延迟
    """

    def __init__(self):
        super().__init__("baostock")
        self._bs = None
        self._latest_ticks: Dict[str, TickData] = {}

    def _init_api(self):
        """初始化 Baostock API"""
        if self._bs is None:
            try:
                import baostock as bs
                self._bs = bs
                logger.info("Baostock API 初始化成功")
            except ImportError:
                logger.error("baostock 库未安装")
                raise

    async def connect(self) -> None:
        """建立连接（登录）"""
        try:
            self._init_api()
            # Baostock 登录（可以匿名）
            result = self._bs.login()
            if result.error_code == '0':
                self._connected = True
                logger.info("Baostock 登录成功")
            else:
                raise Exception(f"Baostock 登录失败: {result.error_msg}")
        except Exception as e:
            logger.error(f"Baostock 连接失败: {e}")
            raise

    async def disconnect(self) -> None:
        """断开连接（登出）"""
        if self._bs:
            self._bs.logout()
            self._connected = False
            logger.info("Baostock 已登出")

    async def subscribe(self, symbols: List[str]) -> None:
        """订阅标的（Baostock不支持实时订阅，仅记录）"""
        for symbol in symbols:
            self._subscribed_symbols.add(symbol)
        logger.info(f"Baostock 订阅记录: {symbols}")

    async def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
        for symbol in symbols:
            self._subscribed_symbols.discard(symbol)
        logger.info(f"Baostock 取消订阅: {symbols}")

    def _convert_symbol(self, symbol: str) -> str:
        """
        转换标的代码为 Baostock 格式

        Args:
            symbol: 如 "000001.SZ"

        Returns:
            bs_code: 如 "sz.000001"
        """
        if '.' in symbol:
            code, exchange = symbol.split('.')
            exchange = exchange.lower()
            return f"{exchange}.{code}"
        return symbol

    async def get_snapshot(self, symbol: str) -> Optional[TickData]:
        """
        获取最新快照（实际为最近交易日的收盘数据）

        注意：Baostock没有真正的实时数据，返回的是最近交易日数据
        """
        if not self._bs:
            return None

        try:
            loop = asyncio.get_event_loop()
            bs_code = self._convert_symbol(symbol)

            # 获取当日日期
            today = datetime.now().strftime('%Y-%m-%d')

            # 查询最新一天的日线数据
            result = await loop.run_in_executor(
                None,
                lambda: self._bs.query_history_k_data_plus(
                    bs_code,
                    "date,code,open,high,low,close,volume,amount,preclose",
                    start_date=today,
                    end_date=today,
                    frequency="d",
                    adjustflag="3"  # 默认前复权
                )
            )

            if result.error_code != '0':
                logger.warning(f"Baostock 获取 {symbol} 失败: {result.error_msg}")
                return None

            # 获取数据
            data_list = []
            while (result.error_code == '0') & result.next():
                data_list.append({
                    'date': result.get_data_fields()[0],
                    'code': result.get_data_fields()[1],
                    'open': result.get_data_fields()[2],
                    'high': result.get_data_fields()[3],
                    'low': result.get_data_fields()[4],
                    'close': result.get_data_fields()[5],
                    'volume': result.get_data_fields()[6],
                    'amount': result.get_data_fields()[7],
                    'preclose': result.get_data_fields()[8],
                })

            if not data_list:
                # 如果今天没有数据（非交易日），获取最新一条
                result = await loop.run_in_executor(
                    None,
                    lambda: self._bs.query_history_k_data_plus(
                        bs_code,
                        "date,code,open,high,low,close,volume,amount,preclose",
                        start_date='',
                        end_date=today,
                        frequency="d",
                        adjustflag="3"
                    )
                )

                data_list = []
                while (result.error_code == '0') & result.next():
                    data_list.append({
                        'date': result.get_data_fields()[0],
                        'code': result.get_data_fields()[1],
                        'open': result.get_data_fields()[2],
                        'high': result.get_data_fields()[3],
                        'low': result.get_data_fields()[4],
                        'close': result.get_data_fields()[5],
                        'volume': result.get_data_fields()[6],
                        'amount': result.get_data_fields()[7],
                        'preclose': result.get_data_fields()[8],
                    })

                if data_list:
                    data_list = [data_list[-1]]  # 取最后一条

            if not data_list:
                return None

            data = data_list[0]

            # 计算涨跌幅
            close_price = Decimal(str(data.get('close', 0)))
            pre_close = Decimal(str(data.get('preclose', 0)))
            change = close_price - pre_close
            change_pct = (change / pre_close * 100) if pre_close > 0 else Decimal('0')

            tick = TickData(
                symbol=symbol,
                timestamp=datetime.now(),
                price=close_price,
                volume=int(Decimal(str(data.get('volume', 0)))),
                amount=Decimal(str(data.get('amount', 0))),
                open=Decimal(str(data.get('open', 0))),
                high=Decimal(str(data.get('high', 0))),
                low=Decimal(str(data.get('low', 0))),
                pre_close=pre_close,
                change=change,
                change_pct=change_pct,
                source="baostock",
            )

            self._latest_ticks[symbol] = tick
            return tick

        except Exception as e:
            logger.error(f"Baostock 获取 {symbol} 快照失败: {e}")
            return None

    async def get_kline_history(
        self,
        symbol: str,
        period: str = "d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> List[KLineData]:
        """
        获取历史 K 线数据

        Args:
            symbol: 标的代码 (如: 000001.SZ)
            period: 周期 d/w/m (日/周/月)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            limit: 最大条数

        Returns:
            KLineData 列表
        """
        if not self._bs:
            return []

        try:
            loop = asyncio.get_event_loop()
            bs_code = self._convert_symbol(symbol)

            # 转换周期
            bs_period = "d"  # 默认日线
            if period in ["W", "weekly", "w"]:
                bs_period = "w"
            elif period in ["M", "monthly", "m"]:
                bs_period = "m"

            # 设置默认日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            else:
                # 转换格式 YYYYMMDD -> YYYY-MM-DD
                end_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

            if not start_date:
                start = datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=limit * 2)
                start_date = start.strftime('%Y-%m-%d')
            else:
                # 转换格式
                start_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"

            # 查询历史K线
            result = await loop.run_in_executor(
                None,
                lambda: self._bs.query_history_k_data_plus(
                    bs_code,
                    "date,code,open,high,low,close,volume,amount",
                    start_date=start_date,
                    end_date=end_date,
                    frequency=bs_period,
                    adjustflag="3"  # 前复权
                )
            )

            if result.error_code != '0':
                logger.error(f"Baostock 获取K线失败: {result.error_msg}")
                return []

            # 解析数据
            klines = []
            while (result.error_code == '0') & result.next():
                try:
                    date_str = result.get_data_fields()[0]
                    kline = KLineData(
                        symbol=symbol,
                        timestamp=datetime.strptime(date_str, '%Y-%m-%d'),
                        open=Decimal(str(result.get_data_fields()[2])),
                        high=Decimal(str(result.get_data_fields()[3])),
                        low=Decimal(str(result.get_data_fields()[4])),
                        close=Decimal(str(result.get_data_fields()[5])),
                        volume=int(Decimal(str(result.get_data_fields()[6]))),
                        amount=Decimal(str(result.get_data_fields()[7])),
                        period=period
                    )
                    klines.append(kline)
                except Exception as e:
                    logger.debug(f"解析K线数据失败: {e}")
                    continue

            return klines[-limit:]  # 返回最近limit条

        except Exception as e:
            logger.error(f"Baostock 获取 {symbol} K线失败: {e}")
            return []

    async def get_stock_list(self) -> List[Dict[str, str]]:
        """
        获取 A 股股票列表

        Returns:
            [{"symbol": "000001.SZ", "name": "平安银行"}, ...]
        """
        if not self._bs:
            return []

        try:
            loop = asyncio.get_event_loop()

            # 查询所有股票
            result = await loop.run_in_executor(
                None,
                lambda: self._bs.query_all_stock(day=datetime.now().strftime('%Y-%m-%d'))
            )

            if result.error_code != '0':
                logger.error(f"Baostock 获取股票列表失败: {result.error_msg}")
                return []

            stocks = []
            while (result.error_code == '0') & result.next():
                try:
                    bs_code = result.get_data_fields()[0]  # 如 "sh.600000"
                    code_name = result.get_data_fields()[1]  # 股票名称

                    # 转换为统一格式
                    if '.' in bs_code:
                        exchange, code = bs_code.split('.')
                        exchange = exchange.upper()
                        symbol = f"{code}.{exchange}"
                    else:
                        symbol = bs_code

                    stocks.append({
                        "symbol": symbol,
                        "name": code_name,
                        "code": bs_code
                    })
                except Exception as e:
                    continue

            return stocks

        except Exception as e:
            logger.error(f"Baostock 获取股票列表失败: {e}")
            return []

    async def get_trade_calendar(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日历

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            交易日列表
        """
        if not self._bs:
            return []

        try:
            loop = asyncio.get_event_loop()

            # 转换日期格式
            start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

            result = await loop.run_in_executor(
                None,
                lambda: self._bs.query_trade_dates(start_date=start, end_date=end)
            )

            if result.error_code != '0':
                return []

            trade_days = []
            while (result.error_code == '0') & result.next():
                date_str = result.get_data_fields()[0]
                is_trading_day = result.get_data_fields()[1] == '1'
                if is_trading_day:
                    trade_days.append(date_str.replace('-', ''))

            return trade_days

        except Exception as e:
            logger.error(f"Baostock 获取交易日历失败: {e}")
            return []
