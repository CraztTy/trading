# 风险控制 API

## 概述

提供仓位管理、止损止盈、风险监控等功能。

## 接口列表

### 1. 获取风控配置

获取当前风控配置。

**请求**

```http
GET /risk/config
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "max_single_stock": 0.10,
    "max_total_position": 0.80,
    "max_industry": 0.30,
    "default_stop_loss": 0.05,
    "default_take_profit": 0.10,
    "enable_stop_loss_monitor": true,
    "enable_position_check": true,
    "check_interval": 1.0
  }
}
```

### 2. 更新风控配置

更新风控配置参数。

**请求**

```http
PUT /risk/config
```

**请求体**

```json
{
  "max_single_stock": 0.15,
  "max_total_position": 0.85,
  "default_stop_loss": 0.07
}
```

### 3. 检查交易信号

检查交易信号是否通过风控。

**请求**

```http
POST /risk/check
```

**请求体**

```json
{
  "symbol": "000001.SZ",
  "side": "BUY",
  "quantity": 10000,
  "price": 10.50
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "allowed": true,
    "reason": null,
    "warnings": [
      {
        "type": "POSITION_WARNING",
        "message": "当前仓位将接近单票上限"
      }
    ],
    "risk_level": "MEDIUM"
  }
}
```

**风控拒绝示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "allowed": false,
    "reason": "单票仓位超限: 当前权重 12.5% > 最大限制 10%",
    "risk_level": "HIGH"
  }
}
```

### 4. 获取止损止盈列表

获取当前所有止损止盈设置。

**请求**

```http
GET /risk/stop-loss
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "stop_losses": [
      {
        "symbol": "600519.SH",
        "order_id": "SL20240115001",
        "position_qty": 100,
        "entry_price": 1650.00,
        "stop_price": 1567.50,
        "stop_loss_type": "percentage",
        "is_active": true,
        "created_at": "2024-01-10T09:30:00Z"
      }
    ],
    "take_profits": [
      {
        "symbol": "600519.SH",
        "order_id": "TP20240115001",
        "position_qty": 100,
        "entry_price": 1650.00,
        "target_price": 1815.00,
        "take_profit_type": "percentage",
        "is_active": true,
        "created_at": "2024-01-10T09:30:00Z"
      }
    ]
  }
}
```

### 5. 设置止损

为持仓设置止损。

**请求**

```http
POST /risk/stop-loss
```

**请求体**

```json
{
  "symbol": "000001.SZ",
  "stop_type": "percentage",
  "stop_pct": 0.05,
  "stop_price": null
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| stop_type | string | 是 | 类型：fixed/percentage/trailing |
| stop_price | decimal | 条件 | 固定止损价（fixed类型） |
| stop_pct | decimal | 条件 | 止损比例（percentage类型） |
| trailing_distance | decimal | 条件 | 跟踪距离（trailing类型） |

### 6. 设置止盈

为持仓设置止盈。

**请求**

```http
POST /risk/take-profit
```

**请求体**

```json
{
  "symbol": "000001.SZ",
  "tp_type": "percentage",
  "target_pct": 0.10
}
```

### 7. 更新止损价

手动更新止损价格。

**请求**

```http
PATCH /risk/stop-loss/{symbol}
```

**请求体**

```json
{
  "stop_price": 9.80
}
```

### 8. 删除止损止盈

删除止损或止盈设置。

**请求**

```http
DELETE /risk/stop-loss/{symbol}
```

```http
DELETE /risk/take-profit/{symbol}
```

### 9. 获取仓位限制

获取当前仓位限制情况。

**请求**

```http
GET /risk/position-limits
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "limits": [
      {
        "type": "single_stock",
        "max_ratio": 0.10,
        "current_ratio": 0.08,
        "remaining_ratio": 0.02,
        "status": "warning"
      },
      {
        "type": "total_position",
        "max_ratio": 0.80,
        "current_ratio": 0.72,
        "remaining_ratio": 0.08,
        "status": "normal"
      },
      {
        "type": "industry",
        "industry": "银行",
        "max_ratio": 0.30,
        "current_ratio": 0.15,
        "remaining_ratio": 0.15,
        "status": "normal"
      }
    ]
  }
}
```

### 10. 获取风控报告

获取风控监控报告。

**请求**

```http
GET /risk/report
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "timestamp": "2024-01-15T10:30:00Z",
    "position": {
      "summary": {
        "current_capital": 1245890.52,
        "total_position_value": 900690.52,
        "total_position_weight": 0.72,
        "position_count": 8
      },
      "alerts": [
        {
          "symbol": "600519.SH",
          "type": "POSITION_HIGH",
          "message": "单票仓位 13.8% 接近限制 15%",
          "severity": "warning"
        }
      ]
    },
    "stop_loss": {
      "active_count": 3,
      "triggered_today": 0
    },
    "overall_risk": "MEDIUM"
  }
}
```

### 11. 紧急清仓

执行紧急清仓（熔断）。

**请求**

```http
POST /risk/emergency-close
```

**请求体**

```json
{
  "reason": "市场风险急剧上升",
  "confirm": true
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "action_id": "EMG20240115001",
    "status": "executing",
    "positions_to_close": 8,
    "estimated_value": 900690.52
  }
}
```

### 12. 获取风险监控日志

获取风险事件日志。

**请求**

```http
GET /risk/logs
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| level | string | 否 | 级别：info/warning/error |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "logs": [
      {
        "log_id": "LOG001",
        "level": "warning",
        "event": "POSITION_LIMIT_WARNING",
        "message": "600519.SH 仓位达到 13.8%",
        "timestamp": "2024-01-15T10:25:00Z"
      },
      {
        "log_id": "LOG002",
        "level": "info",
        "event": "STOP_LOSS_TRIGGERED",
        "message": "000001.SZ 止损触发 @ 9.50",
        "timestamp": "2024-01-15T10:28:35Z"
      }
    ]
  }
}
```

## 风控等级

| 等级 | 说明 |
|------|------|
| LOW | 低风险 |
| MEDIUM | 中等风险 |
| HIGH | 高风险 |
| CRITICAL | 极高风险，禁止交易 |

## 止损类型

| 类型 | 说明 |
|------|------|
| fixed | 固定价格止损 |
| percentage | 比例止损 |
| trailing | 跟踪止损 |

## 止盈类型

| 类型 | 说明 |
|------|------|
| fixed | 固定价格止盈 |
| percentage | 比例止盈 |
| partial | 分批止盈 |
