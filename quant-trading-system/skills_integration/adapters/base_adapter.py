"""
技能适配器基类
"""
import os
import sys
import json
import asyncio
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from src.common.logger import get_logger
from skills_integration.cache import SkillCache
from skills_integration.rate_limiter import RateLimiter

logger = get_logger(__name__)


class BaseSkillAdapter(ABC):
    """技能适配器基类"""

    def __init__(
        self,
        skill_name: str,
        config: Dict[str, Any],
        cache_ttl: int = 3600,
        rate_limit: int = 30
    ):
        self.skill_name = skill_name
        self.config = config
        self.em_api_key = config.get('em_api_key') or config.get('skills', {}).get('em_api_key')

        # 技能路径
        base_path = config.get('skills_base_path', Path.home() / '.claude/skills')
        self.skill_path = Path(base_path) / skill_name

        # 缓存和限流
        self.cache = SkillCache(ttl=cache_ttl)
        self.rate_limiter = RateLimiter(max_calls=rate_limit, window_seconds=60)

    async def execute_script(
        self,
        script_name: str,
        args: list,
        use_cache: bool = False,
        cache_params: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        执行技能脚本

        Args:
            script_name: 脚本名称
            args: 脚本参数列表
            use_cache: 是否使用缓存
            cache_params: 缓存参数

        Returns:
            脚本执行结果
        """
        # 检查缓存
        if use_cache and cache_params:
            cached = self.cache.get(self.skill_name, cache_params)
            if cached:
                logger.debug(f"命中缓存: {self.skill_name}")
                return cached

        # 限流控制
        await self.rate_limiter.acquire()

        try:
            # 构建脚本路径
            script_path = self.skill_path / 'scripts' / script_name

            if not script_path.exists():
                logger.error(f"脚本不存在: {script_path}")
                return None

            # 设置环境变量
            env = os.environ.copy()
            if self.em_api_key:
                env['EM_API_KEY'] = self.em_api_key

            # 构建命令
            cmd = [sys.executable, str(script_path)] + args

            logger.debug(f"执行命令: {' '.join(cmd)}")

            # 异步执行
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=60  # 60秒超时
            )

            if proc.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"脚本执行失败: {error_msg}")
                return None

            # 解析结果
            try:
                result = json.loads(stdout.decode('utf-8'))
            except json.JSONDecodeError:
                # 如果不是JSON，返回原始文本
                result = {'output': stdout.decode('utf-8')}

            # 缓存结果
            if use_cache and cache_params:
                self.cache.set(self.skill_name, cache_params, result)

            return result

        except asyncio.TimeoutError:
            logger.error(f"脚本执行超时: {script_name}")
            return None
        except Exception as e:
            logger.error(f"执行脚本失败: {e}")
            return None

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass
