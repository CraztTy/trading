"""
配置管理模块 - 基于Pydantic Settings的配置管理
"""

import os
from typing import Optional, List, Dict, Any
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    host: str = Field(default="localhost", description="数据库主机")
    port: int = Field(default=3306, description="数据库端口")
    name: str = Field(default="quant_trading", description="数据库名称")
    user: str = Field(default="quant_user", description="数据库用户")
    password: str = Field(default="", description="数据库密码")
    pool_size: int = Field(default=20, description="连接池大小")
    max_overflow: int = Field(default=40, description="最大溢出连接数")

    @property
    def url(self) -> str:
        """获取数据库连接URL"""
        return f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def sync_url(self) -> str:
        """获取同步数据库连接URL"""
        return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class RedisSettings(BaseSettings):
    """Redis配置"""

    host: str = Field(default="localhost", description="Redis主机")
    port: int = Field(default=6379, description="Redis端口")
    password: Optional[str] = Field(default=None, description="Redis密码")
    db: int = Field(default=0, description="Redis数据库编号")

    @property
    def url(self) -> str:
        """获取Redis连接URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class ClickhouseSettings(BaseSettings):
    """ClickHouse配置"""

    host: str = Field(default="localhost", description="ClickHouse主机")
    port: int = Field(default=9000, description="ClickHouse端口")
    user: str = Field(default="default", description="ClickHouse用户")
    password: str = Field(default="", description="ClickHouse密码")
    database: str = Field(default="quant_data", description="ClickHouse数据库")

    @property
    def url(self) -> str:
        """获取ClickHouse连接URL"""
        return f"clickhouse://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class DataSourceSettings(BaseSettings):
    """数据源配置"""

    # 数据源类型: akshare/tushare/mysql/postgresql/default
    provider: str = Field(default="akshare", description="主数据源类型")
    backup_provider: Optional[str] = Field(default=None, description="备用数据源")

    # Baostock配置
    baostock_username: Optional[str] = Field(default=None, description="Baostock用户名")
    baostock_password: Optional[str] = Field(default=None, description="Baostock密码")

    # Tushare配置
    tushare_token: Optional[str] = Field(default=None, description="Tushare Token")
    tushare_pro_token: Optional[str] = Field(default=None, description="Tushare Pro Token")

    # AkShare配置
    akshare_proxy: Optional[str] = Field(default=None, description="AkShare代理地址")

    # 东方财富配置
    eastmoney_token: Optional[str] = Field(default=None, description="东方财富Token")

    # MySQL直连配置
    mysql_host: str = Field(default="localhost", description="MySQL主机")
    mysql_port: int = Field(default=3306, description="MySQL端口")
    mysql_user: str = Field(default="trading", description="MySQL用户")
    mysql_password: Optional[str] = Field(default=None, description="MySQL密码")
    mysql_database: str = Field(default="quant_trading", description="MySQL数据库")
    mysql_pool_size: int = Field(default=10, description="MySQL连接池大小")

    # PostgreSQL直连配置
    postgres_host: str = Field(default="localhost", description="PostgreSQL主机")
    postgres_port: int = Field(default=5432, description="PostgreSQL端口")
    postgres_user: str = Field(default="trading", description="PostgreSQL用户")
    postgres_password: Optional[str] = Field(default=None, description="PostgreSQL密码")
    postgres_database: str = Field(default="quant_trading", description="PostgreSQL数据库")
    postgres_pool_size: int = Field(default=10, description="PostgreSQL连接池大小")

    # 默认API配置
    default_api_url: Optional[str] = Field(default=None, description="默认API地址")
    default_api_key: Optional[str] = Field(default=None, description="默认API密钥")

    @validator("baostock_username", "baostock_password", pre=True)
    def validate_baostock_credentials(cls, v):
        """验证Baostock凭证"""
        if v is None:
            return v
        return v.strip()


class JinCeSettings(BaseSettings):
    """睿之兮引擎配置"""

    # 风控参数
    max_position_per_stock: float = Field(default=0.10, description="单票最大仓位(10%)")
    max_total_position: float = Field(default=0.50, description="总仓位最大(50%)")
    stop_loss_pct: float = Field(default=0.01, description="单笔止损比例(1%)")
    take_profit_pct: float = Field(default=0.05, description="单笔止盈比例(5%)")
    max_daily_loss_pct: float = Field(default=0.02, description="日最大亏损熔断(2%)")
    max_consecutive_losses: int = Field(default=3, description="连续亏损暂停次数")
    min_avg_volume: int = Field(default=1000000, description="最小平均成交量")

    # 回测参数
    default_start_date: str = Field(default="2024-01-01", description="默认回测开始日期")
    default_end_date: str = Field(default="2025-12-31", description="默认回测结束日期")
    initial_capital: float = Field(default=1000000.0, description="初始资金")

    # 交易费用
    commission_rate: float = Field(default=0.0003, description="佣金费率")
    min_commission: float = Field(default=5.0, description="最低佣金")
    stamp_tax_rate: float = Field(default=0.001, description="印花税率")
    transfer_fee_rate: float = Field(default=0.00002, description="过户费率")

    # 实盘参数
    poll_interval: int = Field(default=5, description="实盘轮询间隔(秒)")
    auto_trade: bool = Field(default=False, description="是否启用自动交易")


class SkillsSettings(BaseSettings):
    """金融技能配置"""

    # 东方财富API密钥
    em_api_key: Optional[str] = Field(default=None, description="东方财富妙想API密钥")

    # 技能开关
    enable_finance_data: bool = Field(default=True, description="启用金融数据技能")
    enable_macro_data: bool = Field(default=True, description="启用宏观数据技能")
    enable_earnings_review: bool = Field(default=True, description="启用财报分析技能")
    enable_industry_research: bool = Field(default=True, description="启用行业研究技能")
    enable_industry_tracker: bool = Field(default=True, description="启用行业追踪技能")
    enable_stock_screener: bool = Field(default=True, description="启用股票筛选技能")
    enable_finance_search: bool = Field(default=True, description="启用金融搜索技能")
    enable_finance_assistant: bool = Field(default=True, description="启用金融助手技能")

    # 缓存配置
    skill_cache_ttl: int = Field(default=3600, description="技能结果缓存时间(秒)")
    finance_data_cache_ttl: int = Field(default=300, description="金融数据缓存时间(秒)")
    earnings_cache_ttl: int = Field(default=3600, description="财报分析缓存时间(秒)")
    macro_cache_ttl: int = Field(default=3600, description="宏观数据缓存时间(秒)")

    # 限流配置
    rate_limit_per_minute: int = Field(default=30, description="每分钟最大调用次数")
    finance_data_rate_limit: int = Field(default=30, description="金融数据限流")
    earnings_rate_limit: int = Field(default=20, description="财报分析限流")
    macro_rate_limit: int = Field(default=30, description="宏观数据限流")


class SecuritySettings(BaseSettings):
    """安全配置"""

    secret_key: str = Field(default="your-secret-key-change-in-production", description="应用密钥")
    jwt_secret_key: str = Field(default="your-jwt-secret-key-change-in-production", description="JWT密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    jwt_access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间(分钟)")
    jwt_refresh_token_expire_days: int = Field(default=7, description="刷新令牌过期时间(天)")

    encryption_key: Optional[str] = Field(default=None, description="加密密钥")

    @validator("secret_key", "jwt_secret_key")
    def validate_secret_key(cls, v):
        """验证密钥强度"""
        if len(v) < 32:
            raise ValueError("密钥长度必须至少32个字符")
        return v


class MonitoringSettings(BaseSettings):
    """监控配置"""

    enable_prometheus: bool = Field(default=True, description="启用Prometheus监控")
    prometheus_port: int = Field(default=8001, description="Prometheus指标端口")

    enable_opentelemetry: bool = Field(default=True, description="启用OpenTelemetry追踪")
    otel_service_name: str = Field(default="quant-trading-api", description="OpenTelemetry服务名称")
    otel_endpoint: Optional[str] = Field(default=None, description="OpenTelemetry端点")

    log_level: str = Field(default="INFO", description="日志级别")
    log_format: str = Field(default="json", description="日志格式")
    log_file: Optional[str] = Field(default=None, description="日志文件路径")


class Settings(BaseSettings):
    """主配置类"""

    # 应用配置
    app_name: str = Field(default="quant-trading-system", description="应用名称")
    app_env: str = Field(default="development", description="应用环境")
    app_debug: bool = Field(default=False, description="调试模式")
    app_url: str = Field(default="http://localhost:8000", description="应用URL")

    # 数据库配置
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    clickhouse: ClickhouseSettings = Field(default_factory=ClickhouseSettings)

    # 数据源配置
    data_sources: DataSourceSettings = Field(default_factory=DataSourceSettings)

    # 睿之兮引擎配置
    jince: JinCeSettings = Field(default_factory=JinCeSettings)

    # 金融技能配置
    skills: SkillsSettings = Field(default_factory=SkillsSettings)

    # 安全配置
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    # 监控配置
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)

    # 前端配置
    frontend_url: str = Field(default="http://localhost:9001", description="前端URL")
    frontend_api_url: str = Field(default="http://localhost:9000/api/v1", description="前端API URL")

    # 性能配置
    worker_count: int = Field(default=4, description="工作进程数量")
    max_requests: int = Field(default=1000, description="最大请求数")
    request_timeout: int = Field(default=30, description="请求超时时间(秒)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        case_sensitive = False

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """自定义配置源加载顺序"""
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()


# 全局配置实例
settings = get_settings()