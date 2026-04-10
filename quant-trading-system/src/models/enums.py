"""
数据库枚举类型定义
"""
from enum import Enum


class AccountStatus(str, Enum):
    """账户状态"""
    ACTIVE = "ACTIVE"           # 正常
    SUSPENDED = "SUSPENDED"     # 暂停
    CLOSED = "CLOSED"           # 关闭


class AccountType(str, Enum):
    """账户类型"""
    SIMULATE = "SIMULATE"       # 模拟盘
    REAL = "REAL"               # 实盘


class StrategyStatus(str, Enum):
    """策略状态"""
    INACTIVE = "INACTIVE"       # 未激活
    ACTIVE = "ACTIVE"           # 运行中
    PAUSED = "PAUSED"           # 暂停
    ERROR = "ERROR"             # 错误


class RunMode(str, Enum):
    """运行模式"""
    BACKTEST = "BACKTEST"       # 回测
    SIMULATE = "SIMULATE"       # 模拟盘
    LIVE = "LIVE"               # 实盘


class OrderStatus(str, Enum):
    """订单状态"""
    CREATED = "CREATED"         # 已创建
    PENDING = "PENDING"         # 已报（提交到交易所）
    PARTIAL = "PARTIAL"         # 部分成交
    FILLED = "FILLED"           # 全部成交
    CANCELLED = "CANCELLED"     # 已撤单
    REJECTED = "REJECTED"       # 已拒绝
    EXPIRED = "EXPIRED"         # 已过期


class OrderDirection(str, Enum):
    """订单方向"""
    BUY = "BUY"                 # 买入
    SELL = "SELL"               # 卖出


class OrderType(str, Enum):
    """订单类型"""
    LIMIT = "LIMIT"             # 限价单
    MARKET = "MARKET"           # 市价单
    STOP = "STOP"               # 止损单


class FlowType(str, Enum):
    """资金流水类型"""
    # 出入金
    DEPOSIT = "DEPOSIT"                 # 入金
    WITHDRAW = "WITHDRAW"               # 出金

    # 订单相关
    ORDER_FROZEN = "ORDER_FROZEN"       # 委托冻结
    ORDER_UNFROZEN = "ORDER_UNFROZEN"   # 委托解冻

    # 成交相关
    TRADE_BUY = "TRADE_BUY"             # 买入成交
    TRADE_SELL = "TRADE_SELL"           # 卖出成交

    # 费用
    COMMISSION = "COMMISSION"           # 佣金
    STAMP_TAX = "STAMP_TAX"             # 印花税
    TRANSFER_FEE = "TRANSFER_FEE"       # 过户费

    # 其他
    DIVIDEND = "DIVIDEND"               # 分红
    RIGHTS_ISSUE = "RIGHTS_ISSUE"       # 配股
