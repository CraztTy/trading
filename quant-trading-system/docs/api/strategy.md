# 策略管理 API

## 概述

提供策略的创建、管理、回测和优化功能。

## 接口列表

### 1. 创建策略

创建新的交易策略。

**请求**

```http
POST /strategies
```

**请求体**

```json
{
  "name": "双均线策略",
  "description": "基于5日和20日均线的金叉死叉策略",
  "type": "technical",
  "symbols": ["000001.SZ", "600519.SH"],
  "parameters": {
    "fast_ma": 5,
    "slow_ma": 20,
    "stop_loss": 0.05
  },
  "code": "def on_bar(context, bar):\n    if context.fast_ma > context.slow_ma:\n        buy()",
  "initial_capital": 1000000,
  "position_sizing": "equal"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 策略名称 |
| description | string | 否 | 策略描述 |
| type | string | 是 | 策略类型：technical/fundamental/ml |
| symbols | array | 是 | 标的列表 |
| parameters | object | 是 | 策略参数 |
| code | string | 条件 | 策略代码（Python） |
| initial_capital | decimal | 否 | 初始资金，默认100万 |
| position_sizing | string | 否 | 仓位管理：equal/volatility/kelly |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "strategy_id": "STR20240101001",
    "name": "双均线策略",
    "status": "active",
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

### 2. 获取策略列表

获取所有策略列表。

**请求**

```http
GET /strategies
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | string | 否 | 状态：active/paused/stopped |
| type | string | 否 | 策略类型 |
| page | integer | 否 | 页码，默认1 |
| page_size | integer | 否 | 每页数量，默认20 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 15,
    "page": 1,
    "page_size": 20,
    "strategies": [
      {
        "strategy_id": "STR001",
        "name": "双均线策略",
        "type": "technical",
        "status": "active",
        "symbols_count": 10,
        "created_at": "2024-01-10T08:00:00Z"
      }
    ]
  }
}
```

### 3. 获取策略详情

获取单个策略的详细信息。

**请求**

```http
GET /strategies/{strategy_id}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "strategy_id": "STR001",
    "name": "双均线策略",
    "description": "基于5日和20日均线的金叉死叉策略",
    "type": "technical",
    "status": "active",
    "symbols": ["000001.SZ", "600519.SH"],
    "parameters": {
      "fast_ma": 5,
      "slow_ma": 20
    },
    "performance": {
      "total_return": 0.25,
      "annual_return": 0.30,
      "sharpe_ratio": 1.85,
      "max_drawdown": -0.12,
      "win_rate": 0.62
    },
    "created_at": "2024-01-10T08:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
  }
}
```

### 4. 更新策略

更新策略配置。

**请求**

```http
PUT /strategies/{strategy_id}
```

**请求体**

```json
{
  "name": "双均线策略V2",
  "parameters": {
    "fast_ma": 10,
    "slow_ma": 30
  }
}
```

### 5. 删除策略

删除策略。

**请求**

```http
DELETE /strategies/{strategy_id}
```

### 6. 启动策略

启动策略实盘运行。

**请求**

```http
POST /strategies/{strategy_id}/start
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "strategy_id": "STR001",
    "status": "active",
    "started_at": "2024-01-15T09:30:00Z"
  }
}
```

### 7. 暂停策略

暂停策略运行。

**请求**

```http
POST /strategies/{strategy_id}/pause
```

### 8. 停止策略

停止策略运行。

**请求**

```http
POST /strategies/{strategy_id}/stop
```

### 9. 回测策略

对策略进行历史回测。

**请求**

```http
POST /strategies/{strategy_id}/backtest
```

**请求体**

```json
{
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 1000000,
  "commission_rate": 0.0003,
  "slippage": 0.001
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "backtest_id": "BT20240115001",
    "status": "completed",
    "summary": {
      "total_return": 0.25,
      "annual_return": 0.30,
      "sharpe_ratio": 1.85,
      "max_drawdown": -0.12,
      "win_rate": 0.62,
      "profit_factor": 2.1,
      "total_trades": 156
    },
    "daily_returns": [
      {
        "date": "2023-01-04",
        "return": 0.012,
        "nav": 1.012
      }
    ],
    "trades": [
      {
        "symbol": "000001.SZ",
        "side": "BUY",
        "quantity": 1000,
        "entry_price": 10.50,
        "exit_price": 11.20,
        "pnl": 700,
        "entry_time": "2023-01-04T09:30:00Z"
      }
    ]
  }
}
```

### 10. 获取回测结果

获取回测详细结果。

**请求**

```http
GET /backtests/{backtest_id}
```

### 11. 优化策略参数

对策略参数进行优化。

**请求**

```http
POST /strategies/{strategy_id}/optimize
```

**请求体**

```json
{
  "parameters": {
    "fast_ma": {"min": 3, "max": 20, "step": 1},
    "slow_ma": {"min": 20, "max": 60, "step": 5}
  },
  "metric": "sharpe_ratio",
  "method": "grid_search",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31"
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "optimization_id": "OPT001",
    "best_params": {
      "fast_ma": 10,
      "slow_ma": 30
    },
    "best_performance": {
      "sharpe_ratio": 2.1,
      "total_return": 0.32
    },
    "results_count": 180
  }
}
```

### 12. 获取策略持仓

获取策略当前持仓。

**请求**

```http
GET /strategies/{strategy_id}/positions
```

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "strategy_id": "STR001",
    "positions": [
      {
        "symbol": "000001.SZ",
        "quantity": 1000,
        "avg_cost": 10.50,
        "current_price": 11.20,
        "market_value": 11200,
        "unrealized_pnl": 700,
        "unrealized_pnl_pct": 0.067
      }
    ],
    "total_market_value": 11200,
    "total_unrealized_pnl": 700
  }
}
```

### 13. 获取策略信号

获取策略产生的交易信号。

**请求**

```http
GET /strategies/{strategy_id}/signals
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| limit | integer | 否 | 返回条数 |

**响应示例**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "signals": [
      {
        "signal_id": "SIG001",
        "symbol": "000001.SZ",
        "action": "BUY",
        "quantity": 1000,
        "price": 10.50,
        "reason": "Golden cross detected",
        "created_at": "2024-01-15T09:30:00Z"
      }
    ]
  }
}
```

## 策略类型

| 类型 | 说明 |
|------|------|
| technical | 技术分析策略 |
| fundamental | 基本面策略 |
| ml | 机器学习策略 |
| arbitrage | 套利策略 |
| market_making | 做市策略 |

## 参数优化方法

| 方法 | 说明 |
|------|------|
| grid_search | 网格搜索 |
| random_search | 随机搜索 |
| bayesian | 贝叶斯优化 |
| genetic | 遗传算法 |

## 性能指标

| 指标 | 说明 |
|------|------|
| total_return | 总收益率 |
| annual_return | 年化收益率 |
| sharpe_ratio | 夏普比率 |
| sortino_ratio | 索提诺比率 |
| max_drawdown | 最大回撤 |
| win_rate | 胜率 |
| profit_factor | 盈亏比 |
| calmar_ratio | 卡尔马比率 |
