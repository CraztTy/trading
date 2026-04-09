"""
兵部 - 交易执行

职责：
- 模拟下单
- 撮合成交
- 涨跌停检查
- 止盈止损触发
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.common.logger import get_logger

logger = get_logger(__name__)


class BingBuWar:
    """兵部：交易执行中心"""

    def __init__(self, config: dict):
        self.config = config
        self.order_counter = 0

    async def execute(
        self,
        signal: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行订单

        Args:
            signal: 交易信号
            market_data: 市场数据

        Returns:
            成交结果
        """
        code = signal['code']
        direction = signal['direction']
        qty = signal['qty']

        # 获取当前市场价格
        market = market_data.get(code, {})
        current_price = market.get('close', signal.get('price'))

        # 检查涨跌停
        if not self._check_price_limit(market, direction):
            logger.warning(f"{code} 涨跌停，无法{direction}")
            return {
                'filled': False,
                'reason': 'PRICE_LIMIT',
                'code': code
            }

        # 模拟成交（简化为市价成交）
        fill_price = current_price
        fill_qty = qty

        self.order_counter += 1

        result = {
            'id': f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{self.order_counter:04d}",
            'code': code,
            'direction': direction,
            'price': fill_price,
            'qty': fill_qty,
            'amount': fill_price * fill_qty,
            'filled': True,
            'filled_at': datetime.now().isoformat(),
            'signal': signal
        }

        logger.info(f"订单成交: {result['id']}, {code}, {direction}, {fill_qty}@{fill_price}")
        return result

    def _check_price_limit(
        self,
        market: Dict[str, Any],
        direction: str
    ) -> bool:
        """检查涨跌停"""
        # 简化的涨跌停检查
        # 实际应检查是否涨停(买)或跌停(卖)
        pre_close = market.get('pre_close', 0)
        current = market.get('close', 0)

        if pre_close <= 0:
            return True

        change_pct = (current - pre_close) / pre_close

        # A股一般涨跌停限制10%
        if direction == 'BUY' and change_pct >= 0.099:
            return False  # 涨停，无法买入
        if direction == 'SELL' and change_pct <= -0.099:
            return False  # 跌停，无法卖出

        return True
