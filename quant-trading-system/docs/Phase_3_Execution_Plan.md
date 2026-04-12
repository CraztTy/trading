# Phase 3 策略管理执行计划

## 现状分析

**已有基础**:
- ✅ 策略基类 (`src/strategy/base.py` 626行)
- ✅ 策略管理器 (`src/strategy/manager.py` 388行)
- ✅ 策略API端点 (`src/api/v1/endpoints/strategies.py` 114行)
- ✅ 前端策略视图 (`StrategyView.vue` 存在)
- ✅ 优化器目录 (`src/strategy/optimizer/`)

**需要完善**:
- ⚠️ 策略数据库模型不完整
- ⚠️ 策略CRUD API待完善
- ⚠️ 策略参数优化待实现
- ⚠️ 策略与回测结果关联待实现
- ⚠️ 前端策略管理界面待完善

## 任务分解

### Wave 1: 后端基础（并行）

#### Task 1: 策略数据库模型 (4h)
**负责人**: agent-1
**文件**:
- `src/models/strategy.py` [MODIFY]
- `src/models/strategy_version.py` [NEW]
- `src/models/strategy_backtest.py` [NEW]

**功能**:
- 策略表增加参数配置、源代码存储
- 策略版本表（支持版本管理）
- 策略回测关联表

---

#### Task 2: 策略CRUD API完善 (4h)
**负责人**: agent-2
**文件**:
- `src/api/v1/endpoints/strategies.py` [MODIFY]
- `src/services/strategy_service.py` [NEW]

**功能**:
- 策略创建（支持代码上传）
- 策略编辑
- 策略删除
- 策略启停
- 策略参数配置

**API接口**:
```python
POST   /api/v1/strategies/              # 创建策略
GET    /api/v1/strategies/              # 列表查询
GET    /api/v1/strategies/{id}          # 详情
PUT    /api/v1/strategies/{id}          # 更新
DELETE /api/v1/strategies/{id}          # 删除
POST   /api/v1/strategies/{id}/start    # 启动
POST   /api/v1/strategies/{id}/stop     # 停止
POST   /api/v1/strategies/{id}/backtest # 执行回测
```

---

#### Task 3: 策略参数优化 (6h)
**负责人**: agent-3
**文件**:
- `src/strategy/optimizer/grid_search.py` [NEW]
- `src/strategy/optimizer/genetic.py` [NEW]
- `src/strategy/optimizer/base.py` [NEW]
- `src/api/v1/endpoints/strategy_optimizer.py` [NEW]

**功能**:
- 网格搜索优化
- 遗传算法优化
- 参数空间定义
- 优化结果排序

**优化配置示例**:
```python
{
    "strategy_id": "ma_strategy",
    "parameters": {
        "fast_period": {"type": "int", "min": 5, "max": 20, "step": 1},
        "slow_period": {"type": "int", "min": 10, "max": 60, "step": 5}
    },
    "optimizer": "grid_search",  # or "genetic"
    "metric": "sharpe_ratio",    # 优化目标
    "backtest_config": {...}
}
```

---

### Wave 2: 前端开发（并行）

#### Task 4: 策略管理前端 (6h)
**负责人**: agent-4
**文件**:
- `web/src/views/StrategyView.vue` [MODIFY]
- `web/src/components/strategy/StrategyList.vue` [NEW]
- `web/src/components/strategy/StrategyEditor.vue` [NEW]
- `web/src/components/strategy/StrategyDetail.vue` [NEW]
- `web/src/components/strategy/StrategyOptimizer.vue` [NEW]
- `web/src/api/strategy.ts` [NEW/MODIFY]

**功能**:
- 策略列表（卡片/表格视图）
- 策略编辑器（代码编辑）
- 策略参数配置表单
- 策略启停控制
- 参数优化界面
- 回测结果关联展示

**界面设计**:
```
StrategyView
├── 策略列表 (StrategyList)
│   ├── 卡片展示（名称、状态、收益率）
│   ├── 操作按钮（编辑、删除、启停）
│   └── 新建策略按钮
├── 策略编辑器 (StrategyEditor)
│   ├── 代码编辑器 (Monaco/ CodeMirror)
│   ├── 参数配置表单
│   └── 保存/发布按钮
├── 策略详情 (StrategyDetail)
│   ├── 基本信息
│   ├── 性能指标
│   ├── 回测历史列表
│   └── 参数优化结果
└── 参数优化 (StrategyOptimizer)
    ├── 参数范围设置
    ├── 优化进度
    └── 结果对比表格
```

---

### Wave 3: 集成与测试

#### Task 5: 策略与回测关联 (2h)
**负责人**: agent-5
**文件**:
- `src/services/strategy_service.py` [MODIFY]
- `src/models/strategy_backtest.py` [MODIFY]

**功能**:
- 策略执行回测
- 回测结果关联到策略
- 策略性能历史追踪

---

#### Task 6: 集成测试 (2h)
**负责人**: agent-5
**文件**:
- `tests/integration/test_strategy_management.py` [NEW]

**测试场景**:
- 策略CRUD完整流程
- 策略启停控制
- 参数优化流程
- 策略与回测关联

## 依赖关系

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Task 1: 数据库   │  │ Task 2: API     │  │ Task 3: 优化器  │
│     模型        │  │    CRUD         │  │                │
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
         │ Task 5-6: 集成  │
         └─────────────────┘
```

## 时间安排

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| Wave 1 | Task 1-3 | 4-6小时 |
| Wave 2 | Task 4 | 6小时 |
| Wave 3 | Task 5-6 | 4小时 |

**总计: 约14-16小时**

## 交付标准

- [ ] 策略可创建、编辑、删除
- [ ] 支持策略代码编辑
- [ ] 策略参数可配置
- [ ] 策略可启停控制
- [ ] 支持参数优化（网格搜索）
- [ ] 策略与回测结果关联
- [ ] 所有测试通过

## 技术要点

### 策略代码存储
- 代码存储在数据库TEXT字段
- 支持版本管理（每次保存创建新版本）
- 代码沙箱执行（安全考虑）

### 参数优化
- 网格搜索：遍历所有参数组合
- 遗传算法：进化优化参数
- 并行执行多个回测任务

### 前端代码编辑
- 使用 Monaco Editor 或 CodeMirror
- 支持Python语法高亮
- 代码自动保存

## 建议执行顺序

1. **数据库模型** - 基础数据结构
2. **API CRUD** - 后端接口
3. **优化器** - 参数优化功能
4. **前端视图** - 用户界面
5. **集成测试** - 验证完整性
