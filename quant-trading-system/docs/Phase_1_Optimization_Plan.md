# Phase 1 优化计划

> Sprint 1 已完成核心交易闭环，本计划旨在提升稳定性、可观测性和错误处理

## 优化目标
- [ ] 提升数据质量监控能力
- [ ] 增强风控规则覆盖
- [ ] 完善订单状态追踪
- [ ] 优化API错误处理
- [ ] 增加系统可观测性（日志、指标）

---

## 任务清单

### 1. 太子院数据质量监控 (4h)

**现状**: 基础校验（价格、数量有效性）已实现

**优化内容**:
```
src/core/crown_prince.py      [MODIFY] 添加数据质量评分
src/core/data_quality.py      [NEW] 数据质量监控器
```

- [ ] 数据质量评分系统（完整性、及时性、准确性）
- [ ] 异常数据告警（价格跳空、成交量异常）
- [ ] 数据源健康状态监控
- [ ] 数据延迟检测

**验收标准**:
```python
# 能检测数据质量问题
quality_score = crown_prince.get_data_quality("000001.SZ")
# {"completeness": 0.98, "timeliness": 0.95, "accuracy": 1.0}
```

---

### 2. 门下省风控规则增强 (6h)

**现状**: 基础规则（仓位、止损）已实现

**优化内容**:
```
src/core/menxia_sheng.py      [MODIFY] 添加更多风控规则
src/risk/risk_manager.py      [MODIFY] 完善风控配置
```

- [ ] 委托频率限制（每分钟最大委托数）
- [ ] 连续亏损熔断（连续3次亏损暂停开仓）
- [ ] 价格波动限制（涨跌停板检查）
- [ ] 黑名单/白名单管理
- [ ] 风控规则动态配置（无需重启）

**验收标准**:
```python
# 频率限制
rule = OrderFrequencyRule(max_orders_per_minute=10)
menxia_sheng.add_rule(rule)

# 连续亏损限制
rule = ConsecutiveLossRule(max_consecutive_losses=3)
menxia_sheng.add_rule(rule)
```

---

### 3. 尚书省订单状态追踪 (6h)

**现状**: 基础订单执行已实现，缺少状态追踪

**优化内容**:
```
src/core/shangshu_sheng.py    [MODIFY] 订单状态机
src/models/order_state.py     [NEW] 订单状态记录
```

- [ ] 订单状态机（CREATED -> PENDING -> PARTIAL -> FILLED）
- [ ] 订单状态变更历史
- [ ] 订单取消/撤单支持
- [ ] 部分成交处理
- [ ] 订单超时处理

**验收标准**:
```python
# 订单状态追踪
order_states = shangshu_sheng.get_order_history(order_id)
# [{"state": "CREATED", "time": "..."}, {"state": "PENDING", "time": "..."}]

# 撤单支持
await shangshu_sheng.cancel_order(order_id)
```

---

### 4. 数据库模型完善 (4h)

**现状**: 基础模型已创建，部分字段需完善

**优化内容**:
```
src/models/order.py           [MODIFY] 完善订单状态字段
src/models/signal_log.py      [NEW] 信号记录表
src/models/audit_log.py       [NEW] 风控审核日志表
```

- [ ] 订单状态历史表
- [ ] 信号生成记录表
- [ ] 风控审核日志表
- [ ] 数据质量监控表

**验收标准**:
```sql
-- 信号记录表
CREATE TABLE signal_log (
    id BIGINT PRIMARY KEY,
    strategy_id VARCHAR(32),
    symbol VARCHAR(16),
    signal_type VARCHAR(8),
    price NUMERIC(12,3),
    volume INTEGER,
    status VARCHAR(16),  -- generated, audited, executed, rejected
    audit_result JSON,
    created_at TIMESTAMP
);
```

---

### 5. API错误处理优化 (4h)

**现状**: 基础API已实现，错误处理不够统一

**优化内容**:
```
src/api/v1/endpoints/*.py     [MODIFY] 统一错误处理
src/api/v1/exceptions.py      [NEW] API异常类
src/api/v1/middleware.py      [NEW] 错误处理中间件
```

- [ ] 统一错误响应格式
- [ ] 输入参数校验增强
- [ ] 业务异常分类
- [ ] 错误日志记录

**验收标准**:
```python
# 统一错误响应
{
    "success": False,
    "error_code": "ORDER_INSUFFICIENT_FUNDS",
    "message": "资金不足",
    "details": {"required": 10000, "available": 5000}
}
```

---

### 6. 系统可观测性 (4h)

**优化内容**:
```
src/common/metrics.py         [NEW] 指标收集
src/common/logger.py          [MODIFY] 结构化日志
```

- [ ] 关键指标统计（信号生成数、风控通过率、订单执行数）
- [ ] 性能指标（处理延迟）
- [ ] 结构化日志（JSON格式）
- [ ] 日志级别动态调整

**验收标准**:
```python
# 指标统计
metrics.record("signals.generated", 1)
metrics.record("risk.audit_duration", 0.5)  # 秒
```

---

## 优化优先级

| 优先级 | 任务 | 影响 | 工时 |
|--------|------|------|------|
| P0 | 订单状态追踪 | 核心功能 | 6h |
| P0 | 风控规则增强 | 风险控制 | 6h |
| P1 | API错误处理 | 用户体验 | 4h |
| P1 | 数据质量监控 | 数据可靠性 | 4h |
| P1 | 数据库模型完善 | 数据持久化 | 4h |
| P2 | 系统可观测性 | 运维能力 | 4h |

**总计: 28工时 (约4-5天)**

---

## 建议执行顺序

1. **订单状态追踪** - 最核心，影响交易完整性
2. **风控规则增强** - 提升系统安全性
3. **API错误处理** - 提升开发体验
4. **数据库模型完善** - 配合前3项存储需求
5. **数据质量监控** - 提升数据可靠性
6. **系统可观测性** - 最后做，辅助运维

---

## 交付标准

- [ ] 所有订单状态可追踪
- [ ] 风控规则覆盖主要风险场景
- [ ] API错误响应统一且清晰
- [ ] 关键业务数据持久化到数据库
- [ ] 系统运行指标可观测
