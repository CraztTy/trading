# Phase 4 实盘监控执行计划

## 现状分析

**已有基础**:
- ✅ LiveCabinet (`src/core/live_cabinet.py` 270行) - 实盘模式管理
- ✅ API端点 (`src/api/v1/endpoints/live.py` 143行) - WebSocket、启停控制
- ⚠️ 前端视图 - 缺失
- ⚠️ 信号推送WebSocket集成 - 需要完善
- ⚠️ 自动/手动下单切换 - 需要实现

## 任务分解

### Wave 1: 后端完善

#### Task 1: 实盘信号推送增强 (4h)
**文件**:
- `src/core/live_cabinet.py` [MODIFY]
- `src/core/signal_publisher.py` [NEW]

**功能**:
- WebSocket信号实时推送
- 信号去重和节流
- 信号日志记录
- 手动信号触发接口

**信号格式**:
```python
{
    "type": "signal",
    "timestamp": "2026-01-15T10:30:00Z",
    "strategy_id": "ma_strategy_01",
    "symbol": "000001.SZ",
    "signal_type": "buy",  # buy/sell
    "price": 10.50,
    "volume": 100,
    "confidence": 0.85,
    "reason": "MA金叉",
    "metadata": {...}
}
```

---

#### Task 2: 自动/手动下单切换 (4h)
**文件**:
- `src/core/auto_trader.py` [NEW]
- `src/core/live_cabinet.py` [MODIFY]
- `src/models/trade_mode.py` [NEW]

**功能**:
- 自动下单模式
- 手动确认模式
- 模拟交易模式
- 风控拦截检查

**交易模式**:
```python
class TradeMode(Enum):
    AUTO = "auto"           # 自动下单
    MANUAL = "manual"       # 手动确认
    SIMULATE = "simulate"   # 模拟交易
    PAUSE = "pause"         # 暂停交易
```

**自动下单流程**:
```
信号生成 -> 风控检查 -> 资金检查 -> 自动下单 -> 成交回调
```

**手动确认流程**:
```
信号生成 -> WebSocket推送 -> 用户确认 -> 下单 -> 成交回调
```

---

#### Task 3: 实盘监控API完善 (3h)
**文件**:
- `src/api/v1/endpoints/live.py` [MODIFY]

**新增端点**:
```python
POST   /api/v1/live/mode           # 切换交易模式
GET    /api/v1/live/signals        # 获取信号历史
POST   /api/v1/live/signals/{id}/confirm  # 确认信号下单
POST   /api/v1/live/signals/{id}/ignore   # 忽略信号
GET    /api/v1/live/trades         # 获取实盘交易记录
GET    /api/v1/live/performance    # 获取实盘绩效
```

---

### Wave 2: 前端开发

#### Task 4: 实盘监控前端视图 (6h)
**文件**:
- `web/src/views/LiveView.vue` [NEW]
- `web/src/components/live/LiveStatus.vue` [NEW]
- `web/src/components/live/SignalPanel.vue` [NEW]
- `web/src/components/live/TradePanel.vue` [NEW]
- `web/src/components/live/PerformancePanel.vue` [NEW]
- `web/src/api/live.ts` [NEW]

**界面布局**:
```
LiveView
├── 顶部控制栏
│   ├── 实盘状态指示器
│   ├── 交易模式切换（自动/手动/模拟）
│   ├── 启停按钮
│   └── 策略选择
├── 实时信号面板 (SignalPanel)
│   ├── 信号列表（带确认/忽略按钮）
│   └── 信号详情弹窗
├── 交易面板 (TradePanel)
│   ├── 实时成交记录
│   └── 持仓变动
├── 绩效面板 (PerformancePanel)
│   ├── 实时收益曲线
│   ├── 今日统计
│   └── 策略表现对比
└── 日志面板
    └── 实时运行日志
```

**WebSocket实时更新**:
```typescript
// 信号推送
{ type: 'signal', data: {...} }

// 成交推送
{ type: 'trade', data: {...} }

// 状态推送
{ type: 'status', data: {...} }

// 绩效推送
{ type: 'performance', data: {...} }
```

---

### Wave 3: 集成测试

#### Task 5: 实盘监控集成测试 (2h)
**文件**:
- `tests/integration/test_live_monitoring.py` [NEW]

**测试场景**:
- 实盘启动/停止流程
- 信号接收和展示
- 自动下单模式
- 手动确认模式
- WebSocket连接稳定性

---

## 依赖关系

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Task 1: 信号推送 │  │ Task 2: 自动/   │  │ Task 3: API完善 │
│                 │  │   手动下单      │  │                 │
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
| Wave 1 | Task 1-3 | 4-6小时 |
| Wave 2 | Task 4 | 6小时 |
| Wave 3 | Task 5 | 2小时 |

**总计: 约12-14小时**

## 交付标准

- [ ] 实盘模式可启动/停止
- [ ] 实时信号WebSocket推送
- [ ] 支持自动/手动/模拟三种模式
- [ ] 信号可手动确认或忽略
- [ ] 实时绩效展示
- [ ] 前端界面完整可用

## 技术要点

### WebSocket连接
- 使用原生WebSocket API
- 自动重连机制
- 心跳检测

### 实时更新
- 信号节流（避免频繁刷新）
- 虚拟滚动（大量信号时性能优化）
- 声音提醒（新信号到达）

### 交易安全
- 自动模式下严格风控检查
- 手动模式下防止误操作（二次确认）
- 模拟模式完全隔离真实资金

## 建议执行顺序

1. **信号推送增强** - 核心实时功能
2. **自动/手动下单** - 交易执行逻辑
3. **API完善** - 后端接口
4. **前端视图** - 用户界面
5. **集成测试** - 验证完整性
