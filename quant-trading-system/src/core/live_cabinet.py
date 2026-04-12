"""
实盘内阁

职责：
- 实时数据获取
- 策略预热和历史状态初始化
- 实时风控监控
- 虚拟资金池管理
- 信号推送和告警
- 自动/手动/模拟交易模式切换
"""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import asyncio
from src.common.logger import TradingLogger
from src.core.crown_prince import CrownPrince
from src.core.zhongshu_sheng import ZhongshuSheng
from src.core.menxia_sheng import MenxiaSheng
from src.core.shangshu_sheng import ShangshuSheng
from src.core.auto_trader import auto_trader, TradeMode
from src.core.signal_publisher import signal_publisher, SignalEvent

logger = TradingLogger(__name__)


class LiveCabinet:
    """
    实盘内阁 - 管理实时监控和交易执行
    """

    def __init__(self, config: dict):
        self.config = config
        self.running = False
        self.task = None

        # 初始化三省
        self.crown_prince = CrownPrince(config)
        self.zhongshu = ZhongshuSheng(config)
        self.menxia = MenxiaSheng(config)
        self.shangshu = ShangshuSheng(config)

        # 监控股票列表
        self.watch_list: set = set()
        self.active_strategies: List[str] = []

        # 实时数据提供商
        self.data_provider = None

        # 回调函数
        self.on_signal: Optional[Callable] = None
        self.on_trade: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        # 交易模式
        self.trade_mode = TradeMode.MANUAL

        # 订阅信号
        signal_publisher.subscribe(self._on_signal)

    def set_data_provider(self, provider):
        """设置数据提供者"""
        self.data_provider = provider

    def set_callbacks(
        self,
        on_signal: Optional[Callable] = None,
        on_trade: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        """设置回调函数"""
        self.on_signal = on_signal
        self.on_trade = on_trade
        self.on_error = on_error

    async def start(
        self,
        symbols: List[str],
        strategies: List[str],
        auto_trade: bool = False
    ):
        """
        启动实盘监控

        Args:
            symbols: 监控股票列表
            strategies: 激活策略列表
            auto_trade: 是否自动执行交易
        """
        if self.running:
            logger.warning("实盘监控已在运行中")
            return

        logger.info(f"启动实盘监控: 股票{len(symbols)}只, 策略{len(strategies)}个")

        self.running = True
        self.watch_list = set(symbols)
        self.active_strategies = strategies

        # 1. 初始化数据源
        if not self.data_provider:
            raise ValueError("数据提供者未设置")

        # 2. 策略预热
        await self._warmup_strategies(strategies)

        # 3. 加载历史状态
        portfolio = await self._load_portfolio_state()

        # 4. 启动主循环
        self.task = asyncio.create_task(
            self._main_loop(strategies, portfolio, auto_trade)
        )

    async def stop(self):
        """停止实盘监控"""
        logger.info("停止实盘监控")
        self.running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    async def _main_loop(
        self,
        strategies: List[str],
        portfolio: Dict,
        auto_trade: bool
    ):
        """实盘主循环"""
        poll_interval = self.config.get('poll_interval', 5)

        while self.running:
            try:
                # 获取实时行情
                market_data = await self.data_provider.get_latest_bars(
                    list(self.watch_list)
                )

                for code, bar in market_data.items():
                    # 数据校验
                    valid_bar = await self.crown_prince.validate_and_distribute(
                        bar, code
                    )
                    if valid_bar is None:
                        continue

                    # 生成信号
                    signals = await self.zhongshu.generate_signals(
                        valid_bar, code, strategies
                    )

                    # 风控审核
                    passed, rejected = await self.menxia.review_signals(
                        signals, portfolio
                    )

                    # 推送信号通知
                    if passed:
                        await self._notify_signals(passed, 'PASS', market_data)
                    if rejected:
                        await self._notify_signals(rejected, 'REJECT', market_data)

                    # 执行交易(如配置了自动交易)
                    if passed and auto_trade:
                        executed = await self.shangshu.execute_orders(passed, market_data)
                        for trade in executed:
                            await self._notify_trade(trade)

                    # 检查止盈止损
                    stop_signals = await self.shangshu.check_stops(
                        portfolio.get('positions', {}), market_data
                    )
                    if stop_signals:
                        await self._notify_signals(stop_signals, 'STOP', market_data)
                        if auto_trade:
                            stop_executed = await self.shangshu.execute_orders(
                                stop_signals, market_data
                            )
                            for trade in stop_executed:
                                await self._notify_trade(trade)

                # 保存状态
                await self._save_portfolio_state(portfolio)

                # 等待下一次轮询
                await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                logger.info("实盘循环已取消")
                break
            except Exception as e:
                logger.error(f"实盘循环错误: {e}")
                if self.on_error:
                    await self.on_error(str(e))
                await asyncio.sleep(poll_interval)

    async def _notify_signals(
        self,
        signals: List[Dict],
        status: str,
        market_data: Dict
    ):
        """推送信号通知"""
        for signal in signals:
            signal['status'] = status
            signal['timestamp'] = datetime.now().isoformat()
            signal['market_price'] = market_data.get(signal.get('code', ''), {}).get('close')

            logger.info(f"信号通知 [{status}]: {signal.get('code')} {signal.get('direction')}")

            if self.on_signal:
                await self.on_signal(signal)

    async def _notify_trade(self, trade: Dict):
        """推送交易通知"""
        logger.info(f"交易执行: {trade.get('code')} {trade.get('direction')} {trade.get('qty')}@{trade.get('price')}")

        if self.on_trade:
            await self.on_trade(trade)

    async def _warmup_strategies(self, strategies: List[str]):
        """策略预热"""
        logger.info("策略预热中...")
        # 加载策略历史状态
        for strategy_id in strategies:
            # 从数据库或缓存加载策略上下文
            pass
        logger.info(f"策略预热完成: {len(strategies)}个策略")

    async def _load_portfolio_state(self) -> Dict:
        """加载账户状态"""
        # 从数据库加载
        # 这里简化实现，使用初始值
        initial_capital = self.config.get('initial_capital', 1000000.0)
        return {
            'cash': initial_capital,
            'total_value': initial_capital,
            'positions': {}
        }

    async def _save_portfolio_state(self, portfolio: Dict):
        """保存账户状态"""
        # 保存到数据库或缓存
        pass

    def get_status(self) -> Dict[str, Any]:
        """获取运行状态"""
        return {
            'running': self.running,
            'watch_list': list(self.watch_list),
            'active_strategies': self.active_strategies,
            'portfolio': self.shangshu.get_portfolio_state()
        }

    def add_symbol(self, symbol: str):
        """添加监控股票"""
        self.watch_list.add(symbol)
        logger.info(f"添加监控: {symbol}")

    def remove_symbol(self, symbol: str):
        """移除监控股票"""
        self.watch_list.discard(symbol)
        logger.info(f"移除监控: {symbol}")

    def add_strategy(self, strategy_id: str):
        """添加策略"""
        if strategy_id not in self.active_strategies:
            self.active_strategies.append(strategy_id)
            logger.info(f"添加策略: {strategy_id}")

    def remove_strategy(self, strategy_id: str):
        """移除策略"""
        if strategy_id in self.active_strategies:
            self.active_strategies.remove(strategy_id)
            logger.info(f"移除策略: {strategy_id}")

    async def _on_signal(self, event: SignalEvent):
        """处理信号"""
        # 调用自动交易器处理
        result = await auto_trader.process_signal(event)

        if result.simulated:
            logger.info(f"模拟交易: {event.symbol} {event.signal_type}")
        elif result.success:
            logger.info(f"自动下单: {event.symbol} {event.signal_type}")
        else:
            logger.info(f"信号处理: {result.message}")

    def set_trade_mode(self, mode: str):
        """设置交易模式"""
        trade_mode = TradeMode(mode)
        auto_trader.set_mode(trade_mode)
        self.trade_mode = trade_mode
        logger.info(f"实盘交易模式已切换: {mode}")

    def get_trade_mode(self) -> str:
        """获取当前交易模式"""
        return self.trade_mode.value

    def confirm_signal(self, signal_id: str) -> dict:
        """手动确认信号并下单"""
        import asyncio

        result = asyncio.run(auto_trader.confirm_signal(signal_id))
        return {
            "success": result.success,
            "order_id": result.order_id,
            "message": result.message,
            "simulated": result.simulated
        }

    def ignore_signal(self, signal_id: str) -> bool:
        """忽略信号"""
        return auto_trader.ignore_signal(signal_id)

    def get_pending_signals(self) -> dict:
        """获取待确认的信号列表"""
        pending = auto_trader.get_pending_signals()
        return {
            signal_id: {
                "id": signal.id,
                "symbol": signal.symbol,
                "signal_type": signal.signal_type,
                "price": float(signal.price) if signal.price else None,
                "volume": signal.volume,
                "timestamp": signal.timestamp.isoformat() if signal.timestamp else None
            }
            for signal_id, signal in pending.items()
        }

    def get_simulated_trades(self) -> list:
        """获取模拟交易记录"""
        return auto_trader.get_simulated_trades()
