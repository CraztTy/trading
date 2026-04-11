# 智能选股 API

## 概述

提供股票筛选、多因子评分、基本面分析等智能选股功能。

## 接口列表

### 1. 筛选股票

根据多维度条件筛选股票。

**请求**

```http
POST /screening/stocks
```

**请求体**

```json
{
  "filters": [
    {
      "field": "pe_ttm",
      "operator": "lte",
      "value": 20
    },
    {
      "field": "roe",
      "operator": "gte",
      "value": 0.15
    },
    {
      "field": "market_cap",
      "operator": "gte",
      "value": 10000000000
    }
  ],
  "sort": {
    "field": "roe",
    "order": "desc"
  },
  "limit": 50
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| filters | array | 否 | 筛选条件列表 |
| filters[].field | string | 是 | 筛选字段 |
| filters[].operator | string | 是 | 操作符：eq/ne/gt/gte/lt/lte/between/in |
| filters[].value | any | 是 | 筛选值 |
| sort | object | 否 | 排序配置 |
| limit | integer | 否 | 返回数量限制 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total_count": 5200,
    "filtered_count": 23,
    "execution_time_ms": 45.2,
    "stocks": [
      {
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "industry": "白酒",
        "price": 1725.00,
        "pe_ttm": 35.0,
        "pb": 8.5,
        "roe": 0.25,
        "market_cap": 2100000000000
      },
      {
        "symbol": "000858.SZ",
        "name": "五粮液",
        "industry": "白酒",
        "price": 150.00,
        "pe_ttm": 25.0,
        "pb": 5.0,
        "roe": 0.20,
        "market_cap": 580000000000
      }
    ]
  }
}
```

### 2. 使用预设筛选器

使用预设的筛选策略。

**请求**

```http
POST /screening/presets/{preset_name}
```

**预设名称**

| 预设名 | 说明 |
|--------|------|
| value_stocks | 价值股 |
| growth_stocks | 成长股 |
| dividend_stocks | 红利股 |
| blue_chip | 蓝筹股 |
| small_cap_growth | 小盘成长股 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "preset": "value_stocks",
    "criteria": [
      "PE < 15",
      "PB < 2",
      "ROE > 10%"
    ],
    "stocks": [
      {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "pe_ttm": 5.5,
        "pb": 0.8,
        "roe": 0.12
      }
    ]
  }
}
```

### 3. 多因子评分

对股票列表进行多因子评分。

**请求**

```http
POST /screening/score
```

**请求体**

```json
{
  "symbols": ["000001.SZ", "600519.SH", "300750.SZ"],
  "model": "balanced",
  "factors": {
    "value": 0.25,
    "quality": 0.25,
    "growth": 0.25,
    "risk": 0.25
  }
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbols | array | 是 | 股票代码列表 |
| model | string | 否 | 模型：value/growth/quality/balanced |
| factors | object | 否 | 因子权重配置 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "model": "balanced",
    "count": 3,
    "results": [
      {
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "value_score": 85.5,
        "quality_score": 98.2,
        "growth_score": 88.0,
        "momentum_score": 75.5,
        "risk_score": 82.0,
        "total_score": 88.2,
        "rank": 1,
        "percentile": 95.0,
        "factor_scores": {
          "pe_ttm": {"raw": 35.0, "score": 45.5, "weight": 1.0},
          "roe": {"raw": 0.25, "score": 98.2, "weight": 1.5}
        }
      },
      {
        "symbol": "300750.SZ",
        "name": "宁德时代",
        "total_score": 82.5,
        "rank": 2,
        "percentile": 85.0
      }
    ]
  }
}
```

### 4. 基本面分析

对股票进行基本面分析。

**请求**

```http
POST /fundamental/analyze
```

**请求体**

```json
{
  "symbol": "600519.SH",
  "metrics": {
    "pe_ttm": 35.0,
    "pb": 8.5,
    "roe": 0.25,
    "revenue_growth": 0.15,
    "profit_growth": 0.18,
    "debt_to_equity": 0.25,
    "current_ratio": 2.5
  }
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "600519.SH",
    "name": "贵州茅台",
    "report_date": "2024-01-15",
    "overall_score": 92.5,
    "recommendation": "BUY",
    "valuation": {
      "grade": "B",
      "is_undervalued": false,
      "is_overvalued": true,
      "pe_assessment": "合理偏高",
      "upside_potential": -5.2
    },
    "growth": {
      "grade": "A",
      "is_high_growth": true,
      "revenue_growth_assessment": "稳健增长"
    },
    "profitability": {
      "grade": "A",
      "is_high_quality": true,
      "roe_sustainability": "优秀"
    },
    "health": {
      "grade": "A",
      "liquidity_assessment": "非常健康",
      "solvency_assessment": "健康",
      "strengths": ["资产负债率低", "流动比率高"],
      "red_flags": []
    }
  }
}
```

### 5. 批量基本面分析

批量分析多只股票的基本面。

**请求**

```http
POST /fundamental/analyze-batch
```

**请求体**

```json
{
  "stocks": [
    {
      "symbol": "600519.SH",
      "pe_ttm": 35.0,
      "pb": 8.5,
      "roe": 0.25
    },
    {
      "symbol": "000001.SZ",
      "pe_ttm": 5.5,
      "pb": 0.8,
      "roe": 0.12
    }
  ]
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "count": 2,
    "results": [
      {
        "symbol": "600519.SH",
        "overall_score": 92.5,
        "rank": 1
      },
      {
        "symbol": "000001.SZ",
        "overall_score": 78.0,
        "rank": 2
      }
    ]
  }
}
```

### 6. 寻找低估股票

基于基本面寻找低估股票。

**请求**

```http
GET /fundamental/undervalued
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| min_score | float | 否 | 最低评分，默认70 |
| limit | integer | 否 | 返回数量，默认20 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "criteria": "valuation_score >= 70",
    "count": 15,
    "stocks": [
      {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "overall_score": 82.5,
        "valuation_grade": "A",
        "upside_potential": 25.5
      }
    ]
  }
}
```

### 7. 获取财务数据

获取股票详细财务数据。

**请求**

```http
GET /fundamental/financial/{symbol}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| period | string | 否 | 报告期：annual/quarter |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "600519.SH",
    "report_date": "2023-09-30",
    "valuation": {
      "pe_ttm": 35.0,
      "pb": 8.5,
      "ps": 15.2,
      "dividend_yield": 0.015
    },
    "profitability": {
      "roe": 0.25,
      "roa": 0.18,
      "gross_margin": 0.92,
      "net_margin": 0.52
    },
    "growth": {
      "revenue_growth": 0.15,
      "profit_growth": 0.18,
      "roe_growth": 0.05
    },
    "health": {
      "current_ratio": 2.5,
      "quick_ratio": 2.2,
      "debt_to_equity": 0.25,
      "interest_coverage": 25.0
    }
  }
}
```

### 8. 行业对比

对比同行业股票。

**请求**

```http
GET /fundamental/industry-comparison
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| peers_count | integer | 否 | 对比同业数量，默认5 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "600519.SH",
    "industry": "白酒",
    "peer_average": {
      "pe_ttm": 28.5,
      "roe": 0.18,
      "revenue_growth": 0.12
    },
    "comparison": {
      "pe_ttm": {"value": 35.0, "percentile": 85, "vs_peer": "+22.8%"},
      "roe": {"value": 0.25, "percentile": 95, "vs_peer": "+38.9%"},
      "revenue_growth": {"value": 0.15, "percentile": 75, "vs_peer": "+25.0%"}
    },
    "rank_in_industry": 1
  }
}
```

### 9. 获取推荐股票

获取AI推荐的股票列表。

**请求**

```http
GET /screening/recommendations
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 否 | 推荐类型：value/growth/dividend/quality |
| limit | integer | 否 | 返回数量，默认10 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "type": "value",
    "updated_at": "2024-01-15T10:30:00Z",
    "recommendations": [
      {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "reason": "低估值+高股息",
        "score": 92.0,
        "key_metrics": {
          "pe_ttm": 5.5,
          "pb": 0.8,
          "dividend_yield": 0.045
        }
      }
    ]
  }
}
```

### 10. 计算因子暴露

计算股票组合的因子暴露。

**请求**

```http
POST /screening/factor-exposure
```

**请求体**

```json
{
  "portfolio": [
    {"symbol": "600519.SH", "weight": 0.4},
    {"symbol": "000001.SZ", "weight": 0.3},
    {"symbol": "300750.SZ", "weight": 0.3}
  ]
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "portfolio_exposure": {
      "value": 0.35,
      "growth": 0.55,
      "quality": 0.75,
      "momentum": 0.45,
      "risk": 0.25
    },
    "factor_correlation": {
      "value_growth": -0.35,
      "quality_risk": -0.42
    },
    "risk_concentration": "MEDIUM"
  }
}
```

## 筛选字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | string | 股票代码 |
| name | string | 股票名称 |
| industry | string | 行业 |
| price | decimal | 当前价格 |
| pe_ttm | float | 市盈率TTM |
| pb | float | 市净率 |
| ps | float | 市销率 |
| roe | float | 净资产收益率 |
| roa | float | 总资产收益率 |
| revenue_growth | float | 营收增长率 |
| profit_growth | float | 利润增长率 |
| market_cap | decimal | 市值 |
| dividend_yield | float | 股息率 |
| volatility | float | 波动率 |
| beta | float | Beta系数 |

## 操作建议

| 建议 | 说明 |
|------|------|
| STRONG_BUY | 强烈推荐买入 |
| BUY | 建议买入 |
| HOLD | 持有 |
| REDUCE | 建议减仓 |
| SELL | 建议卖出 |

## 评级说明

| 评级 | 分数范围 | 说明 |
|------|----------|------|
| A | 90-100 | 优秀 |
| B | 80-89 | 良好 |
| C | 60-79 | 一般 |
| D | 40-59 | 较差 |
| F | 0-39 | 差 |
