"""
睿之兮核心模块 - 三省六部架构

三省（决策主链路）：
- 太子院：数据前置校验与分发
- 中书省：策略信号生成
- 门下省：风控审核与拦截
- 尚书省：执行调度与资金清算

六部（职能部门）：
- 吏部：策略注册与生命周期管理
- 户部：现金、成本、净值核算
- 礼部：业绩报表与策略排行
- 兵部：撮合执行与交易管理
- 刑部：违规记录与风险事件
- 工部：行情清洗与指标计算
"""

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)

from .crown_prince import CrownPrince, crown_prince, SymbolNormalizer, DataType, ValidationLevel
from .zhongshu_sheng import ZhongshuSheng, zhongshu_sheng, SignalEvent, SignalStatus
from .menxia_sheng import MenxiaSheng, menxia_sheng, RiskLevel, RiskRule, AuditResult
from .shangshu_sheng import ShangshuSheng, shangshu_sheng, OrderPriority, ExecutionResult
from .backtest_cabinet import BacktestCabinet
from .live_cabinet import LiveCabinet

__all__ = [
    # 太子院
    'CrownPrince',
    'crown_prince',
    'SymbolNormalizer',
    'DataType',
    'ValidationLevel',
    # 中书省
    'ZhongshuSheng',
    'zhongshu_sheng',
    'SignalEvent',
    'SignalStatus',
    # 门下省
    'MenxiaSheng',
    'menxia_sheng',
    'RiskLevel',
    'RiskRule',
    'AuditResult',
    # 尚书省
    'ShangshuSheng',
    'shangshu_sheng',
    'OrderPriority',
    'ExecutionResult',
    # 其他
    'BacktestCabinet',
    'LiveCabinet',
]


class ShengSystem:
    """
    三省系统联动管理器

    将四个省串联起来，形成完整的数据处理链路：
    太子院 → 中书省 → 门下省 → 尚书省
    """

    def __init__(self):
        self.crown_prince = crown_prince
        self.zhongshu_sheng = zhongshu_sheng
        self.menxia_sheng = menxia_sheng
        self.shangshu_sheng = shangshu_sheng

        self._setup_linkage()

    def _setup_linkage(self):
        """设置省之间的联动"""
        # 门下省审核通过后，发送到尚书省执行
        self.menxia_sheng.on_approval(self._on_signal_approved)

        # 中书省生成信号后，发送到门下省审核
        self.zhongshu_sheng.add_signal_handler(self._on_signal_generated)

        logger.info("三省联动已设置")

    async def _on_signal_generated(self, event: SignalEvent, validation_result):
        """信号生成回调 - 中书省 → 门下省"""
        logger.info(f"中书省生成信号，送门下省审核: {event.signal_id}")

        # 获取账户上下文（简化版本）
        context = {
            "positions": {},
            "total_value": 100000,
        }

        # 送门下省审核
        audit_result = await self.menxia_sheng.audit_signal(event.signal, context)

        if audit_result.approved:
            logger.info(f"信号审核通过: {event.signal_id}")
        else:
            logger.warning(f"信号审核拒绝: {event.signal_id} - {audit_result.reject_reason}")

    async def _on_signal_approved(self, signal, audit_result: AuditResult):
        """信号审核通过回调 - 门下省 → 尚书省"""
        logger.info(f"门下省审核通过，送尚书省执行: {signal.symbol}")

        # 送尚书省执行
        await self.shangshu_sheng.submit_signal(
            signal=signal,
            account_id=1,  # 简化
            priority=OrderPriority.NORMAL
        )

    async def start(self):
        """启动三省系统"""
        await self.shangshu_sheng.start()
        logger.info("三省系统已启动")

    async def stop(self):
        """停止三省系统"""
        await self.shangshu_sheng.stop()
        logger.info("三省系统已停止")

    def get_stats(self) -> dict:
        """获取三省统计"""
        return {
            "crown_prince": self.crown_prince.get_stats(),
            "zhongshu_sheng": self.zhongshu_sheng.get_stats(),
            "menxia_sheng": self.menxia_sheng.get_stats(),
            "shangshu_sheng": self.shangshu_sheng.get_stats(),
        }


# 全局三省系统实例
sheng_system = ShengSystem()
