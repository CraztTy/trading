"""
尚书省 - 执行调度与资金清算

职责：
- 调度六部执行模拟成交
- 资金清算
- 持仓管理
- T+1结算
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from src.common.logger import get_logger

logger = get_logger(__name__)


class ShangshuSheng:
    """尚书省：执行调度中心"""

    def __init__(self, config: dict):
        self.config = config
        self.positions: Dict[str, Dict] = {}  # 持仓
        self.cash: float = config.get('initial_capital', 1_000_000.0)
        self.total_value: float = self.cash

        # 交易费用
        self.commission_rate = config.get('commission_rate', 0.0003)
        self.min_commission = config.get('min_commission', 5.0)
        self.stamp_tax_rate = config.get('stamp_tax_rate', 0.001)
        self.transfer_fee_rate = config.get('transfer_fee_rate', 0.00002)

    async def execute_orders(
        self,
        signals: List[Dict[str, Any]],
        market_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """执行订单列表"""
        executed_orders = []

        for signal in signals:
            try:
                result = await self._execute_single(signal, market_data)
                if result:
                    executed_orders.append(result)
            except Exception as e:
                logger.error(f"订单执行失败: {e}")

        return executed_orders

    async def _execute_single(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """执行单个订单"""
        code = signal['code']
        direction = signal['direction']
        price = signal['price']
        qty = signal['qty']

        # 检查资金/持仓
        if direction == 'BUY':
            if not self._has_enough_cash(price, qty):
                logger.warning(f"资金不足: {code}")
                return None
        else:
            if not self._has_enough_position(code, qty):
                logger.warning(f"持仓不足: {code}")
                return None

        # 计算费用
        amount = price * qty
        commission = self._calc_commission(amount)
        stamp_tax = self._calc_stamp_tax(amount, direction)
        transfer_fee = self._calc_transfer_fee(amount)
        total_cost = commission + stamp_tax + transfer_fee

        # 执行交易
        if direction == 'BUY':
            self.cash -= (amount + total_cost)
            self._add_position(code, qty, price, signal.get('stop_loss'), signal.get('take_profit'))
        else:
            self.cash += (amount - total_cost)
            self._reduce_position(code, qty)

        # 更新总市值
        self._update_total_value(market_data)

        result = {
            'order_id': f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'code': code,
            'direction': direction,
            'price': price,
            'qty': qty,
            'amount': amount,
            'commission': commission,
            'stamp_tax': stamp_tax,
            'transfer_fee': transfer_fee,
            'total_cost': total_cost,
            'timestamp': datetime.now().isoformat(),
            'cash_after': self.cash,
            'total_value': self.total_value
        }

        logger.info(f"订单执行成功: {result}")
        return result

    def _has_enough_cash(self, price: float, qty: float) -> bool:
        """检查资金是否充足"""
        required = price * qty * 1.002  # 预留费用
        return self.cash >= required

    def _has_enough_position(self, code: str, qty: float) -> bool:
        """检查持仓是否充足"""
        position = self.positions.get(code, {})
        available = position.get('qty', 0) - position.get('frozen', 0)
        return available >= qty

    def _calc_commission(self, amount: float) -> float:
        """计算佣金"""
        commission = amount * self.commission_rate
        return max(commission, self.min_commission)

    def _calc_stamp_tax(self, amount: float, direction: str) -> float:
        """计算印花税（仅卖出）"""
        if direction == 'SELL':
            return amount * self.stamp_tax_rate
        return 0.0

    def _calc_transfer_fee(self, amount: float) -> float:
        """计算过户费"""
        return amount * self.transfer_fee_rate

    def _add_position(
        self,
        code: str,
        qty: float,
        price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ):
        """增加持仓"""
        if code not in self.positions:
            self.positions[code] = {
                'qty': 0,
                'cost': 0,
                'frozen': 0,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }

        position = self.positions[code]
        old_qty = position['qty']
        old_cost = position['cost']

        # 计算新的平均成本
        position['qty'] += qty
        position['cost'] = (old_cost * old_qty + price * qty) / position['qty']

        if stop_loss:
            position['stop_loss'] = stop_loss
        if take_profit:
            position['take_profit'] = take_profit

    def _reduce_position(self, code: str, qty: float):
        """减少持仓"""
        if code in self.positions:
            self.positions[code]['qty'] -= qty
            if self.positions[code]['qty'] <= 0:
                del self.positions[code]

    def _update_total_value(self, market_data: Dict[str, Any]):
        """更新总市值"""
        position_value = 0
        for code, position in self.positions.items():
            price = market_data.get(code, {}).get('close', position['cost'])
            position_value += position['qty'] * price
        self.total_value = self.cash + position_value

    def get_portfolio_state(self) -> Dict[str, Any]:
        """获取账户状态"""
        total_position_value = sum(
            p['qty'] * p.get('cost', 0)
            for p in self.positions.values()
        )

        return {
            'cash': self.cash,
            'total_value': self.total_value,
            'total_position': total_position_value,
            'positions': self.positions,
            'total_position_pct': total_position_value / self.total_value if self.total_value > 0 else 0
        }

    async def check_stops(
        self,
        market_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """检查止盈止损"""
        stop_signals = []

        for code, position in self.positions.items():
            current_price = market_data.get(code, {}).get('close')
            if not current_price:
                continue

            stop_loss = position.get('stop_loss')
            take_profit = position.get('take_profit')

            # 检查止损
            if stop_loss and current_price <= stop_loss:
                stop_signals.append({
                    'code': code,
                    'direction': 'SELL',
                    'price': current_price,
                    'qty': position['qty'],
                    'reason': 'STOP_LOSS',
                    'trigger_price': stop_loss
                })
            # 检查止盈
            elif take_profit and current_price >= take_profit:
                stop_signals.append({
                    'code': code,
                    'direction': 'SELL',
                    'price': current_price,
                    'qty': position['qty'],
                    'reason': 'TAKE_PROFIT',
                    'trigger_price': take_profit
                })

        return stop_signals
