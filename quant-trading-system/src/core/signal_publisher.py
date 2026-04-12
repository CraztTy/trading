"""
信号发布器

负责：
- 信号实时推送（WebSocket）
- 信号去重和节流
- 信号日志记录
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Callable, Optional, Set
from dataclasses import dataclass, asdict
from decimal import Decimal

from src.common.logger import TradingLogger
from src.strategy.base import Signal

logger = TradingLogger(__name__)


@dataclass
class SignalEvent:
    """信号事件"""
    id: str                          # 唯一ID
    timestamp: datetime              # 生成时间
    strategy_id: str                 # 策略ID
    strategy_name: str               # 策略名称
    symbol: str                      # 股票代码
    signal_type: str                 # buy/sell
    price: Optional[Decimal]         # 价格
    volume: int                      # 数量
    confidence: float                # 置信度
    reason: str                      # 原因
    status: str = "pending"          # pending/confirmed/ignored/executed
    metadata: Dict = None            # 额外数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "price": float(self.price) if self.price else None,
            "volume": self.volume,
            "confidence": self.confidence,
            "reason": self.reason,
            "status": self.status,
            "metadata": self.metadata
        }


class SignalPublisher:
    """信号发布器（单例）"""

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

        # WebSocket连接管理
        self._subscribers: List[Callable] = []

        # 信号缓存（用于去重）
        self._signal_cache: Dict[str, datetime] = {}
        self._cache_ttl = 60  # 60秒去重窗口

        # 节流控制
        self._last_publish_time: Dict[str, datetime] = {}
        self._throttle_interval = 1  # 1秒节流间隔

        # 信号历史
        self._signal_history: List[SignalEvent] = []
        self._max_history = 1000

        # 统计
        self._stats = {
            "total_signals": 0,
            "published_signals": 0,
            "deduplicated_signals": 0,
            "throttled_signals": 0
        }

        logger.info("信号发布器初始化完成")

    def subscribe(self, callback: Callable[[SignalEvent], None]):
        """订阅信号"""
        self._subscribers.append(callback)
        logger.info(f"新增信号订阅者，当前订阅数: {len(self._subscribers)}")

    def unsubscribe(self, callback: Callable[[SignalEvent], None]):
        """取消订阅"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def publish(self, signal: Signal, strategy_id: str, strategy_name: str = "") -> Optional[SignalEvent]:
        """
        发布信号

        Returns:
            SignalEvent or None: 如果信号被去重或节流，返回None
        """
        # 生成信号ID
        signal_id = self._generate_signal_id(signal, strategy_id)

        # 去重检查
        if self._is_duplicate(signal_id):
            self._stats["deduplicated_signals"] += 1
            logger.debug(f"信号去重: {signal_id}")
            return None

        # 节流检查
        throttle_key = f"{strategy_id}:{signal.symbol}"
        if self._is_throttled(throttle_key):
            self._stats["throttled_signals"] += 1
            logger.debug(f"信号节流: {throttle_key}")
            return None

        # 创建信号事件
        event = SignalEvent(
            id=signal_id,
            timestamp=datetime.now(),
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbol=signal.symbol,
            signal_type=signal.type.value,
            price=signal.price,
            volume=signal.volume or 100,
            confidence=signal.confidence,
            reason=signal.reason,
            metadata=signal.metadata
        )

        # 更新缓存
        self._signal_cache[signal_id] = datetime.now()
        self._last_publish_time[throttle_key] = datetime.now()

        # 添加到历史
        self._signal_history.append(event)
        if len(self._signal_history) > self._max_history:
            self._signal_history = self._signal_history[-self._max_history:]

        # 发布到订阅者
        await self._notify_subscribers(event)

        self._stats["total_signals"] += 1
        self._stats["published_signals"] += 1

        logger.info(f"信号发布: {signal_id} [{event.signal_type}] {event.symbol}")

        return event

    def _generate_signal_id(self, signal: Signal, strategy_id: str) -> str:
        """生成信号唯一ID"""
        import hashlib
        content = f"{strategy_id}:{signal.symbol}:{signal.type.value}:{signal.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _is_duplicate(self, signal_id: str) -> bool:
        """检查是否重复信号"""
        if signal_id not in self._signal_cache:
            return False

        # 检查是否过期
        last_time = self._signal_cache[signal_id]
        if (datetime.now() - last_time).total_seconds() > self._cache_ttl:
            # 过期，删除并返回不重复
            del self._signal_cache[signal_id]
            return False

        return True

    def _is_throttled(self, key: str) -> bool:
        """检查是否被节流"""
        if key not in self._last_publish_time:
            return False

        last_time = self._last_publish_time[key]
        return (datetime.now() - last_time).total_seconds() < self._throttle_interval

    async def _notify_subscribers(self, event: SignalEvent):
        """通知所有订阅者"""
        for callback in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"信号通知失败: {e}")

    def get_signal_history(
        self,
        strategy_id: str = None,
        symbol: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[SignalEvent]:
        """获取信号历史"""
        results = self._signal_history

        if strategy_id:
            results = [s for s in results if s.strategy_id == strategy_id]

        if symbol:
            results = [s for s in results if s.symbol == symbol]

        if status:
            results = [s for s in results if s.status == status]

        return results[-limit:]

    def update_signal_status(self, signal_id: str, status: str):
        """更新信号状态"""
        for signal in self._signal_history:
            if signal.id == signal_id:
                signal.status = status
                logger.info(f"信号状态更新: {signal_id} -> {status}")
                break

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self._stats.copy()

    def clear_cache(self):
        """清理过期缓存"""
        now = datetime.now()

        # 清理信号缓存
        expired = [
            sid for sid, ts in self._signal_cache.items()
            if (now - ts).total_seconds() > self._cache_ttl
        ]
        for sid in expired:
            del self._signal_cache[sid]

        logger.debug(f"清理缓存: {len(expired)} 个过期信号")


# 全局信号发布器实例
signal_publisher = SignalPublisher()
