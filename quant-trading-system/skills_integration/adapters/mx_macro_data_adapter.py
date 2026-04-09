"""
mx-macro-data 技能适配器

提供宏观经济数据获取能力：
- 国民经济数据
- 货币金融数据
- 价格指数数据
- 行业经济数据
"""
from typing import Dict, List, Optional, Any
from skills_integration.adapters.base_adapter import BaseSkillAdapter
from src.common.logger import get_logger

logger = get_logger(__name__)


class MxMacroDataAdapter(BaseSkillAdapter):
    """
    东方财富宏观数据适配器
    """

    def __init__(self, config: Dict[str, Any]):
        cache_ttl = config.get('macro_cache_ttl', 3600)  # 1小时缓存
        rate_limit = config.get('macro_rate_limit', 30)
        super().__init__('mx-macro-data', config, cache_ttl, rate_limit)

    async def fetch_macro_data(
        self,
        query: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        获取宏观数据

        Args:
            query: 自然语言查询，如"中国GDP同比增速"
            use_cache: 是否使用缓存

        Returns:
            数据结果字典
        """
        cache_params = {'query': query} if use_cache else None

        result = await self.execute_script(
            'get_data.py',
            ['--query', query],
            use_cache=use_cache,
            cache_params=cache_params
        )

        return result

    async def get_gdp_growth(self) -> Optional[Dict[str, Any]]:
        """获取GDP增速数据"""
        return await self.fetch_macro_data("中国GDP同比增速")

    async def get_cpi(self) -> Optional[Dict[str, Any]]:
        """获取CPI数据"""
        return await self.fetch_macro_data("中国CPI同比")

    async def get_ppi(self) -> Optional[Dict[str, Any]]:
        """获取PPI数据"""
        return await self.fetch_macro_data("中国PPI同比")

    async def get_pmi(self) -> Optional[Dict[str, Any]]:
        """获取PMI数据"""
        return await self.fetch_macro_data("中国制造业PMI")

    async def get_money_supply(self) -> Optional[Dict[str, Any]]:
        """获取货币供应量数据"""
        return await self.fetch_macro_data("中国M2货币供应量同比")

    async def get_interest_rates(self) -> Optional[Dict[str, Any]]:
        """获取利率数据"""
        return await self.fetch_macro_data("中国LPR利率最新数据")

    async def get_economic_indicators(self) -> Dict[str, Any]:
        """
        获取主要经济指标合集
        """
        indicators = {
            'gdp': await self.get_gdp_growth(),
            'cpi': await self.get_cpi(),
            'ppi': await self.get_ppi(),
            'pmi': await self.get_pmi(),
            'm2': await self.get_money_supply(),
        }
        return indicators

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            result = await self.get_gdp_growth()
            return result is not None
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
