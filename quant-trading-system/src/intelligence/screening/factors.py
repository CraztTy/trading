"""
多因子评分模型

提供多因子选股评分功能：
- 价值因子：PE、PB、PS等
- 质量因子：ROE、ROA、毛利率等
- 成长因子：营收增长、利润增长等
- 动量因子：价格动量、成交量动量等
- 风险因子：波动率、Beta等
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
import statistics
import math

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class FactorType(Enum):
    """因子类型"""
    VALUE = "value"           # 价值因子
    QUALITY = "quality"       # 质量因子
    GROWTH = "growth"         # 成长因子
    MOMENTUM = "momentum"     # 动量因子
    RISK = "risk"             # 风险因子
    SIZE = "size"             # 规模因子


class FactorDirection(Enum):
    """因子方向"""
    POSITIVE = 1      # 正向（值越大越好）
    NEGATIVE = -1     # 反向（值越小越好）


@dataclass
class FactorDefinition:
    """因子定义"""
    name: str
    type: FactorType
    direction: FactorDirection
    weight: float = 1.0
    description: str = ""
    normalize_method: str = "zscore"  # zscore, minmax, rank


@dataclass
class FactorScore:
    """因子得分"""
    symbol: str
    factor_name: str
    raw_value: Optional[float]
    normalized_score: float  # 标准化后的分数，0-100
    weighted_score: float    # 加权后的分数
    rank: int = 0


@dataclass
class MultiFactorResult:
    """多因子评分结果"""
    symbol: str
    name: Optional[str] = None

    # 各类因子得分
    value_score: float = 0.0
    quality_score: float = 0.0
    growth_score: float = 0.0
    momentum_score: float = 0.0
    risk_score: float = 0.0
    size_score: float = 0.0

    # 总分
    total_score: float = 0.0

    # 排名
    rank: int = 0
    percentile: float = 0.0

    # 详情
    factor_scores: Dict[str, FactorScore] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "name": self.name,
            "value_score": round(self.value_score, 2),
            "quality_score": round(self.quality_score, 2),
            "growth_score": round(self.growth_score, 2),
            "momentum_score": round(self.momentum_score, 2),
            "risk_score": round(self.risk_score, 2),
            "total_score": round(self.total_score, 2),
            "rank": self.rank,
            "percentile": round(self.percentile, 2),
        }


class FactorNormalizer:
    """因子标准化器"""

    @staticmethod
    def zscore(values: List[float]) -> List[float]:
        """Z-Score标准化"""
        if not values or len(values) < 2:
            return [50.0] * len(values)

        mean = statistics.mean(values)
        std = statistics.stdev(values)

        if std == 0:
            return [50.0] * len(values)

        # 转换为0-100分
        z_scores = [(v - mean) / std for v in values]
        # Z-score通常范围在-3到3之间，映射到0-100
        return [max(0, min(100, 50 + z * 16.67)) for z in z_scores]

    @staticmethod
    def minmax(values: List[float]) -> List[float]:
        """Min-Max标准化"""
        if not values:
            return []

        min_val = min(values)
        max_val = max(values)

        if max_val == min_val:
            return [50.0] * len(values)

        return [(v - min_val) / (max_val - min_val) * 100 for v in values]

    @staticmethod
    def rank(values: List[float], reverse: bool = False) -> List[float]:
        """排名标准化"""
        if not values:
            return []

        n = len(values)
        # 获取排序后的索引
        sorted_indices = sorted(range(n), key=lambda i: values[i], reverse=reverse)
        # 分配排名分数
        scores = [0.0] * n
        for rank, idx in enumerate(sorted_indices):
            # 排名越靠前分数越高
            scores[idx] = (n - rank) / n * 100

        return scores

    @staticmethod
    def percentile(values: List[float]) -> List[float]:
        """百分位数标准化"""
        if not values:
            return []

        sorted_values = sorted(values)
        n = len(values)

        result = []
        for v in values:
            # 计算小于v的值的比例
            count = sum(1 for sv in sorted_values if sv < v)
            result.append(count / n * 100)

        return result


class MultiFactorModel:
    """
    多因子评分模型

    综合多个因子对股票进行评分排名
    """

    # 默认因子定义
    DEFAULT_FACTORS = [
        # 价值因子（负向：越低越好）
        FactorDefinition("pe_ttm", FactorType.VALUE, FactorDirection.NEGATIVE, 1.0, "市盈率TTM"),
        FactorDefinition("pb", FactorType.VALUE, FactorDirection.NEGATIVE, 1.0, "市净率"),
        FactorDefinition("ps", FactorType.VALUE, FactorDirection.NEGATIVE, 0.5, "市销率"),
        FactorDefinition("dividend_yield", FactorType.VALUE, FactorDirection.POSITIVE, 1.0, "股息率"),

        # 质量因子（正向：越高越好）
        FactorDefinition("roe", FactorType.QUALITY, FactorDirection.POSITIVE, 1.5, "净资产收益率"),
        FactorDefinition("roa", FactorType.QUALITY, FactorDirection.POSITIVE, 1.0, "总资产收益率"),
        FactorDefinition("gross_margin", FactorType.QUALITY, FactorDirection.POSITIVE, 1.0, "毛利率"),
        FactorDefinition("net_margin", FactorType.QUALITY, FactorDirection.POSITIVE, 1.0, "净利率"),

        # 成长因子（正向：越高越好）
        FactorDefinition("revenue_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 1.5, "营收增长率"),
        FactorDefinition("profit_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 1.5, "利润增长率"),
        FactorDefinition("roe_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 1.0, "ROE增长率"),

        # 动量因子
        FactorDefinition("price_momentum_20d", FactorType.MOMENTUM, FactorDirection.POSITIVE, 1.0, "20日价格动量"),
        FactorDefinition("price_momentum_60d", FactorType.MOMENTUM, FactorDirection.POSITIVE, 0.8, "60日价格动量"),
        FactorDefinition("volume_momentum", FactorType.MOMENTUM, FactorDirection.POSITIVE, 0.5, "成交量动量"),

        # 风险因子（反向：越低越好）
        FactorDefinition("volatility", FactorType.RISK, FactorDirection.NEGATIVE, 1.0, "波动率"),
        FactorDefinition("beta", FactorType.RISK, FactorDirection.NEGATIVE, 0.8, "Beta系数"),
        FactorDefinition("max_drawdown", FactorType.RISK, FactorDirection.NEGATIVE, 1.0, "最大回撤"),

        # 规模因子
        FactorDefinition("market_cap", FactorType.SIZE, FactorDirection.POSITIVE, 0.5, "市值"),
    ]

    def __init__(self, factors: Optional[List[FactorDefinition]] = None):
        self.factors = factors or self.DEFAULT_FACTORS.copy()
        self.normalizer = FactorNormalizer()

        # 按类型分组
        self._factors_by_type: Dict[FactorType, List[FactorDefinition]] = {}
        for factor in self.factors:
            if factor.type not in self._factors_by_type:
                self._factors_by_type[factor.type] = []
            self._factors_by_type[factor.type].append(factor)

    def add_factor(self, factor: FactorDefinition) -> 'MultiFactorModel':
        """添加因子"""
        self.factors.append(factor)
        if factor.type not in self._factors_by_type:
            self._factors_by_type[factor.type] = []
        self._factors_by_type[factor.type].append(factor)
        return self

    def remove_factor(self, name: str) -> 'MultiFactorModel':
        """移除因子"""
        self.factors = [f for f in self.factors if f.name != name]
        for type_list in self._factors_by_type.values():
            type_list[:] = [f for f in type_list if f.name != name]
        return self

    def set_factor_weight(self, name: str, weight: float) -> 'MultiFactorModel':
        """设置因子权重"""
        for factor in self.factors:
            if factor.name == name:
                factor.weight = weight
                break
        return self

    def score(self, stocks_data: List[Dict[str, Any]]) -> List[MultiFactorResult]:
        """
        对股票列表进行多因子评分

        Args:
            stocks_data: 股票数据列表

        Returns:
            List[MultiFactorResult]: 评分结果列表
        """
        if not stocks_data:
            return []

        logger.info(f"开始多因子评分: 股票数={len(stocks_data)}, 因子数={len(self.factors)}")

        results = []

        # 对每个因子计算得分
        for factor in self.factors:
            self._calculate_factor_score(stocks_data, results, factor)

        # 计算各类因子总分
        self._calculate_category_scores(results)

        # 计算综合得分
        self._calculate_total_scores(results)

        # 排名
        self._rank_results(results)

        logger.info(f"多因子评分完成: 结果数={len(results)}")

        return sorted(results, key=lambda x: x.total_score, reverse=True)

    def _calculate_factor_score(
        self,
        stocks_data: List[Dict[str, Any]],
        results: List[MultiFactorResult],
        factor: FactorDefinition
    ) -> None:
        """计算单个因子的得分"""
        # 提取因子值
        values = []
        valid_indices = []

        for i, stock in enumerate(stocks_data):
            value = stock.get(factor.name)
            if value is not None and isinstance(value, (int, float)):
                # 处理无穷大和NaN
                if math.isfinite(value):
                    values.append(float(value))
                    valid_indices.append(i)

        if not values:
            return

        # 标准化
        if factor.direction == FactorDirection.NEGATIVE:
            # 反向因子，反转分数
            normalized = self.normalizer.zscore(values)
            normalized = [100 - s for s in normalized]
        else:
            normalized = self.normalizer.zscore(values)

        # 创建或更新结果
        for idx, (stock_idx, norm_score) in enumerate(zip(valid_indices, normalized)):
            stock = stocks_data[stock_idx]
            symbol = stock.get('symbol', f'UNKNOWN_{stock_idx}')

            # 查找或创建结果
            result = None
            for r in results:
                if r.symbol == symbol:
                    result = r
                    break

            if result is None:
                result = MultiFactorResult(
                    symbol=symbol,
                    name=stock.get('name')
                )
                results.append(result)

            # 计算加权得分
            weighted_score = norm_score * factor.weight

            # 记录因子得分
            factor_score = FactorScore(
                symbol=symbol,
                factor_name=factor.name,
                raw_value=values[idx],
                normalized_score=norm_score,
                weighted_score=weighted_score
            )
            result.factor_scores[factor.name] = factor_score

    def _calculate_category_scores(self, results: List[MultiFactorResult]) -> None:
        """计算各类因子得分"""
        for result in results:
            # 价值因子
            value_scores = [
                fs.weighted_score for fs in result.factor_scores.values()
                if any(f.name == fs.factor_name and f.type == FactorType.VALUE for f in self.factors)
            ]
            if value_scores:
                result.value_score = statistics.mean(value_scores)

            # 质量因子
            quality_scores = [
                fs.weighted_score for fs in result.factor_scores.values()
                if any(f.name == fs.factor_name and f.type == FactorType.QUALITY for f in self.factors)
            ]
            if quality_scores:
                result.quality_score = statistics.mean(quality_scores)

            # 成长因子
            growth_scores = [
                fs.weighted_score for fs in result.factor_scores.values()
                if any(f.name == fs.factor_name and f.type == FactorType.GROWTH for f in self.factors)
            ]
            if growth_scores:
                result.growth_score = statistics.mean(growth_scores)

            # 动量因子
            momentum_scores = [
                fs.weighted_score for fs in result.factor_scores.values()
                if any(f.name == fs.factor_name and f.type == FactorType.MOMENTUM for f in self.factors)
            ]
            if momentum_scores:
                result.momentum_score = statistics.mean(momentum_scores)

            # 风险因子
            risk_scores = [
                fs.weighted_score for fs in result.factor_scores.values()
                if any(f.name == fs.factor_name and f.type == FactorType.RISK for f in self.factors)
            ]
            if risk_scores:
                result.risk_score = statistics.mean(risk_scores)

            # 规模因子
            size_scores = [
                fs.weighted_score for fs in result.factor_scores.values()
                if any(f.name == fs.factor_name and f.type == FactorType.SIZE for f in self.factors)
            ]
            if size_scores:
                result.size_score = statistics.mean(size_scores)

    def _calculate_total_scores(self, results: List[MultiFactorResult]) -> None:
        """计算综合得分"""
        # 计算总权重
        total_weight = sum(
            sum(f.weight for f in factors)
            for factors in self._factors_by_type.values()
        )

        if total_weight == 0:
            return

        for result in results:
            total = (
                result.value_score * sum(f.weight for f in self._factors_by_type.get(FactorType.VALUE, [])) +
                result.quality_score * sum(f.weight for f in self._factors_by_type.get(FactorType.QUALITY, [])) +
                result.growth_score * sum(f.weight for f in self._factors_by_type.get(FactorType.GROWTH, [])) +
                result.momentum_score * sum(f.weight for f in self._factors_by_type.get(FactorType.MOMENTUM, [])) +
                result.risk_score * sum(f.weight for f in self._factors_by_type.get(FactorType.RISK, [])) +
                result.size_score * sum(f.weight for f in self._factors_by_type.get(FactorType.SIZE, []))
            )
            result.total_score = total / total_weight

    def _rank_results(self, results: List[MultiFactorResult]) -> None:
        """对结果进行排名"""
        # 按总分排序
        sorted_results = sorted(results, key=lambda x: x.total_score, reverse=True)

        n = len(sorted_results)
        for rank, result in enumerate(sorted_results, 1):
            result.rank = rank
            result.percentile = (n - rank + 1) / n * 100

            # 更新因子排名
            for fs in result.factor_scores.values():
                # 这里简化处理，实际应该对每个因子单独排名
                fs.rank = rank


class FactorBuilder:
    """因子模型构建器"""

    @staticmethod
    def value_model() -> MultiFactorModel:
        """纯价值模型"""
        factors = [
            FactorDefinition("pe_ttm", FactorType.VALUE, FactorDirection.NEGATIVE, 2.0, "市盈率"),
            FactorDefinition("pb", FactorType.VALUE, FactorDirection.NEGATIVE, 2.0, "市净率"),
            FactorDefinition("ps", FactorType.VALUE, FactorDirection.NEGATIVE, 1.0, "市销率"),
            FactorDefinition("dividend_yield", FactorType.VALUE, FactorDirection.POSITIVE, 1.5, "股息率"),
            FactorDefinition("roe", FactorType.QUALITY, FactorDirection.POSITIVE, 0.5, "ROE"),
        ]
        return MultiFactorModel(factors)

    @staticmethod
    def growth_model() -> MultiFactorModel:
        """纯成长模型"""
        factors = [
            FactorDefinition("revenue_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 2.0, "营收增长"),
            FactorDefinition("profit_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 2.0, "利润增长"),
            FactorDefinition("roe_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 1.5, "ROE增长"),
            FactorDefinition("roe", FactorType.QUALITY, FactorDirection.POSITIVE, 1.0, "ROE"),
        ]
        return MultiFactorModel(factors)

    @staticmethod
    def quality_model() -> MultiFactorModel:
        """纯质量模型"""
        factors = [
            FactorDefinition("roe", FactorType.QUALITY, FactorDirection.POSITIVE, 2.0, "ROE"),
            FactorDefinition("roa", FactorType.QUALITY, FactorDirection.POSITIVE, 1.5, "ROA"),
            FactorDefinition("gross_margin", FactorType.QUALITY, FactorDirection.POSITIVE, 1.5, "毛利率"),
            FactorDefinition("net_margin", FactorType.QUALITY, FactorDirection.POSITIVE, 1.5, "净利率"),
            FactorDefinition("revenue_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 0.5, "营收增长"),
        ]
        return MultiFactorModel(factors)

    @staticmethod
    def balanced_model() -> MultiFactorModel:
        """平衡模型（各因子均衡）"""
        factors = [
            # 价值
            FactorDefinition("pe_ttm", FactorType.VALUE, FactorDirection.NEGATIVE, 1.0, "市盈率"),
            FactorDefinition("pb", FactorType.VALUE, FactorDirection.NEGATIVE, 1.0, "市净率"),

            # 质量
            FactorDefinition("roe", FactorType.QUALITY, FactorDirection.POSITIVE, 1.5, "ROE"),
            FactorDefinition("gross_margin", FactorType.QUALITY, FactorDirection.POSITIVE, 1.0, "毛利率"),

            # 成长
            FactorDefinition("revenue_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 1.5, "营收增长"),
            FactorDefinition("profit_growth", FactorType.GROWTH, FactorDirection.POSITIVE, 1.5, "利润增长"),

            # 风险
            FactorDefinition("volatility", FactorType.RISK, FactorDirection.NEGATIVE, 1.0, "波动率"),
        ]
        return MultiFactorModel(factors)
