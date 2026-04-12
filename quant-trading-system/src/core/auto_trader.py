"""
自动交易器

支持三种交易模式：
- AUTO: 自动下单
- MANUAL: 手动确认
- SIMULATE: 模拟交易
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Callable
from dataclasses import dataclass

from src.core.signal_publisher import SignalEvent
from src.core.shangshu_sheng import shangshu_sheng
from src.core.menxia_sheng import menxia_sheng
from src.strategy.base import SignalType
from src.models.enums import OrderDirection
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class TradeMode(Enum):
    """交易模式"""
    AUTO = "auto"           # 自动下单
    MANUAL = "manual"       # 手动确认
    SIMULATE = "simulate"   # 模拟交易
    PAUSE = "pause"         # 暂停交易


@dataclass
class TradeResult:
    """交易结果"""
    success: bool
    order_id: Optional[str]
    message: str
    simulated: bool = False


class AutoTrader:
    """自动交易器"""

    def __init__(self, account_id: int = 1):
        self.account_id = account_id
        self.trade_mode = TradeMode.MANUAL  # 默认手动模式

        # 风控检查开关
        self.enable_risk_check = True

        # 资金检查开关
        self.enable_capital_check = True

        # 模拟交易记录
        self._simulated_trades: list = []

        # 待确认信号（手动模式）
        self._pending_signals: Dict[str, SignalEvent] = {}

        # 回调
        self._on_trade_callbacks: list = []

        logger.info(f"自动交易器初始化，账户: {account_id}")

    def set_mode(self, mode: TradeMode):
        """设置交易模式"""
        old_mode = self.trade_mode
        self.trade_mode = mode
        logger.info(f"交易模式切换: {old_mode.value} -> {mode.value}")

    def get_mode(self) -> TradeMode:
        """获取当前交易模式"""
        return self.trade_mode

    async def process_signal(self, signal: SignalEvent) -> TradeResult:
        """
        处理信号

        根据当前交易模式决定如何处理
        """
        if self.trade_mode == TradeMode.PAUSE:
            return TradeResult(False, None, "交易已暂停")

        # 风控检查
        if self.enable_risk_check:
            risk_passed = await self._risk_check(signal)
            if not risk_passed:
                return TradeResult(False, None, "风控检查未通过")

        if self.trade_mode == TradeMode.AUTO:
            # 自动下单
            return await self._auto_execute(signal)

        elif self.trade_mode == TradeMode.MANUAL:
            # 加入待确认列表
            self._pending_signals[signal.id] = signal
            return TradeResult(False, None, "等待手动确认", simulated=False)

        elif self.trade_mode == TradeMode.SIMULATE:
            # 模拟交易
            return await self._simulate_execute(signal)

        return TradeResult(False, None, "未知的交易模式")

    async def confirm_signal(self, signal_id: str) -> TradeResult:
        """手动确认信号并下单"""
        if signal_id not in self._pending_signals:
            return TradeResult(False, None, "信号不存在或已过期")

        signal = self._pending_signals.pop(signal_id)
        return await self._auto_execute(signal)

    def ignore_signal(self, signal_id: str) -> bool:
        """忽略信号"""
        if signal_id in self._pending_signals:
            signal = self._pending_signals.pop(signal_id)
            # 更新信号状态
            from src.core.signal_publisher import signal_publisher
            signal_publisher.update_signal_status(signal_id, "ignored")
            logger.info(f"信号已忽略: {signal_id}")
            return True
        return False

    async def _risk_check(self, signal: SignalEvent) -> bool:
        """风控检查"""
        # 构建Signal对象
        from src.strategy.base import Signal
        s = Signal(
            type=SignalType.BUY if signal.signal_type == "buy" else SignalType.SELL,
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            price=signal.price,
            volume=signal.volume
        )

        # 调用门下省风控
        result = await menxia_sheng.audit_signal(s, {})
        return result.approved

    async def _auto_execute(self, signal: SignalEvent) -> TradeResult:
        """自动执行下单"""
        try:
            from src.strategy.base import Signal as BaseSignal, SignalType

            # 构建信号
            s = BaseSignal(
                type=SignalType.BUY if signal.signal_type == "buy" else SignalType.SELL,
                symbol=signal.symbol,
                timestamp=signal.timestamp,
                price=signal.price,
                volume=signal.volume
            )

            # 提交到尚书省
            request_id = await shangshu_sheng.submit_signal(
                signal=s,
                account_id=self.account_id
            )

            # 更新信号状态
            from src.core.signal_publisher import signal_publisher
            signal_publisher.update_signal_status(signal.id, "executed")

            logger.info(f"自动下单成功: {signal.id} -> {request_id}")

            return TradeResult(True, request_id, "下单成功")

        except Exception as e:
            logger.error(f"自动下单失败: {e}")
            return TradeResult(False, None, f"下单失败: {str(e)}")

    async def _simulate_execute(self, signal: SignalEvent) -> TradeResult:
        """模拟执行"""
        # 模拟成交
        simulated_order_id = f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}_{signal.id[:8]}"

        # 记录模拟交易
        self._simulated_trades.append({
            "order_id": simulated_order_id,
            "signal_id": signal.id,
            "symbol": signal.symbol,
            "type": signal.signal_type,
            "price": float(signal.price) if signal.price else 0,
            "volume": signal.volume,
            "timestamp": datetime.now().isoformat()
        })

        # 更新信号状态
        from src.core.signal_publisher import signal_publisher
        signal_publisher.update_signal_status(signal.id, "simulated")

        logger.info(f"模拟交易执行: {signal.id} -> {simulated_order_id}")

        return TradeResult(True, simulated_order_id, "模拟交易执行成功", simulated=True)

    def get_pending_signals(self) -> Dict[str, SignalEvent]:
        """获取待确认的信号"""
        return self._pending_signals.copy()

    def get_simulated_trades(self) -> list:
        """获取模拟交易记录"""
        return self._simulated_trades.copy()

    def on_trade(self, callback: Callable):
        """注册交易回调"""
        self._on_trade_callbacks.append(callback)


# 全局自动交易器实例
auto_trader = AutoTrader()
