"""
中书省 - 策略信号生成

职责：
- 为每套策略独立生成买卖信号
- 管理策略生命周期
- 传递策略上下文信息
"""
from typing import List, Dict, Optional, Any
import pandas as pd
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class ZhongshuSheng:
    """中书省：策略信号生成中心"""

    def __init__(self, config: dict):
        self.config = config
        self.active_strategies: Dict[str, Any] = {}
        self.strategy_contexts: Dict[str, Dict] = {}

    def register_strategy(self, strategy_id: str, strategy: Any):
        """注册策略"""
        self.active_strategies[strategy_id] = strategy
        self.strategy_contexts[strategy_id] = {}
        logger.info(f"注册策略: {strategy_id}")

    def unregister_strategy(self, strategy_id: str):
        """注销策略"""
        self.active_strategies.pop(strategy_id, None)
        self.strategy_contexts.pop(strategy_id, None)
        logger.info(f"注销策略: {strategy_id}")

    async def generate_signals(
        self,
        klines: pd.DataFrame,
        code: str,
        strategy_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        为所有策略生成当前bar的信号

        Args:
            klines: 清洗后的K线数据
            code: 股票代码
            strategy_filter: 策略过滤列表，None表示所有激活策略

        Returns:
            信号列表
        """
        signals = []

        # 获取需要运行的策略
        strategies = self._get_strategies(strategy_filter)

        for strategy_id, strategy in strategies.items():
            try:
                # 获取策略上下文(历史状态)
                context = self._get_strategy_context(strategy_id, code)

                # 生成信号
                signal = strategy.on_bar(klines, context)

                if signal and self._validate_signal(signal):
                    signal['strategy_id'] = strategy_id
                    signal['code'] = code
                    signal['timestamp'] = klines.index[-1] if len(klines) > 0 else None
                    signals.append(signal)
                    logger.debug(f"策略{strategy_id}生成信号: {signal}")

            except Exception as e:
                logger.error(f"策略{strategy_id}信号生成失败: {e}")
                continue

        return signals

    def _get_strategies(self, strategy_filter: Optional[List[str]]) -> Dict:
        """获取策略列表"""
        if strategy_filter:
            return {
                sid: s for sid, s in self.active_strategies.items()
                if sid in strategy_filter
            }
        return self.active_strategies

    def _get_strategy_context(self, strategy_id: str, code: str) -> dict:
        """获取策略上下文(历史持仓、盈亏等)"""
        context = self.strategy_contexts.get(strategy_id, {})
        return context.get(code, {})

    def update_strategy_context(
        self,
        strategy_id: str,
        code: str,
        context: dict
    ):
        """更新策略上下文"""
        if strategy_id not in self.strategy_contexts:
            self.strategy_contexts[strategy_id] = {}
        self.strategy_contexts[strategy_id][code] = context

    def _validate_signal(self, signal: Dict) -> bool:
        """验证信号格式"""
        required_fields = ['direction', 'price', 'qty']

        for field in required_fields:
            if field not in signal:
                logger.error(f"信号缺少必要字段: {field}")
                return False

        # 验证方向
        if signal['direction'] not in ['BUY', 'SELL']:
            logger.error(f"无效的信号方向: {signal['direction']}")
            return False

        # 验证价格
        if signal['price'] <= 0:
            logger.error(f"无效的价格: {signal['price']}")
            return False

        # 验证数量
        if signal['qty'] <= 0:
            logger.error(f"无效的数量: {signal['qty']}")
            return False

        return True

    def get_active_strategy_ids(self) -> List[str]:
        """获取所有活跃策略ID"""
        return list(self.active_strategies.keys())
