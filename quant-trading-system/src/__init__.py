"""
量化交易系统 - 企业级A股量化交易平台

版本: 0.1.0
作者: Quant Trading Team
"""

__version__ = "0.1.0"
__author__ = "Quant Trading Team"
__email__ = "quant@your-org.com"

from .common.logger import setup_logging
from .common.config import settings

# 配置日志
logger = setup_logging(settings.monitoring.log_level)