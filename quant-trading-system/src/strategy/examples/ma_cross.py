"""
双均线交叉策略

策略逻辑：
- 短期均线上穿长期均线（金叉）→ 买入
- 短期均线下穿长期均线（死叉）→ 卖出

参数：
- fast_period: 短期均线周期，默认 5
- slow_period: 长期均线周期，默认 20
- volume_threshold: 成交量阈值（可选）
"""
from decimal import Decimal
from typing import List, Optional

import numpy as np
import pandas as pd

from src.strategy.base import StrategyBase, StrategyContext, BarData, TickData
from src.strategy.base import Signal, SignalType
from src.strategy.indicators import MovingAverage, MACD
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class MACrossStrategy(StrategyBase):
    """
    双均线交叉策略

    示例配置：
    {
        "fast_period": 5,
        "slow_period": 20,
        "volume_threshold": 100000
    }
    """

    def __init__(self, strategy_id: str, name: str, symbols: List[str], params: Optional[dict] = None):
        super().__init__(strategy_id, name, symbols, params)

        # 参数设置
        self.fast_period = self.params.get("fast_period", 5)
        self.slow_period = self.params.get("slow_period", 20)
        self.volume_threshold = self.params.get("volume_threshold", 0)

        # 状态
        self._bars: dict = {symbol: [] for symbol in symbols}
        self._position: dict = {symbol: 0 for symbol in symbols}  # 当前持仓
        self._last_signal: dict = {symbol: None for symbol in symbols}

        logger.info(
            f"[{strategy_id}] 双均线策略初始化: "
            f"fast={self.fast_period}, slow={self.slow_period}"
        )

    def on_init(self, context: StrategyContext) -> None:
        """初始化 - 加载历史数据计算初始均线"""
        logger.info(f"[{self.strategy_id}] 策略初始化中...")

        for symbol in self.symbols:
            # 加载足够的历史数据
            bars = context.get_bars(symbol, n=self.slow_period + 10)
            self._bars[symbol] = bars

            if len(bars) >= self.slow_period:
                self._update_ma(symbol)

        logger.info(f"[{self.strategy_id}] 初始化完成，数据已加载")

    def on_bar(self, bar: BarData) -> None:
        """K线触发 - 执行策略逻辑"""
        symbol = bar.symbol

        # 更新K线缓存
        self._bars[symbol].append(bar)
        if len(self._bars[symbol]) > self.slow_period + 20:
            self._bars[symbol].pop(0)

        # 数据不足时不交易
        if len(self._bars[symbol]) < self.slow_period:
            return

        # 成交量过滤
        if self.volume_threshold > 0 and bar.volume < self.volume_threshold:
            return

        # 计算均线
        fast_ma, slow_ma, signal = self._update_ma(symbol)

        if signal is None:
            return

        # 获取当前持仓
        position = self.get_position_quantity(symbol)

        # 交易逻辑
        if signal == 1 and position <= 0:
            # 金叉买入
            self._buy_signal(bar, fast_ma, slow_ma)

        elif signal == -1 and position > 0:
            # 死叉卖出
            self._sell_signal(bar, fast_ma, slow_ma)

    def on_tick(self, tick: TickData) -> None:
        """Tick触发 - 实盘高频场景使用"""
        # 双均线策略通常在K线级别交易，Tick级别可用于止损
        pass

    def _update_ma(self, symbol: str):
        """
        更新均线并检测信号

        Returns:
            (fast_ma_value, slow_ma_value, signal)
            signal: 1=金叉, -1=死叉, None=无信号
        """
        bars = self._bars[symbol]
        closes = np.array([float(b.close) for b in bars])

        # 计算均线
        fast_ma = MovingAverage.sma(closes, self.fast_period)
        slow_ma = MovingAverage.sma(closes, self.slow_period)

        # 检测交叉
        signal = None
        if len(fast_ma) >= 2 and len(slow_ma) >= 2:
            prev_fast = fast_ma[-2]
            prev_slow = slow_ma[-2]
            curr_fast = fast_ma[-1]
            curr_slow = slow_ma[-1]

            # 金叉: 快线从下向上穿越慢线
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                signal = 1
            # 死叉: 快线从上向下穿越慢线
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                signal = -1

        return fast_ma[-1] if len(fast_ma) > 0 else None, \
               slow_ma[-1] if len(slow_ma) > 0 else None, \
               signal

    def _buy_signal(self, bar: BarData, fast_ma: float, slow_ma: float) -> None:
        """买入信号"""
        symbol = bar.symbol

        # 计算买入数量（示例：固定买入1手）
        volume = 100  # 1手 = 100股

        # 发送买入订单
        order_id = self.buy(
            symbol=symbol,
            volume=volume,
            price=bar.close,
            reason=f"金叉: MA{self.fast_period}({fast_ma:.2f}) 上穿 MA{self.slow_period}({slow_ma:.2f})"
        )

        if order_id:
            self._position[symbol] = volume

            # 发出信号
            self.emit_signal(Signal(
                type=SignalType.BUY,
                symbol=symbol,
                timestamp=bar.timestamp,
                price=bar.close,
                volume=volume,
                confidence=0.7,
                reason=f"双均线金叉: {self.fast_period}/{self.slow_period}",
                metadata={
                    "fast_ma": float(fast_ma),
                    "slow_ma": float(slow_ma),
                    "order_id": order_id
                }
            ))

            logger.info(
                f"[{self.strategy_id}] 买入信号: {symbol} @ {bar.close} "
                f"(MA{self.fast_period}={fast_ma:.2f}, MA{self.slow_period}={slow_ma:.2f})"
            )

    def _sell_signal(self, bar: BarData, fast_ma: float, slow_ma: float) -> None:
        """卖出信号"""
        symbol = bar.symbol

        # 发送卖出订单
        order_id = self.sell(
            symbol=symbol,
            volume=self._position[symbol],
            price=bar.close,
            reason=f"死叉: MA{self.fast_period}({fast_ma:.2f}) 下穿 MA{self.slow_period}({slow_ma:.2f})"
        )

        if order_id:
            self._position[symbol] = 0

            # 发出信号
            self.emit_signal(Signal(
                type=SignalType.SELL,
                symbol=symbol,
                timestamp=bar.timestamp,
                price=bar.close,
                volume=self._position[symbol],
                confidence=0.7,
                reason=f"双均线死叉: {self.fast_period}/{self.slow_period}",
                metadata={
                    "fast_ma": float(fast_ma),
                    "slow_ma": float(slow_ma),
                    "order_id": order_id
                }
            ))

            logger.info(
                f"[{self.strategy_id}] 卖出信号: {symbol} @ {bar.close} "
                f"(MA{self.fast_period}={fast_ma:.2f}, MA{self.slow_period}={slow_ma:.2f})"
            )

    def get_status(self) -> dict:
        """获取策略状态"""
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "state": self.state.value,
            "params": {
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
            },
            "positions": self._position,
            "bar_count": self._bar_count,
            "signal_count": len(self.signals),
        }
