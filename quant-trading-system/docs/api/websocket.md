# WebSocket API

## 概述

提供实时数据推送服务，包括行情、交易、风控等实时事件。

## 连接信息

- **地址**: `wss://api.example.com/ws`
- **协议**: WebSocket (RFC 6455)
- **心跳间隔**: 30秒

## 认证

连接时通过 URL 参数携带 token：

```
wss://api.example.com/ws?token=your_jwt_token
```

## 消息格式

所有消息为 JSON 格式：

```json
{
  "type": "message_type",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "data": {}
}
```

## 客户端消息

### 订阅行情

```json
{
  "action": "subscribe",
  "channel": "quotes",
  "symbols": ["000001.SZ", "600519.SH"]
}
```

### 取消订阅

```json
{
  "action": "unsubscribe",
  "channel": "quotes",
  "symbols": ["000001.SZ"]
}
```

### 心跳

```json
{
  "action": "ping",
  "time": 1705312200123
}
```

## 服务端消息

### 实时行情

```json
{
  "type": "quote",
  "timestamp": "2024-01-15T10:30:00.123Z",
  "data": {
    "symbol": "000001.SZ",
    "price": 10.52,
    "change": 0.04,
    "change_pct": 0.38,
    "volume": 1520341,
    "bid": [[10.51, 5200], [10.50, 8300]],
    "ask": [[10.53, 4100], [10.54, 6200]]
  }
}
```

### 成交推送

```json
{
  "type": "trade",
  "timestamp": "2024-01-15T10:30:15.456Z",
  "data": {
    "trade_id": "T20240115001",
    "order_id": "ORD001",
    "symbol": "000001.SZ",
    "side": "BUY",
    "quantity": 1000,
    "price": 10.50,
    "amount": 10500.00
  }
}
```

### 订单状态更新

```json
{
  "type": "order_update",
  "timestamp": "2024-01-15T10:30:15.456Z",
  "data": {
    "order_id": "ORD001",
    "status": "FILLED",
    "filled_quantity": 1000,
    "avg_price": 10.50,
    "update_time": "2024-01-15T10:30:15Z"
  }
}
```

### 风控告警

```json
{
  "type": "risk_alert",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "alert_type": "STOP_LOSS_TRIGGERED",
    "symbol": "000001.SZ",
    "message": "止损触发 @ 9.50",
    "severity": "HIGH",
    "action_required": true
  }
}
```

### 持仓更新

```json
{
  "type": "position_update",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "symbol": "000001.SZ",
    "quantity": 2000,
    "avg_cost": 10.35,
    "current_price": 10.52,
    "unrealized_pnl": 340.00,
    "unrealized_pnl_pct": 0.0164
  }
}
```

### 心跳响应

```json
{
  "type": "pong",
  "time": 1705312200123,
  "server_time": 1705312200156
}
```

## 订阅频道

| 频道 | 说明 | 权限 |
|------|------|------|
| quotes | 实时行情 | 所有用户 |
| trades | 成交推送 | 所有用户 |
| orders | 订单更新 | 所有用户 |
| positions | 持仓更新 | 所有用户 |
| risk | 风控告警 | 所有用户 |
| account | 资金变动 | 所有用户 |
| system | 系统公告 | 所有用户 |

## 错误处理

```json
{
  "type": "error",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "code": "WS001",
    "message": "Invalid symbol",
    "details": "Symbol 999999.SZ does not exist"
  }
}
```

## 断开连接

服务端会在以下情况断开连接：
- 认证失败
- 心跳超时（60秒未收到ping）
- 消息频率超限
- 系统维护

## 重连策略

建议客户端实现指数退避重连：
- 第1次：1秒后
- 第2次：2秒后
- 第3次：4秒后
- 第4次：8秒后
- 最大：30秒
