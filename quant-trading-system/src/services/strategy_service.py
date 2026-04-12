"""
策略服务

提供策略相关的业务操作：
- 策略创建、查询、更新、删除
- 策略版本管理
- 策略状态控制
- 策略统计
- 策略回测关联
"""
import uuid
import types
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.strategy import Strategy
from src.models.strategy_backtest import StrategyBacktest
from src.models.enums import StrategyStatus, RunMode
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class StrategyService:
    """
    策略服务

    处理策略相关的业务逻辑
    """

    def __init__(self, session: AsyncSession):
        """
        初始化策略服务

        Args:
            session: 数据库会话
        """
        self.session = session

    async def create_strategy(
        self,
        account_id: int,
        name: str,
        description: str = "",
        category: str = None,
        style: str = None,
        params: Dict[str, Any] = None,
        max_position: float = 0.10,
        stop_loss: float = 0.02,
        take_profit: float = 0.05,
        run_mode: RunMode = RunMode.SIMULATE
    ) -> Strategy:
        """
        创建策略

        Args:
            account_id: 账户ID
            name: 策略名称
            description: 策略描述
            category: 策略分类
            style: 策略风格
            params: 策略参数
            max_position: 最大持仓比例
            stop_loss: 止损比例
            take_profit: 止盈比例
            run_mode: 运行模式

        Returns:
            Strategy: 创建的策略
        """
        strategy_id = f"stg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        strategy = Strategy(
            strategy_id=strategy_id,
            name=name,
            description=description,
            account_id=account_id,
            category=category,
            style=style,
            params=params or {},
            max_position=Decimal(str(max_position)),
            stop_loss=Decimal(str(stop_loss)),
            take_profit=Decimal(str(take_profit)),
            run_mode=run_mode,
            status=StrategyStatus.INACTIVE
        )

        self.session.add(strategy)
        await self.session.commit()
        await self.session.refresh(strategy)

        logger.info(f"创建策略: {strategy_id}, 名称: {name}, 账户: {account_id}")
        return strategy

    async def get_strategy(
        self,
        strategy_id: str,
        account_id: int = None
    ) -> Optional[Strategy]:
        """
        获取策略

        Args:
            strategy_id: 策略ID
            account_id: 账户ID（可选，用于权限校验）

        Returns:
            Strategy: 策略，不存在返回None
        """
        query = select(Strategy).where(Strategy.strategy_id == strategy_id)

        if account_id is not None:
            query = query.where(Strategy.account_id == account_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_strategy_by_db_id(
        self,
        db_id: int,
        account_id: int = None
    ) -> Optional[Strategy]:
        """
        通过数据库ID获取策略

        Args:
            db_id: 数据库主键ID
            account_id: 账户ID（可选，用于权限校验）

        Returns:
            Strategy: 策略，不存在返回None
        """
        query = select(Strategy).where(Strategy.id == db_id)

        if account_id is not None:
            query = query.where(Strategy.account_id == account_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_strategies(
        self,
        account_id: int,
        status: StrategyStatus = None,
        category: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Strategy]:
        """
        获取策略列表

        Args:
            account_id: 账户ID
            status: 状态过滤
            category: 分类过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[Strategy]: 策略列表
        """
        query = select(Strategy).where(Strategy.account_id == account_id)

        if status:
            query = query.where(Strategy.status == status)
        if category:
            query = query.where(Strategy.category == category)

        query = query.order_by(desc(Strategy.updated_at)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_strategy(
        self,
        strategy_id: str,
        account_id: int,
        updates: Dict[str, Any]
    ) -> Optional[Strategy]:
        """
        更新策略

        Args:
            strategy_id: 策略ID
            account_id: 账户ID
            updates: 更新字段

        Returns:
            Strategy: 更新后的策略，不存在返回None
        """
        strategy = await self.get_strategy(strategy_id, account_id)
        if not strategy:
            return None

        # 更新允许修改的字段
        allowed_fields = ["name", "description", "category", "style"]
        for field in allowed_fields:
            if field in updates:
                setattr(strategy, field, updates[field])

        # 更新参数（合并而非替换）
        if "params" in updates and updates["params"]:
            strategy.params.update(updates["params"])

        # 更新风控参数
        if "max_position" in updates:
            strategy.max_position = Decimal(str(updates["max_position"]))
        if "stop_loss" in updates:
            strategy.stop_loss = Decimal(str(updates["stop_loss"]))
        if "take_profit" in updates:
            strategy.take_profit = Decimal(str(updates["take_profit"]))

        await self.session.commit()
        await self.session.refresh(strategy)

        logger.info(f"更新策略: {strategy_id}")
        return strategy

    async def delete_strategy(
        self,
        strategy_id: str,
        account_id: int
    ) -> bool:
        """
        删除策略

        Args:
            strategy_id: 策略ID
            account_id: 账户ID

        Returns:
            bool: 是否成功删除
        """
        strategy = await self.get_strategy(strategy_id, account_id)
        if not strategy:
            return False

        # 检查策略状态，运行中的策略不能删除
        if strategy.status == StrategyStatus.ACTIVE:
            logger.warning(f"无法删除运行中的策略: {strategy_id}")
            return False

        await self.session.delete(strategy)
        await self.session.commit()

        logger.info(f"删除策略: {strategy_id}")
        return True

    async def update_status(
        self,
        strategy_id: str,
        account_id: int,
        status: StrategyStatus
    ) -> Optional[Strategy]:
        """
        更新策略状态

        Args:
            strategy_id: 策略ID
            account_id: 账户ID
            status: 新状态

        Returns:
            Strategy: 更新后的策略，不存在返回None
        """
        strategy = await self.get_strategy(strategy_id, account_id)
        if not strategy:
            return None

        strategy.status = status

        if status == StrategyStatus.ACTIVE:
            strategy.activated_at = datetime.now()

        await self.session.commit()
        await self.session.refresh(strategy)

        logger.info(f"策略状态更新: {strategy_id} -> {status.value}")
        return strategy

    async def start_strategy(
        self,
        strategy_id: str,
        account_id: int
    ) -> Optional[Strategy]:
        """
        启动策略

        Args:
            strategy_id: 策略ID
            account_id: 账户ID

        Returns:
            Strategy: 更新后的策略，不存在返回None
        """
        return await self.update_status(
            strategy_id,
            account_id,
            StrategyStatus.ACTIVE
        )

    async def stop_strategy(
        self,
        strategy_id: str,
        account_id: int
    ) -> Optional[Strategy]:
        """
        停止策略

        Args:
            strategy_id: 策略ID
            account_id: 账户ID

        Returns:
            Strategy: 更新后的策略，不存在返回None
        """
        return await self.update_status(
            strategy_id,
            account_id,
            StrategyStatus.INACTIVE
        )

    async def pause_strategy(
        self,
        strategy_id: str,
        account_id: int
    ) -> Optional[Strategy]:
        """
        暂停策略

        Args:
            strategy_id: 策略ID
            account_id: 账户ID

        Returns:
            Strategy: 更新后的策略，不存在返回None
        """
        return await self.update_status(
            strategy_id,
            account_id,
            StrategyStatus.PAUSED
        )

    async def update_stats(
        self,
        strategy_id: str,
        total_return: float = None,
        sharpe_ratio: float = None,
        max_drawdown: float = None,
        total_trades: int = None,
        win_trades: int = None,
        loss_trades: int = None
    ) -> Optional[Strategy]:
        """
        更新策略统计信息

        Args:
            strategy_id: 策略ID
            total_return: 总收益
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            total_trades: 总交易次数
            win_trades: 盈利交易次数
            loss_trades: 亏损交易次数

        Returns:
            Strategy: 更新后的策略，不存在返回None
        """
        strategy = await self.get_strategy(strategy_id)
        if not strategy:
            return None

        if total_return is not None:
            strategy.total_return = Decimal(str(total_return))
        if sharpe_ratio is not None:
            strategy.sharpe_ratio = Decimal(str(sharpe_ratio))
        if max_drawdown is not None:
            strategy.max_drawdown = Decimal(str(max_drawdown))
        if total_trades is not None:
            strategy.total_trades = total_trades
        if win_trades is not None:
            strategy.win_trades = win_trades
        if loss_trades is not None:
            strategy.loss_trades = loss_trades

        await self.session.commit()
        await self.session.refresh(strategy)

        logger.info(f"更新策略统计: {strategy_id}")
        return strategy

    async def run_backtest(
        self,
        strategy_id: str,
        backtest_config: dict,
        account_id: int = None
    ) -> str:
        """
        为策略执行回测

        Args:
            strategy_id: 策略ID
            backtest_config: 回测配置
            account_id: 账户ID（可选）

        Returns:
            backtest_task_id: 回测任务ID
        """
        from src.backtest.engine import BacktestEngine, BacktestConfig
        from src.services.backtest_service import BacktestService

        # 获取策略
        strategy = await self.get_strategy(strategy_id, account_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        # 创建回测任务
        backtest_service = BacktestService(self.session)
        task_id = f"bt_{uuid.uuid4().hex[:16]}"

        # 使用策略默认参数
        params = backtest_config.get("parameters") or strategy.default_parameters

        # 创建回测任务
        await backtest_service.create_task(
            task_id=task_id,
            account_id=strategy.account_id,
            symbols=backtest_config.get("symbols", strategy.symbols),
            start_date=backtest_config["start_date"],
            end_date=backtest_config["end_date"],
            strategy_id=strategy_id,
            initial_capital=backtest_config.get("initial_capital", 100000),
            strategy_params=params
        )

        # 创建策略回测关联记录
        strategy_backtest = StrategyBacktest(
            strategy_id=strategy.id,
            backtest_task_id=task_id,
            parameters_used=params
        )
        self.session.add(strategy_backtest)
        await self.session.commit()

        # 启动后台回测
        asyncio.create_task(
            self._execute_backtest(strategy, task_id, backtest_config)
        )

        return task_id

    async def _execute_backtest(
        self,
        strategy: Strategy,
        task_id: str,
        config: dict
    ):
        """后台执行回测"""
        from src.backtest.engine import BacktestEngine, BacktestConfig
        from src.services.backtest_service import BacktestService
        from src.backtest.metrics import BacktestResult

        try:
            # 更新任务状态为运行中
            backtest_service = BacktestService(self.session)
            await backtest_service.update_status(task_id, "running", 10)

            # 加载策略代码
            strategy_class = self._load_strategy_class(strategy.code)
            strategy_instance = strategy_class(
                strategy_id=strategy.strategy_id,
                name=strategy.name,
                symbols=config.get("symbols", strategy.symbols)
            )

            # 设置参数
            if config.get("parameters"):
                strategy_instance.params = config["parameters"]

            # 配置回测
            backtest_config = BacktestConfig(
                start_date=datetime.strptime(config["start_date"], "%Y-%m-%d"),
                end_date=datetime.strptime(config["end_date"], "%Y-%m-%d"),
                initial_capital=Decimal(str(config.get("initial_capital", 100000)))
            )

            # 执行回测
            engine = BacktestEngine()
            result = await engine.run(strategy_instance, backtest_config)

            # 保存结果
            await backtest_service.save_results(task_id, result.metrics.to_dict())
            await backtest_service.update_status(task_id, "completed", 100)

            # 更新策略回测关联记录
            await self._update_backtest_results(strategy.id, task_id, result)

            # 更新策略统计信息
            await self.update_stats(
                strategy.strategy_id,
                total_return=float(result.metrics.total_return),
                sharpe_ratio=float(result.metrics.sharpe_ratio),
                max_drawdown=float(result.metrics.max_drawdown),
                total_trades=result.metrics.total_trades,
                win_trades=result.metrics.winning_trades
            )

            logger.info(f"回测完成: {task_id}")

        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            backtest_service = BacktestService(self.session)
            await backtest_service.save_error(task_id, str(e))
            await backtest_service.update_status(task_id, "failed", 0)

    async def _update_backtest_results(
        self,
        strategy_id: int,
        task_id: str,
        result
    ):
        """更新策略回测关联记录的结果"""
        stmt = select(StrategyBacktest).where(
            StrategyBacktest.strategy_id == strategy_id,
            StrategyBacktest.backtest_task_id == task_id
        )
        result_db = await self.session.execute(stmt)
        record = result_db.scalar_one_or_none()

        if record:
            record.total_return = Decimal(str(result.metrics.total_return))
            record.sharpe_ratio = Decimal(str(result.metrics.sharpe_ratio))
            record.max_drawdown = Decimal(str(result.metrics.max_drawdown))
            record.win_rate = Decimal(str(result.metrics.win_rate))
            record.total_trades = result.metrics.total_trades
            await self.session.commit()

    def _load_strategy_class(self, code: str):
        """从代码字符串加载策略类"""
        # 简化实现：动态执行代码
        # 实际生产环境应该使用沙箱
        module = types.ModuleType("dynamic_strategy")
        exec(code, module.__dict__)

        # 查找策略类
        for name, obj in module.__dict__.items():
            if isinstance(obj, type) and hasattr(obj, 'on_bar'):
                return obj

        raise ValueError("No strategy class found in code")

    async def get_strategy_summary(
        self,
        strategy_id: str,
        account_id: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取策略摘要

        Args:
            strategy_id: 策略ID
            account_id: 账户ID（可选）

        Returns:
            dict: 策略摘要
        """
        strategy = await self.get_strategy(strategy_id, account_id)
        if not strategy:
            return None

        return {
            "strategy_id": strategy.strategy_id,
            "name": strategy.name,
            "description": strategy.description,
            "category": strategy.category,
            "style": strategy.style,
            "status": strategy.status.value,
            "run_mode": strategy.run_mode.value,
            "total_trades": strategy.total_trades,
            "win_rate": float(strategy.win_rate),
            "total_return": float(strategy.total_return),
            "sharpe_ratio": float(strategy.sharpe_ratio),
            "max_drawdown": float(strategy.max_drawdown),
            "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
            "activated_at": strategy.activated_at.isoformat() if strategy.activated_at else None,
        }
