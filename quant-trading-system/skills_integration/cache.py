"""
技能结果缓存管理
"""
import hashlib
import json
from typing import Any, Optional
from datetime import datetime, timedelta


class SkillCache:
    """技能结果缓存 - 基于内存的简单实现"""

    def __init__(self, ttl: int = 3600):
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = ttl

    def _make_key(self, skill_name: str, params: dict) -> str:
        """生成缓存键"""
        param_str = json.dumps(params, sort_keys=True, default=str)
        hash_str = hashlib.md5(param_str.encode()).hexdigest()[:12]
        return f"{skill_name}:{hash_str}"

    def get(self, skill_name: str, params: dict) -> Optional[Any]:
        """获取缓存"""
        key = self._make_key(skill_name, params)

        if key in self._cache:
            # 检查是否过期
            timestamp = self._timestamps.get(key)
            if timestamp and (datetime.now() - timestamp).seconds < self.default_ttl:
                return self._cache[key]
            else:
                # 过期清理
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)

        return None

    def set(
        self,
        skill_name: str,
        params: dict,
        value: Any,
        ttl: Optional[int] = None
    ):
        """设置缓存"""
        key = self._make_key(skill_name, params)
        self._cache[key] = value
        self._timestamps[key] = datetime.now()

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._timestamps.clear()
