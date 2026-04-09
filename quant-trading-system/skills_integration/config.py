"""
技能集成配置
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field


class SkillsConfig(BaseSettings):
    """技能集成配置"""

    # 东方财富API密钥
    em_api_key: Optional[str] = Field(default=None, description="东方财富妙想API密钥")

    # 技能根目录
    skills_base_path: Path = Field(
        default=Path.home() / ".claude/skills",
        description="技能安装根目录"
    )

    # 输出目录
    output_base_dir: str = Field(
        default="miaoxiang",
        description="技能输出根目录"
    )

    # 技能开关
    enable_finance_data: bool = True
    enable_macro_data: bool = True
    enable_earnings_review: bool = True
    enable_industry_research: bool = True
    enable_stock_screener: bool = True
    enable_finance_search: bool = True

    # 缓存配置
    skill_cache_ttl: int = 3600
    finance_data_cache_ttl: int = 300
    earnings_cache_ttl: int = 3600
    macro_cache_ttl: int = 3600

    # 限流配置
    rate_limit_per_minute: int = 30
    finance_data_rate_limit: int = 30
    earnings_rate_limit: int = 20
    macro_rate_limit: int = 30

    class Config:
        env_prefix = "SKILLS_"

    def get_skill_path(self, skill_name: str) -> Path:
        """获取技能路径"""
        return self.skills_base_path / skill_name

    def get_output_path(self, skill_name: str) -> Path:
        """获取技能输出路径"""
        return Path(self.output_base_dir) / skill_name
