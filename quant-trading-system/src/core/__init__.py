"""
金策智算核心模块 - 三省六部架构

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

from .crown_prince import CrownPrince
from .zhongshu_sheng import ZhongshuSheng
from .menxia_sheng import MenxiaSheng
from .shangshu_sheng import ShangshuSheng
from .backtest_cabinet import BacktestCabinet
from .live_cabinet import LiveCabinet

__all__ = [
    'CrownPrince',
    'ZhongshuSheng',
    'MenxiaSheng',
    'ShangshuSheng',
    'BacktestCabinet',
    'LiveCabinet'
]
