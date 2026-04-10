"""
户部 - 资金核算

职责：
- 逐笔核算资金
- 净值计算
- 手续费、印花税核算
- 总成本计算
"""
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class HuBuRevenue:
    """户部：资金核算中心"""

    def __init__(self, config: dict):
        self.config = config
        self.commission_rate = config.get('commission_rate', 0.0003)
        self.min_commission = config.get('min_commission', 5.0)
        self.stamp_tax_rate = config.get('stamp_tax_rate', 0.001)
        self.transfer_fee_rate = config.get('transfer_fee_rate', 0.00002)

        self.settlements: List[Dict] = []  # 结算记录

    def calculate_costs(
        self,
        amount: float,
        direction: str
    ) -> Dict[str, float]:
        """
        计算交易成本

        Args:
            amount: 交易金额
            direction: 方向 (BUY/SELL)

        Returns:
            费用明细
        """
        amount_dec = Decimal(str(amount))

        # 佣金
        commission = max(
            amount_dec * Decimal(str(self.commission_rate)),
            Decimal(str(self.min_commission))
        )

        # 印花税（仅卖出）
        stamp_tax = (
            amount_dec * Decimal(str(self.stamp_tax_rate))
            if direction == 'SELL' else Decimal('0')
        )

        # 过户费
        transfer_fee = amount_dec * Decimal(str(self.transfer_fee_rate))

        total_cost = commission + stamp_tax + transfer_fee

        return {
            'commission': float(commission),
            'stamp_tax': float(stamp_tax),
            'transfer_fee': float(transfer_fee),
            'total_cost': float(total_cost)
        }

    def settle(
        self,
        order: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        交易结算

        Args:
            order: 成交订单

        Returns:
            结算结果
        """
        direction = order['direction']
        price = order['price']
        qty = order['qty']
        amount = price * qty

        # 计算费用
        costs = self.calculate_costs(amount, direction)

        # 计算净金额
        if direction == 'BUY':
            net_amount = amount + costs['total_cost']
        else:
            net_amount = amount - costs['total_cost']

        settlement = {
            'order_id': order.get('id', 'unknown'),
            'direction': direction,
            'amount': amount,
            'net_amount': net_amount,
            'costs': costs,
            'settled_at': datetime.now().isoformat()
        }

        self.settlements.append(settlement)

        logger.info(f"结算完成: {order.get('id')}, 费用: {costs['total_cost']:.2f}")
        return settlement

    def get_settlement_history(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """获取结算历史"""
        settlements = self.settlements

        if start_date:
            settlements = [
                s for s in settlements
                if s['settled_at'] >= start_date
            ]

        if end_date:
            settlements = [
                s for s in settlements
                if s['settled_at'] <= end_date
            ]

        return settlements

    def get_total_fees(self) -> Dict[str, float]:
        """获取总费用统计"""
        total_commission = sum(s['costs']['commission'] for s in self.settlements)
        total_stamp_tax = sum(s['costs']['stamp_tax'] for s in self.settlements)
        total_transfer_fee = sum(s['costs']['transfer_fee'] for s in self.settlements)
        total_cost = sum(s['costs']['total_cost'] for s in self.settlements)

        return {
            'total_commission': total_commission,
            'total_stamp_tax': total_stamp_tax,
            'total_transfer_fee': total_transfer_fee,
            'total_cost': total_cost
        }
