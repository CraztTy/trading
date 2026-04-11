"""
风控管理器

集成仓位管理、止损止盈到策略执行流程
提供统一的风控接口给策略使用
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any
import asyncio

from src.risk.position_manager import PositionManager, PositionLimit, PositionLimitType
from src.risk.stop_loss import (
    StopLossManager, StopLossType, TakeProfitType,
    StopLossResult, TakeProfitResult
)
from src.strategy.base import StrategyBase, BarData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass
class RiskConfig:
    """风控配置"""
    # 仓位限制
    max_single_stock: Decimal = Decimal("0.10")      # 单票最大10%
    max_total_position: Decimal = Decimal("0.80")    # 总仓位最大80%

    # 止损设置
    default_stop_loss_pct: Decimal = Decimal("0.05")  # 默认止损5%
    default_take_profit_pct: Decimal = Decimal("0.10") # 默认止盈10%

    # 监控设置
    enable_stop_loss_monitor: bool = True
    enable_position_check: bool = True
    check_interval: float = 1.0


@dataclass
class TradeSignal:
    """交易信号（风控系统使用）"""
    symbol: str
    direction: str  # BUY or SELL
    qty: int
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    reason: str = ""


class RiskManager:
    """
    风控管理器

    职责：
    - 统一管理仓位和止损止盈
    - 在策略下单前进行风控检查
    - 实时监控持仓风险
    - 触发止损止盈时自动执行
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

        # 初始化仓位管理器
        self.position_manager = PositionManager(
            initial_capital=Decimal("1000000")
        )
        self.position_manager.set_default_limits(
            max_single_stock=self.config.max_single_stock,
            max_total=self.config.max_total_position
        )

        # 初始化止损止盈管理器
        self.stop_loss_manager = StopLossManager(
            check_interval=self.config.check_interval
        )

        # 绑定回调
        self.stop_loss_manager.on_stop_loss(self._on_stop_loss_triggered)
        self.stop_loss_manager.on_take_profit(self._on_take_profit_triggered)
        self.position_manager.on_warning(self._on_position_warning)

        # 策略引用（用于执行止损止盈）
        self._strategy: Optional[StrategyBase] = None

        # 风控拦截回调
        self._reject_callbacks: List[Callable[[str, str], None]] = []

        logger.info("风控管理器初始化完成")

    async def start(self) -> None:
        """启动风控监控"""
        if self.config.enable_stop_loss_monitor:
            await self.stop_loss_manager.start_monitoring()
        logger.info("风控监控已启动")

    async def stop(self) -> None:
        """停止风控监控"""
        await self.stop_loss_manager.stop_monitoring()
        logger.info("风控监控已停止")

    def bind_strategy(self, strategy: StrategyBase) -> None:
        """绑定策略（用于执行止损止盈）"""
        self._strategy = strategy

    # ============ 风控检查接口 ============

    def check_trade(self, signal: TradeSignal) -> tuple[bool, Optional[str]]:
        """
        检查交易信号是否可以通过风控

        Returns:
            (是否允许, 拒绝原因)
        """
        # 买入检查
        if signal.direction == "BUY":
            return self._check_buy_signal(signal)

        # 卖出检查（通常都允许）
        return True, None

    def _check_buy_signal(self, signal: TradeSignal) -> tuple[bool, Optional[str]]:
        """检查买入信号"""
        # 检查仓位限制
        if self.config.enable_position_check:
            can_open, reason = self.position_manager.can_open_position(
                signal.symbol,
                signal.qty,
                signal.price or Decimal("0")
            )
            if not can_open:
                return False, f"仓位限制: {reason}"

        return True, None

    # ============ 持仓管理接口 ============

    def on_position_opened(
        self,
        symbol: str,
        quantity: int,
        avg_cost: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None
    ) -> None:
        """
        持仓建立后调用

        - 更新仓位管理器
        - 设置止损止盈
        """
        # 更新仓位
        self.position_manager.update_position(symbol, quantity, avg_cost, avg_cost)

        # 设置止损
        if stop_loss:
            self.stop_loss_manager.add_stop_loss(
                symbol=symbol,
                position_qty=quantity,
                entry_price=avg_cost,
                stop_type=StopLossType.FIXED,
                stop_price=stop_loss
            )
        elif self.config.default_stop_loss_pct > 0:
            # 使用默认止损比例
            self.stop_loss_manager.add_stop_loss(
                symbol=symbol,
                position_qty=quantity,
                entry_price=avg_cost,
                stop_type=StopLossType.PERCENTAGE,
                stop_pct=self.config.default_stop_loss_pct
            )

        # 设置止盈
        if take_profit:
            self.stop_loss_manager.add_take_profit(
                symbol=symbol,
                position_qty=quantity,
                entry_price=avg_cost,
                tp_type=TakeProfitType.FIXED,
                target_price=take_profit
            )
        elif self.config.default_take_profit_pct > 0:
            # 使用默认止盈比例
            self.stop_loss_manager.add_take_profit(
                symbol=symbol,
                position_qty=quantity,
                entry_price=avg_cost,
                tp_type=TakeProfitType.PERCENTAGE,
                target_pct=self.config.default_take_profit_pct
            )

        logger.info(f"风控: 已建立 {symbol} 的仓位和风控设置")

    def on_position_closed(self, symbol: str) -> None:
        """持仓关闭后调用"""
        # 移除仓位
        self.position_manager.remove_position(symbol)

        # 移除止损止盈
        self.stop_loss_manager.remove_stop_loss(symbol)
        self.stop_loss_manager.remove_take_profit(symbol)

        logger.info(f"风控: 已清除 {symbol} 的风控设置")

    def on_position_reduced(self, symbol: str, remaining_qty: int) -> None:
        """持仓减少后调用（部分平仓）"""
        pos = self.position_manager.get_position(symbol)
        if pos:
            # 更新仓位数量
            self.position_manager.update_position(
                symbol, remaining_qty, pos.avg_cost, pos.market_price
            )

            # 如果全部平仓，移除风控设置
            if remaining_qty == 0:
                self.on_position_closed(symbol)

    # ============ 实时数据更新 ============

    def on_bar_update(self, bar: BarData) -> None:
        """K线数据更新时调用"""
        symbol = bar.symbol
        price = bar.close

        # 更新仓位市值
        self.position_manager.update_market_price(symbol, price)

        # 更新止损止盈价格
        self.stop_loss_manager.update_price(symbol, price)

    def on_tick_update(self, symbol: str, price: Decimal) -> None:
        """Tick数据更新时调用"""
        # 更新仓位市值
        self.position_manager.update_market_price(symbol, price)

        # 更新止损止盈价格
        self.stop_loss_manager.update_price(symbol, price)

    # ============ 回调处理 ============

    def _on_stop_loss_triggered(self, result: StopLossResult) -> None:
        """止损触发回调"""
        logger.warning(
            f"风控: 止损触发 {result.symbol} @ {result.stop_price}, "
            f"盈亏: {result.pnl}"
        )

        # 通过策略执行平仓
        if self._strategy:
            try:
                self._strategy.close_position(
                    result.symbol,
                    reason=f"止损触发: {result.reason}"
                )
            except (ValueError, TypeError, RuntimeError) as e:
                logger.error(f"止损平仓失败: {e}")

        # 触发外部回调
        for callback in self._reject_callbacks:
            try:
                callback(result.symbol, f"止损: {result.reason}")
            except (ValueError, TypeError, RuntimeError) as e:
                logger.error(f"止损回调失败: {e}")

    def _on_take_profit_triggered(self, result: TakeProfitResult) -> None:
        """止盈触发回调"""
        logger.info(
            f"风控: 止盈触发 {result.symbol} @ {result.target_price}, "
            f"原因: {result.reason}"
        )

        # 通过策略执行平仓（如果是全部止盈）
        if self._strategy and not result.partial_qty:
            try:
                self._strategy.close_position(
                    result.symbol,
                    reason=f"止盈触发: {result.reason}"
                )
            except (ValueError, TypeError, RuntimeError) as e:
                logger.error(f"止盈平仓失败: {e}")
        elif self._strategy and result.partial_qty:
            # 分批止盈
            try:
                self._strategy.sell(
                    result.symbol,
                    result.partial_qty,
                    price=result.target_price,
                    reason=f"分批止盈 {result.level}"
                )
            except (ValueError, TypeError, RuntimeError) as e:
                logger.error(f"分批止盈失败: {e}")

    def _on_position_warning(self, warnings: List[Dict]) -> None:
        """仓位预警回调"""
        for warning in warnings:
            logger.warning(
                f"风控: 仓位预警 {warning.get('symbol')}: {warning.get('message')}"
            )

    # ============ 外部接口 ============

    def on_reject(self, callback: Callable[[str, str], None]) -> None:
        """注册风控拦截回调"""
        self._reject_callbacks.append(callback)

    def get_risk_report(self) -> Dict[str, Any]:
        """获取风控报告"""
        position_report = self.position_manager.get_position_report()
        active_orders = self.stop_loss_manager.get_active_orders()

        return {
            "timestamp": datetime.now().isoformat(),
            "position": position_report,
            "stop_loss": {
                symbol: {
                    "stop_price": str(order.stop_price) if order.stop_price else None,
                    "type": order.stop_loss_type.value,
                    "is_active": order.is_active
                }
                for symbol, order in active_orders["stop_losses"].items()
            },
            "take_profit": {
                symbol: {
                    "target_price": str(order.target_price) if order.target_price else None,
                    "type": order.take_profit_type.value,
                    "is_active": order.is_active
                }
                for symbol, order in active_orders["take_profits"].items()
            }
        }

    def update_stop_loss(self, symbol: str, new_stop_price: Decimal) -> bool:
        """手动更新止损价"""
        return self.stop_loss_manager.update_stop_loss_price(symbol, new_stop_price)

    def update_take_profit(self, symbol: str, new_target_price: Decimal) -> bool:
        """手动更新止盈价"""
        return self.stop_loss_manager.update_take_profit_price(symbol, new_target_price)

    def emergency_close_all(self) -> None:
        """紧急清仓（熔断等场景）"""
        logger.critical("风控: 执行紧急清仓！")

        if self._strategy:
            positions = self.position_manager.get_all_positions()
            for symbol in positions.keys():
                try:
                    self._strategy.close_position(symbol, reason="紧急清仓")
                except Exception as e:
                    logger.error(f"紧急清仓 {symbol} 失败: {e}")
