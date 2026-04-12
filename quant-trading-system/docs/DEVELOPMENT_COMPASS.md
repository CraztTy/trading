# 📍 量化交易系统开发罗盘

> 版本：v1.0  
> 更新日期：2026-04-12  
> 作用：指导项目迭代开发的路线图

---

## 🎯 项目现状评估

### 已完成（约60%）
- ✅ 基础架构搭建（FastAPI + Vue3 + 分层架构）
- ✅ 多数据源集成（AKShare / Tushare / Baostock / Mock）
- ✅ 认证授权系统（JWT + 登录/注册）
- ✅ 基础前端视图（Dashboard / Market / Trade / Positions）
- ✅ 资金管理API（入金/出金/转账/流水）
- ✅ 持仓管理API
- ✅ 订单管理基础

### 骨架待填充（约40%）
- 🟡 回测系统（只有任务管理，无真实回测逻辑）
- 🟡 实盘监控（只有状态管理，无信号生成）
- 🟡 策略管理（只有mock数据，无真实CRUD）
- 🟡 风控系统（只有基础框架）
- 🟡 智能分析（只有UI组件）
- 🟡 三省六部架构（只有目录结构）

---

## 🧭 迭代路线图

### Phase 1：核心交易闭环（Week 1-2）✅
**目标**：实现从行情获取 → 信号生成 → 下单 → 持仓的完整闭环

#### 1.1 三省六部核心实现 ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `src/core/crown_prince.py` | 数据前置校验与分发 | P0 | ✅ |
| `src/core/zhongshu_sheng.py` | 策略信号生成引擎 | P0 | ✅ |
| `src/core/menxia_sheng.py` | 风控审核拦截 | P0 | ✅ |
| `src/core/shangshu_sheng.py` | 执行调度与资金清算 | P0 | ✅ |

**Phase 1 交付标准**：
- [x] 策略信号能触发订单
- [x] 风控规则能拦截订单
- [x] 订单成交后更新持仓

---

### Phase 1.5：核心功能优化（Week 2-3）✅
**目标**：提升交易系统的稳定性、安全性和可观测性

#### 1.5.1 订单状态管理 ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `src/core/order_state_machine.py` | 订单状态机 | P0 | ✅ |
| `src/models/order_state_history.py` | 订单状态历史表 | P0 | ✅ |
| `src/core/shangshu_sheng.py` | 撤单/部分成交支持 | P0 | ✅ |

#### 1.5.2 风控规则增强 ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `src/risk/rules.py` | 新增风控规则 | P0 | ✅ |
| `src/core/menxia_sheng.py` | 动态规则配置 | P0 | ✅ |

**新增规则**：
- 委托频率限制 (R004)
- 连续亏损熔断 (R005)
- 涨跌停检查 (R006)
- 黑名单规则 (R007)

#### 1.5.3 API错误处理优化 ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `src/api/v1/exceptions.py` | API异常类定义 | P0 | ✅ |
| `src/api/v1/middleware.py` | 错误处理中间件 | P0 | ✅ |
| `src/api/v1/endpoints/*.py` | 统一错误响应 | P0 | ✅ |

#### 1.5.4 数据质量监控 ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `src/core/data_quality.py` | 数据质量监控器 | P0 | ✅ |
| `src/core/crown_prince.py` | 集成质量监控 | P0 | ✅ |

#### 1.5.5 系统可观测性 ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `src/common/metrics.py` | 指标收集器 | P1 | ✅ |
| `src/common/logger.py` | 结构化日志 | P1 | ✅ |

**Phase 1.5 交付标准**：
- [x] 订单状态可追踪
- [x] 支持撤单操作
- [x] 风控规则覆盖主要风险场景
- [x] API错误响应统一
- [x] 数据质量可监控
- [x] 业务指标可观测

---

### Phase 2：回测系统（Week 3-4）✅
**目标**：实现策略回测功能，支持策略验证

#### 2.1 回测引擎 ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `src/backtest/engine.py` | 回测引擎核心逻辑 | P0 | ✅ |
| `src/backtest/engine.py` | 滑点模型 | P0 | ✅ |
| `src/backtest/engine.py` | 手续费计算器 | P0 | ✅ |
| `src/backtest/data_loader.py` | 历史数据加载器 | P0 | ✅ |
| `src/backtest/metrics.py` | 回测指标计算（夏普/最大回撤等） | P0 | ✅ |

#### 2.2 回测API ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `src/api/v1/endpoints/backtest.py` | 完善回测API（真实逻辑） | P0 | ✅ |
| `src/models/backtest_task.py` | 回测任务表 | P0 | ✅ |
| `src/services/backtest_service.py` | 回测服务 | P0 | ✅ |

#### 2.3 前端回测视图 ✅
| 文件路径 | 任务 | 优先级 | 状态 |
|---------|------|--------|------|
| `web/src/views/BacktestView.vue` | 回测主视图 | P0 | ✅ |
| `web/src/components/backtest/BacktestForm.vue` | 回测表单 | P0 | ✅ |
| `web/src/components/backtest/BacktestResults.vue` | 结果展示 | P0 | ✅ |
| `web/src/components/backtest/BacktestTaskList.vue` | 任务列表 | P0 | ✅ |
| `web/src/api/backtest.ts` | 回测API客户端 | P1 | ✅ |

**Phase 2 交付标准**：
- [x] 支持策略回测任务创建
- [x] 回测结果展示（收益曲线、指标）
- [x] 支持多策略对比
- [x] 滑点和手续费计算
- [x] 任务状态管理

---

### Phase 3：策略管理（Week 5-6）
**目标**：实现策略的CRUD、参数优化、版本管理

#### 3.1 策略管理后端
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `src/strategy/manager.py` | 完善策略生命周期管理 | P0 | 4h |
| `src/strategy/optimizer/` | 策略参数优化（网格搜索/遗传算法） | P1 | 8h |
| `src/api/v1/endpoints/strategies.py` | 完善策略API | P0 | 3h |

#### 3.2 策略管理前端
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `web/src/views/StrategyView.vue` | 重构为真实策略管理 | P0 | 6h |
| `web/src/api/strategy.ts` | 策略API客户端（恢复） | P0 | 2h |
| `web/src/stores/strategy.ts` | 策略状态管理（恢复） | P0 | 2h |

**Phase 3 交付标准**：
- [ ] 策略创建/编辑/删除
- [ ] 策略参数优化
- [ ] 策略与回测结果关联

---

### Phase 4：实盘监控（Week 7-8）
**目标**：实现实盘模式下的信号监控和自动交易

#### 4.1 实盘引擎
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `src/core/live_cabinet.py` | 实盘模式管理 | P0 | 4h |
| `src/api/v1/endpoints/live.py` | 完善实盘监控API | P0 | 3h |

#### 4.2 自动交易
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `src/ministries/bing_bu_war.py` | 交易执行部（兵部）实现 | P0 | 4h |
| `src/execution/engine.py` | 执行引擎完善 | P1 | 3h |

#### 4.3 前端实盘视图
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `web/src/views/LiveView.vue` | 新建实盘监控视图（新增） | P0 | 6h |
| `web/src/stores/monitoring.ts` | 监控状态管理（恢复） | P0 | 2h |

**Phase 4 交付标准**：
- [ ] 实盘模式启动/停止
- [ ] 实时信号推送
- [ ] 自动/手动下单切换

---

### Phase 5：风控系统完善（Week 9）
**目标**：完善风险控制和止损止盈

#### 5.1 风控规则
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `src/risk/risk_manager.py` | 风险规则引擎完善 | P0 | 6h |
| `src/risk/stop_loss.py` | 止损止盈执行 | P0 | 4h |
| `src/ministries/xing_bu_justice.py` | 风控部（刑部）实现 | P1 | 3h |

#### 5.2 前端风控视图
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `web/src/views/RiskView.vue` | 重构为真实风控管理 | P0 | 4h |

**Phase 5 交付标准**：
- [ ] 多维度风控规则配置
- [ ] 自动止损止盈执行
- [ ] 风险预警通知

---

### Phase 6：智能分析（Week 10-11）
**目标**：实现AI驱动的智能选股和分析

#### 6.1 智能分析后端
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `src/intelligence/fundamental/analyzer.py` | 基本面分析实现 | P1 | 6h |
| `src/intelligence/screening/screener.py` | 智能选股引擎 | P1 | 6h |
| `src/intelligence/screening/factors.py` | 因子计算 | P1 | 4h |
| `src/api/v1/endpoints/intelligence.py` | 智能分析API完善 | P1 | 3h |

#### 6.2 前端智能分析
| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `web/src/components/dashboard/AIRecommendations.vue` | AI推荐组件实现 | P1 | 4h |
| `web/src/views/ScreenerView.vue` | 选股器完善 | P1 | 4h |

**Phase 6 交付标准**：
- [ ] 智能选股结果
- [ ] 基本面分析报告
- [ ] AI交易建议

---

### Phase 7：报告系统（Week 12）
**目标**：完善交易报告和业绩归因

| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `src/reports/generator.py` | 报告生成器实现 | P1 | 4h |
| `src/reports/metrics.py` | 业绩指标计算 | P1 | 3h |
| `src/reports/export.py` | 报告导出（PDF/Excel） | P2 | 4h |
| `web/src/views/ReportsView.vue` | 报告视图完善 | P1 | 4h |

---

### Phase 8：测试与优化（Week 13-14）
**目标**：提升代码质量和测试覆盖

| 文件路径 | 任务 | 优先级 | 预估工时 |
|---------|------|--------|----------|
| `tests/unit/` | 单元测试覆盖 | P1 | 12h |
| `tests/integration/` | 集成测试 | P1 | 8h |
| `tests/e2e/` | E2E测试（Playwright） | P2 | 8h |
| 性能优化 | 数据库查询优化 | P1 | 4h |
| 性能优化 | 前端懒加载 | P2 | 2h |

---

## 📊 迭代总览

| Phase | 周期 | 核心目标 | 关键交付 |
|-------|------|----------|----------|
| Phase 1 | Week 1 | 交易闭环 | 能下单、能持仓 |
| Phase 1.5 | Week 2 | 功能优化 | 状态可追踪、风控完善 |
| Phase 2 | Week 3-4 | 回测系统 | 能回测策略 |
| Phase 3 | Week 5-6 | 策略管理 | 能管理策略 |
| Phase 4 | Week 7-8 | 实盘监控 | 能实盘运行 |
| Phase 5 | Week 9 | 风控完善 | 能控制风险 |
| Phase 6 | Week 10-11 | 智能分析 | 能智能选股 |
| Phase 7 | Week 12 | 报告系统 | 能生成报告 |
| Phase 8 | Week 13-14 | 测试优化 | 质量保障 |

**总计：约14周（3.5个月）完成核心功能**

---

## 🎯 当前迭代（Next Sprint）

### Sprint 1：交易闭环（Week 1）

#### Day 1-2：数据库与连接
```
src/common/database.py      [NEW] 数据库连接池
src/models/base.py          [MODIFY] 完善get_db
scripts/init_database.py    [MODIFY] 初始化脚本完善
```

#### Day 3-4：三省六部核心
```
src/core/crown_prince.py    [NEW] 太子院-数据校验
src/core/zhongshu_sheng.py  [NEW] 中书省-信号生成
```

#### Day 5-6：风控与执行
```
src/core/menxia_sheng.py    [NEW] 门下省-风控审核
src/core/shangshu_sheng.py  [NEW] 尚书省-执行调度
```

#### Day 7：联调测试 ✅
- 信号生成 → 风控审核 → 订单执行的完整链路测试
- 修复信号去重逻辑（基于信号内容而非时间戳）
- 修复异步回调等待问题（使用 await 等待回调完成）
- 测试覆盖：Tick校验、代码标准化、禁售拦截、信号生成、风控审核、订单执行、持仓更新

---

## 📈 进度追踪

使用方式：
1. 每个Phase开始前，创建对应的Todo List
2. 每天更新文件完成状态
3. 每个Phase结束后进行复盘

状态标记：
- `⬜` 未开始
- `🟡` 进行中
- `✅` 已完成
- `❌` 阻塞/延期

---

## 📝 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2026-04-12 | v1.0 | 初始版本，基于当前代码结构制定 |

---

**使用说明**：
1. 将此文件作为项目开发的北极星指标
2. 每个迭代开始前，据此制定详细任务列表
3. 遇到需求变更时，优先更新此文档再调整代码
4. 定期回顾（建议每周一次），确保方向正确
