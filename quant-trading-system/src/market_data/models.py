"""
行情数据模型

标准化的数据结构，支持多数据源
"""
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class TickData:
    """
    标准化Tick数据

    统一所有数据源的数据格式
    """
    symbol: str                           # 标的代码 (如: 000001.SZ)
    timestamp: datetime                   # 时间戳
    price: Decimal                        # 最新价
    volume: int                           # 成交量 (手)
    amount: Optional[Decimal] = None      # 成交额

    # 买卖盘
    bid_price: Optional[Decimal] = None   # 买一价
    bid_volume: Optional[int] = None      # 买一量
    ask_price: Optional[Decimal] = None   # 卖一价
    ask_volume: Optional[int] = None      # 卖一量

    # 价格信息
    open: Optional[Decimal] = None        # 开盘价
    high: Optional[Decimal] = None        # 最高价
    low: Optional[Decimal] = None         # 最低价
    pre_close: Optional[Decimal] = None   # 昨收价

    # 额外数据
    change: Optional[Decimal] = None      # 涨跌额
    change_pct: Optional[Decimal] = None  # 涨跌幅

    # 数据源
    source: str = "unknown"               # 数据来源
    raw_data: Optional[Dict[str, Any]] = None  # 原始数据(调试用)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典(用于JSON序列化)"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "price": float(self.price) if self.price else None,
            "volume": self.volume,
            "amount": float(self.amount) if self.amount else None,
            "bid_price": float(self.bid_price) if self.bid_price else None,
            "bid_volume": self.bid_volume,
            "ask_price": float(self.ask_price) if self.ask_price else None,
            "ask_volume": self.ask_volume,
            "open": float(self.open) if self.open else None,
            "high": float(self.high) if self.high else None,
            "low": float(self.low) if self.low else None,
            "pre_close": float(self.pre_close) if self.pre_close else None,
            "change": float(self.change) if self.change else None,
            "change_pct": float(self.change_pct) if self.change_pct else None,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TickData':
        """从字典创建实例"""
        return cls(
            symbol=data["symbol"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
            price=Decimal(str(data["price"])) if data.get("price") else Decimal("0"),
            volume=data.get("volume", 0),
            amount=Decimal(str(data["amount"])) if data.get("amount") else None,
            bid_price=Decimal(str(data["bid_price"])) if data.get("bid_price") else None,
            bid_volume=data.get("bid_volume"),
            ask_price=Decimal(str(data["ask_price"])) if data.get("ask_price") else None,
            ask_volume=data.get("ask_volume"),
            open=Decimal(str(data["open"])) if data.get("open") else None,
            high=Decimal(str(data["high"])) if data.get("high") else None,
            low=Decimal(str(data["low"])) if data.get("low") else None,
            pre_close=Decimal(str(data["pre_close"])) if data.get("pre_close") else None,
            change=Decimal(str(data["change"])) if data.get("change") else None,
            change_pct=Decimal(str(data["change_pct"])) if data.get("change_pct") else None,
            source=data.get("source", "unknown"),
        )


@dataclass
class KLineData:
    """
    标准化K线数据
    """
    symbol: str                           # 标的代码
    timestamp: datetime                   # 开始时间
    open: Decimal                         # 开盘价
    high: Decimal                         # 最高价
    low: Decimal                          # 最低价
    close: Decimal                        # 收盘价
    volume: int                           # 成交量
    amount: Optional[Decimal] = None      # 成交额
    period: str = "1m"                    # 周期: 1m, 5m, 15m, 1h, 1d, 1w, 1M

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "open": float(self.open) if self.open else None,
            "high": float(self.high) if self.high else None,
            "low": float(self.low) if self.low else None,
            "close": float(self.close) if self.close else None,
            "volume": self.volume,
            "amount": float(self.amount) if self.amount else None,
            "period": self.period,
        }


@dataclass
class MarketDepth:
    """
    市场深度数据 (Level 2)
    """
    symbol: str
    timestamp: datetime
    bids: list = field(default_factory=list)  # 买盘 [(price, volume), ...]
    asks: list = field(default_factory=list)  # 卖盘 [(price, volume), ...]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "bids": self.bids,
            "asks": self.asks,
        }


@dataclass
class MarketSnapshot:
    """
    市场快照 (完整行情)
    """
    symbol: str
    timestamp: datetime

    # 价格
    price: Decimal
    open: Decimal
    high: Decimal
    low: Decimal
    pre_close: Decimal

    # 成交量额
    volume: int
    amount: Decimal

    # 买卖盘
    bid_price_1: Optional[Decimal] = None
    bid_volume_1: Optional[int] = None
    ask_price_1: Optional[Decimal] = None
    ask_volume_1: Optional[int] = None

    # 市场状态
    status: Optional[str] = None  # 交易状态: 交易中/停牌/收盘等

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "price": float(self.price) if self.price else None,
            "open": float(self.open) if self.open else None,
            "high": float(self.high) if self.high else None,
            "low": float(self.low) if self.low else None,
            "pre_close": float(self.pre_close) if self.pre_close else None,
            "volume": self.volume,
            "amount": float(self.amount) if self.amount else None,
            "bid_price_1": float(self.bid_price_1) if self.bid_price_1 else None,
            "bid_volume_1": self.bid_volume_1,
            "ask_price_1": float(self.ask_price_1) if self.ask_price_1 else None,
            "ask_volume_1": self.ask_volume_1,
            "status": self.status,
        }
