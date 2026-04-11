# Quant Trading System API 文档

## 概述

Quant Trading System API 提供完整的量化交易功能，包括市场数据、订单执行、策略管理、风险控制等。

## 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **协议**: HTTP/REST
- **数据格式**: JSON
- **认证**: Bearer Token (JWT)

## 认证

所有 API 请求需要在 Header 中携带认证令牌：

```http
Authorization: Bearer <your_jwt_token>
```

## 响应格式

标准响应结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": "2024-01-15T10:30:00Z"
}
```

错误响应：

```json
{
  "code": 400,
  "message": "参数错误",
  "error": "symbol is required",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 模块列表

| 模块 | 说明 | 文档链接 |
|------|------|----------|
| 市场数据 | 行情数据、历史数据 | [market_data.md](market_data.md) |
| 订单执行 | 下单、撤单、订单查询 | [execution.md](execution.md) |
| 策略管理 | 策略CRUD、回测 | [strategy.md](strategy.md) |
| 资金管理 | 账户、持仓、资金 | [finance.md](finance.md) |
| 风险控制 | 仓位、止损、风控报告 | [risk.md](risk.md) |
| 报告系统 | 交易报告、绩效分析 | [reports.md](reports.md) |
| 智能选股 | 筛选、评分、基本面 | [intelligence.md](intelligence.md) |

## HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

## 限流规则

- 行情接口：100次/分钟
- 交易接口：10次/秒
- 其他接口：60次/分钟

## SDK

- [Python SDK](../sdk/python.md)
- [JavaScript SDK](../sdk/javascript.md)
