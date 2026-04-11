"""
回测引擎

提供完整的回测功能：
- 历史数据回测
- 模拟交易执行
- 绩效分析
- 回测报告
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
import asyncio

from src.strategy.base import (
    StrategyBase, StrategyContext, BarData, Signal,
    SignalType, Position, AccountInfo
)
from src.strategy.indicators import IndicatorEngine
from src.backtest.data_loader import HistoryDataLoader, HistoryDataRequest
from src.backtest.metrics import MetricsCalculator, TradeRecord, DailyPortfolio, BacktestMetrics
from src.common.logger import TradingLogger
from src.models.enums import OrderDirection, OrderType

logger = TradingLogger(__name__)


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal("1000000")
    commission_rate: float = 0.0003  # 佣金率
    min_commission: float = 5.0  # 最低佣金
    stamp_tax_rate: float = 0.001  # 印花税率（卖出）
    slippage: float = 0.0  # 滑点


@dataclass
class BacktestResult:
    """回测结果"""
    config: BacktestConfig
    metrics: BacktestMetrics
    daily_portfolios: List[DailyPortfolio] = field(default_factory=list)
    trades: List[TradeRecord] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)

    def print_report(self) -> None:
        """打印回测报告"""
        print("\n" + "=" * 60)
        print("回测报告")
        print("=" * 60)

        for category, items in self.metrics.to_dict().items():
            print(f"\n【{category}】")
            for key, value in items.items():
                print(f"  {key}: {value}")

        print("\n" + "=" * 60)


class BacktestContext(StrategyContext):
    """回测专用策略上下文"""

    def __init__(
        self,
        strategy_id: str,
        initial_capital: Decimal = Decimal("1000000"),
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 0.001
    ):
        super().__init__(strategy_id, initial_capital)

        # 回测专用配置
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_tax_rate = stamp_tax_rate

        # 持仓成本记录: symbol -> avg_price
        self._position_costs: Dict[str, Decimal] = {}

        # 交易记录
        self.trades: List[TradeRecord] = []

        # 每日持仓记录
        self.daily_portfolios: List[DailyPortfolio] = []

        # 当前日期（用于回测时间推进）
        self._current_date: Optional[datetime] = None

    def buy(
        self,
        symbol: str,
        volume: int,
        price: Optional[Decimal] = None,
        reason: str = ""
    ) -> Optional[str]:
        """买入（回测版本）"""
        if price is None:
            # 从最新 bar 获取价格
            bar = self.get_latest_bar(symbol)
            if bar:
                price = bar.close
            else:
                logger.warning(f"无法获取 {symbol} 价格，无法买入")
                return None

        # 计算金额
        amount = price * volume

        # 计算佣金
        commission = max(amount * Decimal(str(self.commission_rate)), Decimal(str(self.min_commission)))

        # 检查资金
        total_cost = amount + commission
        if total_cost > self.current_capital:
            logger.warning(f"资金不足: 需要 {total_cost}, 可用 {self.current_capital}")
            return None

        # 执行买入
        self.current_capital -= total_cost

        # 更新持仓
        current_qty = self._positions.get(symbol, Position(
            symbol=symbol, quantity=0, avg_price=Decimal("0"),
            current_price=price, market_value=Decimal("0"), unrealized_pnl=Decimal("0")
        )).quantity

        new_qty = current_qty + volume

        # 计算新的平均成本
        if current_qty > 0:
            old_cost = self._position_costs.get(symbol, Decimal("0")) * current_qty
            new_cost = old_cost + amount
            avg_cost = new_cost / new_qty
        else:
            avg_cost = price

        self._position_costs[symbol] = avg_cost

        # 创建持仓对象
        position = Position(
            symbol=symbol,
            quantity=new_qty,
            avg_price=avg_cost,
            current_price=price,
            market_value=price * new_qty,
            unrealized_pnl=Decimal("0")
        )
        self._positions[symbol] = position

        # 记录交易
        trade = TradeRecord(
            timestamp=self._current_date or datetime.now(),
            symbol=symbol,
            side="BUY",
            qty=volume,
            price=price,
            amount=amount,
            commission=commission
        )
        self.trades.append(trade)

        order_id = f"BACKTEST_BUY_{len(self.trades)}"
        logger.info(f"[回测] 买入 {symbol} {volume}股 @ {price}, 佣金: {commission}")

        return order_id

    def sell(
        self,
        symbol: str,
        volume: int,
        price: Optional[Decimal] = None,
        reason: str = ""
    ) -> Optional[str]:
        """卖出（回测版本）"""
        position = self._positions.get(symbol)
        if not position or position.quantity < volume:
            logger.warning(f"持仓不足: 需要 {volume}, 可用 {position.quantity if position else 0}")
            return None

        if price is None:
            bar = self.get_latest_bar(symbol)
            if bar:
                price = bar.close
            else:
                logger.warning(f"无法获取 {symbol} 价格，无法卖出")
                return None

        # 计算金额
        amount = price * volume

        # 计算佣金和印花税
        commission = max(amount * Decimal(str(self.commission_rate)), Decimal(str(self.min_commission)))
        stamp_tax = amount * Decimal(str(self.stamp_tax_rate))
        total_cost = commission + stamp_tax

        # 计算盈亏
        cost_price = self._position_costs.get(symbol, price)
        pnl = (price - cost_price) * volume

        # 执行卖出
        self.current_capital += amount - total_cost

        # 更新持仓
        new_qty = position.quantity - volume
        if new_qty > 0:
            position.quantity = new_qty
            position.market_value = price * new_qty
        else:
            # 清仓
            del self._positions[symbol]
            if symbol in self._position_costs:
                del self._position_costs[symbol]

        # 记录交易
        trade = TradeRecord(
            timestamp=self._current_date or datetime.now(),
            symbol=symbol,
            side="SELL",
            qty=volume,
            price=price,
            amount=amount,
            commission=commission + stamp_tax,
            pnl=pnl
        )
        self.trades.append(trade)

        order_id = f"BACKTEST_SELL_{len(self.trades)}"
        logger.info(f"[回测] 卖出 {symbol} {volume}股 @ {price}, 盈亏: {pnl}, 税费: {total_cost}")

        return order_id

    def record_daily_portfolio(self, date: datetime) -> None:
        """记录每日持仓"""
        self._current_date = date

        # 计算总市值
        market_value = Decimal("0")
        for symbol, position in self._positions.items():
            # 获取最新价格
            bar = self.get_latest_bar(symbol)
            if bar:
                price = bar.close
            else:
                price = position.current_price

            market_value += price * position.quantity

        total_value = self.current_capital + market_value

        portfolio = DailyPortfolio(
            date=date,
            cash=self.current_capital,
            market_value=market_value,
            total_value=total_value,
            positions={s: p.quantity for s, p in self._positions.items()}
        )
        self.daily_portfolios.append(portfolio)


class BacktestEngine:
    """
    回测引擎

    使用示例:
    ```python
    engine = BacktestEngine()
    config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=Decimal("1000000")
    )
    result = await engine.run(strategy, config)
    result.print_report()
    ```
    """

    def __init__(self):
        self.data_loader = HistoryDataLoader()
        self.metrics_calculator = MetricsCalculator()
        self.indicator_engine = IndicatorEngine()

    async def run(
        self,
        strategy: StrategyBase,
        config: BacktestConfig
    ) -> BacktestResult:
        """
        执行回测

        Args:
            strategy: 策略实例
            config: 回测配置

        Returns:
            BacktestResult 回测结果
        """
        logger.info(
            f"开始回测: {strategy.strategy_id} "
            f"({config.start_date.date()} ~ {config.end_date.date()})"
        )

        # 创建回测上下文
        context = BacktestContext(
            strategy_id=strategy.strategy_id,
            initial_capital=config.initial_capital,
            commission_rate=config.commission_rate,
            min_commission=config.min_commission,
            stamp_tax_rate=config.stamp_tax_rate
        )

        # 初始化策略
        strategy.initialize(context)
        strategy.start()

        # 加载历史数据
        all_bars: Dict[str, List[BarData]] = {}
        for symbol in strategy.symbols:
            request = HistoryDataRequest(
                symbol=symbol,
                start_date=config.start_date,
                end_date=config.end_date,
                period="1d"
            )
            bars = await self.data_loader.load_bars(request)
            all_bars[symbol] = bars
            logger.info(f"加载 {symbol} 数据: {len(bars)} 条")

        # 合并所有日期的 bar
        all_dates = set()
        for bars in all_bars.values():
            for bar in bars:
                all_dates.add(bar.timestamp.date())

        sorted_dates = sorted(all_dates)
        logger.info(f"回测总天数: {len(sorted_dates)}")

        # 回测主循环
        for current_date in sorted_dates:
            # 更新每个标的的最新 bar
            for symbol, bars in all_bars.items():
                for bar in bars:
                    if bar.timestamp.date() == current_date:
                        context._update_bar(bar)
                        strategy.on_bar(bar)
                        break

            # 记录每日持仓
            context.record_daily_portfolio(
                datetime.combine(current_date, datetime.min.time())
            )

        # 停止策略
        strategy.stop()

        # 计算绩效指标
        metrics = self.metrics_calculator.calculate(
            daily_portfolios=context.daily_portfolios,
            trades=context.trades
        )

        # 构建结果
        result = BacktestResult(
            config=config,
            metrics=metrics,
            daily_portfolios=context.daily_portfolios,
            trades=context.trades,
            signals=strategy.signals
        )

        logger.info(
            f"回测完成: 总收益率 {metrics.total_return * 100:.2f}%, "
            f"夏普比率 {metrics.sharpe_ratio:.2f}"
        )

        return result
