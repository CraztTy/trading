"""
技能适配器模块

提供与金融分析技能的统一接口封装
"""

from .base_adapter import BaseSkillAdapter
from .mx_finance_data_adapter import MxFinanceDataAdapter
from .stock_earnings_adapter import StockEarningsAdapter
from .mx_macro_data_adapter import MxMacroDataAdapter

__all__ = [
    'BaseSkillAdapter',
    'MxFinanceDataAdapter',
    'StockEarningsAdapter',
    'MxMacroDataAdapter'
]
