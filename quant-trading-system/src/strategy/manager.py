"""
策略管理器

负责：
- 策略的注册、加载、卸载
- 策略生命周期管理（启动、停止、暂停、恢复）
- 数据分发到各个策略
- 策略状态监控
"""
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type
import importlib
import inspect

from src.common.logger import TradingLogger
from src.strategy.base import StrategyBase, StrategyContext, BarData, TickData
from src.strategy.base import AccountInfo, Position

logger = TradingLogger(__name__)


class StrategyManager:
    """
    策略管理器

    单例模式，管理所有策略实例
    """

    _instance: Optional["StrategyManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._initialized = True
        self._strategies: Dict[str, StrategyBase] = {}  # strategy_id -> Strategy
        self._contexts: Dict[str, StrategyContext] = {}  # strategy_id -> Context
        self._strategy_classes: Dict[str, Type[StrategyBase]] = {}  # name -> Class

        # 运行状态
        self._running = False
        self._data_queue: asyncio.Queue = asyncio.Queue()
        self._data_task: Optional[asyncio.Task] = None

        logger.info("策略管理器初始化完成")

    # ============ 策略注册 ============

    def register_strategy_class(
        self,
        name: str,
        strategy_class: Type[StrategyBase]
    ) -> None:
        """
        注册策略类

        Args:
            name: 策略类名称
            strategy_class: 策略类（继承自 StrategyBase）
        """
        if not issubclass(strategy_class, StrategyBase):
            raise ValueError(f"策略类必须继承自 StrategyBase: {strategy_class}")

        self._strategy_classes[name] = strategy_class
        logger.info(f"策略类注册: {name}")

    def load_strategy_from_module(
        self,
        module_path: str,
        class_name: str
    ) -> Type[StrategyBase]:
        """
        从模块加载策略类

        Args:
            module_path: 模块路径，如 "src.strategy.examples.ma_cross"
            class_name: 类名

        Returns:
            策略类
        """
        try:
            module = importlib.import_module(module_path)
            strategy_class = getattr(module, class_name)

            if not issubclass(strategy_class, StrategyBase):
                raise ValueError(f"类 {class_name} 不是 StrategyBase 的子类")

            self.register_strategy_class(class_name, strategy_class)
            return strategy_class

        except Exception as e:
            logger.error(f"加载策略类失败 {module_path}.{class_name}: {e}")
            raise

    def create_strategy(
        self,
        strategy_class_name: str,
        strategy_id: str,
        name: str,
        symbols: List[str],
        params: Optional[Dict[str, Any]] = None,
        initial_capital: Decimal = Decimal("100000")
    ) -> StrategyBase:
        """
        创建策略实例

        Args:
            strategy_class_name: 已注册的策略类名
            strategy_id: 策略唯一ID
            name: 策略名称
            symbols: 交易标的列表
            params: 策略参数
            initial_capital: 初始资金

        Returns:
            策略实例
        """
        if strategy_id in self._strategies:
            raise ValueError(f"策略ID已存在: {strategy_id}")

        strategy_class = self._strategy_classes.get(strategy_class_name)
        if not strategy_class:
            raise ValueError(f"未找到策略类: {strategy_class_name}")

        # 创建策略实例
        strategy = strategy_class(
            strategy_id=strategy_id,
            name=name,
            symbols=symbols,
            params=params
        )

        # 创建策略上下文
        context = StrategyContext(
            strategy_id=strategy_id,
            initial_capital=initial_capital
        )

        # 注册订单回调
        context.on_order_callback(
            lambda order: self._on_strategy_order(strategy_id, order)
        )

        # 初始化策略
        strategy.initialize(context)

        # 保存
        self._strategies[strategy_id] = strategy
        self._contexts[strategy_id] = context

        logger.info(f"策略创建成功: {strategy_id} ({name})")
        return strategy

    def remove_strategy(self, strategy_id: str) -> None:
        """移除策略"""
        if strategy_id not in self._strategies:
            logger.warning(f"策略不存在: {strategy_id}")
            return

        strategy = self._strategies[strategy_id]

        # 停止策略
        if strategy.state.value in ["running", "paused"]:
            strategy.stop()

        # 移除
        del self._strategies[strategy_id]
        del self._contexts[strategy_id]

        logger.info(f"策略移除: {strategy_id}")

    # ============ 生命周期控制 ============

    def start_strategy(self, strategy_id: str) -> None:
        """启动策略"""
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            raise ValueError(f"策略不存在: {strategy_id}")

        strategy.start()

    def stop_strategy(self, strategy_id: str) -> None:
        """停止策略"""
        strategy = self._strategies.get(strategy_id)
        if strategy:
            strategy.stop()

    def pause_strategy(self, strategy_id: str) -> None:
        """暂停策略"""
        strategy = self._strategies.get(strategy_id)
        if strategy:
            strategy.pause()

    def resume_strategy(self, strategy_id: str) -> None:
        """恢复策略"""
        strategy = self._strategies.get(strategy_id)
        if strategy:
            strategy.resume()

    def start_all(self) -> None:
        """启动所有策略"""
        for strategy_id, strategy in self._strategies.items():
            if strategy.state.value == "ready":
                strategy.start()

    def stop_all(self) -> None:
        """停止所有策略"""
        for strategy_id, strategy in self._strategies.items():
            strategy.stop()

    # ============ 数据分发 ============

    async def start_data_distribution(self) -> None:
        """启动数据分发任务"""
        if self._running:
            return

        self._running = True
        self._data_task = asyncio.create_task(self._data_distribution_loop())
        logger.info("数据分发已启动")

    async def stop_data_distribution(self) -> None:
        """停止数据分发"""
        self._running = False

        if self._data_task:
            self._data_task.cancel()
            try:
                await self._data_task
            except asyncio.CancelledError:
                pass

        logger.info("数据分发已停止")

    async def _data_distribution_loop(self) -> None:
        """数据分发循环"""
        while self._running:
            try:
                data = await asyncio.wait_for(
                    self._data_queue.get(),
                    timeout=1.0
                )

                if isinstance(data, BarData):
                    await self._distribute_bar(data)
                elif isinstance(data, TickData):
                    await self._distribute_tick(data)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"数据分发错误: {e}")

    async def _distribute_bar(self, bar: BarData) -> None:
        """分发K线数据到订阅的策略"""
        for strategy_id, strategy in self._strategies.items():
            if strategy.state.value != "running":
                continue

            if bar.symbol not in strategy.symbols:
                continue

            try:
                # 更新上下文数据
                context = self._contexts[strategy_id]
                context._update_bar(bar)

                # 调用策略 on_bar
                strategy.on_bar(bar)
                strategy._bar_count += 1

            except Exception as e:
                logger.error(f"策略 {strategy_id} on_bar 错误: {e}")

    async def _distribute_tick(self, tick: TickData) -> None:
        """分发Tick数据到订阅的策略"""
        for strategy_id, strategy in self._strategies.items():
            if strategy.state.value != "running":
                continue

            if tick.symbol not in strategy.symbols:
                continue

            try:
                # 更新上下文数据
                context = self._contexts[strategy_id]
                context._update_tick(tick)

                # 调用策略 on_tick
                strategy.on_tick(tick)
                strategy._tick_count += 1

            except Exception as e:
                logger.error(f"策略 {strategy_id} on_tick 错误: {e}")

    def publish_bar(self, bar: BarData) -> None:
        """发布K线数据"""
        try:
            self._data_queue.put_nowait(bar)
        except asyncio.QueueFull:
            logger.warning("数据队列已满，丢弃数据")

    def publish_tick(self, tick: TickData) -> None:
        """发布Tick数据"""
        try:
            self._data_queue.put_nowait(tick)
        except asyncio.QueueFull:
            logger.warning("数据队列已满，丢弃数据")

    # ============ 账户/持仓更新 ============

    def update_account(self, strategy_id: str, account: AccountInfo) -> None:
        """更新策略账户信息"""
        context = self._contexts.get(strategy_id)
        if context:
            context._update_account(account)

            # 通知策略持仓更新
            strategy = self._strategies.get(strategy_id)
            if strategy:
                for symbol, position in account.positions.items():
                    strategy.on_position_update(position)

    # ============ 事件回调 ============

    def _on_strategy_order(self, strategy_id: str, order: Dict[str, Any]) -> None:
        """策略订单回调"""
        strategy = self._strategies.get(strategy_id)
        if strategy:
            strategy.on_order_update(order)

    # ============ 查询接口 ============

    def get_strategy(self, strategy_id: str) -> Optional[StrategyBase]:
        """获取策略实例"""
        return self._strategies.get(strategy_id)

    def get_context(self, strategy_id: str) -> Optional[StrategyContext]:
        """获取策略上下文"""
        return self._contexts.get(strategy_id)

    def list_strategies(self) -> List[str]:
        """列出所有策略ID"""
        return list(self._strategies.keys())

    def get_strategy_stats(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取策略统计"""
        strategy = self._strategies.get(strategy_id)
        return strategy.stats if strategy else None

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有策略统计"""
        return {
            sid: strategy.stats
            for sid, strategy in self._strategies.items()
        }

    # ============ 状态监控 ============

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    @property
    def strategy_count(self) -> int:
        """策略数量"""
        return len(self._strategies)

    @property
    def running_strategy_count(self) -> int:
        """运行中策略数量"""
        return sum(
            1 for s in self._strategies.values()
            if s.state.value == "running"
        )


# 全局策略管理器实例
strategy_manager = StrategyManager()
