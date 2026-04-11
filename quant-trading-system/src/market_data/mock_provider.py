"""
模拟数据提供器

用于开发和测试环境，当外部API不可用时提供模拟数据
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import random

from src.market_data.models import TickData, KLineData


class MockDataProvider:
    """模拟数据提供器"""

    # 模拟股票列表
    MOCK_STOCKS = [
        {"symbol": "000001.SZ", "name": "平安银行"},
        {"symbol": "000002.SZ", "name": "万科A"},
        {"symbol": "000333.SZ", "name": "美的集团"},
        {"symbol": "000858.SZ", "name": "五粮液"},
        {"symbol": "002594.SZ", "name": "比亚迪"},
        {"symbol": "300750.SZ", "name": "宁德时代"},
        {"symbol": "300760.SZ", "name": "迈瑞医疗"},
        {"symbol": "600519.SH", "name": "贵州茅台"},
        {"symbol": "600900.SH", "name": "长江电力"},
        {"symbol": "601012.SH", "name": "隆基绿能"},
        {"symbol": "601318.SH", "name": "中国平安"},
        {"symbol": "601888.SH", "name": "中国中免"},
        {"symbol": "603288.SH", "name": "海天味业"},
        {"symbol": "603986.SH", "name": "兆易创新"},
        {"symbol": "688111.SH", "name": "金山办公"},
        {"symbol": "688981.SH", "name": "中芯国际"},
    ]

    # 股票价格（用于生成Tick数据）
    STOCK_PRICES = {
        "000001.SZ": 10.52,
        "000002.SZ": 15.30,
        "000333.SZ": 59.80,
        "000858.SZ": 154.80,
        "002594.SZ": 245.60,
        "300750.SZ": 200.50,
        "300760.SZ": 312.50,
        "600519.SH": 1725.00,
        "600900.SH": 23.15,
        "601012.SH": 27.65,
        "601318.SH": 48.50,
        "601888.SH": 85.40,
        "603288.SH": 42.50,
        "603986.SH": 108.50,
        "688111.SH": 285.80,
        "688981.SH": 58.90,
    }

    @classmethod
    def get_stock_list(cls, limit: int = 100) -> List[Dict[str, str]]:
        """获取模拟股票列表"""
        return cls.MOCK_STOCKS[:limit]

    @classmethod
    def search_stocks(cls, keyword: str, limit: int = 10) -> List[Dict[str, str]]:
        """搜索模拟股票"""
        keyword = keyword.upper()
        results = []
        for stock in cls.MOCK_STOCKS:
            if keyword in stock["symbol"] or keyword in stock["name"]:
                results.append(stock)
                if len(results) >= limit:
                    break
        return results

    @classmethod
    def get_tick(cls, symbol: str) -> Optional[TickData]:
        """获取模拟Tick数据"""
        base_price = cls.STOCK_PRICES.get(symbol, 100.0)
        if base_price is None:
            return None

        price_change = (random.random() - 0.5) * base_price * 0.02
        current_price = base_price + price_change

        return TickData(
            symbol=symbol,
            timestamp=datetime.now(),
            price=Decimal(str(current_price)),
            volume=random.randint(1000, 100000),
            bid_price=Decimal(str(current_price - 0.01)),
            bid_volume=random.randint(100, 5000),
            ask_price=Decimal(str(current_price + 0.01)),
            ask_volume=random.randint(100, 5000),
            open=Decimal(str(base_price * (1 + (random.random() - 0.5) * 0.01))),
            high=Decimal(str(base_price * (1 + random.random() * 0.03))),
            low=Decimal(str(base_price * (1 - random.random() * 0.03))),
            pre_close=Decimal(str(base_price)),
            change=Decimal(str(price_change)),
            change_pct=Decimal(str(price_change / base_price * 100)),
            source="mock",
        )
