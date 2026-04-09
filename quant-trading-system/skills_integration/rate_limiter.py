"""
API限流器
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Deque
from collections import deque


class RateLimiter:
    """基于滑动窗口的API限流器"""

    def __init__(self, max_calls: int = 30, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        """获取调用许可"""
        async with self._lock:
            now = time.time()

            # 移除窗口外的记录
            cutoff = now - self.window_seconds
            while self._calls and self._calls[0] < cutoff:
                self._calls.popleft()

            # 检查是否超过限制
            if len(self._calls) >= self.max_calls:
                wait_time = self._calls[0] - cutoff
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    return await self.acquire()

            self._calls.append(now)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
