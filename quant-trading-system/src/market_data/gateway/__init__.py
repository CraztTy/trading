"""
行情网关模块

支持多数据源接入：
- 东方财富 (Eastmoney)
- Tushare
- 腾讯财经
"""

from src.market_data.gateway.base import MarketDataGateway
from src.market_data.gateway.eastmoney import EastmoneyGateway

__all__ = [
    'MarketDataGateway',
    'EastmoneyGateway',
]
