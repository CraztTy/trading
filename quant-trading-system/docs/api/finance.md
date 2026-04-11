# 资金管理 API

## 概述

提供账户管理、持仓查询、资金流水等功能。

## 接口列表

### 1. 获取账户信息

获取当前账户的基本信息。

**请求**

```http
GET /account
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "account_id": "ACC001",
    "account_name": "主账户",
    "account_type": "stock",
    "status": "active",
    "currency": "CNY",
    "total_assets": 1245890.52,
    "available_cash": 345200.00,
    "market_value": 900690.52,
    "frozen_amount": 10000.00,
    "initial_capital": 1000000.00,
    "total_pnl": 245890.52,
    "total_pnl_pct": 0.2459,
    "created_at": "2023-01-01T00:00:00Z"
  }
}
```

### 2. 获取持仓列表

获取当前所有持仓。

**请求**

```http
GET /positions
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 否 | 筛选特定股票 |
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认50 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 8,
    "positions": [
      {
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "quantity": 100,
        "available_quantity": 100,
        "frozen_quantity": 0,
        "avg_cost": 1650.00,
        "current_price": 1725.00,
        "market_value": 172500.00,
        "unrealized_pnl": 7500.00,
        "unrealized_pnl_pct": 0.0455,
        "weight": 0.138,
        "updated_at": "2024-01-15T10:30:00Z"
      },
      {
        "symbol": "300750.SZ",
        "name": "宁德时代",
        "quantity": 500,
        "available_quantity": 0,
        "frozen_quantity": 500,
        "avg_cost": 195.00,
        "current_price": 200.00,
        "market_value": 100000.00,
        "unrealized_pnl": 2500.00,
        "unrealized_pnl_pct": 0.0256,
        "weight": 0.080,
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "summary": {
      "total_market_value": 900690.52,
      "total_unrealized_pnl": 52680.00,
      "total_unrealized_pnl_pct": 0.0624,
      "position_count": 8
    }
  }
}
```

### 3. 获取单个持仓

获取指定股票的持仓详情。

**请求**

```http
GET /positions/{symbol}
```

### 4. 获取资金流水

查询资金变动记录。

**请求**

```http
GET /capital/flows
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 否 | 类型：deposit/withdraw/trade/fee/dividend |
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
    "flows": [
      {
        "flow_id": "FLW001",
        "type": "trade",
        "amount": -10500.00,
        "balance": 345200.00,
        "description": "买入 000001.SZ 1000股",
        "related_order": "ORD001",
        "created_at": "2024-01-15T09:30:01Z"
      },
      {
        "flow_id": "FLW002",
        "type": "fee",
        "amount": -10.50,
        "balance": 345189.50,
        "description": "交易佣金",
        "related_order": "ORD001",
        "created_at": "2024-01-15T09:30:01Z"
      }
    ]
  }
}
```

### 5. 获取每日结算

获取每日结算数据。

**请求**

```http
GET /settlements
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "settlements": [
      {
        "date": "2024-01-15",
        "begin_balance": 345000.00,
        "end_balance": 345200.00,
        "realized_pnl": 200.00,
        "unrealized_pnl": 52680.00,
        "commission": 52.50,
        "stamp_tax": 105.00,
        "transfer_fee": 2.00,
        "dividend": 0,
        "deposit": 0,
        "withdraw": 0,
        "return_pct": 0.0006
      }
    ]
  }
}
```

### 6. 资金划转

在账户间划转资金。

**请求**

```http
POST /capital/transfer
```

**请求体**

```json
{
  "from_account": "ACC001",
  "to_account": "ACC002",
  "amount": 100000.00,
  "remark": "策略资金分配"
}
```

### 7. 获取账户列表

获取所有账户列表。

**请求**

```http
GET /accounts
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "accounts": [
      {
        "account_id": "ACC001",
        "account_name": "主账户",
        "account_type": "stock",
        "total_assets": 1245890.52,
        "available_cash": 345200.00,
        "status": "active"
      },
      {
        "account_id": "ACC002",
        "account_name": "策略账户A",
        "account_type": "stock",
        "total_assets": 500000.00,
        "available_cash": 100000.00,
        "status": "active"
      }
    ]
  }
}
```

### 8. 创建账户

创建新的资金账户。

**请求**

```http
POST /accounts
```

**请求体**

```json
{
  "account_name": "策略账户B",
  "account_type": "stock",
  "initial_capital": 1000000.00,
  "currency": "CNY"
}
```

### 9. 获取资金曲线

获取资金曲线数据。

**请求**

```http
GET /capital/curve
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "points": [
      {
        "date": "2024-01-01",
        "total_assets": 1000000.00,
        "nav": 1.0000
      },
      {
        "date": "2024-01-15",
        "total_assets": 1245890.52,
        "nav": 1.2459
      }
    ],
    "total_return": 0.2459,
    "annual_return": 2.951,
    "max_drawdown": -0.085
  }
}
```

### 10. 调整持仓成本

调整持仓成本价（用于分红除权等）。

**请求**

```http
POST /positions/{symbol}/adjust
```

**请求体**

```json
{
  "adjust_type": "dividend",
  "dividend_amount": 1.50,
  "ex_dividend_date": "2024-01-15"
}
```

## 资金流水类型

| 类型 | 说明 |
|------|------|
| deposit | 入金 |
| withdraw | 出金 |
| trade | 交易 |
| fee | 费用（佣金/印花税） |
| dividend | 分红 |
| interest | 利息 |
| transfer_in | 转入 |
| transfer_out | 转出 |
| adjust | 调整 |
