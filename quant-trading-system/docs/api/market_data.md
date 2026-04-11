# 市场数据 API

## 概述

提供实时行情、历史数据、股票信息等市场数据服务。

## 接口列表

### 1. 获取实时行情

获取指定股票的最新行情数据。

**请求**

```http
GET /market/realtime/{symbol}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码，如 000001.SZ |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "000001.SZ",
    "name": "平安银行",
    "price": 10.52,
    "open": 10.35,
    "high": 10.68,
    "low": 10.28,
    "close": 10.48,
    "change": 0.04,
    "change_pct": 0.38,
    "volume": 1520341,
    "amount": 15843200.52,
    "bid": [
      {"price": 10.51, "volume": 5200},
      {"price": 10.50, "volume": 8300}
    ],
    "ask": [
      {"price": 10.53, "volume": 4100},
      {"price": 10.54, "volume": 6200}
    ],
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 2. 批量获取行情

批量获取多只股票实时行情。

**请求**

```http
POST /market/realtime/batch
```

**请求体**

```json
{
  "symbols": ["000001.SZ", "600519.SH", "300750.SZ"]
}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbols | array | 是 | 股票代码列表，最多50个 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "count": 3,
    "quotes": [
      {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "price": 10.52,
        "change_pct": 0.38
      },
      {
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "price": 1725.00,
        "change_pct": 1.25
      }
    ]
  }
}
```

### 3. 获取K线数据

获取历史K线数据。

**请求**

```http
GET /market/kline/{symbol}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| period | string | 否 | 周期：1m, 5m, 15m, 30m, 60m, 1d, 1w, 1M，默认1d |
| start_date | string | 否 | 开始日期，格式：YYYY-MM-DD |
| end_date | string | 否 | 结束日期，格式：YYYY-MM-DD |
| limit | integer | 否 | 返回条数，默认100，最大1000 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "000001.SZ",
    "period": "1d",
    "count": 100,
    "klines": [
      {
        "timestamp": "2024-01-15T00:00:00Z",
        "open": 10.35,
        "high": 10.68,
        "low": 10.28,
        "close": 10.48,
        "volume": 1520341,
        "amount": 15843200.52
      }
    ]
  }
}
```

### 4. 获取分时数据

获取当日分时数据。

**请求**

```http
GET /market/intraday/{symbol}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| date | string | 否 | 日期，默认当日 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "000001.SZ",
    "date": "2024-01-15",
    "pre_close": 10.44,
    "ticks": [
      {
        "time": "09:30",
        "price": 10.35,
        "volume": 12500,
        "avg_price": 10.38
      }
    ]
  }
}
```

### 5. 搜索股票

根据关键词搜索股票。

**请求**

```http
GET /market/search
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| keyword | string | 是 | 搜索关键词（代码或名称） |
| limit | integer | 否 | 返回数量，默认20 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "count": 3,
    "results": [
      {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "exchange": "SZSE",
        "industry": "银行"
      },
      {
        "symbol": "600000.SH",
        "name": "浦发银行",
        "exchange": "SSE",
        "industry": "银行"
      }
    ]
  }
}
```

### 6. 获取股票列表

获取全市场股票列表。

**请求**

```http
GET /market/stocks
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| exchange | string | 否 | 交易所：SSE, SZSE, BSE |
| industry | string | 否 | 行业分类 |
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认100 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 5200,
    "page": 1,
    "page_size": 100,
    "stocks": [
      {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "exchange": "SZSE",
        "industry": "银行",
        "market_cap": 200000000000
      }
    ]
  }
}
```

### 7. 获取财务数据

获取股票财务数据。

**请求**

```http
GET /market/finance/{symbol}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| report_type | string | 否 | 报告类型：annual, quarter，默认quarter |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "000001.SZ",
    "report_date": "2023-09-30",
    "report_type": "quarter",
    "eps": 2.45,
    "bvps": 18.52,
    "roe": 12.5,
    "revenue": 12760000000,
    "net_profit": 3960000000,
    "total_assets": 520000000000,
    "total_liabilities": 480000000000
  }
}
```

### 8. WebSocket 实时行情

建立WebSocket连接接收实时行情推送。

**连接地址**

```
wss://api.example.com/ws/market
```

**订阅消息**

```json
{
  "action": "subscribe",
  "symbols": ["000001.SZ", "600519.SH"],
  "fields": ["price", "volume", "bid", "ask"]
}
```

**推送消息格式**

```json
{
  "type": "quote",
  "data": {
    "symbol": "000001.SZ",
    "price": 10.52,
    "change_pct": 0.38,
    "timestamp": "2024-01-15T10:30:00.123Z"
  }
}
```

## 数据字典

### 周期类型 (Period)

| 值 | 说明 |
|----|------|
| 1m | 1分钟 |
| 5m | 5分钟 |
| 15m | 15分钟 |
| 30m | 30分钟 |
| 60m | 60分钟 |
| 1d | 日线 |
| 1w | 周线 |
| 1M | 月线 |

### 交易所 (Exchange)

| 值 | 说明 |
|----|------|
| SSE | 上海证券交易所 |
| SZSE | 深圳证券交易所 |
| BSE | 北京证券交易所 |
| HKEX | 香港交易所 |
| NASDAQ | 纳斯达克 |
| NYSE | 纽约证券交易所 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| 400001 | 股票代码不存在 |
| 400002 | 日期格式错误 |
| 400003 | 周期类型不支持 |
| 429001 | 请求频率超限 |
