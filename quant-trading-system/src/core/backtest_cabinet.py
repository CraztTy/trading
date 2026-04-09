"""
回测内阁

职责：
- 管理回测任务生命周期
- 历史数据回放
- 多策略并行回测
- 完整风控规则执行
- 详细业绩报告生成
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import pandas as pd
import numpy as np
import asyncio
from src.common.logger import get_logger
from src.core.crown_prince import CrownPrince
from src.core.zhongshu_sheng import ZhongshuSheng
from src.core.menxia_sheng import MenxiaSheng
from src.core.shangshu_sheng import ShangshuSheng
from src.ministries.li_bu_rites import LiBuRites

logger = get_logger(__name__)


class BacktestCabinet:
    """
    回测内阁 - 管理完整的回测流程
    """

    def __init__(self, config: dict):
        self.config = config
        self.tasks: Dict[str, Dict] = {}  # 回测任务存储

        # 初始化三省
        self.crown_prince = CrownPrince(config)
        self.zhongshu = ZhongshuSheng(config)
        self.menxia = MenxiaSheng(config)
        self.shangshu = ShangshuSheng(config)
        self.li_bu = LiBuRites(config)

        # 数据源提供者（将在运行时注入）
        self.data_provider = None

    def set_data_provider(self, provider):
        """设置数据提供者"""
        self.data_provider = provider

    async def create_task(self, params: dict) -> str:
        """
        创建回测任务

        Returns:
            任务ID
        """
        task_id = f"bt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        self.tasks[task_id] = {
            'id': task_id,
            'status': 'pending',
            'params': params,
            'created_at': datetime.now().isoformat(),
            'started_at': None,
            'completed_at': None,
            'progress': 0,
            'results': None,
            'error': None,
            'logs': []
        }

        logger.info(f"回测任务创建: {task_id}")
        return task_id

    async def run_backtest(self, task_id: str, params: Optional[dict] = None):
        """
        执行回测

        Args:
            task_id: 任务ID
            params: 回测参数（可选，默认使用创建时的参数）
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")

        task = self.tasks[task_id]

        if task['status'] == 'running':
            logger.warning(f"任务已在运行: {task_id}")
            return

        task['status'] = 'running'
        task['started_at'] = datetime.now().isoformat()

        # 使用传入参数或创建时的参数
        run_params = params or task['params']

        try:
            # 1. 准备回测参数
            symbols = run_params.get('symbols', [])
            start_date = run_params.get('start_date', self.config.get('default_start_date', '2024-01-01'))
            end_date = run_params.get('end_date', self.config.get('default_end_date', '2025-12-31'))
            strategy_ids = run_params.get('strategies', [])
            initial_capital = run_params.get('initial_capital', 1000000.0)

            if not symbols:
                raise ValueError("回测股票列表不能为空")

            if not self.data_provider:
                raise ValueError("数据提供者未设置")

            logger.info(f"开始回测: {symbols} [{start_date} ~ {end_date}]")

            # 2. 加载历史数据
            historical_data = await self._load_historical_data(symbols, start_date, end_date)

            if not historical_data:
                raise ValueError("无法加载历史数据")

            # 3. 初始化账户状态
            portfolio = self._init_portfolio(initial_capital)

            # 4. 按时间顺序回放
            all_dates = self._get_all_trading_dates(historical_data)
            total_bars = len(all_dates)

            trade_records = []

            for i, current_time in enumerate(all_dates):
                # 更新进度
                task['progress'] = int((i / total_bars) * 100)

                # 获取当前bar的所有股票数据
                current_bars = self._get_bars_at_time(historical_data, current_time)

                for code, klines in current_bars.items():
                    # 太子院：数据校验
                    valid_klines = await self.crown_prince.validate_and_distribute(klines, code)
                    if valid_klines is None:
                        continue

                    # 中书省：策略信号生成
                    signals = await self.zhongshu.generate_signals(valid_klines, code, strategy_ids)

                    # 门下省：风控审核
                    passed_signals, rejected = await self.menxia.review_signals(signals, portfolio)

                    # 尚书省：执行订单
                    if passed_signals:
                        executed = await self.shangshu.execute_orders(passed_signals, current_bars)
                        trade_records.extend(executed)

                        # 记录交易
                        for trade in executed:
                            self.li_bu.record_trade(trade)

                    # 检查止盈止损
                    stop_signals = await self.shangshu.check_stops(portfolio.get('positions', {}), current_bars)
                    if stop_signals:
                        stop_executed = await self.shangshu.execute_orders(stop_signals, current_bars)
                        trade_records.extend(stop_executed)
                        for trade in stop_executed:
                            self.li_bu.record_trade(trade)

                # 更新投资组合市值
                self._update_portfolio_value(portfolio, current_bars)

                # 记录每日统计
                date_str = current_time.strftime('%Y-%m-%d') if hasattr(current_time, 'strftime') else str(current_time)[:10]
                self.li_bu.record_daily_value(
                    date=date_str,
                    total_value=portfolio.get('total_value', initial_capital),
                    cash=portfolio.get('cash', initial_capital),
                    positions_value=portfolio.get('total_value', initial_capital) - portfolio.get('cash', 0)
                )

            # 5. 生成回测报告
            results = self._generate_report(task_id, run_params, trade_records, portfolio)

            task['results'] = results
            task['status'] = 'completed'
            task['completed_at'] = datetime.now().isoformat()
            task['progress'] = 100

            logger.info(f"回测任务完成: {task_id}, 总收益: {results['summary'].get('total_return_pct', 'N/A')}")

        except Exception as e:
            logger.error(f"回测失败: {e}")
            task['status'] = 'failed'
            task['error'] = str(e)
            raise

    async def get_task_status(self, task_id: str) -> dict:
        """获取任务状态"""
        return self.tasks.get(task_id, {})

    async def get_task_results(self, task_id: str) -> Optional[dict]:
        """获取任务结果"""
        task = self.tasks.get(task_id)
        if task:
            return task.get('results')
        return None

    async def list_tasks(self, status: Optional[str] = None) -> List[dict]:
        """列出所有任务"""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t['status'] == status]
        return tasks

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.tasks:
            self.tasks[task_id]['status'] = 'cancelled'
            return True
        return False

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

    async def _load_historical_data(
        self,
        symbols: List[str],
        start: str,
        end: str
    ) -> Dict[str, pd.DataFrame]:
        """加载历史数据"""
        data = {}
        for symbol in symbols:
            try:
                df = await self.data_provider.fetch_data(symbol, start, end)
                if df is not None and not df.empty:
                    data[symbol] = df
                    logger.debug(f"加载数据: {symbol}, {len(df)} 条记录")
                else:
                    logger.warning(f"无数据: {symbol}")
            except Exception as e:
                logger.error(f"加载数据失败 {symbol}: {e}")
        return data

    def _init_portfolio(self, capital: float) -> dict:
        """初始化账户"""
        return {
            'cash': capital,
            'total_value': capital,
            'positions': {},
            'daily_pnl': 0,
            'total_pnl': 0
        }

    def _get_all_trading_dates(self, data: Dict[str, pd.DataFrame]) -> list:
        """获取所有交易日期"""
        all_dates = set()
        for df in data.values():
            if 'datetime' in df.columns:
                all_dates.update(df['datetime'].tolist())
            elif isinstance(df.index, pd.DatetimeIndex):
                all_dates.update(df.index.tolist())
        return sorted(list(all_dates))

    def _get_bars_at_time(
        self,
        data: Dict[str, pd.DataFrame],
        time
    ) -> Dict[str, pd.DataFrame]:
        """获取指定时间的所有股票数据"""
        bars = {}
        for code, df in data.items():
            if 'datetime' in df.columns:
                mask = df['datetime'] == time
                if mask.any():
                    bars[code] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                if time in df.index:
                    bars[code] = df.loc[[time]]
        return bars

    def _update_portfolio_value(self, portfolio: dict, market_data: Dict):
        """更新投资组合市值"""
        positions_value = 0
        for code, position in portfolio.get('positions', {}).items():
            if code in market_data:
                current_price = market_data[code]['close'].iloc[-1] if not market_data[code].empty else position.get('cost', 0)
                positions_value += position.get('qty', 0) * current_price

        portfolio['total_value'] = portfolio.get('cash', 0) + positions_value

    def _generate_report(
        self,
        task_id: str,
        params: dict,
        trades: list,
        final_portfolio: dict
    ) -> dict:
        """生成回测报告"""
        initial_capital = params.get('initial_capital', 1000000.0)
        final_value = final_portfolio.get('total_value', initial_capital)
        total_return = (final_value - initial_capital) / initial_capital if initial_capital > 0 else 0

        # 生成详细报告
        report = self.li_bu.generate_report()

        return {
            'task_id': task_id,
            'summary': {
                'initial_capital': initial_capital,
                'final_value': final_value,
                'total_return': total_return,
                'total_return_pct': f"{total_return:.2%}",
                'total_trades': len(trades),
                'start_date': params.get('start_date'),
                'end_date': params.get('end_date'),
            },
            'performance': report,
            'trades': trades[-100:] if len(trades) > 100 else trades,  # 只保留最近100笔交易详情
            'params': params,
            'generated_at': datetime.now().isoformat()
        }

    def _calc_win_rate(self, trades: list) -> float:
        """计算胜率"""
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        return wins / len(trades)

    def _calc_max_drawdown(self, daily_stats: list) -> float:
        """计算最大回撤"""
        if not daily_stats:
            return 0.0
        peak = daily_stats[0].get('total_value', 0)
        max_dd = 0
        for stat in daily_stats:
            value = stat.get('total_value', 0)
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd
