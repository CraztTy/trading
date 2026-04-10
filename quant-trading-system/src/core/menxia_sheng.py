"""
门下省 - 风控审核与拦截

职责：
- 对每一个信号做强制风控审核
- 一票否决机制
- 实时风险计算
- 熔断机制
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass
class RiskCheckResult:
    """风控检查结果"""
    passed: bool
    rule_code: str
    message: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW


class MenxiaSheng:
    """门下省：风控审核中心"""

    def __init__(self, config: dict):
        self.config = config
        self.daily_stats = {}  # 日统计
        self.order_history = {}  # 委托历史

        # 风控参数
        self.max_position_per_stock = config.get('max_position_per_stock', 0.10)
        self.max_total_position = config.get('max_total_position', 0.50)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.01)
        self.max_daily_loss_pct = config.get('max_daily_loss_pct', 0.02)
        self.max_consecutive_losses = config.get('max_consecutive_losses', 3)

    async def review_signals(
        self,
        signals: List[Dict[str, Any]],
        portfolio_state: Dict[str, Any]
    ):
        """
        审核信号列表

        Returns:
            (通过的信号列表, 被拒绝的信号列表)
        """
        passed_signals = []
        rejected_signals = []

        for signal in signals:
            result = await self._review_single_signal(signal, portfolio_state)

            if result.passed:
                passed_signals.append(signal)
                logger.debug(f"信号通过风控审核: {signal.get('code')}")
            else:
                rejected_signal = {
                    **signal,
                    'reject_reason': result.message,
                    'reject_rule': result.rule_code
                }
                rejected_signals.append(rejected_signal)
                logger.warning(
                    f"信号被风控拦截: {signal.get('code')}, "
                    f"规则: {result.rule_code}, 原因: {result.message}"
                )

        return passed_signals, rejected_signals

    async def _review_single_signal(
        self,
        signal: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> RiskCheckResult:
        """审核单个信号"""
        checks = [
            self._check_stop_loss(signal),
            self._check_single_position(signal, portfolio),
            self._check_total_position(signal, portfolio),
            self._check_daily_loss(portfolio),
            self._check_consecutive_losses(portfolio),
            self._check_order_frequency(signal),
        ]

        for result in checks:
            if not result.passed:
                return result

        return RiskCheckResult(True, 'PASS', '所有风控规则通过', 'INFO')

    def _check_stop_loss(self, signal: Dict) -> RiskCheckResult:
        """检查止损设置"""
        stop_loss = signal.get('stop_loss')
        entry_price = signal.get('price')

        if stop_loss and entry_price:
            loss_pct = abs(entry_price - stop_loss) / entry_price
            if loss_pct > self.stop_loss_pct:
                return RiskCheckResult(
                    False, 'R001',
                    f'止损比例{loss_pct:.2%}超过限制{self.stop_loss_pct:.2%}',
                    'HIGH'
                )
        return RiskCheckResult(True, 'R001', '', 'INFO')

    def _check_single_position(
        self, signal: Dict, portfolio: Dict
    ) -> RiskCheckResult:
        """检查单票仓位"""
        if signal['direction'] != 'BUY':
            return RiskCheckResult(True, 'R002', '', 'INFO')

        code = signal['code']
        positions = portfolio.get('positions', {})
        position_value = positions.get(code, {}).get('value', 0)

        # 新买入的金额
        new_value = signal['price'] * signal['qty']
        total_value = portfolio.get('total_value', 1)

        new_pct = (position_value + new_value) / total_value

        if new_pct > self.max_position_per_stock:
            return RiskCheckResult(
                False, 'R002',
                f'单票仓位{new_pct:.2%}超过限制{self.max_position_per_stock:.2%}',
                'CRITICAL'
            )
        return RiskCheckResult(True, 'R002', '', 'INFO')

    def _check_total_position(
        self, signal: Dict, portfolio: Dict
    ) -> RiskCheckResult:
        """检查总仓位"""
        if signal['direction'] != 'BUY':
            return RiskCheckResult(True, 'R003', '', 'INFO')

        total_position = portfolio.get('total_position', 0)
        new_position = total_position + (signal['price'] * signal['qty'])
        total_value = portfolio.get('total_value', 1)

        new_pct = new_position / total_value

        if new_pct > self.max_total_position:
            return RiskCheckResult(
                False, 'R003',
                f'总仓位{new_pct:.2%}超过限制{self.max_total_position:.2%}',
                'CRITICAL'
            )
        return RiskCheckResult(True, 'R003', '', 'INFO')

    def _check_daily_loss(self, portfolio: Dict) -> RiskCheckResult:
        """检查日亏损熔断"""
        today = datetime.now().date().isoformat()
        daily_pnl = self.daily_stats.get(today, {}).get('pnl', 0)
        total_value = portfolio.get('total_value', 1)

        daily_loss_pct = abs(daily_pnl) / total_value

        if daily_loss_pct > self.max_daily_loss_pct:
            return RiskCheckResult(
                False, 'R004',
                f'日亏损{daily_loss_pct:.2%}触发熔断限制{self.max_daily_loss_pct:.2%}',
                'CRITICAL'
            )
        return RiskCheckResult(True, 'R004', '', 'INFO')

    def _check_consecutive_losses(self, portfolio: Dict) -> RiskCheckResult:
        """检查连续亏损"""
        consecutive_losses = portfolio.get('consecutive_losses', 0)

        if consecutive_losses >= self.max_consecutive_losses:
            return RiskCheckResult(
                False, 'R005',
                f'连续亏损{consecutive_losses}次，暂停开仓',
                'HIGH'
            )
        return RiskCheckResult(True, 'R005', '', 'INFO')

    def _check_order_frequency(self, signal: Dict) -> RiskCheckResult:
        """检查委托频率"""
        code = signal['code']
        now = datetime.now()

        if code not in self.order_history:
            self.order_history[code] = []

        # 清理1分钟前的记录
        self.order_history[code] = [
            t for t in self.order_history[code]
            if (now - t).seconds < 60
        ]

        if len(self.order_history[code]) >= 1:
            return RiskCheckResult(
                False, 'R006',
                '1分钟内同股票已有委托，频率限制',
                'MEDIUM'
            )

        self.order_history[code].append(now)
        return RiskCheckResult(True, 'R006', '', 'INFO')

    def update_daily_pnl(self, pnl: float):
        """更新日盈亏统计"""
        today = datetime.now().date().isoformat()
        if today not in self.daily_stats:
            self.daily_stats[today] = {'pnl': 0, 'trades': 0}
        self.daily_stats[today]['pnl'] += pnl
        self.daily_stats[today]['trades'] += 1
