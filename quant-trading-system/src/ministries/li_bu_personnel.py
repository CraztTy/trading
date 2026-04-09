"""
吏部 - 策略注册与生命周期管理

职责：
- 策略注册与注销
- 策略状态管理（激活/停用）
- 策略权限控制
- 策略性能追踪
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.common.logger import get_logger

logger = get_logger(__name__)


class LiBuPersonnel:
    """吏部：策略管理中心"""

    def __init__(self, config: dict):
        self.config = config
        self.strategies: Dict[str, Dict] = {}  # 策略注册表
        self.strategy_stats: Dict[str, Dict] = {}  # 策略统计

    def register_strategy(
        self,
        strategy_id: str,
        name: str,
        strategy_class: Any,
        params: Optional[Dict] = None,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        注册策略

        Args:
            strategy_id: 策略唯一标识
            name: 策略名称
            strategy_class: 策略类
            params: 策略参数
            description: 策略描述

        Returns:
            注册结果
        """
        if strategy_id in self.strategies:
            logger.warning(f"策略{strategy_id}已存在，将更新")

        self.strategies[strategy_id] = {
            'id': strategy_id,
            'name': name,
            'class': strategy_class,
            'params': params or {},
            'description': description,
            'status': 'inactive',  # inactive/active/paused
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'activated_at': None
        }

        self.strategy_stats[strategy_id] = {
            'total_trades': 0,
            'win_trades': 0,
            'loss_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0
        }

        logger.info(f"策略注册成功: {strategy_id}")
        return self.strategies[strategy_id]

    def unregister_strategy(self, strategy_id: str) -> bool:
        """注销策略"""
        if strategy_id not in self.strategies:
            logger.warning(f"策略{strategy_id}不存在")
            return False

        # 检查是否有关联持仓
        # TODO: 实现持仓检查

        del self.strategies[strategy_id]
        del self.strategy_stats[strategy_id]

        logger.info(f"策略注销成功: {strategy_id}")
        return True

    def activate_strategy(self, strategy_id: str) -> bool:
        """激活策略"""
        if strategy_id not in self.strategies:
            return False

        self.strategies[strategy_id]['status'] = 'active'
        self.strategies[strategy_id]['activated_at'] = datetime.now().isoformat()
        self.strategies[strategy_id]['updated_at'] = datetime.now().isoformat()

        logger.info(f"策略激活: {strategy_id}")
        return True

    def deactivate_strategy(self, strategy_id: str) -> bool:
        """停用策略"""
        if strategy_id not in self.strategies:
            return False

        self.strategies[strategy_id]['status'] = 'inactive'
        self.strategies[strategy_id]['updated_at'] = datetime.now().isoformat()

        logger.info(f"策略停用: {strategy_id}")
        return True

    def pause_strategy(self, strategy_id: str) -> bool:
        """暂停策略（临时）"""
        if strategy_id not in self.strategies:
            return False

        if self.strategies[strategy_id]['status'] == 'active':
            self.strategies[strategy_id]['status'] = 'paused'
            self.strategies[strategy_id]['updated_at'] = datetime.now().isoformat()
            logger.info(f"策略暂停: {strategy_id}")

        return True

    def resume_strategy(self, strategy_id: str) -> bool:
        """恢复策略"""
        if strategy_id not in self.strategies:
            return False

        if self.strategies[strategy_id]['status'] == 'paused':
            self.strategies[strategy_id]['status'] = 'active'
            self.strategies[strategy_id]['updated_at'] = datetime.now().isoformat()
            logger.info(f"策略恢复: {strategy_id}")

        return True

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略信息"""
        return self.strategies.get(strategy_id)

    def list_strategies(
        self,
        status: Optional[str] = None,
        active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        列出策略

        Args:
            status: 按状态过滤
            active_only: 仅显示激活的策略

        Returns:
            策略列表
        """
        strategies = list(self.strategies.values())

        if active_only:
            strategies = [s for s in strategies if s['status'] == 'active']
        elif status:
            strategies = [s for s in strategies if s['status'] == status]

        return strategies

    def update_strategy_params(
        self,
        strategy_id: str,
        params: Dict[str, Any]
    ) -> bool:
        """更新策略参数"""
        if strategy_id not in self.strategies:
            return False

        self.strategies[strategy_id]['params'].update(params)
        self.strategies[strategy_id]['updated_at'] = datetime.now().isoformat()

        logger.info(f"策略参数更新: {strategy_id}")
        return True

    def update_strategy_stats(
        self,
        strategy_id: str,
        trade_result: Dict[str, Any]
    ):
        """更新策略统计"""
        if strategy_id not in self.strategy_stats:
            return

        stats = self.strategy_stats[strategy_id]
        stats['total_trades'] += 1

        pnl = trade_result.get('pnl', 0)
        stats['total_pnl'] += pnl

        if pnl > 0:
            stats['win_trades'] += 1
        elif pnl < 0:
            stats['loss_trades'] += 1

    def get_strategy_stats(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略统计"""
        return self.strategy_stats.get(strategy_id)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有策略统计"""
        return self.strategy_stats.copy()
