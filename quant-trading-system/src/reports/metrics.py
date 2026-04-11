"""
交易指标和绩效指标计算模块

提供各类交易和绩效指标的计算：
- 交易指标：胜率、盈亏比、平均盈亏等
- 绩效指标：收益率、夏普比率、最大回撤等
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Dict, Any
import statistics
import math

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass
class TradeMetrics:
    """交易指标"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0

    win_rate: float = 0.0
    loss_rate: float = 0.0

    total_profit: Decimal = Decimal("0")
    total_loss: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")

    avg_profit: Decimal = Decimal("0")
    avg_loss: Decimal = Decimal("0")
    avg_trade: Decimal = Decimal("0")

    profit_factor: float = 0.0
    profit_loss_ratio: float = 0.0

    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    total_commission: Decimal = Decimal("0")
    total_tax: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")

    @classmethod
    def calculate(cls, trades: List[Any]) -> 'TradeMetrics':
        """
        从交易列表计算指标

        Args:
            trades: 交易对象列表，需要有 pnl, commission, stamp_tax 属性

        Returns:
            TradeMetrics: 交易指标
        """
        metrics = cls()

        if not trades:
            return metrics

        metrics.total_trades = len(trades)

        # 盈亏统计
        profits = []
        losses = []

        for trade in trades:
            # 统计费用
            if hasattr(trade, 'commission') and trade.commission:
                commission = trade.commission
                if not isinstance(commission, Decimal):
                    try:
                        commission = Decimal(str(float(commission)))
                    except (ValueError, TypeError):
                        continue
                metrics.total_commission += commission
            if hasattr(trade, 'stamp_tax') and trade.stamp_tax:
                stamp_tax = trade.stamp_tax
                if not isinstance(stamp_tax, Decimal):
                    try:
                        stamp_tax = Decimal(str(float(stamp_tax)))
                    except (ValueError, TypeError):
                        continue
                metrics.total_tax += stamp_tax

            # 统计盈亏
            if hasattr(trade, 'pnl') and trade.pnl is not None:
                pnl = trade.pnl
                if not isinstance(pnl, Decimal):
                    try:
                        pnl = Decimal(str(float(pnl)))
                    except (ValueError, TypeError):
                        continue
                if pnl > 0:
                    metrics.winning_trades += 1
                    profits.append(float(pnl))
                    metrics.total_profit += pnl
                elif pnl < 0:
                    metrics.losing_trades += 1
                    losses.append(float(pnl))
                    metrics.total_loss += abs(pnl)
                else:
                    metrics.break_even_trades += 1

        metrics.total_fees = metrics.total_commission + metrics.total_tax
        metrics.net_profit = metrics.total_profit - metrics.total_loss - metrics.total_fees

        # 计算胜率
        closed_trades = metrics.winning_trades + metrics.losing_trades
        if closed_trades > 0:
            metrics.win_rate = metrics.winning_trades / closed_trades
            metrics.loss_rate = metrics.losing_trades / closed_trades

        # 计算平均盈亏
        if profits:
            metrics.avg_profit = Decimal(str(statistics.mean(profits)))
        if losses:
            metrics.avg_loss = Decimal(str(statistics.mean(losses)))

        if metrics.total_trades > 0:
            all_pnl = [float(t.pnl) for t in trades if hasattr(t, 'pnl') and t.pnl is not None]
            if all_pnl:
                metrics.avg_trade = Decimal(str(statistics.mean(all_pnl)))

        # 计算盈亏因子
        if metrics.total_loss > 0:
            metrics.profit_factor = float(metrics.total_profit / metrics.total_loss)
        elif metrics.total_profit > 0:
            metrics.profit_factor = float('inf')

        # 计算盈亏比
        if metrics.avg_loss != 0:
            metrics.profit_loss_ratio = float(metrics.avg_profit / abs(metrics.avg_loss))

        # 计算最大连续盈亏
        metrics.max_consecutive_wins = cls._calc_max_consecutive(trades, True)
        metrics.max_consecutive_losses = cls._calc_max_consecutive(trades, False)

        return metrics

    @staticmethod
    def _calc_max_consecutive(trades: List[Any], is_win: bool) -> int:
        """计算最大连续次数"""
        max_count = 0
        current_count = 0

        for trade in trades:
            if hasattr(trade, 'pnl') and trade.pnl is not None:
                if is_win and trade.pnl > 0:
                    current_count += 1
                    max_count = max(max_count, current_count)
                elif not is_win and trade.pnl < 0:
                    current_count += 1
                    max_count = max(max_count, current_count)
                else:
                    current_count = 0

        return max_count

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "break_even_trades": self.break_even_trades,
            "win_rate": round(self.win_rate, 4),
            "loss_rate": round(self.loss_rate, 4),
            "total_profit": float(self.total_profit),
            "total_loss": float(self.total_loss),
            "net_profit": float(self.net_profit),
            "avg_profit": float(self.avg_profit),
            "avg_loss": float(self.avg_loss),
            "avg_trade": float(self.avg_trade),
            "profit_factor": round(self.profit_factor, 4),
            "profit_loss_ratio": round(self.profit_loss_ratio, 4),
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_consecutive_losses": self.max_consecutive_losses,
            "total_commission": float(self.total_commission),
            "total_tax": float(self.total_tax),
            "total_fees": float(self.total_fees),
        }


@dataclass
class PerformanceMetrics:
    """绩效指标"""
    total_return: float = 0.0
    annual_return: float = 0.0

    volatility: float = 0.0
    annual_volatility: float = 0.0

    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0

    var_95: float = 0.0  # 95% VaR
    cvar_95: float = 0.0  # 95% CVaR

    alpha: float = 0.0
    beta: float = 0.0

    information_ratio: float = 0.0
    tracking_error: float = 0.0

    @classmethod
    def calculate(
        cls,
        portfolio_values: List[Decimal],
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ) -> 'PerformanceMetrics':
        """
        从组合价值序列计算绩效指标

        Args:
            portfolio_values: 组合价值序列
            risk_free_rate: 无风险利率（年化）
            trading_days: 年交易日数量

        Returns:
            PerformanceMetrics: 绩效指标
        """
        metrics = cls()

        if not portfolio_values or len(portfolio_values) < 2:
            return metrics

        # 转换为列表
        values = [float(v) for v in portfolio_values]

        # 计算收益率序列
        returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                ret = (values[i] - values[i-1]) / values[i-1]
                returns.append(ret)

        if not returns:
            return metrics

        # 总收益率
        metrics.total_return = (values[-1] - values[0]) / values[0] if values[0] > 0 else 0

        # 年化收益率
        n = len(returns)
        if n > 0:
            avg_return = statistics.mean(returns)
            metrics.annual_return = (1 + avg_return) ** trading_days - 1

        # 波动率
        if len(returns) > 1:
            metrics.volatility = statistics.stdev(returns)
            metrics.annual_volatility = metrics.volatility * math.sqrt(trading_days)

        # 夏普比率
        if metrics.annual_volatility > 0:
            daily_rf = risk_free_rate / trading_days
            excess_return = avg_return - daily_rf
            metrics.sharpe_ratio = excess_return / metrics.volatility * math.sqrt(trading_days)

        # 索提诺比率（只考虑下行波动）
        downside_returns = [r for r in returns if r < 0]
        if downside_returns and len(downside_returns) > 1:
            downside_std = statistics.stdev(downside_returns)
            if downside_std > 0:
                daily_rf = risk_free_rate / trading_days
                metrics.sortino_ratio = (avg_return - daily_rf) / downside_std * math.sqrt(trading_days)

        # 最大回撤
        metrics.max_drawdown, metrics.max_drawdown_duration = cls._calc_max_drawdown(values)

        # 卡尔马比率
        if abs(metrics.max_drawdown) > 0:
            metrics.calmar_ratio = metrics.annual_return / abs(metrics.max_drawdown)

        # VaR 和 CVaR
        if returns:
            sorted_returns = sorted(returns)
            var_index = int(len(sorted_returns) * 0.05)
            if var_index > 0:
                metrics.var_95 = sorted_returns[var_index]
                cvar_values = sorted_returns[:var_index]
                metrics.cvar_95 = statistics.mean(cvar_values)

        return metrics

    @staticmethod
    def _calc_max_drawdown(values: List[float]) -> tuple[float, int]:
        """
        计算最大回撤和回撤持续时间

        Returns:
            (最大回撤, 最大回撤持续天数)
        """
        peak = values[0]
        max_drawdown = 0.0
        max_duration = 0
        current_duration = 0

        for value in values:
            if value > peak:
                peak = value
                current_duration = 0
            else:
                current_duration += 1
                # 回撤是负数表示亏损
                drawdown = (value - peak) / peak
                if drawdown < max_drawdown:
                    max_drawdown = drawdown
                    max_duration = current_duration

        return max_drawdown, max_duration

    @classmethod
    def calculate_sharpe(
        cls,
        returns: List[float],
        risk_free_rate: float = 0.02,
        trading_days: int = 252
    ) -> float:
        """
        计算夏普比率

        Args:
            returns: 日收益率列表
            risk_free_rate: 无风险利率（年化）
            trading_days: 年交易日数量

        Returns:
            float: 夏普比率
        """
        if not returns or len(returns) < 2:
            return 0.0

        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)

        if std_return == 0:
            return 0.0

        daily_rf = risk_free_rate / trading_days
        excess_return = avg_return - daily_rf

        return excess_return / std_return * math.sqrt(trading_days)

    @classmethod
    def calculate_volatility(
        cls,
        returns: List[float],
        trading_days: int = 252
    ) -> float:
        """
        计算年化波动率

        Args:
            returns: 日收益率列表
            trading_days: 年交易日数量

        Returns:
            float: 年化波动率
        """
        if not returns or len(returns) < 2:
            return 0.0

        return statistics.stdev(returns) * math.sqrt(trading_days)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_return": round(self.total_return, 4),
            "annual_return": round(self.annual_return, 4),
            "volatility": round(self.volatility, 4),
            "annual_volatility": round(self.annual_volatility, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "max_drawdown_duration": self.max_drawdown_duration,
            "var_95": round(self.var_95, 4),
            "cvar_95": round(self.cvar_95, 4),
        }


@dataclass
class RiskMetrics:
    """风险指标"""
    var_95: float = 0.0  # 95% 风险价值
    var_99: float = 0.0  # 99% 风险价值
    cvar_95: float = 0.0  # 95% 条件风险价值
    cvar_99: float = 0.0  # 99% 条件风险价值

    beta: float = 0.0  # 贝塔系数
    alpha: float = 0.0  # 阿尔法系数

    correlation: float = 0.0  # 与基准的相关性
    r_squared: float = 0.0  # R平方

    @classmethod
    def calculate(
        cls,
        returns: List[float],
        benchmark_returns: Optional[List[float]] = None
    ) -> 'RiskMetrics':
        """
        计算风险指标

        Args:
            returns: 策略收益率列表
            benchmark_returns: 基准收益率列表（可选）

        Returns:
            RiskMetrics: 风险指标
        """
        metrics = cls()

        if not returns:
            return metrics

        sorted_returns = sorted(returns)
        n = len(sorted_returns)

        # VaR (历史模拟法)
        if n >= 20:
            var_95_idx = int(n * 0.05)
            var_99_idx = int(n * 0.01)

            if var_95_idx > 0:
                metrics.var_95 = sorted_returns[var_95_idx]
                metrics.cvar_95 = statistics.mean(sorted_returns[:var_95_idx])

            if var_99_idx > 0:
                metrics.var_99 = sorted_returns[var_99_idx]
                metrics.cvar_99 = statistics.mean(sorted_returns[:var_99_idx])

        # 与基准的相关性
        if benchmark_returns and len(benchmark_returns) == len(returns):
            metrics.correlation = cls._calc_correlation(returns, benchmark_returns)
            metrics.r_squared = metrics.correlation ** 2

            # Beta
            bench_std = statistics.stdev(benchmark_returns) if len(benchmark_returns) > 1 else 0
            if bench_std > 0:
                bench_var = bench_std ** 2
                covariance = cls._calc_covariance(returns, benchmark_returns)
                metrics.beta = covariance / bench_var

            # Alpha (简化计算)
            avg_return = statistics.mean(returns)
            avg_benchmark = statistics.mean(benchmark_returns)
            metrics.alpha = avg_return - metrics.beta * avg_benchmark

        return metrics

    @staticmethod
    def _calc_correlation(x: List[float], y: List[float]) -> float:
        """计算相关系数"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        std_x = statistics.stdev(x)
        std_y = statistics.stdev(y)

        if std_x == 0 or std_y == 0:
            return 0.0

        return numerator / ((n - 1) * std_x * std_y)

    @staticmethod
    def _calc_covariance(x: List[float], y: List[float]) -> float:
        """计算协方差"""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)

        return sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "var_95": round(self.var_95, 4),
            "var_99": round(self.var_99, 4),
            "cvar_95": round(self.cvar_95, 4),
            "cvar_99": round(self.cvar_99, 4),
            "beta": round(self.beta, 4),
            "alpha": round(self.alpha, 4),
            "correlation": round(self.correlation, 4),
            "r_squared": round(self.r_squared, 4),
        }
