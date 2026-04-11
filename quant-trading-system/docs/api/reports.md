# 报告系统 API

## 概述

提供交易报告、绩效分析、报告导出等功能。

## 接口列表

### 1. 生成日报告

生成指定日期的交易报告。

**请求**

```http
POST /reports/daily
```

**请求体**

```json
{
  "account_id": 1,
  "report_date": "2024-01-15"
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "report_type": "daily",
    "account_id": 1,
    "report_date": "2024-01-15",
    "trade_count": 12,
    "order_count": 15,
    "filled_order_count": 12,
    "realized_pnl": 5240.00,
    "unrealized_pnl": 15680.00,
    "total_fee": 125.50,
    "total_pnl": 5114.50,
    "win_rate": 0.67,
    "profit_factor": 2.35,
    "begin_balance": 345000.00,
    "end_balance": 350114.50,
    "total_value": 1240114.50
  }
}
```

### 2. 生成周报告

生成指定周的报告。

**请求**

```http
POST /reports/weekly
```

**请求体**

```json
{
  "account_id": 1,
  "year": 2024,
  "week": 3
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "report_type": "weekly",
    "account_id": 1,
    "year": 2024,
    "week": 3,
    "start_date": "2024-01-15",
    "end_date": "2024-01-21",
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "realized_pnl": 25800.00,
    "total_fee": 525.00,
    "net_pnl": 25275.00,
    "weekly_return": 0.025,
    "cumulative_return": 0.245,
    "daily_returns": [
      {
        "date": "2024-01-15",
        "return": 0.015,
        "pnl": 15000.00
      }
    ]
  }
}
```

### 3. 生成月报告

生成指定月份的报告。

**请求**

```http
POST /reports/monthly
```

**请求体**

```json
{
  "account_id": 1,
  "year": 2024,
  "month": 1
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "report_type": "monthly",
    "account_id": 1,
    "year": 2024,
    "month": 1,
    "trading_days": 18,
    "win_days": 12,
    "lose_days": 6,
    "win_rate": 0.67,
    "total_trades": 156,
    "avg_daily_trades": 8.7,
    "realized_pnl": 98500.00,
    "total_fee": 2150.00,
    "net_pnl": 96350.00,
    "monthly_return": 0.095,
    "max_daily_return": 0.035,
    "min_daily_return": -0.018,
    "volatility": 0.185,
    "symbols_traded": ["000001.SZ", "600519.SH", "300750.SZ"]
  }
}
```

### 4. 生成自定义报告

生成自定义时间段的报告。

**请求**

```http
POST /reports/custom
```

**请求体**

```json
{
  "account_id": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-01-15"
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "report_type": "custom",
    "account_id": 1,
    "start_date": "2024-01-01",
    "end_date": "2024-01-15",
    "days": 15,
    "total_trades": 89,
    "total_orders": 102,
    "realized_pnl": 45800.00,
    "total_commission": 980.00,
    "total_tax": 458.00,
    "total_return": 0.0458,
    "annual_return": 1.146,
    "max_drawdown": -0.035,
    "sharpe_ratio": 1.85
  }
}
```

### 5. 获取报告列表

获取历史报告列表。

**请求**

```http
GET /reports
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| report_type | string | 否 | 报告类型：daily/weekly/monthly/custom |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认20 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 45,
    "reports": [
      {
        "report_id": "RPT20240115001",
        "report_type": "daily",
        "report_date": "2024-01-15",
        "total_pnl": 5114.50,
        "created_at": "2024-01-15T15:30:00Z"
      }
    ]
  }
}
```

### 6. 导出报告

导出报告为指定格式。

**请求**

```http
POST /reports/{report_id}/export
```

**请求体**

```json
{
  "format": "pdf",
  "template": "default"
}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| format | string | 是 | 格式：json/csv/html/pdf |
| template | string | 否 | 模板名称 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "download_url": "https://api.example.com/reports/RPT001.pdf",
    "expires_at": "2024-01-16T10:30:00Z"
  }
}
```

### 7. 计算绩效指标

计算指定时间段的交易绩效指标。

**请求**

```http
POST /reports/metrics
```

**请求体**

```json
{
  "account_id": 1,
  "start_date": "2024-01-01",
  "end_date": "2024-01-15"
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "trade_metrics": {
      "total_trades": 89,
      "winning_trades": 56,
      "losing_trades": 33,
      "win_rate": 0.629,
      "total_profit": 75800.00,
      "total_loss": 30000.00,
      "profit_factor": 2.53,
      "avg_profit": 1353.57,
      "avg_loss": -909.09,
      "max_consecutive_wins": 7,
      "max_consecutive_losses": 4
    },
    "performance_metrics": {
      "total_return": 0.0458,
      "annual_return": 1.146,
      "volatility": 0.125,
      "sharpe_ratio": 1.85,
      "sortino_ratio": 2.12,
      "max_drawdown": -0.035,
      "calmar_ratio": 32.74
    },
    "risk_metrics": {
      "var_95": -0.018,
      "cvar_95": -0.025,
      "beta": 0.85,
      "alpha": 0.035
    }
  }
}
```

### 8. 对比报告

对比两个报告周期的数据。

**请求**

```http
POST /reports/compare
```

**请求体**

```json
{
  "report_id_1": "RPT20240114001",
  "report_id_2": "RPT20240115001"
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "date1": "2024-01-14",
    "date2": "2024-01-15",
    "trade_count_change": 2,
    "pnl_change": 1500.00,
    "pnl_change_pct": 0.125,
    "win_rate_change": 0.05,
    "improvement_areas": ["profitability", "activity"],
    "degradation_areas": []
  }
}
```

### 9. 获取交易明细

获取指定时间段的交易明细。

**请求**

```http
GET /reports/trades
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| symbol | string | 否 | 筛选特定股票 |
| page | integer | 否 | 页码 |
| page_size | integer | 否 | 每页数量 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 89,
    "trades": [
      {
        "trade_id": "T20240115001",
        "symbol": "600519.SH",
        "side": "BUY",
        "quantity": 100,
        "entry_price": 1650.00,
        "exit_price": 1725.00,
        "pnl": 7500.00,
        "pnl_pct": 0.0455,
        "entry_time": "2024-01-15T09:35:00Z",
        "exit_time": "2024-01-15T14:20:00Z",
        "holding_period": "4h45m"
      }
    ]
  }
}
```

### 10. 获取图表数据

获取报告图表所需的数据。

**请求**

```http
GET /reports/chart-data
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| metric | string | 是 | 指标：pnl/returns/nav/volatility |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "metric": "pnl",
    "dates": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "values": [1500, 2300, -500, 1800],
    "cumulative": [1500, 3800, 3300, 5100]
  }
}
```

## 报告类型

| 类型 | 说明 | 生成频率 |
|------|------|----------|
| daily | 日报告 | 每日收盘后 |
| weekly | 周报告 | 每周日 |
| monthly | 月报告 | 每月最后一个交易日 |
| yearly | 年报 | 每年年底 |
| custom | 自定义 | 按需生成 |

## 导出格式

| 格式 | 说明 | 适用场景 |
|------|------|----------|
| json | JSON数据 | 程序处理 |
| csv | CSV表格 | Excel分析 |
| html | HTML页面 | 浏览器查看 |
| pdf | PDF文档 | 打印分享 |

## 绩效指标说明

| 指标 | 说明 | 计算方式 |
|------|------|----------|
| win_rate | 胜率 | 盈利次数/总次数 |
| profit_factor | 盈亏比 | 总盈利/总亏损 |
| sharpe_ratio | 夏普比率 | (收益率-无风险利率)/波动率 |
| max_drawdown | 最大回撤 | 最大峰值到谷底跌幅 |
| calmar_ratio | 卡尔马比率 | 年化收益/最大回撤 |
