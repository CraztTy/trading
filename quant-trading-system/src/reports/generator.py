"""
交易报告生成器

职责：
- 生成各类交易报告（日报、周报、月报、年报、自定义）
- 整合交易数据、订单数据、持仓数据
- 计算报告指标和统计
"""
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from enum import Enum
import calendar
import decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.models.order import Order
from src.models.trade import Trade
from src.models.daily_settlement import DailySettlement
from src.models.account import Account
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class ReportType(Enum):
    """报告类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class ReportPeriod:
    """报告周期"""
    start_date: date
    end_date: date
    period_type: ReportType

    @property
    def days(self) -> int:
        """天数"""
        return (self.end_date - self.start_date).days + 1


@dataclass
class DailyReport:
    """日交易报告"""
    account_id: int
    report_date: date
    report_type: ReportType = ReportType.DAILY

    # 基本统计
    trade_count: int = 0
    order_count: int = 0
    filled_order_count: int = 0

    # 盈亏
    realized_pnl: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    total_pnl: Decimal = Decimal("0")

    # 费用
    total_commission: Decimal = Decimal("0")
    total_tax: Decimal = Decimal("0")
    total_fee: Decimal = Decimal("0")

    # 交易指标
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_profit: Decimal = Decimal("0")
    avg_loss: Decimal = Decimal("0")

    # 资金
    begin_balance: Decimal = Decimal("0")
    end_balance: Decimal = Decimal("0")
    total_value: Decimal = Decimal("0")

    # 明细
    trades: List[Trade] = field(default_factory=list)
    orders: List[Order] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "report_type": self.report_type.value,
            "account_id": self.account_id,
            "report_date": self.report_date.isoformat(),
            "trade_count": self.trade_count,
            "order_count": self.order_count,
            "realized_pnl": float(self.realized_pnl),
            "unrealized_pnl": float(self.unrealized_pnl),
            "total_fee": float(self.total_fee),
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "begin_balance": float(self.begin_balance),
            "end_balance": float(self.end_balance),
            "total_value": float(self.total_value),
        }


@dataclass
class WeeklyReport:
    """周交易报告"""
    account_id: int
    year: int
    week: int
    report_type: ReportType = ReportType.WEEKLY

    # 日期范围
    start_date: date = date(1970, 1, 1)
    end_date: date = date(1970, 1, 1)

    # 交易统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    # 盈亏
    realized_pnl: Decimal = Decimal("0")
    total_fee: Decimal = Decimal("0")
    net_pnl: Decimal = Decimal("0")

    # 收益率
    weekly_return: float = 0.0
    cumulative_return: float = 0.0

    # 每日数据
    daily_returns: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "report_type": self.report_type.value,
            "account_id": self.account_id,
            "year": self.year,
            "week": self.week,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_trades": self.total_trades,
            "realized_pnl": float(self.realized_pnl),
            "weekly_return": self.weekly_return,
            "cumulative_return": self.cumulative_return,
        }


@dataclass
class MonthlyReport:
    """月交易报告"""
    account_id: int
    year: int
    month: int
    report_type: ReportType = ReportType.MONTHLY

    # 交易天数
    trading_days: int = 0
    win_days: int = 0
    lose_days: int = 0
    win_rate: float = 0.0

    # 交易统计
    total_trades: int = 0
    avg_daily_trades: float = 0.0

    # 盈亏
    realized_pnl: Decimal = Decimal("0")
    total_fee: Decimal = Decimal("0")
    net_pnl: Decimal = Decimal("0")

    # 收益率
    monthly_return: float = 0.0
    max_daily_return: float = 0.0
    min_daily_return: float = 0.0
    volatility: float = 0.0

    # 交易品种
    symbols_traded: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "report_type": self.report_type.value,
            "account_id": self.account_id,
            "year": self.year,
            "month": self.month,
            "trading_days": self.trading_days,
            "win_days": self.win_days,
            "lose_days": self.lose_days,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "realized_pnl": float(self.realized_pnl),
            "monthly_return": self.monthly_return,
            "volatility": self.volatility,
        }


@dataclass
class CustomReport:
    """自定义时间段报告"""
    account_id: int
    start_date: date
    end_date: date
    report_type: ReportType = ReportType.CUSTOM

    # 综合统计
    total_trades: int = 0
    total_orders: int = 0

    # 盈亏统计
    realized_pnl: Decimal = Decimal("0")
    total_commission: Decimal = Decimal("0")
    total_tax: Decimal = Decimal("0")

    # 绩效指标
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0

    # 交易明细
    trades: List[Trade] = field(default_factory=list)
    daily_settlements: List[DailySettlement] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "report_type": self.report_type.value,
            "account_id": self.account_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days": (self.end_date - self.start_date).days + 1,
            "total_trades": self.total_trades,
            "realized_pnl": float(self.realized_pnl),
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
        }


class ReportGenerator:
    """
    报告生成器

    生成各类交易报告
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_daily_report(
        self,
        account_id: int,
        report_date: date
    ) -> DailyReport:
        """
        生成日报告

        Args:
            account_id: 账户ID
            report_date: 报告日期

        Returns:
            DailyReport: 日报告
        """
        logger.info(f"生成日报告: account={account_id}, date={report_date}")

        # 获取数据
        trades = await self._get_trades(account_id, report_date, report_date)
        orders = await self._get_orders(account_id, report_date, report_date)
        settlements = await self._get_daily_settlements(account_id, report_date, report_date)

        # 计算统计
        report = DailyReport(
            account_id=account_id,
            report_date=report_date,
            trades=trades,
            orders=orders
        )

        # 基本统计
        report.trade_count = len(trades)
        report.order_count = len(orders)
        report.filled_order_count = sum(1 for o in orders if o.status.value == "FILLED")

        # 计算盈亏和费用
        for trade in trades:
            if trade.pnl:
                pnl = trade.pnl
                if not isinstance(pnl, Decimal):
                    try:
                        pnl = Decimal(str(float(pnl)))
                    except (ValueError, TypeError):
                        pnl = Decimal("0")
                report.realized_pnl += pnl
            if trade.commission:
                commission = trade.commission
                if not isinstance(commission, Decimal):
                    try:
                        commission = Decimal(str(float(commission)))
                    except (ValueError, TypeError):
                        commission = Decimal("0")
                report.total_commission += commission
            if trade.stamp_tax:
                stamp_tax = trade.stamp_tax
                if not isinstance(stamp_tax, Decimal):
                    try:
                        stamp_tax = Decimal(str(float(stamp_tax)))
                    except (ValueError, TypeError):
                        stamp_tax = Decimal("0")
                report.total_tax += stamp_tax
            if hasattr(trade, 'transfer_fee') and trade.transfer_fee:
                fee = trade.transfer_fee
                if not isinstance(fee, Decimal):
                    try:
                        fee = Decimal(str(float(fee)))
                    except (ValueError, TypeError, decimal.InvalidOperation):
                        fee = Decimal("0")
                report.total_fee += fee

        report.total_fee = report.total_commission + report.total_tax
        report.total_pnl = report.realized_pnl - report.total_fee

        # 计算胜率等
        if trades:
            closed_trades = [t for t in trades if t.pnl is not None]
            if closed_trades:
                winning_trades = [t for t in closed_trades if t.pnl > 0]
                report.win_rate = len(winning_trades) / len(closed_trades)

        # 资金数据
        if settlements:
            report.begin_balance = settlements[0].begin_balance
            report.end_balance = settlements[0].end_balance
            report.total_value = report.end_balance + settlements[0].position_value

        return report

    async def generate_weekly_report(
        self,
        account_id: int,
        year: int,
        week: int
    ) -> WeeklyReport:
        """
        生成周报告

        Args:
            account_id: 账户ID
            year: 年份
            week: 周数（1-53）

        Returns:
            WeeklyReport: 周报告
        """
        logger.info(f"生成周报告: account={account_id}, year={year}, week={week}")

        # 计算周的起止日期
        start_date, end_date = self._get_week_dates(year, week)

        # 获取数据
        trades = await self._get_trades(account_id, start_date, end_date)
        settlements = await self._get_daily_settlements(account_id, start_date, end_date)

        report = WeeklyReport(
            account_id=account_id,
            year=year,
            week=week,
            start_date=start_date,
            end_date=end_date
        )

        # 交易统计
        report.total_trades = len(trades)
        closed_trades = [t for t in trades if t.pnl is not None]
        report.winning_trades = sum(1 for t in closed_trades if t.pnl > 0)
        report.losing_trades = sum(1 for t in closed_trades if t.pnl < 0)

        # 盈亏
        for trade in trades:
            if trade.pnl:
                pnl = trade.pnl
                if not isinstance(pnl, Decimal):
                    try:
                        pnl = Decimal(str(float(pnl)))
                    except (ValueError, TypeError, decimal.InvalidOperation):
                        pnl = Decimal("0")
                report.realized_pnl += pnl
            if trade.commission:
                commission = trade.commission
                if not isinstance(commission, Decimal):
                    try:
                        commission = Decimal(str(float(commission)))
                    except (ValueError, TypeError, decimal.InvalidOperation):
                        commission = Decimal("0")
                report.total_fee += commission
            if trade.stamp_tax:
                stamp_tax = trade.stamp_tax
                if not isinstance(stamp_tax, Decimal):
                    try:
                        stamp_tax = Decimal(str(float(stamp_tax)))
                    except (ValueError, TypeError, decimal.InvalidOperation):
                        stamp_tax = Decimal("0")
                report.total_fee += stamp_tax

        report.net_pnl = report.realized_pnl - report.total_fee

        # 收益率
        if settlements:
            begin = settlements[0].begin_balance
            end = settlements[-1].end_balance
            # 处理 Mock 对象
            if not isinstance(begin, (int, float, Decimal)):
                begin = float(begin)
            if not isinstance(end, (int, float, Decimal)):
                end = float(end)
            if begin > 0:
                report.weekly_return = float((end - begin) / begin)
                return_pct = settlements[-1].return_pct if settlements[-1].return_pct else 0
                if not isinstance(return_pct, (int, float)):
                    return_pct = float(return_pct)
                report.cumulative_return = return_pct

            # 每日数据
            for s in settlements:
                return_pct = s.return_pct if s.return_pct else 0
                if not isinstance(return_pct, (int, float)):
                    return_pct = float(return_pct)
                net_pnl = s.net_pnl if s.net_pnl else 0
                if not isinstance(net_pnl, (int, float, Decimal)):
                    net_pnl = float(net_pnl)
                report.daily_returns.append({
                    "date": s.trade_date.isoformat() if hasattr(s.trade_date, 'isoformat') else str(s.trade_date),
                    "return": return_pct,
                    "pnl": float(net_pnl)
                })

        return report

    async def generate_monthly_report(
        self,
        account_id: int,
        year: int,
        month: int
    ) -> MonthlyReport:
        """
        生成月报告

        Args:
            account_id: 账户ID
            year: 年份
            month: 月份（1-12）

        Returns:
            MonthlyReport: 月报告
        """
        logger.info(f"生成月报告: account={account_id}, year={year}, month={month}")

        # 计算月起止日期
        start_date = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = date(year, month, last_day)

        # 获取数据
        trades = await self._get_trades(account_id, start_date, end_date)
        settlements = await self._get_daily_settlements(account_id, start_date, end_date)

        report = MonthlyReport(
            account_id=account_id,
            year=year,
            month=month
        )

        # 交易天数
        report.trading_days = len(settlements)
        for s in settlements:
            net_pnl = s.net_pnl
            if net_pnl is not None:
                if not isinstance(net_pnl, (int, float, Decimal)):
                    net_pnl = float(net_pnl)
                if net_pnl > 0:
                    report.win_days += 1
                elif net_pnl < 0:
                    report.lose_days += 1
        if report.trading_days > 0:
            report.win_rate = report.win_days / report.trading_days

        # 交易统计
        report.total_trades = len(trades)
        if report.trading_days > 0:
            report.avg_daily_trades = report.total_trades / report.trading_days

        # 盈亏
        for trade in trades:
            if trade.pnl:
                pnl = trade.pnl
                if not isinstance(pnl, Decimal):
                    try:
                        pnl = Decimal(str(float(pnl)))
                    except (ValueError, TypeError, decimal.InvalidOperation):
                        pnl = Decimal("0")
                report.realized_pnl += pnl
            if trade.commission:
                commission = trade.commission
                if not isinstance(commission, Decimal):
                    try:
                        commission = Decimal(str(float(commission)))
                    except (ValueError, TypeError, decimal.InvalidOperation):
                        commission = Decimal("0")
                report.total_fee += commission
            if trade.stamp_tax:
                stamp_tax = trade.stamp_tax
                if not isinstance(stamp_tax, Decimal):
                    try:
                        stamp_tax = Decimal(str(float(stamp_tax)))
                    except (ValueError, TypeError, decimal.InvalidOperation):
                        stamp_tax = Decimal("0")
                report.total_fee += stamp_tax

        report.net_pnl = report.realized_pnl - report.total_fee

        # 收益率
        if settlements:
            begin = settlements[0].begin_balance
            end = settlements[-1].end_balance
            # 处理 Mock 对象
            if not isinstance(begin, (int, float, Decimal)):
                begin = float(begin)
            if not isinstance(end, (int, float, Decimal)):
                end = float(end)
            if begin > 0:
                report.monthly_return = float((end - begin) / begin)

            # 每日收益率
            daily_returns = []
            for s in settlements:
                rp = s.return_pct if s.return_pct else 0
                if not isinstance(rp, (int, float)):
                    rp = float(rp)
                daily_returns.append(rp)
            if daily_returns:
                report.max_daily_return = max(daily_returns)
                report.min_daily_return = min(daily_returns)
                # 计算波动率
                import statistics
                if len(daily_returns) > 1:
                    report.volatility = statistics.stdev(daily_returns) * (252 ** 0.5)

        # 交易品种
        symbols = set()
        for trade in trades:
            symbols.add(trade.symbol)
        report.symbols_traded = sorted(list(symbols))

        return report

    async def generate_custom_report(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> CustomReport:
        """
        生成自定义时间段报告

        Args:
            account_id: 账户ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            CustomReport: 自定义报告
        """
        logger.info(f"生成自定义报告: account={account_id}, {start_date} ~ {end_date}")

        # 获取数据
        trades = await self._get_trades(account_id, start_date, end_date)
        orders = await self._get_orders(account_id, start_date, end_date)
        settlements = await self._get_daily_settlements(account_id, start_date, end_date)

        report = CustomReport(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            trades=trades,
            daily_settlements=settlements
        )

        # 基本统计
        report.total_trades = len(trades)
        report.total_orders = len(orders)

        # 盈亏和费用
        for trade in trades:
            if trade.pnl:
                report.realized_pnl += trade.pnl
            if trade.commission:
                report.total_commission += trade.commission
            if trade.stamp_tax:
                report.total_tax += trade.stamp_tax

        # 绩效指标
        if settlements:
            begin = settlements[0].begin_balance
            end = settlements[-1].end_balance
            if begin > 0:
                report.total_return = float((end - begin) / begin)

                # 年化收益
                days = (end_date - start_date).days + 1
                if days > 0:
                    years = days / 365
                    report.annual_return = (1 + report.total_return) ** (1 / years) - 1

        return report

    async def _get_trades(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> List[Trade]:
        """获取交易记录"""
        query = select(Trade).where(
            and_(
                Trade.account_id == account_id,
                func.date(Trade.trade_time) >= start_date,
                func.date(Trade.trade_time) <= end_date
            )
        ).order_by(Trade.trade_time)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def _get_orders(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> List[Order]:
        """获取订单记录"""
        query = select(Order).where(
            and_(
                Order.account_id == account_id,
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date
            )
        ).order_by(Order.created_at)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def _get_portfolio_snapshots(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> List[Any]:
        """获取组合快照记录（用于回测和模拟）"""
        # 实际实现中应该从数据库查询
        # 这里返回空列表作为占位
        return []

    async def _get_daily_settlements(
        self,
        account_id: int,
        start_date: date,
        end_date: date
    ) -> List[DailySettlement]:
        """获取日结算记录"""
        query = select(DailySettlement).where(
            and_(
                DailySettlement.account_id == account_id,
                DailySettlement.trade_date >= start_date,
                DailySettlement.trade_date <= end_date
            )
        ).order_by(DailySettlement.trade_date)

        result = await self.session.execute(query)
        return result.scalars().all()

    def _get_week_dates(self, year: int, week: int) -> Tuple[date, date]:
        """获取周的起止日期"""
        # 找到该年的第一个星期四（ISO周定义）
        jan4 = date(year, 1, 4)
        first_monday = jan4 - timedelta(days=jan4.weekday())

        # 计算目标周的起始日期
        start_date = first_monday + timedelta(weeks=week-1)
        end_date = start_date + timedelta(days=6)

        return start_date, end_date
