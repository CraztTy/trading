"""
智能分析API

集成基本面分析、股票筛选、多因子评分
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from src.intelligence.fundamental.analyzer import (
    FundamentalAnalyzer, FinancialMetrics, BatchFundamentalAnalyzer
)
from src.intelligence.screening.screener import StockScreener, StockData, PresetScreeners
from src.intelligence.screening.factors import MultiFactorModel, FactorBuilder
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)
router = APIRouter()

# 初始化分析器
fundamental_analyzer = FundamentalAnalyzer()
batch_analyzer = BatchFundamentalAnalyzer()
stock_screener = StockScreener()


# ============ Pydantic 模型 ============

from pydantic import BaseModel

class FundamentalRequest(BaseModel):
    code: str
    name: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class FundamentalResponse(BaseModel):
    symbol: str
    name: Optional[str]
    overall_score: float
    recommendation: str
    valuation: Dict[str, Any]
    growth: Dict[str, Any]
    profitability: Dict[str, Any]
    health: Dict[str, Any]
    analysis_time: str


class ScreenRequest(BaseModel):
    # 估值条件
    pe_min: Optional[float] = None
    pe_max: Optional[float] = None
    pb_min: Optional[float] = None
    pb_max: Optional[float] = None

    # 盈利能力
    roe_min: Optional[float] = None
    roa_min: Optional[float] = None
    gross_margin_min: Optional[float] = None

    # 成长性
    revenue_growth_min: Optional[float] = None
    profit_growth_min: Optional[float] = None

    # 市值
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None

    # 行业
    industries: Optional[List[str]] = None

    # 排序
    sort_by: Optional[str] = "score"
    sort_order: Optional[str] = "desc"

    # 分页
    limit: Optional[int] = 50
    offset: Optional[int] = 0


class ScreenResponse(BaseModel):
    total_count: int
    filtered_count: int
    execution_time_ms: float
    stocks: List[Dict[str, Any]]


class MultiFactorRequest(BaseModel):
    stocks: List[Dict[str, Any]]
    model_type: Optional[str] = "balanced"  # value, growth, quality, balanced


class MultiFactorResponse(BaseModel):
    results: List[Dict[str, Any]]
    model_type: str
    analysis_time: str


# ============ API 端点 ============

@router.post("/fundamental", response_model=FundamentalResponse)
async def analyze_fundamental(request: FundamentalRequest):
    """
    基本面分析

    请求体:
    {
        "code": "600519.SH",
        "name": "贵州茅台",
        "metrics": {
            "pe_ttm": 28.5,
            "pb": 8.2,
            "roe": 0.25,
            "revenue_growth": 0.15,
            ...
        }
    }
    """
    try:
        # 构建财务指标
        if request.metrics:
            metrics = FinancialMetrics(**request.metrics)
        else:
            # 使用默认指标进行演示
            metrics = _get_demo_metrics(request.code)

        # 执行分析
        report = fundamental_analyzer.analyze(
            symbol=request.code,
            metrics=metrics,
            name=request.name
        )

        return FundamentalResponse(
            symbol=report.symbol,
            name=report.name,
            overall_score=report.overall_score,
            recommendation=report.investment_recommendation,
            valuation={
                "grade": report.valuation.valuation_grade,
                "is_undervalued": report.valuation.is_undervalued,
                "is_overvalued": report.valuation.is_overvalued,
                "upside_potential": report.valuation.upside_potential
            },
            growth={
                "grade": report.growth.growth_grade,
                "is_high_growth": report.growth.is_high_growth,
                "revenue_assessment": report.growth.revenue_growth_assessment
            },
            profitability={
                "grade": report.profitability.profitability_grade,
                "is_high_quality": report.profitability.is_high_quality
            },
            health={
                "grade": report.health.overall_grade.value,
                "red_flags": report.health.red_flags[:3] if report.health.red_flags else [],
                "strengths": report.health.strengths[:3] if report.health.strengths else []
            },
            analysis_time=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"基本面分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fundamental/batch")
async def batch_analyze_fundamental(request: Dict[str, Any]):
    """批量基本面分析"""
    try:
        codes = request.get('codes', [])
        stocks_data = request.get('stocks_data', [])

        if not stocks_data and codes:
            # 为演示生成模拟数据
            stocks_data = [_get_demo_stock_data(code) for code in codes]

        reports = batch_analyzer.analyze_batch(stocks_data)

        return {
            "results": [
                {
                    "symbol": r.symbol,
                    "name": r.name,
                    "score": r.overall_score,
                    "recommendation": r.investment_recommendation,
                    "valuation_grade": r.valuation.valuation_grade,
                    "growth_grade": r.growth.growth_grade
                }
                for r in reports
            ],
            "analysis_time": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screen", response_model=ScreenResponse)
async def screen_stocks(request: ScreenRequest):
    """
    智能选股

    支持多条件组合筛选
    """
    try:
        import time
        start_time = time.time()

        # 构建筛选器
        screener = StockScreener()

        # 估值条件
        if request.pe_min is not None or request.pe_max is not None:
            screener.pe_ratio(request.pe_min, request.pe_max)
        if request.pb_min is not None or request.pb_max is not None:
            screener.pb_ratio(request.pb_min, request.pb_max)

        # 盈利能力
        if request.roe_min is not None:
            screener.roe(request.roe_min)
        if request.roa_min is not None:
            screener.roa(request.roa_min)

        # 成长性
        if request.revenue_growth_min is not None:
            screener.revenue_growth(request.revenue_growth_min)
        if request.profit_growth_min is not None:
            screener.profit_growth(request.profit_growth_min)

        # 市值
        if request.market_cap_min is not None or request.market_cap_max is not None:
            min_cap = Decimal(str(request.market_cap_min * 100000000)) if request.market_cap_min else None
            max_cap = Decimal(str(request.market_cap_max * 100000000)) if request.market_cap_max else None
            screener.market_cap(min_cap, max_cap)

        # 行业
        if request.industries:
            screener.industry(request.industries)

        # 排序
        if request.sort_by:
            from src.intelligence.screening.screener import SortOrder
            order = SortOrder.DESC if request.sort_order == "desc" else SortOrder.ASC
            screener.order_by(request.sort_by, order)

        # 限制数量
        screener.limit(request.limit)
        screener.offset(request.offset)

        # 执行筛选（使用演示数据）
        demo_pool = _get_demo_stock_pool()
        result = await screener.execute(demo_pool)

        execution_time = (time.time() - start_time) * 1000

        return ScreenResponse(
            total_count=result.total_count,
            filtered_count=result.filtered_count,
            execution_time_ms=execution_time,
            stocks=result.to_dict()["stocks"]
        )

    except Exception as e:
        logger.error(f"选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screen/presets/{preset_name}")
async def preset_screening(
    preset_name: str,
    limit: int = Query(default=50, le=100)
):
    """
    预设选股策略

    - low_pe: 低PE价值股
    - high_roe: 高ROE优质股
    - small_cap_growth: 小盘成长股
    - blue_chip_dividend: 蓝筹红利股
    """
    try:
        demo_pool = _get_demo_stock_pool()

        if preset_name == "low_pe":
            screener = PresetScreeners.low_pe()
        elif preset_name == "high_roe":
            screener = PresetScreeners.high_roe()
        elif preset_name == "small_cap_growth":
            screener = PresetScreeners.small_cap_growth()
        elif preset_name == "blue_chip_dividend":
            screener = PresetScreeners.blue_chip_dividend()
        else:
            raise HTTPException(status_code=400, detail=f"未知的预设策略: {preset_name}")

        screener.limit(limit)
        result = await screener.execute(demo_pool)

        return {
            "preset": preset_name,
            "count": result.filtered_count,
            "stocks": result.to_dict()["stocks"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预设选股失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multifactor", response_model=MultiFactorResponse)
async def multifactor_score(request: MultiFactorRequest):
    """
    多因子评分

    使用多因子模型对股票进行评分排名
    """
    try:
        # 选择模型
        model_map = {
            "value": FactorBuilder.value_model,
            "growth": FactorBuilder.growth_model,
            "quality": FactorBuilder.quality_model,
            "balanced": FactorBuilder.balanced_model
        }

        model_factory = model_map.get(request.model_type, FactorBuilder.balanced_model)
        model = model_factory()

        # 执行评分
        results = model.score(request.stocks)

        return MultiFactorResponse(
            results=[r.to_dict() for r in results],
            model_type=request.model_type,
            analysis_time=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"多因子评分失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro")
async def get_macro_analysis():
    """宏观分析（保持原有实现）"""
    return {
        "economic_cycle": {
            "cycle": "expansion",
            "confidence": 0.75,
            "key_indicators": {
                "gdp_growth": "5.2%",
                "cpi": "2.1%",
                "ppi": "-1.5%",
                "pmi": "50.8"
            },
            "implications": "经济处于扩张期，利好权益资产"
        },
        "policy_direction": {
            "monetary_policy": "neutral",
            "key_rates": {
                "mlf": "2.5%",
                "lpr_1y": "3.45%",
                "lpr_5y": "4.2%"
            },
            "market_impact": "货币政策保持中性，市场流动性合理充裕"
        },
        "analysis_time": datetime.now().isoformat()
    }


@router.post("/industry")
async def analyze_industry(request: dict):
    """行业分析（保持原有实现）"""
    industry_name = request.get('industry_name', '未指定行业')
    report_type = request.get('report_type', '深度研究')

    return {
        "industry_name": industry_name,
        "report_type": report_type,
        "title": f"{industry_name}行业{report_type}报告",
        "summary": "行业处于快速发展期，市场需求旺盛，技术创新活跃...",
        "key_points": [
            "市场规模持续扩大",
            "龙头企业优势明显",
            "技术迭代加速"
        ],
        "recommendations": ["关注龙头企业", "布局产业链上游"],
        "analysis_time": datetime.now().isoformat()
    }


# ============ 辅助函数 ============

def _get_demo_metrics(symbol: str) -> FinancialMetrics:
    """获取演示用的财务指标"""
    # 根据代码返回不同的演示数据
    demo_data = {
        "600519.SH": {  # 贵州茅台
            "pe_ttm": 28.5,
            "pb": 8.2,
            "roe": 0.25,
            "roa": 0.18,
            "gross_margin": 0.915,
            "net_margin": 0.525,
            "revenue_growth": 0.15,
            "profit_growth": 0.18,
            "debt_to_equity": 0.195,
            "current_ratio": 2.5,
            "dividend_yield": 0.015
        },
        "000858.SZ": {  # 五粮液
            "pe_ttm": 18.2,
            "pb": 4.5,
            "roe": 0.22,
            "roa": 0.16,
            "gross_margin": 0.75,
            "net_margin": 0.38,
            "revenue_growth": 0.12,
            "profit_growth": 0.15,
            "debt_to_equity": 0.15,
            "current_ratio": 2.8,
            "dividend_yield": 0.025
        }
    }

    metrics = demo_data.get(symbol, {
        "pe_ttm": 20.0,
        "pb": 3.0,
        "roe": 0.15,
        "revenue_growth": 0.10,
        "profit_growth": 0.12
    })

    return FinancialMetrics(**metrics)


def _get_demo_stock_data(symbol: str) -> Dict[str, Any]:
    """获取演示用的股票数据"""
    metrics = _get_demo_metrics(symbol)
    return {
        "symbol": symbol,
        "name": "演示股票",
        **{k: v for k, v in metrics.__dict__.items() if v is not None}
    }


def _get_demo_stock_pool() -> List[StockData]:
    """获取演示用的股票池"""
    demo_stocks = [
        {"symbol": "600519.SH", "name": "贵州茅台", "industry": "白酒", "pe_ttm": 28.5, "pb": 8.2, "roe": 0.25, "market_cap": Decimal("2500000000000"), "revenue_growth": 0.15, "profit_growth": 0.18},
        {"symbol": "000858.SZ", "name": "五粮液", "industry": "白酒", "pe_ttm": 18.2, "pb": 4.5, "roe": 0.22, "market_cap": Decimal("600000000000"), "revenue_growth": 0.12, "profit_growth": 0.15},
        {"symbol": "002371.SZ", "name": "北方华创", "industry": "半导体", "pe_ttm": 45.2, "pb": 8.5, "roe": 0.18, "market_cap": Decimal("180000000000"), "revenue_growth": 0.35, "profit_growth": 0.42},
        {"symbol": "300760.SZ", "name": "迈瑞医疗", "industry": "医疗器械", "pe_ttm": 32.1, "pb": 8.5, "roe": 0.28, "market_cap": Decimal("380000000000"), "revenue_growth": 0.22, "profit_growth": 0.25},
        {"symbol": "600900.SH", "name": "长江电力", "industry": "电力", "pe_ttm": 18.2, "pb": 2.1, "roe": 0.14, "market_cap": Decimal("520000000000"), "revenue_growth": 0.05, "profit_growth": 0.06, "dividend_yield": 0.04},
        {"symbol": "000333.SZ", "name": "美的集团", "industry": "家电", "pe_ttm": 12.5, "pb": 2.8, "roe": 0.22, "market_cap": Decimal("420000000000"), "revenue_growth": 0.08, "profit_growth": 0.10, "dividend_yield": 0.035},
        {"symbol": "002594.SZ", "name": "比亚迪", "industry": "汽车", "pe_ttm": 35.2, "pb": 5.8, "roe": 0.17, "market_cap": Decimal("680000000000"), "revenue_growth": 0.28, "profit_growth": 0.32},
        {"symbol": "601012.SH", "name": "隆基绿能", "industry": "光伏", "pe_ttm": 15.8, "pb": 2.5, "roe": 0.20, "market_cap": Decimal("210000000000"), "revenue_growth": 0.25, "profit_growth": 0.28, "dividend_yield": 0.02},
        {"symbol": "300750.SZ", "name": "宁德时代", "industry": "电池", "pe_ttm": 25.5, "pb": 6.2, "roe": 0.21, "market_cap": Decimal("850000000000"), "revenue_growth": 0.30, "profit_growth": 0.35},
        {"symbol": "601318.SH", "name": "中国平安", "industry": "保险", "pe_ttm": 8.5, "pb": 0.9, "roe": 0.16, "market_cap": Decimal("800000000000"), "revenue_growth": 0.02, "profit_growth": 0.03, "dividend_yield": 0.05},
    ]

    return [StockData(**stock) for stock in demo_stocks]
