"""
Tushare 数据网关

通过 Tushare 获取 A 股实时和历史行情数据
特点：
- 数据质量高
- 接口稳定
- 免费版有积分限制
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Callable
from src.market_data.gateway.base import MarketDataGateway
from src.market_data.models import TickData, KLineData
from src.common.logger import TradingLogger
from src.common.config import settings

logger = TradingLogger(__name__)


class TushareGateway(MarketDataGateway):
    """
    Tushare 数据网关

    使用 Tushare Pro 接口获取高质量金融数据
    """

    def __init__(self, token: Optional[str] = None):
        super().__init__("tushare")
        self.token = token or settings.data_sources.tushare_token
        self.pro = None
        self._latest_ticks: Dict[str, TickData] = {}

    def _init_api(self):
        """初始化 Tushare API"""
        if self.pro is None:
            try:
                import tushare as ts
                if self.token:
                    self.pro = ts.pro_api(self.token)
                    logger.info("Tushare API 初始化成功")
                else:
                    logger.warning("Tushare Token 未配置")
            except ImportError:
                logger.error("tushare 库未安装")
                raise

    async def connect(self) -> None:
        """建立连接"""
        try:
            self._init_api()
            # 测试连接
            if self.pro:
                df = self.pro.query('stock_basic', limit=1)
                if df is not None:
                    self._connected = True
                    logger.info("Tushare 网关已连接")
                else:
                    raise Exception("Tushare 连接测试失败")
        except Exception as e:
            logger.error(f"Tushare 连接失败: {e}")
            raise

    async def disconnect(self) -> None:
        """断开连接"""
        self._connected = False
        logger.info("Tushare 网关已断开")

    async def subscribe(self, symbols: List[str]) -> None:
        """订阅标的"""
        for symbol in symbols:
            self._subscribed_symbols.add(symbol)
        logger.info(f"Tushare 订阅: {symbols}")

    async def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
        for symbol in symbols:
            self._subscribed_symbols.discard(symbol)
        logger.info(f"Tushare 取消订阅: {symbols}")

    def _parse_symbol(self, symbol: str) -> str:
        """
        解析标的代码为 Tushare 格式

        Args:
            symbol: 如 "000001.SZ"

        Returns:
            ts_code: 如 "000001.SZ"
        """
        if '.' in symbol:
            code, exchange = symbol.split('.')
            # Tushare 格式: 代码.交易所 (大写)
            return f"{code}.{exchange.upper()}"
        return symbol

    async def get_snapshot(self, symbol: str) -> Optional[TickData]:
        """
        获取最新快照

        使用 Tushare 的实时行情接口
        """
        if not self.pro:
            return None

        try:
            # 在事件循环中执行同步的 Tushare API 调用
            loop = asyncio.get_event_loop()
            ts_code = self._parse_symbol(symbol)

            # 使用每日行情接口（T+1，最新收盘数据）
            # 实时数据需要积分或付费
            today = datetime.now().strftime('%Y%m%d')

            df = await loop.run_in_executor(
                None,
                lambda: self.pro.daily(ts_code=ts_code, trade_date=today)
            )

            if df is None or df.empty:
                # 如果今天没有数据，获取最新一条
                df = await loop.run_in_executor(
                    None,
                    lambda: self.pro.daily(ts_code=ts_code, limit=1)
                )

            if df is None or df.empty:
                return None

            data = df.iloc[0]

            tick = TickData(
                symbol=symbol,
                timestamp=datetime.now(),
                price=Decimal(str(data.get('close', 0))),
                volume=int(data.get('vol', 0) * 100),  # 转换为股
                amount=Decimal(str(data.get('amount', 0) * 1000)),
                open=Decimal(str(data.get('open', 0))),
                high=Decimal(str(data.get('high', 0))),
                low=Decimal(str(data.get('low', 0))),
                pre_close=Decimal(str(data.get('pre_close', 0))),
                change=Decimal(str(data.get('change', 0))),
                change_pct=Decimal(str(data.get('pct_chg', 0))),
                source="tushare",
            )

            self._latest_ticks[symbol] = tick
            return tick

        except Exception as e:
            logger.error(f"Tushare 获取 {symbol} 快照失败: {e}")
            return None

    async def get_kline_history(
        self,
        symbol: str,
        period: str = "D",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> List[KLineData]:
        """
        获取历史 K 线数据

        Args:
            symbol: 标的代码 (如: 000001.SZ)
            period: 周期 D/W/M (日线/周线/月线)
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            limit: 最大条数

        Returns:
            KLineData 列表
        """
        if not self.pro:
            return []

        try:
            loop = asyncio.get_event_loop()
            ts_code = self._parse_symbol(symbol)

            # 设置默认日期范围
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=limit)
                start_date = start.strftime('%Y%m%d')

            # 根据周期选择接口
            if period in ["D", "daily"]:
                df = await loop.run_in_executor(
                    None,
                    lambda: self.pro.daily(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                )
            elif period in ["W", "weekly"]:
                df = await loop.run_in_executor(
                    None,
                    lambda: self.pro.weekly(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                )
            elif period in ["M", "monthly"]:
                df = await loop.run_in_executor(
                    None,
                    lambda: self.pro.monthly(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                )
            else:
                raise ValueError(f"不支持的周期: {period}")

            if df is None or df.empty:
                return []

            # 转换为 KLineData
            klines = []
            for _, row in df.iterrows():
                kline = KLineData(
                    symbol=symbol,
                    timestamp=datetime.strptime(str(row['trade_date']), '%Y%m%d'),
                    open=Decimal(str(row['open'])),
                    high=Decimal(str(row['high'])),
                    low=Decimal(str(row['low'])),
                    close=Decimal(str(row['close'])),
                    volume=int(row['vol'] * 100),  # 转换为股
                    amount=Decimal(str(row['amount'] * 1000)) if 'amount' in row else None,
                    period=period
                )
                klines.append(kline)

            # 按时间排序
            klines.sort(key=lambda x: x.timestamp)
            return klines[-limit:]

        except Exception as e:
            logger.error(f"Tushare 获取 {symbol} K线失败: {e}")
            return []

    async def get_stock_list(self) -> List[Dict[str, str]]:
        """
        获取 A 股股票列表

        Returns:
            [{"symbol": "000001.SZ", "name": "平安银行"}, ...]
        """
        if not self.pro:
            return []

        try:
            loop = asyncio.get_event_loop()

            df = await loop.run_in_executor(
                None,
                lambda: self.pro.query(
                    'stock_basic',
                    exchange='',
                    list_status='L',
                    fields='ts_code,symbol,name'
                )
            )

            if df is None or df.empty:
                return []

            stocks = []
            for _, row in df.iterrows():
                ts_code = row['ts_code']
                # 转换为统一格式
                if '.' in ts_code:
                    code, exchange = ts_code.split('.')
                else:
                    code = row.get('symbol', ts_code)
                    # 根据代码规则判断交易所
                    if code.startswith('6'):
                        exchange = 'SH'
                    else:
                        exchange = 'SZ'

                stocks.append({
                    "symbol": f"{code}.{exchange}",
                    "name": row['name'],
                    "code": code
                })

            return stocks

        except Exception as e:
            logger.error(f"Tushare 获取股票列表失败: {e}")
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
        if not self.pro:
            return []

        try:
            loop = asyncio.get_event_loop()

            df = await loop.run_in_executor(
                None,
                lambda: self.pro.query(
                    'trade_cal',
                    start_date=start_date,
                    end_date=end_date,
                    is_open='1'
                )
            )

            if df is None or df.empty:
                return []

            return df['cal_date'].tolist()

        except Exception as e:
            logger.error(f"Tushare 获取交易日历失败: {e}")
            return []
