"""
中书省 - 策略信号生成中心

职责：
- 加载和管理策略实例
- 接收市场数据，驱动策略计算
- 生成交易信号
- 信号去重和缓存
- 将信号传递给门下省（风控）审核

数据流向：
太子院(校验后数据) → 中书省(信号生成) → 门下省(风控审核)
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set, Any, Callable, Type
import asyncio

from src.strategy.base import StrategyBase, StrategyContext, Signal, SignalType
from src.market_data.models import TickData, KLineData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class SignalStatus(Enum):
    """信号状态"""
    PENDING = "pending"      # 待审核
    APPROVED = "approved"    # 审核通过
    REJECTED = "rejected"    # 审核拒绝
    EXECUTED = "executed"    # 已执行
    EXPIRED = "expired"      # 已过期


@dataclass
class SignalEvent:
    """信号事件（包装Signal，添加元数据）"""
    signal: Signal
    strategy_id: str
    status: SignalStatus = SignalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    audit_result: Optional[Dict] = None
    order_id: Optional[str] = None

    def __post_init__(self):
        if self.expires_at is None:
            # 默认5分钟后过期
            self.expires_at = self.created_at + timedelta(minutes=5)

    @property
    def is_expired(self) -> bool:
        """检查信号是否过期"""
        return datetime.now() > self.expires_at

    @property
    def signal_id(self) -> str:
        """生成唯一信号ID（基于信号内容而非时间戳，用于去重）"""
        # 使用信号的关键属性生成ID，相同symbol/type/price的信号被认为是重复
        price_str = str(self.signal.price) if self.signal.price else "0"
        content = f"{self.strategy_id}:{self.signal.symbol}:{self.signal.type.value}:{price_str}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class StrategyLoader:
    """策略加载器"""

    def __init__(self):
        self._strategies: Dict[str, Type[StrategyBase]] = {}
        self._instances: Dict[str, StrategyBase] = {}

    def register_strategy_class(
        self,
        strategy_id: str,
        strategy_class: Type[StrategyBase]
    ):
        """注册策略类"""
        self._strategies[strategy_id] = strategy_class
        logger.info(f"注册策略类: {strategy_id} -> {strategy_class.__name__}")

    def create_instance(
        self,
        strategy_id: str,
        name: str,
        symbols: List[str],
        params: Optional[Dict] = None,
        context: Optional[StrategyContext] = None
    ) -> Optional[StrategyBase]:
        """创建策略实例"""
        strategy_class = self._strategies.get(strategy_id)
        if not strategy_class:
            logger.error(f"策略类未注册: {strategy_id}")
            return None

        try:
            instance = strategy_class(
                strategy_id=strategy_id,
                name=name,
                symbols=symbols,
                params=params or {},
                context=context
            )
            self._instances[strategy_id] = instance
            logger.info(f"创建策略实例: {strategy_id}")
            return instance
        except Exception as e:
            logger.error(f"创建策略实例失败: {e}")
            return None

    def get_instance(self, strategy_id: str) -> Optional[StrategyBase]:
        """获取策略实例"""
        return self._instances.get(strategy_id)

    def remove_instance(self, strategy_id: str):
        """移除策略实例"""
        if strategy_id in self._instances:
            instance = self._instances[strategy_id]
            instance.stop()
            del self._instances[strategy_id]
            logger.info(f"移除策略实例: {strategy_id}")

    def list_registered(self) -> List[str]:
        """列出所有已注册的策略类"""
        return list(self._strategies.keys())

    def list_active(self) -> List[str]:
        """列出所有活跃的策略实例"""
        return list(self._instances.keys())


class SignalCache:
    """信号缓存与去重"""

    def __init__(self, ttl_seconds: int = 60):
        self._cache: Dict[str, SignalEvent] = {}
        self._ttl = ttl_seconds
        self._stats = {
            "total": 0,
            "duplicates": 0,
            "expired": 0,
        }

    def add(self, event: SignalEvent) -> bool:
        """
        添加信号到缓存

        Returns:
            True: 新信号
            False: 重复信号
        """
        signal_id = event.signal_id

        # 检查是否已存在
        if signal_id in self._cache:
            self._stats["duplicates"] += 1
            logger.debug(f"信号重复: {signal_id}")
            return False

        self._cache[signal_id] = event
        self._stats["total"] += 1
        logger.debug(f"信号缓存: {signal_id}")
        return True

    def get(self, signal_id: str) -> Optional[SignalEvent]:
        """获取信号"""
        return self._cache.get(signal_id)

    def update_status(self, signal_id: str, status: SignalStatus):
        """更新信号状态"""
        if signal_id in self._cache:
            self._cache[signal_id].status = status

    def clean_expired(self):
        """清理过期信号"""
        expired_ids = [
            sid for sid, event in self._cache.items()
            if event.is_expired
        ]
        for sid in expired_ids:
            del self._cache[sid]
            self._stats["expired"] += 1

        if expired_ids:
            logger.debug(f"清理过期信号: {len(expired_ids)}个")

    def get_stats(self) -> Dict[str, int]:
        """获取统计"""
        return self._stats.copy()

    def clear(self):
        """清空缓存"""
        self._cache.clear()


class SignalGenerator:
    """信号生成引擎"""

    def __init__(self):
        self._handlers: List[Callable[[SignalEvent], None]] = []

    def add_handler(self, handler: Callable[[SignalEvent], None]):
        """添加信号处理器（如下送到门下省）"""
        self._handlers.append(handler)
        logger.info(f"注册信号处理器: {handler.__name__}")

    def remove_handler(self, handler: Callable[[SignalEvent], None]):
        """移除信号处理器"""
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def generate_from_strategy(
        self,
        strategy: StrategyBase,
        data: Any,  # TickData or KLineData
        data_type: str = "tick"
    ) -> Optional[Signal]:
        """
        从策略生成信号

        Args:
            strategy: 策略实例
            data: 市场数据
            data_type: "tick" or "kline"

        Returns:
            Signal or None
        """
        if not strategy.is_running:
            return None

        try:
            if data_type == "tick":
                signal = await strategy.on_tick_async(data)
            else:
                signal = await strategy.on_bar_async(data)

            return signal

        except Exception as e:
            logger.error(f"策略信号生成失败 [{strategy.strategy_id}]: {e}")
            return None

    async def dispatch(self, event: SignalEvent):
        """分发信号到所有处理器"""
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"信号分发失败 [{handler.__name__}]: {e}")


class ZhongshuSheng:
    """
    中书省 - 策略信号生成中心（单例）
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # 策略加载器
        self.strategy_loader = StrategyLoader()

        # 信号缓存
        self.signal_cache = SignalCache(ttl_seconds=60)

        # 信号生成引擎
        self.signal_generator = SignalGenerator()

        # 活跃策略列表（账户 -> 策略列表）
        self._account_strategies: Dict[int, Set[str]] = {}

        # 数据缓存（用于驱动策略）
        self._latest_data: Dict[str, Any] = {}

        # 统计
        self._stats = {
            "signals_generated": 0,
            "signals_deduplicated": 0,
            "strategies_active": 0,
        }

        logger.info("中书省初始化完成")

    def register_strategy_class(
        self,
        strategy_id: str,
        strategy_class: Type[StrategyBase]
    ):
        """注册策略类"""
        self.strategy_loader.register_strategy_class(strategy_id, strategy_class)

    def activate_strategy(
        self,
        account_id: int,
        strategy_id: str,
        name: str,
        symbols: List[str],
        params: Optional[Dict] = None
    ) -> bool:
        """
        激活策略（为账户启动策略实例）
        """
        # 创建策略上下文
        context = StrategyContext(strategy_id=strategy_id)

        # 创建策略实例
        instance = self.strategy_loader.create_instance(
            strategy_id=strategy_id,
            name=name,
            symbols=symbols,
            params=params,
            context=context
        )

        if not instance:
            return False

        # 启动策略
        instance.start()

        # 记录账户-策略关系
        if account_id not in self._account_strategies:
            self._account_strategies[account_id] = set()
        self._account_strategies[account_id].add(strategy_id)

        self._stats["strategies_active"] += 1
        logger.info(f"策略激活: {strategy_id} for account {account_id}")
        return True

    def deactivate_strategy(self, account_id: int, strategy_id: str):
        """停用策略"""
        # 停止策略实例
        instance = self.strategy_loader.get_instance(strategy_id)
        if instance:
            instance.stop()

        self.strategy_loader.remove_instance(strategy_id)

        # 移除账户-策略关系
        if account_id in self._account_strategies:
            self._account_strategies[account_id].discard(strategy_id)

        self._stats["strategies_active"] = max(0, self._stats["strategies_active"] - 1)
        logger.info(f"策略停用: {strategy_id} for account {account_id}")

    def on_tick(self, tick: TickData):
        """
        处理Tick数据（驱动策略计算）
        """
        # 缓存最新数据
        self._latest_data[tick.symbol] = tick

        # 驱动每个活跃策略
        for strategy_id in self.strategy_loader.list_active():
            strategy = self.strategy_loader.get_instance(strategy_id)
            if strategy and tick.symbol in strategy.symbols:
                asyncio.create_task(self._process_tick_strategy(strategy, tick))

    def on_kline(self, kline: KLineData):
        """
        处理K线数据（驱动策略计算）
        """
        # 缓存最新数据
        self._latest_data[f"{kline.symbol}_{kline.period}"] = kline

        # 驱动每个活跃策略
        for strategy_id in self.strategy_loader.list_active():
            strategy = self.strategy_loader.get_instance(strategy_id)
            if strategy and kline.symbol in strategy.symbols:
                asyncio.create_task(self._process_kline_strategy(strategy, kline))

    async def _process_tick_strategy(self, strategy: StrategyBase, tick: TickData):
        """处理策略的tick计算"""
        signal = await self.signal_generator.generate_from_strategy(
            strategy, tick, "tick"
        )

        if signal:
            await self._handle_signal(strategy, signal)

    async def _process_kline_strategy(self, strategy: StrategyBase, kline: KLineData):
        """处理策略的kline计算"""
        signal = await self.signal_generator.generate_from_strategy(
            strategy, kline, "kline"
        )

        if signal:
            await self._handle_signal(strategy, signal)

    async def _handle_signal(self, strategy: StrategyBase, signal: Signal):
        """处理生成的信号"""
        # 创建信号事件
        event = SignalEvent(
            signal=signal,
            strategy_id=strategy.strategy_id
        )

        # 信号去重
        is_new = self.signal_cache.add(event)
        if not is_new:
            self._stats["signals_deduplicated"] += 1
            return

        self._stats["signals_generated"] += 1
        logger.info(f"生成信号: {event.signal_id} [{signal.type.value}] {signal.symbol}")

        # 分发信号（到门下省风控）
        await self.signal_generator.dispatch(event)

    def add_signal_handler(self, handler: Callable[[SignalEvent], None]):
        """添加信号处理器（如门下省风控）"""
        self.signal_generator.add_handler(handler)

    def remove_signal_handler(self, handler: Callable[[SignalEvent], None]):
        """移除信号处理器"""
        self.signal_generator.remove_handler(handler)

    def get_account_strategies(self, account_id: int) -> List[str]:
        """获取账户的所有活跃策略"""
        return list(self._account_strategies.get(account_id, set()))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "signal_cache": self.signal_cache.get_stats(),
            "registered_strategies": self.strategy_loader.list_registered(),
            "active_strategies": self.strategy_loader.list_active(),
        }

    def clean_expired_signals(self):
        """清理过期信号"""
        self.signal_cache.clean_expired()

    async def generate_signals(
        self,
        data: Any,
        strategy_filter: Optional[List[str]] = None
    ) -> List[SignalEvent]:
        """
        批量生成信号（兼容旧API）
        """
        events = []

        strategies = self.strategy_loader.list_active()
        if strategy_filter:
            strategies = [s for s in strategies if s in strategy_filter]

        for strategy_id in strategies:
            strategy = self.strategy_loader.get_instance(strategy_id)
            if not strategy:
                continue

            signal = await self.signal_generator.generate_from_strategy(
                strategy, data, "kline"
            )

            if signal:
                event = SignalEvent(signal=signal, strategy_id=strategy_id)
                if self.signal_cache.add(event):
                    events.append(event)
                    await self.signal_generator.dispatch(event)

        return events


# 全局中书省实例
zhongshu_sheng = ZhongshuSheng()
