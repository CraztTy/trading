# 订单执行 API

## 概述

提供订单管理、交易执行、订单查询等功能。

## 接口列表

### 1. 下单

提交新的交易订单。

**请求**

```http
POST /orders
```

**请求体**

```json
{
  "symbol": "000001.SZ",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": 1000,
  "price": 10.50,
  "strategy_id": "strategy_001",
  "algorithm": "TWAP",
  "algo_params": {
    "duration": 300,
    "participation_rate": 0.1
  }
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| side | string | 是 | 买卖方向：BUY/SELL |
| type | string | 是 | 订单类型：LIMIT/MARKET/STOP |
| quantity | integer | 是 | 委托数量 |
| price | decimal | 条件 | 限价单价格 |
| stop_price | decimal | 条件 | 止损单价格 |
| strategy_id | string | 否 | 策略ID |
| algorithm | string | 否 | 执行算法：TWAP/VWAP/POV |
| algo_params | object | 否 | 算法参数 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "order_id": "ORD20240115093001001",
    "status": "PENDING",
    "symbol": "000001.SZ",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": 1000,
    "price": 10.50,
    "filled_quantity": 0,
    "filled_amount": 0,
    "avg_price": 0,
    "created_at": "2024-01-15T09:30:01Z"
  }
}
```

### 2. 撤单

撤销未成交的订单。

**请求**

```http
DELETE /orders/{order_id}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_id | string | 是 | 订单ID |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "order_id": "ORD20240115093001001",
    "status": "CANCELLED",
    "cancelled_at": "2024-01-15T09:35:20Z"
  }
}
```

### 3. 批量撤单

批量撤销多个订单。

**请求**

```http
POST /orders/batch/cancel
```

**请求体**

```json
{
  "order_ids": ["ORD001", "ORD002", "ORD003"]
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 3,
    "cancelled": 3,
    "failed": 0,
    "results": [
      {
        "order_id": "ORD001",
        "status": "CANCELLED"
      }
    ]
  }
}
```

### 4. 查询订单

查询单个订单详情。

**请求**

```http
GET /orders/{order_id}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "order_id": "ORD20240115093001001",
    "status": "FILLED",
    "symbol": "000001.SZ",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": 1000,
    "price": 10.50,
    "filled_quantity": 1000,
    "filled_amount": 10500.00,
    "avg_price": 10.50,
    "commission": 10.50,
    "stamp_tax": 0,
    "trades": [
      {
        "trade_id": "T20240115093001001",
        "quantity": 500,
        "price": 10.50,
        "amount": 5250.00,
        "time": "09:30:15"
      },
      {
        "trade_id": "T20240115093001002",
        "quantity": 500,
        "price": 10.50,
        "amount": 5250.00,
        "time": "09:30:45"
      }
    ],
    "created_at": "2024-01-15T09:30:01Z",
    "updated_at": "2024-01-15T09:30:45Z"
  }
}
```

### 5. 查询订单列表

查询历史订单列表。

**请求**

```http
GET /orders
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 否 | 股票代码 |
| status | string | 否 | 订单状态 |
| side | string | 否 | 买卖方向 |
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
    "total": 156,
    "page": 1,
    "page_size": 20,
    "orders": [
      {
        "order_id": "ORD20240115093001001",
        "symbol": "000001.SZ",
        "side": "BUY",
        "status": "FILLED",
        "quantity": 1000,
        "filled_quantity": 1000,
        "avg_price": 10.50,
        "created_at": "2024-01-15T09:30:01Z"
      }
    ]
  }
}
```

### 6. 修改订单

修改未成交订单的价格或数量。

**请求**

```http
PATCH /orders/{order_id}
```

**请求体**

```json
{
  "price": 10.48,
  "quantity": 2000
}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| price | decimal | 否 | 新价格 |
| quantity | integer | 否 | 新数量（必须≥已成交量） |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "order_id": "ORD20240115093001001",
    "status": "PENDING",
    "price": 10.48,
    "quantity": 2000,
    "updated_at": "2024-01-15T09:31:00Z"
  }
}
```

### 7. 查询成交明细

查询订单的成交明细。

**请求**

```http
GET /orders/{order_id}/trades
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "order_id": "ORD20240115093001001",
    "total_trades": 5,
    "trades": [
      {
        "trade_id": "T001",
        "quantity": 200,
        "price": 10.50,
        "amount": 2100.00,
        "commission": 2.10,
        "trade_time": "2024-01-15T09:30:15Z"
      }
    ]
  }
}
```

### 8. 获取订单簿

获取实时订单簿数据。

**请求**

```http
GET /orderbook/{symbol}
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| depth | integer | 否 | 深度，默认5，最大10 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "symbol": "000001.SZ",
    "timestamp": "2024-01-15T09:30:00Z",
    "bids": [
      {"price": 10.51, "volume": 5200},
      {"price": 10.50, "volume": 8300},
      {"price": 10.49, "volume": 12000},
      {"price": 10.48, "volume": 6500},
      {"price": 10.47, "volume": 9800}
    ],
    "asks": [
      {"price": 10.53, "volume": 4100},
      {"price": 10.54, "volume": 6200},
      {"price": 10.55, "volume": 8900},
      {"price": 10.56, "volume": 4500},
      {"price": 10.57, "volume": 7200}
    ]
  }
}
```

## 订单状态

| 状态 | 说明 |
|------|------|
| PENDING | 待报（已接收） |
| SUBMITTED | 已提交到交易所 |
| PARTIAL_FILLED | 部分成交 |
| FILLED | 全部成交 |
| CANCELLED | 已撤单 |
| REJECTED | 被拒绝 |
| EXPIRED | 已过期 |

## 订单类型

| 类型 | 说明 |
|------|------|
| MARKET | 市价单 |
| LIMIT | 限价单 |
| STOP | 止损单 |
| STOP_LIMIT | 止损限价单 |
| ICEBERG | 冰山单 |
| TWAP | 时间加权平均价单 |
| VWAP | 成交量加权平均价单 |

## 执行算法

| 算法 | 说明 |
|------|------|
| TWAP | 时间加权平均价格 |
| VWAP | 成交量加权平均价格 |
| POV | 参与率算法 |
| Implementation Shortfall | 执行缺口算法 |

## 错误码

| 错误码 | 说明 |
|--------|------|
| 400101 | 订单参数无效 |
| 400102 | 价格超出涨跌停限制 |
| 400103 | 资金不足 |
| 400104 | 持仓不足 |
| 400105 | 订单已成交或已撤销 |
| 400106 | 交易时间不允许 |
| 400107 | 该股票禁止交易 |
| 400108 | 订单数量超出限制 |
