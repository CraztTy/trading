# Phase 5 风控系统完善执行计划

## 现状分析

**已有基础 (完成度 70%)**:
- ✅ 风控管理器 (`risk_manager.py`) - 集成仓位、止损、风控检查
- ✅ 风控规则引擎 (`rules.py`) - 7种规则完整实现
- ✅ 止损止盈管理器 (`stop_loss.py`) - 实时监控和触发
- ✅ 仓位管理器 (`position_manager.py`) - 限制检查和预警
- ⚠️ 前端视图 (`RiskView.vue`) - 只有静态 mock 数据
- ❌ API 端点 - 未暴露风控接口给前端

## 任务分解

### Task 1: 风控 API 端点 (3h)
**文件**: `src/api/v1/endpoints/risk.py` [NEW]

**端点设计**:
```python
GET    /api/v1/risk/status              # 获取风控状态
GET    /api/v1/risk/report              # 获取风控报告
GET    /api/v1/risk/rules               # 获取所有规则状态
POST   /api/v1/risk/rules/{code}/toggle # 启用/禁用规则
PUT    /api/v1/risk/rules/{code}        # 更新规则配置
GET    /api/v1/risk/alerts              # 获取风险预警列表
POST   /api/v1/risk/alerts/{id}/ack     # 确认预警
POST   /api/v1/risk/emergency-close     # 紧急清仓
WS     /api/v1/risk/ws                  # 实时风险推送
```

---

### Task 2: 风险预警通知 (2h)
**文件**:
- `src/core/risk_alerts.py` [NEW]
- `src/api/v1/endpoints/risk.py` [MODIFY]

**功能**:
- 风险事件收集
- 预警级别分类 (WARNING/CRITICAL)
- WebSocket 实时推送
- 预警确认机制

---

### Task 3: 重构前端 RiskView (4h)
**文件**:
- `web/src/views/RiskView.vue` [MODIFY]
- `web/src/api/risk.ts` [NEW]

**界面布局**:
```
RiskView
├── 顶部状态栏
│   ├── 风险评分（实时计算）
│   ├── 当前状态（安全/警告/危险）
│   └── 紧急操作按钮
├── 风控规则面板
│   ├── 规则列表（启用/禁用/配置）
│   └── 规则统计
├── 持仓风险面板
│   ├── 单票仓位占比
│   ├── 止损/止盈设置
│   └── 风险热力图
├── 预警通知面板
│   ├── 未确认预警
│   └── 历史预警
└── 快捷操作
    ├── 暂停开仓
    ├── 全部止盈
    └── 紧急清仓
```

---

### Task 4: 风控集成测试 (2h)
**文件**: `tests/integration/test_risk_management.py` [NEW]

**测试场景**:
- 规则触发和拦截
- 止损止盈触发
- 预警通知推送
- 紧急清仓执行

---

## 依赖关系

```
Task 1: API端点
    │
    ├──> Task 2: 预警通知（依赖API推送）
    │
    └──> Task 3: 前端视图（依赖API数据）
              │
              └──> Task 4: 集成测试
```

## 时间安排

| 任务 | 预计时间 | 优先级 |
|------|----------|--------|
| Task 1: API端点 | 3h | P0 |
| Task 2: 预警通知 | 2h | P0 |
| Task 3: 前端重构 | 4h | P0 |
| Task 4: 集成测试 | 2h | P1 |

**总计: 约11小时**

## 交付标准

- [ ] 风控规则可配置（启用/禁用/参数调整）
- [ ] 实时风险评分计算
- [ ] 风险预警 WebSocket 推送
- [ ] 紧急清仓按钮可用
- [ ] 持仓风险可视化

## 技术要点

### 风险评分算法
```python
risk_score = (
    position_risk * 0.4 +      # 仓位风险 40%
    stop_loss_risk * 0.3 +     # 止损风险 30%
    market_risk * 0.2 +        # 市场风险 20%
    concentration_risk * 0.1   # 集中度风险 10%
)
```

### WebSocket 消息格式
```typescript
{
  type: 'risk_alert',
  data: {
    id: string,
    level: 'WARNING' | 'CRITICAL',
    title: string,
    message: string,
    timestamp: string,
    acknowledged: boolean
  }
}
```
