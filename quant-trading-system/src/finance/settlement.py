"""
日终结算管理器

职责：
- 日终结算数据生成
- 对账处理
- 结算报表生成
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
import math

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.daily_settlement import DailySettlement
from src.models.balance_flow import BalanceFlow
from src.models.enums import FlowType
from src.common.logger import TradingLogger
from src.common.exceptions import BusinessLogicError

logger = TradingLogger(__name__)


@dataclass
class SettlementResult:
    """结算结果"""
    success: bool
    settlement: Optional[DailySettlement]
    error_msg: Optional[str] = None


def calculate_max_drawdown(nav_values: List[Decimal]) -> Decimal:
    """
    计算最大回撤

    Args:
        nav_values: 净值序列

    Returns:
        最大回撤（负数）
    """
    if not nav_values or len(nav_values) < 2:
        return Decimal("0")

    max_dd = Decimal("0")
    peak = nav_values[0]

    for value in nav_values:
        if value > peak:
            peak = value
        dd = (value - peak) / peak
        if dd < max_dd:
            max_dd = dd

    return max_dd


def calculate_sharpe(
    daily_returns: List[Decimal],
    risk_free_rate: Decimal = Decimal("0.0001"),
    periods_per_year: int = 252
) -> float:
    """
    计算夏普比率

    Args:
        daily_returns: 日收益率列表
        risk_free_rate: 日无风险利率
        periods_per_year: 每年交易天数

    Returns:
        夏普比率
    """
    if not daily_returns or len(daily_returns) < 2:
        return 0.0

    # 计算平均收益
    mean_return = sum(daily_returns) / len(daily_returns)

    # 计算标准差
    variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std_dev = math.sqrt(float(variance))

    if std_dev == 0:
        return 0.0

    # 年化夏普
    excess_return = float(mean_return - risk_free_rate)
    annualized_sharpe = excess_return / std_dev * math.sqrt(periods_per_year)

    return annualized_sharpe


def calculate_volatility(
    daily_returns: List[Decimal],
    periods_per_year: int = 252
) -> float:
    """
    计算波动率

    Args:
        daily_returns: 日收益率列表
        periods_per_year: 每年交易天数

    Returns:
        年化波动率
    """
    if not daily_returns or len(daily_returns) < 2:
        return 0.0

    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std_dev = math.sqrt(float(variance))

    return std_dev * math.sqrt(periods_per_year)


class SettlementReport:
    """结算报表生成器"""

    @staticmethod
    def generate_daily_report(settlement: DailySettlement) -> Dict:
        """
        生成日报表

        Args:
            settlement: 结算数据

        Returns:
            报表字典
        """
        return {
            "trade_date": settlement.trade_date.isoformat(),
            "account_id": settlement.account_id,
            "begin_balance": float(settlement.begin_balance),
            "end_balance": float(settlement.end_balance),
            "deposit": float(settlement.deposit),
            "withdraw": float(settlement.withdraw),
            "realized_pnl": float(settlement.realized_pnl),
            "total_fee": float(settlement.total_fee),
            "net_pnl": float(settlement.net_pnl),
            "return_pct": float(settlement.return_pct * 100),
            "position_count": settlement.position_count,
            "position_value": float(settlement.position_value),
            "total_orders": settlement.total_orders,
            "filled_orders": settlement.filled_orders,
            "total_trades": settlement.total_trades,
            "total_volume": settlement.total_volume,
            "total_turnover": float(settlement.total_turnover),
            "reconciled": settlement.reconciled,
            "reconcile_diff": float(settlement.reconcile_diff),
        }

    @staticmethod
    def generate_monthly_summary(
        account_id: int,
        year: int,
        month: int,
        settlements: List[DailySettlement]
    ) -> Dict:
        """
        生成月报

        Args:
            account_id: 账户ID
            year: 年份
            month: 月份
            settlements: 结算数据列表

        Returns:
            月报字典
        """
        if not settlements:
            return {
                "account_id": account_id,
                "year": year,
                "month": month,
                "total_days": 0,
                "total_trades": 0,
                "total_pnl": 0.0,
                "total_fee": 0.0,
                "avg_return": 0.0,
            }

        total_days = len(settlements)
        total_trades = sum(s.total_trades for s in settlements)
        total_pnl = sum(float(s.net_pnl) for s in settlements)
        total_fee = sum(float(s.total_fee) for s in settlements)

        # 计算平均日收益
        returns = [float(s.return_pct) for s in settlements]
        avg_return = sum(returns) / len(returns) if returns else 0.0

        # 计算胜率
        positive_days = sum(1 for s in settlements if s.net_pnl > 0)
        win_rate = positive_days / total_days if total_days > 0 else 0.0

        return {
            "account_id": account_id,
            "year": year,
            "month": month,
            "total_days": total_days,
            "positive_days": positive_days,
            "negative_days": total_days - positive_days,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "total_fee": total_fee,
            "net_pnl": total_pnl - total_fee,
            "avg_return": avg_return * 100,
            "max_daily_return": max(returns) * 100 if returns else 0.0,
            "min_daily_return": min(returns) * 100 if returns else 0.0,
        }


class SettlementManager:
    """
    结算管理器

    处理日终结算相关业务
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_settlement(
        self,
        account_id: int,
        trade_date: date,
        trades: List,
        orders: List,
        begin_balance: Optional[Decimal] = None
    ) -> SettlementResult:
        """
        生成日终结算数据

        Args:
            account_id: 账户ID
            trade_date: 交易日期
            trades: 成交列表
            orders: 订单列表
            begin_balance: 期初余额（可选，默认从流水计算）

        Returns:
            SettlementResult: 结算结果
        """
        try:
            # 如果没有提供期初余额，从昨天的结算获取
            if begin_balance is None:
                yesterday = trade_date - timedelta(days=1)
                yesterday_settlement = await self._get_settlement(account_id, yesterday)
                if yesterday_settlement:
                    begin_balance = yesterday_settlement.end_balance
                else:
                    begin_balance = Decimal("0")

            # 统计成交数据
            total_trades = len(trades)
            total_volume = sum(t.qty for t in trades if hasattr(t, 'qty'))
            total_turnover = sum(
                t.amount for t in trades
                if hasattr(t, 'amount') and t.amount
            )

            # 统计订单数据
            total_orders = len(orders)
            filled_orders = sum(1 for o in orders if o.status == "FILLED")

            # 统计费用和盈亏
            total_fee = Decimal("0")
            realized_pnl = Decimal("0")

            for trade in trades:
                # 费用
                if hasattr(trade, 'commission') and trade.commission:
                    total_fee += trade.commission
                if hasattr(trade, 'stamp_tax') and trade.stamp_tax:
                    total_fee += trade.stamp_tax
                if hasattr(trade, 'transfer_fee') and trade.transfer_fee:
                    total_fee += trade.transfer_fee

                # 盈亏（卖出才有）
                if hasattr(trade, 'side') and trade.side == "SELL":
                    if hasattr(trade, 'pnl') and trade.pnl:
                        realized_pnl += trade.pnl

            # 计算期末余额
            # 简化计算：期初 + 入金 - 出金 + 卖出 - 买入 - 费用
            daily_flows = await self._get_daily_flows(account_id, trade_date)

            deposit = sum(
                f.amount for f in daily_flows
                if f.flow_type == FlowType.DEPOSIT
            )
            withdraw = sum(
                abs(f.amount) for f in daily_flows
                if f.flow_type == FlowType.WITHDRAW
            )
            buy_amount = sum(
                abs(f.amount) for f in daily_flows
                if f.flow_type == FlowType.TRADE_BUY
            )
            sell_amount = sum(
                f.amount for f in daily_flows
                if f.flow_type == FlowType.TRADE_SELL
            )

            end_balance = (
                begin_balance +
                deposit -
                withdraw +
                sell_amount -
                buy_amount
            )

            # 创建结算记录
            settlement = DailySettlement(
                account_id=account_id,
                trade_date=trade_date,
                begin_balance=begin_balance,
                end_balance=end_balance,
                deposit=deposit,
                withdraw=withdraw,
                realized_pnl=realized_pnl,
                total_fee=total_fee,
                position_count=0,  # 可由外部传入
                position_value=Decimal("0"),
                total_orders=total_orders,
                filled_orders=filled_orders,
                total_trades=total_trades,
                total_volume=total_volume,
                total_turnover=total_turnover,
                reconciled=False
            )

            self.session.add(settlement)
            await self.session.flush()

            logger.info(
                "日终结算生成成功",
                account_id=account_id,
                trade_date=trade_date.isoformat(),
                return_pct=float(settlement.return_pct * 100)
            )

            return SettlementResult(
                success=True,
                settlement=settlement
            )

        except Exception as e:
            logger.error(
                f"日终结算生成失败: {e}",
                account_id=account_id,
                trade_date=trade_date.isoformat()
            )
            return SettlementResult(
                success=False,
                settlement=None,
                error_msg=str(e)
            )

    async def reconcile(
        self,
        account_id: int,
        trade_date: date,
        actual_balance: Decimal
    ) -> bool:
        """
        对账

        Args:
            account_id: 账户ID
            trade_date: 交易日期
            actual_balance: 实际余额

        Returns:
            是否对账成功
        """
        settlement = await self._get_settlement(account_id, trade_date)
        if not settlement:
            raise BusinessLogicError(f"未找到结算记录: {trade_date}")

        result = settlement.reconcile(actual_balance)

        if result:
            logger.info(
                "对账成功",
                account_id=account_id,
                trade_date=trade_date.isoformat()
            )
        else:
            logger.warning(
                "对账有差异",
                account_id=account_id,
                trade_date=trade_date.isoformat(),
                diff=float(settlement.reconcile_diff)
            )

        await self.session.flush()
        return result

    async def get_settlement_history(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> List[DailySettlement]:
        """
        获取结算历史

        Args:
            account_id: 账户ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            结算记录列表
        """
        query = select(DailySettlement).where(
            and_(
                DailySettlement.account_id == account_id,
                DailySettlement.trade_date >= start_date,
                DailySettlement.trade_date <= end_date
            )
        ).order_by(DailySettlement.trade_date.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    async def calculate_period_return(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        计算期间收益

        Args:
            account_id: 账户ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            收益统计字典
        """
        settlements = await self.get_settlement_history(
            account_id, start_date, end_date
        )

        if not settlements:
            return {
                "total_days": 0,
                "positive_days": 0,
                "negative_days": 0,
                "cumulative_return": 0.0,
                "avg_daily_return": 0.0,
                "volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0
            }

        returns = [float(s.return_pct) for s in settlements]
        nav_values = []
        nav = Decimal("1.0")
        for s in settlements:
            nav = nav * (Decimal("1") + s.return_pct)
            nav_values.append(nav)

        total_days = len(settlements)
        positive_days = sum(1 for r in returns if r > 0)
        negative_days = total_days - positive_days

        # 累计收益
        cumulative_return = float((nav - Decimal("1")) * 100)

        # 平均日收益
        avg_daily_return = sum(returns) / len(returns) * 100

        # 波动率
        volatility = calculate_volatility([Decimal(str(r)) for r in returns]) * 100

        # 夏普比率
        sharpe = calculate_sharpe([Decimal(str(r)) for r in returns])

        # 最大回撤
        max_dd = calculate_max_drawdown(nav_values) * 100

        return {
            "total_days": total_days,
            "positive_days": positive_days,
            "negative_days": negative_days,
            "cumulative_return": cumulative_return,
            "avg_daily_return": avg_daily_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd
        }

    async def _get_settlement(
        self,
        account_id: int,
        trade_date: date
    ) -> Optional[DailySettlement]:
        """获取指定日期的结算记录"""
        query = select(DailySettlement).where(
            and_(
                DailySettlement.account_id == account_id,
                DailySettlement.trade_date == trade_date
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_daily_flows(
        self,
        account_id: int,
        trade_date: date
    ) -> List[BalanceFlow]:
        """获取指定日期的流水"""
        query = select(BalanceFlow).where(
            and_(
                BalanceFlow.account_id == account_id,
                func.date(BalanceFlow.created_at) == trade_date
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()
