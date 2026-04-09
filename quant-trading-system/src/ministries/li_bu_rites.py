"""
礼部 - 业绩报表与策略排行

职责：
- 生成策略业绩报表
- 计算收益率、夏普比率等指标
- 策略排行榜
- 综合评分卡
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from src.common.logger import get_logger

logger = get_logger(__name__)


class LiBuRites:
    """礼部：业绩报表中心"""

    def __init__(self, config: dict):
        self.config = config
        self.trade_records: List[Dict] = []  # 交易记录
        self.daily_records: List[Dict] = []  # 每日净值记录

    def record_trade(self, trade: Dict[str, Any]):
        """记录交易"""
        self.trade_records.append({
            **trade,
            'recorded_at': datetime.now().isoformat()
        })

    def record_daily_value(
        self,
        date: str,
        total_value: float,
        cash: float,
        positions_value: float
    ):
        """记录每日净值"""
        self.daily_records.append({
            'date': date,
            'total_value': total_value,
            'cash': cash,
            'positions_value': positions_value,
            'recorded_at': datetime.now().isoformat()
        })

    def generate_report(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成业绩报告

        Returns:
            业绩报告字典
        """
        df_trades = pd.DataFrame(self.trade_records)
        df_daily = pd.DataFrame(self.daily_records)

        if df_daily.empty:
            return {'error': '无数据'}

        # 计算基础指标
        initial_value = df_daily['total_value'].iloc[0]
        final_value = df_daily['total_value'].iloc[-1]
        total_return = (final_value - initial_value) / initial_value

        report = {
            'summary': {
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': total_return,
                'total_return_pct': f"{total_return:.2%}",
                'total_trades': len(df_trades),
                'start_date': df_daily['date'].iloc[0] if not df_daily.empty else None,
                'end_date': df_daily['date'].iloc[-1] if not df_daily.empty else None,
            },
            'returns': self._calc_return_metrics(df_daily),
            'risks': self._calc_risk_metrics(df_daily),
            'trades': self._calc_trade_metrics(df_trades),
            'generated_at': datetime.now().isoformat()
        }

        return report

    def _calc_return_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算收益指标"""
        if df.empty or 'total_value' not in df.columns:
            return {}

        values = df['total_value'].values
        returns = np.diff(values) / values[:-1]

        # 年化收益率
        total_days = len(df)
        total_return = (values[-1] - values[0]) / values[0]
        annual_return = (1 + total_return) ** (252 / total_days) - 1 if total_days > 0 else 0

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'annual_return_pct': f"{annual_return:.2%}",
            'daily_returns_mean': np.mean(returns) if len(returns) > 0 else 0,
            'daily_returns_std': np.std(returns) if len(returns) > 0 else 0,
        }

    def _calc_risk_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算风险指标"""
        if df.empty or 'total_value' not in df.columns:
            return {}

        values = df['total_value'].values
        returns = np.diff(values) / values[:-1]

        # 最大回撤
        peak = values[0]
        max_drawdown = 0
        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)

        # 夏普比率（假设无风险利率2%）
        if len(returns) > 0 and np.std(returns) > 0:
            excess_returns = np.mean(returns) - 0.02 / 252
            sharpe_ratio = excess_returns / np.std(returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        # 胜率
        win_rate = np.sum(returns > 0) / len(returns) if len(returns) > 0 else 0

        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': f"{max_drawdown:.2%}",
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'win_rate_pct': f"{win_rate:.2%}",
            'volatility': np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0,
        }

    def _calc_trade_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算交易指标"""
        if df.empty:
            return {}

        # 胜率
        if 'pnl' in df.columns:
            wins = df[df['pnl'] > 0]
            losses = df[df['pnl'] < 0]
            win_rate = len(wins) / len(df) if len(df) > 0 else 0

            avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
            avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0

            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0

        return {
            'total_trades': len(df),
            'win_rate': win_rate,
            'win_rate_pct': f"{win_rate:.2%}",
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
        }

    def generate_ranking(
        self,
        strategy_stats: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成策略排行榜

        Args:
            strategy_stats: 策略统计字典

        Returns:
            排名列表
        """
        rankings = []

        for strategy_id, stats in strategy_stats.items():
            # 计算综合得分
            score = self._calc_score(stats)

            rankings.append({
                'strategy_id': strategy_id,
                'total_return': stats.get('total_pnl', 0),
                'win_rate': stats.get('win_trades', 0) / max(stats.get('total_trades', 1), 1),
                'total_trades': stats.get('total_trades', 0),
                'score': score,
                'rank': 0  # 将在排序后填充
            })

        # 按得分排序
        rankings.sort(key=lambda x: x['score'], reverse=True)

        # 填充排名
        for i, r in enumerate(rankings):
            r['rank'] = i + 1

        return rankings

    def _calc_score(self, stats: Dict[str, Any]) -> float:
        """计算策略综合得分"""
        total_trades = stats.get('total_trades', 0)
        if total_trades == 0:
            return 0

        win_rate = stats.get('win_trades', 0) / total_trades
        total_pnl = stats.get('total_pnl', 0)

        # 简单的评分公式
        score = win_rate * 50 + min(total_pnl / 10000, 50)
        return score
