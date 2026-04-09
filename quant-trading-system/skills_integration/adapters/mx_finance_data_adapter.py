"""
mx-finance-data 技能适配器

提供金融数据获取能力：
- 实时行情数据
- 历史财务数据
- 估值指标
- 技术指标
"""
from typing import Dict, List, Optional, Any
from skills_integration.adapters.base_adapter import BaseSkillAdapter
from src.common.logger import get_logger

logger = get_logger(__name__)


class MxFinanceDataAdapter(BaseSkillAdapter):
    """
    东方财富金融数据适配器
    """

    def __init__(self, config: Dict[str, Any]):
        cache_ttl = config.get('finance_data_cache_ttl', 300)  # 5分钟缓存
        rate_limit = config.get('finance_data_rate_limit', 30)
        super().__init__('mx-finance-data', config, cache_ttl, rate_limit)

    async def fetch_data(
        self,
        query: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        获取金融数据

        Args:
            query: 自然语言查询，如"贵州茅台最新财务指标"
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

    async def get_realtime_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """获取实时行情"""
        query = f"{code}最新行情数据"
        return await self.fetch_data(query)

    async def get_financial_indicators(self, code: str) -> Optional[Dict[str, Any]]:
        """获取财务指标"""
        query = f"{code}最新财务指标，ROE、ROA、毛利率、净利率"
        return await self.fetch_data(query)

    async def get_valuation_metrics(self, code: str) -> Optional[Dict[str, Any]]:
        """获取估值指标"""
        query = f"{code}最新估值指标，PE、PB、PS、股息率"
        return await self.fetch_data(query)

    async def batch_fetch(
        self,
        codes: List[str],
        fields: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量获取多只股票数据

        注意：东方财富API单次查询最多支持5个实体
        """
        results = {}
        batch_size = 5

        for i in range(0, len(codes), batch_size):
            batch = codes[i:i+batch_size]
            codes_str = ','.join(batch)
            fields_str = ','.join(fields)
            query = f"查询{codes_str}的{fields_str}"

            result = await self.fetch_data(query, use_cache=False)
            if result:
                # 解析批量结果
                for code in batch:
                    if code in result:
                        results[code] = result[code]

        return results

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            result = await self.get_realtime_quote("000001.SZ")
            return result is not None
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
