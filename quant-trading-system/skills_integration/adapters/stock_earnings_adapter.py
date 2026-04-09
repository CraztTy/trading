"""
stock-earnings-review 技能适配器

提供财报分析能力：
- 财报深度分析
- 业绩解读
- 财务健康度评估
"""
from typing import Dict, List, Optional, Any
from skills_integration.adapters.base_adapter import BaseSkillAdapter
from src.common.logger import get_logger

logger = get_logger(__name__)


class StockEarningsAdapter(BaseSkillAdapter):
    """
    上市公司业绩点评适配器
    """

    def __init__(self, config: Dict[str, Any]):
        cache_ttl = config.get('earnings_cache_ttl', 3600)  # 1小时缓存
        rate_limit = config.get('earnings_rate_limit', 20)
        super().__init__('stock-earnings-review', config, cache_ttl, rate_limit)

    async def analyze_earnings(
        self,
        query: str,
        report_date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        分析公司业绩（分步调用）

        Args:
            query: 查询语句，如"分析贵州茅台2025年报"
            report_date: 指定报告期，如"2025-12-31"

        Returns:
            分析结果，包含content、title、share_url等
        """
        cache_key = {'query': query, 'report_date': report_date}

        # 检查缓存
        cached = self.cache.get(self.skill_name, cache_key)
        if cached:
            return cached

        try:
            # 第一步：实体识别
            entity = await self._validate_entity(query)
            if not entity:
                logger.warning(f"实体识别失败: {query}")
                return None

            secu_code = entity.get('secuCode')
            market_char = entity.get('marketChar')
            class_code = entity.get('classCode')
            secu_name = entity.get('secuName')

            # 第二步：获取报告期列表
            report_periods = await self._get_report_periods(
                secu_code, market_char, class_code
            )
            if not report_periods:
                logger.warning(f"无可用报告期: {secu_name}")
                return None

            # 第三步：选择报告期
            if report_date:
                if report_date not in report_periods:
                    logger.warning(f"指定报告期{report_date}不可用，使用最新期")
                    report_date = report_periods[0]
            else:
                report_date = report_periods[0]  # 默认最新期

            # 第四步：生成业绩点评
            result = await self._call_review_api(
                secu_code, market_char, class_code, report_date, secu_name
            )

            # 缓存结果
            if result:
                self.cache.set(self.skill_name, cache_key, result)

            return result

        except Exception as e:
            logger.error(f"财报分析失败: {e}")
            return None

    async def _validate_entity(self, query: str) -> Optional[Dict]:
        """实体识别"""
        result = await self.execute_script(
            'validate_entity.py',
            ['--query', query]
        )
        return result

    async def _get_report_periods(
        self,
        secu_code: str,
        market_char: str,
        class_code: str
    ) -> List[str]:
        """获取报告期列表"""
        result = await self.execute_script(
            'normalize_report_period.py',
            [
                '--secu-code', secu_code,
                '--market-char', market_char,
                '--class-code', class_code
            ]
        )

        if result and 'reportPeriods' in result:
            return result['reportPeriods']
        return []

    async def _call_review_api(
        self,
        secu_code: str,
        market_char: str,
        class_code: str,
        report_date: str,
        secu_name: str
    ) -> Optional[Dict]:
        """调用业绩点评API"""
        result = await self.execute_script(
            'call_review_api.py',
            [
                '--secu-code', secu_code,
                '--market-char', market_char,
                '--class-code', class_code,
                '--report-date', report_date,
                '--secu-name', secu_name
            ]
        )
        return result

    async def batch_analyze(
        self,
        codes: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """批量分析多家公司"""
        results = {}

        for code in codes:
            try:
                query = f"分析{code}最新业绩"
                result = await self.analyze_earnings(query)
                if result:
                    results[code] = result
            except Exception as e:
                logger.error(f"分析{code}失败: {e}")

        return results

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            result = await self.analyze_earnings("贵州茅台业绩分析")
            return result is not None
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False
