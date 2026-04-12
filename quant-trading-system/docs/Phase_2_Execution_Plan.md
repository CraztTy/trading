# Phase 2 回测系统执行计划

## 现状分析

**已有基础**:
- ✅ 回测引擎框架 (`src/backtest/engine.py` 380行)
- ✅ 历史数据加载器 (`src/backtest/data_loader.py` 220行)
- ✅ 绩效指标计算 (`src/backtest/metrics.py` 360行)
- ⚠️ API端点模拟实现 (`src/api/v1/endpoints/backtest.py`) - 需要完善
- ❌ 前端回测视图 - 缺失
- ❌ 回测任务管理 - 缺失

## 任务分解

### Wave 1: 后端完善（并行）

#### Task 1: 完善回测API端点 (4h)
**负责人**: agent-1
**文件**:
- `src/api/v1/endpoints/backtest.py` [MODIFY]

**功能**:
- 集成真实回测引擎
- 支持多策略回测
- 回测结果持久化
- 任务状态查询
- 回测结果查询

**验收标准**:
```python
POST /api/v1/backtest/      # 启动回测
GET  /api/v1/backtest/{id}  # 查询回测状态
GET  /api/v1/backtest/{id}/results  # 获取回测结果
```

---

#### Task 2: 回测任务管理 (4h)
**负责人**: agent-2
**文件**:
- `src/models/backtest_task.py` [NEW]
- `src/services/backtest_service.py` [NEW]

**功能**:
- 回测任务CRUD
- 任务状态管理 (pending/running/completed/failed)
- 回测结果存储
- 任务队列管理

**验收标准**:
- 任务可创建、查询、删除
- 任务状态正确流转
- 结果可持久化到数据库

---

#### Task 3: 完善回测引擎 (4h)
**负责人**: agent-3
**文件**:
- `src/backtest/engine.py` [MODIFY]
- `src/backtest/metrics.py` [MODIFY]

**功能**:
- 滑点模型实现
- 手续费计算
- 成交价格模拟
- 持仓收益计算
- 修复TODO (avg_position_duration)

**验收标准**:
- 回测结果包含完整指标
- 滑点和手续费计算正确
- 成交逻辑符合A股规则

---

### Wave 2: 前端开发（并行）

#### Task 4: 前端回测视图 (6h)
**负责人**: agent-4
**文件**:
- `web/src/views/BacktestView.vue` [NEW]
- `web/src/components/backtest/BacktestForm.vue` [NEW]
- `web/src/components/backtest/BacktestResults.vue` [NEW]
- `web/src/components/backtest/BacktestChart.vue` [NEW]
- `web/src/api/backtest.ts` [NEW]

**功能**:
- 回测参数配置表单
  - 股票代码选择
  - 时间范围选择
  - 策略选择
  - 初始资金设置
- 回测结果展示
  - 收益曲线图
  - 绩效指标卡片
  - 交易记录表格
  - 月度收益统计
- 回测任务列表
  - 任务状态显示
  - 进度条
  - 结果查看按钮

**验收标准**:
```
用户可以在BacktestView页面:
1. 选择策略和股票
2. 设置回测参数
3. 启动回测任务
4. 查看回测进度
5. 查看回测结果（图表+数据）
```

---

### Wave 3: 集成测试 (2h)

#### Task 5: 集成测试
**负责人**: agent-5
**文件**:
- `tests/integration/test_backtest.py` [NEW]

**测试场景**:
- 完整回测流程测试
- 多策略回测测试
- 错误处理测试
- 性能测试（大数据量）

---

## 依赖关系

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Task 1: API端点  │  │ Task 2: 任务管理 │  │ Task 3: 引擎完善 │
└────────┬────────┘  └────────┬────────┘  └─────────────────┘
         │                    │
         └────────────────────┘
                    │
                    ▼
         ┌─────────────────┐
         │ Task 4: 前端视图 │
         └─────────────────┘
                    │
                    ▼
         ┌─────────────────┐
         │ Task 5: 集成测试 │
         └─────────────────┘
```

## 时间安排

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| Wave 1 | Task 1-3 | 4小时 |
| Wave 2 | Task 4 | 6小时 |
| Wave 3 | Task 5 | 2小时 |

**总计: 约12-14小时**

## 接口约定

### API接口

```typescript
// 启动回测
POST /api/v1/backtest/
{
  symbols: string[];      // ["000001.SZ", "600036.SH"]
  start_date: string;     // "2024-01-01"
  end_date: string;       // "2024-12-31"
  strategy_id: string;    // "strategy_01"
  initial_capital: number; // 1000000
  params?: object;        // 策略参数
}

// 响应
{
  task_id: string;
  status: "pending" | "running" | "completed" | "failed";
  message: string;
}

// 查询回测状态
GET /api/v1/backtest/{task_id}
{
  task_id: string;
  status: string;
  progress: number;  // 0-100
  params: object;
  created_at: string;
  completed_at?: string;
}

// 获取回测结果
GET /api/v1/backtest/{task_id}/results
{
  summary: {
    total_return: number;      // 总收益
    total_return_pct: string;  // 总收益率
    total_trades: number;      // 总交易次数
    win_rate: string;          // 胜率
    max_drawdown: string;      // 最大回撤
    sharpe_ratio: number;      // 夏普比率
    annualized_return: string; // 年化收益
  };
  trades: TradeRecord[];       // 交易记录
  daily_values: DailyValue[]; // 每日净值
  monthly_returns: MonthlyReturn[]; // 月度收益
}
```

## 交付标准

- [ ] 支持策略回测任务创建
- [ ] 回测结果展示（收益曲线、指标）
- [ ] 支持多策略对比
- [ ] 回测任务可持久化
- [ ] 前端视图完整可用
- [ ] 所有测试通过

## 技术要点

### 回测引擎集成
- 使用现有的 `BacktestEngine` 类
- 注意异步执行和进度更新
- 滑点设置：0.1%-0.3%
- 手续费：佣金万3，印花税千1（卖出）

### 数据加载
- 使用 `HistoryDataLoader`
- 支持AKShare/Tushare数据源
- 本地缓存避免重复请求

### 前端图表
- 使用 ECharts 绘制收益曲线
- 支持缩放和区域选择
- 暗色主题适配

### 任务管理
- 使用数据库表存储任务状态
- 支持任务取消
- 结果JSON格式存储
