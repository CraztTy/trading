# Phase 1 优化执行计划

## 任务分解与依赖关系

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Task 1: 订单状态  │  │  Task 2: 风控增强 │  │  Task 3: API错误 │
│     追踪        │  │                │  │     处理       │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Task 4: 数据库  │
                    │   模型完善      │
                    └────────┬────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Task 5: 数据质量 │  │  Task 6: 可观测性 │  │  Task 7: 集成测试 │
│     监控        │  │                │  │               │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 任务详情

### Task 1: 订单状态追踪 (6h) - 负责人: agent-1
**文件**: 
- `src/core/shangshu_sheng.py` [MODIFY]
- `src/core/order_state_machine.py` [NEW]
- `src/models/order_state.py` [NEW]

**功能**:
- 订单状态机实现
- 状态变更历史记录
- 撤单/部分成交支持
- 订单超时处理

**验收**: 订单全生命周期可追踪

---

### Task 2: 风控规则增强 (6h) - 负责人: agent-2
**文件**:
- `src/core/menxia_sheng.py` [MODIFY]
- `src/risk/rules.py` [NEW]

**功能**:
- OrderFrequencyRule (委托频率限制)
- ConsecutiveLossRule (连续亏损熔断)
- PriceLimitRule (涨跌停检查)
- BlacklistRule (黑名单)
- 规则动态配置

**验收**: 5条风控规则全部生效

---

### Task 3: API错误处理 (4h) - 负责人: agent-3
**文件**:
- `src/api/v1/exceptions.py` [NEW]
- `src/api/v1/middleware.py` [NEW]
- `src/api/v1/endpoints/orders.py` [MODIFY]
- `src/api/v1/endpoints/capital.py` [MODIFY]

**功能**:
- 统一错误响应格式
- 业务异常分类定义
- 参数校验增强
- 错误处理中间件

**验收**: 所有API返回统一错误格式

---

### Task 4: 数据库模型完善 (4h) - 依赖 Task 1,2
**文件**:
- `src/models/signal_log.py` [NEW]
- `src/models/audit_log.py` [NEW]
- `src/models/order_state_history.py` [NEW]
- `scripts/init_database.py` [MODIFY]

**功能**:
- 信号生成记录表
- 风控审核日志表
- 订单状态历史表

**验收**: 数据库表可正常创建

---

### Task 5: 数据质量监控 (4h) - 负责人: agent-4
**文件**:
- `src/core/data_quality.py` [NEW]
- `src/core/crown_prince.py` [MODIFY]

**功能**:
- 数据质量评分系统
- 异常数据检测
- 数据源健康监控
- 延迟检测

**验收**: 能输出数据质量评分

---

### Task 6: 可观测性 (4h) - 依赖 Task 3
**文件**:
- `src/common/metrics.py` [NEW]
- `src/common/logger.py` [MODIFY]

**功能**:
- 指标收集器
- 性能计时
- 结构化日志
- 日志级别动态调整

**验收**: 指标可收集，日志结构化

---

### Task 7: 集成测试 (2h) - 依赖所有任务
**文件**:
- `tests/integration/test_phase1_optimization.py` [NEW]

**功能**:
- 订单状态流转测试
- 风控规则组合测试
- API错误处理测试
- 数据质量测试

**验收**: 所有测试通过

---

## 并行执行策略

### Wave 1 (独立任务，可并行)
- Task 1: 订单状态追踪
- Task 2: 风控规则增强
- Task 3: API错误处理
- Task 5: 数据质量监控

### Wave 2 (依赖Wave 1)
- Task 4: 数据库模型完善
- Task 6: 可观测性

### Wave 3 (最终验证)
- Task 7: 集成测试

## 沟通协调

### 接口约定

**订单状态变更事件**:
```python
class OrderStateChangedEvent:
    order_id: str
    from_state: str
    to_state: str
    timestamp: datetime
    reason: Optional[str]
```

**风控审核结果**:
```python
class AuditResult:
    approved: bool
    reject_reason: Optional[str]
    rule_code: Optional[str]
    processing_time_ms: float
```

**API错误响应**:
```python
{
    "success": False,
    "error_code": "ERROR_CODE",
    "message": "用户友好错误信息",
    "details": {},
    "timestamp": "2026-04-12T10:00:00Z"
}
```

## 时间安排

| 时间段 | 任务 |
|--------|------|
| 0-6h | Wave 1 并行执行 |
| 6-10h | Wave 2 并行执行 |
| 10-12h | Wave 3 集成测试 |

**总计: 约12小时完成所有优化**
