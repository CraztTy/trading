"""
回测绩效计算

计算各种回测指标：
- 收益率相关：总收益率、年化收益率、超额收益
- 风险相关：最大回撤、波动率、下行风险
- 风险调整收益：夏普比率、索提诺比率、卡玛比率
- 交易统计：胜率、盈亏比、交易频次
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
import math

import numpy as np
import pandas as pd

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass
class TradeRecord:
    """交易记录"""
    timestamp: datetime
    symbol: str
    side: str  # BUY / SELL
    qty: int
    price: Decimal
    amount: Decimal
    commission: Decimal = Decimal("0")
    pnl: Optional[Decimal] = None  # 平仓时记录盈亏


@dataclass
class DailyPortfolio:
    """每日持仓市值"""
    date: datetime
    cash: Decimal
    market_value: Decimal
    total_value: Decimal
    positions: Dict[str, int] = field(default_factory=dict)


@dataclass
class BacktestMetrics:
    """回测绩效指标"""

    # 基本信息
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal
    final_capital: Decimal

    # 收益率指标
    total_return: float  # 总收益率
    annual_return: float  # 年化收益率
    excess_return: float  # 超额收益（相对基准）

    # 风险指标
    max_drawdown: float  # 最大回撤
    max_drawdown_duration: int  # 最大回撤持续天数
    volatility: float  # 年化波动率
    downside_volatility: float  # 下行波动率

    # 风险调整收益
    sharpe_ratio: float  # 夏普比率
    sortino_ratio: float  # 索提诺比率
    calmar_ratio: float  # 卡玛比率

    # 交易统计
    total_trades: int  # 总交易次数
    winning_trades: int  # 盈利次数
    losing_trades: int  # 亏损次数
    win_rate: float  # 胜率
    profit_factor: float  # 盈亏比
    avg_profit: float  # 平均盈利
    avg_loss: float  # 平均亏损
    largest_profit: float  # 最大盈利
    largest_loss: float  # 最大亏损

    # 持仓统计
    avg_position_count: float  # 平均持仓数量
    avg_position_duration: float  # 平均持仓天数

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            '基本信息': {
                '回测区间': f"{self.start_date.date()} ~ {self.end_date.date()}",
                '初始资金': float(self.initial_capital),
                '最终资金': float(self.final_capital),
            },
            '收益指标': {
                '总收益率': f"{self.total_return * 100:.2f}%",
                '年化收益率': f"{self.annual_return * 100:.2f}%",
                '超额收益': f"{self.excess_return * 100:.2f}%",
            },
            '风险指标': {
                '最大回撤': f"{self.max_drawdown * 100:.2f}%",
                '回撤持续天数': self.max_drawdown_duration,
                '年化波动率': f"{self.volatility * 100:.2f}%",
            },
            '风险调整收益': {
                '夏普比率': f"{self.sharpe_ratio:.2f}",
                '索提诺比率': f"{self.sortino_ratio:.2f}",
                '卡玛比率': f"{self.calmar_ratio:.2f}",
            },
            '交易统计': {
                '总交易次数': self.total_trades,
                '胜率': f"{self.win_rate * 100:.2f}%",
                '盈亏比': f"{self.profit_factor:.2f}",
                '平均盈利': f"{self.avg_profit:.2f}",
                '平均亏损': f"{self.avg_loss:.2f}",
            },
        }


class MetricsCalculator:
    """绩效计算器"""

    def __init__(self, risk_free_rate: float = 0.03):
        """
        Args:
            risk_free_rate: 无风险利率（年化），默认 3%
        """
        self.risk_free_rate = risk_free_rate

    def calculate(
        self,
        daily_portfolios: List[DailyPortfolio],
        trades: List[TradeRecord],
        benchmark_returns: Optional[List[float]] = None
    ) -> BacktestMetrics:
        """
        计算回测绩效指标

        Args:
            daily_portfolios: 每日持仓记录
            trades: 交易记录
            benchmark_returns: 基准收益率序列（可选）

        Returns:
            BacktestMetrics 绩效指标
        """
        if not daily_portfolios:
            raise ValueError("每日持仓记录为空")

        # 基本信息
        start_date = daily_portfolios[0].date
        end_date = daily_portfolios[-1].date
        initial_capital = daily_portfolios[0].total_value
        final_capital = daily_portfolios[-1].total_value

        # 计算每日收益率
        daily_returns = self._calc_daily_returns(daily_portfolios)

        # 收益率指标
        total_return = float(final_capital / initial_capital - 1)
        days = (end_date - start_date).days
        years = days / 365.0
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

        # 超额收益
        if benchmark_returns:
            excess_return = annual_return - np.mean(benchmark_returns) * 252
        else:
            excess_return = annual_return - self.risk_free_rate

        # 风险指标
        max_drawdown, max_dd_duration = self._calc_max_drawdown(daily_portfolios)
        volatility = np.std(daily_returns) * np.sqrt(252) if daily_returns else 0
        downside_volatility = self._calc_downside_volatility(daily_returns)

        # 风险调整收益
        sharpe = self._calc_sharpe_ratio(annual_return, volatility)
        sortino = self._calc_sortino_ratio(annual_return, downside_volatility)
        calmar = self._calc_calmar_ratio(annual_return, max_drawdown)

        # 交易统计
        trade_stats = self._calc_trade_stats(trades)

        # 持仓统计
        avg_position_count = self._calc_avg_position_count(daily_portfolios)

        return BacktestMetrics(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            annual_return=annual_return,
            excess_return=excess_return,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            volatility=volatility,
            downside_volatility=downside_volatility,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            avg_position_count=avg_position_count,
            avg_position_duration=0,  # TODO: 计算平均持仓天数
            **trade_stats
        )

    def _calc_daily_returns(
        self,
        portfolios: List[DailyPortfolio]
    ) -> List[float]:
        """计算每日收益率"""
        returns = []
        for i in range(1, len(portfolios)):
            prev_value = float(portfolios[i-1].total_value)
            curr_value = float(portfolios[i].total_value)
            if prev_value > 0:
                daily_return = curr_value / prev_value - 1
                returns.append(daily_return)
        return returns

    def _calc_max_drawdown(
        self,
        portfolios: List[DailyPortfolio]
    ) -> tuple:
        """
        计算最大回撤

        Returns:
            (最大回撤比例, 回撤持续天数)
        """
        if not portfolios:
            return 0, 0

        values = [float(p.total_value) for p in portfolios]
        peak = values[0]
        max_dd = 0
        max_dd_start = 0
        max_dd_end = 0
        current_dd_start = 0

        for i, value in enumerate(values):
            if value > peak:
                peak = value
                current_dd_start = i
            else:
                dd = (peak - value) / peak
                if dd > max_dd:
                    max_dd = dd
                    max_dd_start = current_dd_start
                    max_dd_end = i

        duration = max_dd_end - max_dd_start
        return max_dd, duration

    def _calc_downside_volatility(self, returns: List[float]) -> float:
        """计算下行波动率"""
        if not returns:
            return 0

        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return 0

        return np.std(downside_returns) * np.sqrt(252)

    def _calc_sharpe_ratio(self, annual_return: float, volatility: float) -> float:
        """计算夏普比率"""
        if volatility == 0:
            return 0
        return (annual_return - self.risk_free_rate) / volatility

    def _calc_sortino_ratio(
        self,
        annual_return: float,
        downside_volatility: float
    ) -> float:
        """计算索提诺比率"""
        if downside_volatility == 0:
            return 0
        return (annual_return - self.risk_free_rate) / downside_volatility

    def _calc_calmar_ratio(self, annual_return: float, max_drawdown: float) -> float:
        """计算卡玛比率"""
        if max_drawdown == 0:
            return 0
        return annual_return / max_drawdown

    def _calc_trade_stats(self, trades: List[TradeRecord]) -> Dict:
        """计算交易统计"""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'largest_profit': 0,
                'largest_loss': 0,
            }

        # 只统计平仓交易（有 PnL 的）
        closed_trades = [t for t in trades if t.pnl is not None]

        if not closed_trades:
            return {
                'total_trades': len(trades),
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'largest_profit': 0,
                'largest_loss': 0,
            }

        profits = [float(t.pnl) for t in closed_trades if t.pnl > 0]
        losses = [float(t.pnl) for t in closed_trades if t.pnl < 0]

        winning_trades = len(profits)
        losing_trades = len(losses)
        total_trades = len(closed_trades)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        total_profit = sum(profits) if profits else 0
        total_loss = abs(sum(losses)) if losses else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = -total_loss / losing_trades if losing_trades > 0 else 0

        largest_profit = max(profits) if profits else 0
        largest_loss = min(losses) if losses else 0

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'largest_profit': largest_profit,
            'largest_loss': largest_loss,
        }

    def _calc_avg_position_count(
        self,
        portfolios: List[DailyPortfolio]
    ) -> float:
        """计算平均持仓数量"""
        if not portfolios:
            return 0

        counts = [len(p.positions) for p in portfolios]
        return sum(counts) / len(counts)
