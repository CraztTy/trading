# 睿之兮量化交易系统 - 全面测试计划

## 📋 概述

本文档定义了L3级别量化交易系统的完整测试策略，覆盖三省六部架构、订单系统、撮合引擎及前端应用。

**测试目标**: 确保系统在高并发、低延迟场景下的稳定性、正确性和安全性

---

## 🎯 测试范围

### 1. 核心引擎模块 (Core Engine)

| 模块 | 文件 | 测试重点 |
|------|------|----------|
| 订单状态机 | `order_state_machine.py` | 状态流转、非法转换拦截、回调机制 |
| 撮合引擎 | `matching_engine.py` | 价格优先、时间优先、涨跌停限制、滑点计算 |
| 太子院 | `crown_prince.py` | 数据校验、前置过滤 |
| 中书省 | `zhongshu_sheng.py` | 信号生成、策略上下文管理 |
| 门下省 | `menxia_sheng.py` | 风控规则、熔断机制 |
| 尚书省 | `shangshu_sheng.py` | 资金清算、持仓管理、费用计算 |
| 回测引擎 | `backtest_cabinet.py` | 历史回放、业绩计算 |
| 实盘监控 | `live_cabinet.py` | 实时数据处理、信号推送 |

### 2. API服务模块

| 端点 | 文件 | 测试重点 |
|------|------|----------|
| 订单管理 | `orders.py` | CRUD、撤单、成交、批量操作 |
| 撮合接口 | `matching.py` | 撮合结果、价格更新 |
| 策略管理 | `strategies.py` | 策略CRUD、启停控制 |
| 回测接口 | `backtest.py` | 任务提交、结果查询 |
| 智能分析 | `intelligence.py` | 数据分析、报告生成 |

### 3. 前端应用 (Web Dashboard)

| 模块 | 路径 | 测试重点 |
|------|------|----------|
| 状态管理 | `stores/*.ts` | Pinia状态、WebSocket实时更新 |
| 视图组件 | `views/*.vue` | 渲染、交互、数据绑定 |
| 图表组件 | `components/charts/*.vue` | 数据可视化、实时更新 |

---

## 🧪 测试类型

### 1. 单元测试 (Unit Tests)

#### 1.1 订单状态机测试 (`tests/unit/test_order_state_machine.py`)

```python
# 测试覆盖点：

# 1. 合法状态流转
- CREATED → PENDING (SUBMIT事件)
- PENDING → PARTIAL (FILL_PARTIAL事件)
- PENDING → FILLED (FILL_FULL事件)
- PENDING → CANCELLED (CANCEL事件)
- PENDING → REJECTED (REJECT事件)
- PARTIAL → FILLED (FILL_FULL事件)
- PARTIAL → PARTIAL (FILL_PARTIAL事件)
- PARTIAL → CANCELLED (CANCEL事件)
- 任何活跃状态 → EXPIRED (EXPIRE事件)

# 2. 非法状态转换（应抛出异常）
- CREATED → FILLED (直接成交，非法)
- FILLED → CANCELLED (已成交后撤单，非法)
- REJECTED → PENDING (拒绝后提交，非法)
- CANCELLED → PARTIAL (撤单后成交，非法)

# 3. 终结状态检查
- 验证TERMINAL_STATES中状态不可转换
- FILLED, CANCELLED, REJECTED, EXPIRED

# 4. 回调机制
- 注册/注销回调函数
- 回调触发验证
- 回调异常处理（不应阻塞主流程）

# 5. 成交计算
- 部分成交数量计算
- 成交均价计算
- 成交金额累计
```

#### 1.2 撮合引擎测试 (`tests/unit/test_matching_engine.py`)

```python
# 测试覆盖点：

# 1. 撮合逻辑
- 价格优先原则（买单价高优先）
- 价格优先原则（卖单价低优先）
- 时间优先原则（同价格先委托先成交）

# 2. 涨跌停限制
- 涨停时买入订单被拒绝
- 跌停时卖出订单被拒绝
- 买入价格超过涨停价被拒绝
- 卖出价格低于跌停价被拒绝

# 3. 成交数量计算
- 小单（<10万）全额成交
- 大单部分成交（30%-100%随机）
- 成交数量对齐100股（A股最小单位）
- 不超过订单剩余数量

# 4. 滑点计算
- 买入滑点（成交价 ≥ 委托价）
- 卖出滑点（成交价 ≤ 委托价）
- 滑点率配置生效

# 5. 市场数据模拟器
- 基准价格设置
- 价格变动模拟（-1% ~ +1%）
- 涨跌停价格计算（10%限制）
```

#### 1.3 风控模块测试 (`tests/unit/test_risk_management.py`)

```python
# 门下省风控测试：

# 1. 止损检查
- 止损比例在限制内通过
- 止损比例超限被拒绝

# 2. 单票仓位检查
- 仓位在限制内通过
- 单票仓位超限被拒绝
- 卖出订单跳过检查

# 3. 总仓位检查
- 总仓位在限制内通过
- 总仓位超限被拒绝

# 4. 日亏损熔断
- 日亏损在限制内通过
- 日亏损超限触发熔断

# 5. 连续亏损检查
- 连续亏损次数在限制内通过
- 连续亏损超限暂停开仓

# 6. 委托频率限制
- 1分钟内同股票只能委托一次
- 不同股票不受限制
```

#### 1.4 资金清算测试 (`tests/unit/test_clearing.py`)

```python
# 尚书省清算测试：

# 1. 费用计算
- 佣金计算（最低5元）
- 印花税计算（仅卖出）
- 过户费计算
- 总费用汇总

# 2. 资金变动
- 买入扣减资金（含费用）
- 卖出增加资金（扣减费用）
- 资金不足拒绝交易

# 3. 持仓管理
- 买入增加持仓（计算平均成本）
- 卖出减少持仓
- 持仓不足拒绝交易
- 持仓为0时删除记录

# 4. 止盈止损检查
- 价格触及止损线生成卖出信号
- 价格触及止盈线生成卖出信号
```

### 2. 集成测试 (Integration Tests)

#### 2.1 订单全流程测试 (`tests/integration/test_order_lifecycle.py`)

```python
# 测试场景：

# 1. 完整订单生命周期
创建订单 → 提交订单 → 部分成交 → 全部成交
创建订单 → 提交订单 → 撤单
创建订单 → 提交订单 → 被拒绝

# 2. 并发订单处理
- 多订单同时提交
- 多订单同时成交
- 资金/持仓竞争条件测试

# 3. 错误恢复
- 数据库连接断开恢复
- 部分成交后系统重启
- 状态机持久化与恢复
```

#### 2.2 三省协同测试 (`tests/integration/test_three_provinces.py`)

```python
# 中书省 → 门下省 → 尚书省 流程测试：

# 1. 正常信号流程
生成信号 → 风控通过 → 执行成交

# 2. 风控拦截流程
生成信号 → 风控拒绝 → 不执行

# 3. 批量信号处理
生成多个信号 → 批量风控检查 → 批量执行

# 4. 策略上下文传递
- 策略状态在组件间正确传递
- 持仓信息在风控中使用
```

#### 2.3 API集成测试 (`tests/integration/test_api_endpoints.py`)

```python
# 端到端API测试：

# 1. 订单API流程
POST /orders/ → 创建订单
GET /orders/{id} → 查询订单
POST /orders/{id}/fill → 模拟成交
POST /orders/{id}/cancel → 撤单

# 2. 批量操作
POST /orders/account/{id}/cancel-all → 批量撤单

# 3. 错误处理
- 404 订单不存在
- 400 参数错误
- 409 状态冲突（已成交订单撤单）
```

### 3. 端到端测试 (E2E Tests)

#### 3.1 回测全流程 (`tests/e2e/test_backtest_workflow.py`)

```python
# 测试场景：

# 1. 策略回测完整流程
上传策略 → 设置参数 → 启动回测 → 等待完成 → 查看报告

# 2. 多策略并行回测
同时启动多个回测任务 → 资源分配 → 结果隔离

# 3. 回测中断恢复
回测进行中重启 → 状态恢复 → 继续/重新执行
```

#### 3.2 实盘模拟交易 (`tests/e2e/test_live_trading.py`)

```python
# 测试场景：

# 1. 信号到成交完整链路
市场数据 → 策略信号 → 风控审核 → 订单提交 → 撮合成交 → 持仓更新

# 2. 实时监控
- WebSocket实时推送
- 订单状态变更通知
- 成交回报推送

# 3. 日终结算
- T+1结算模拟
- 持仓解冻
- 资金对账
```

### 4. 性能测试 (Performance Tests)

#### 4.1 撮合引擎性能 (`tests/performance/test_matching_performance.py`)

```python
# 测试指标：

# 1. 吞吐量
- 每秒处理订单数（目标: >10000 TPS）
- 每秒撮合成交数

# 2. 延迟
- 平均撮合延迟（目标: <1ms）
- P99延迟（目标: <5ms）
- P999延迟（目标: <10ms）

# 3. 并发能力
- 100并发用户
- 1000并发订单
- 10000并发订单

# 4. 稳定性
- 持续运行1小时
- 内存使用稳定
- 无内存泄漏
```

#### 4.2 API性能测试 (`tests/performance/test_api_performance.py`)

```python
# 测试场景：

# 1. 订单接口
- POST /orders/ 响应时间 < 50ms
- GET /orders/ 响应时间 < 30ms
- 支持1000 QPS

# 2. WebSocket推送
- 1000客户端同时连接
- 消息延迟 < 100ms
- 重连恢复时间 < 5s
```

### 5. 安全测试 (Security Tests)

#### 5.1 输入验证 (`tests/security/test_input_validation.py`)

```python
# 测试场景：

# 1. SQL注入防护
- 订单ID特殊字符
- 股票代码注入尝试

# 2. XSS防护
- 股票名称脚本注入
- 错误信息HTML注入

# 3. 参数边界
- 超大数量（整数溢出）
- 负数价格/数量
- 空值处理
```

#### 5.2 权限控制 (`tests/security/test_authorization.py`)

```python
# 测试场景：

# 1. 跨账户访问
- 用户A访问用户B的订单（应拒绝）
- 未认证访问（应拒绝）

# 2. 操作权限
- 普通用户删除他人订单（应拒绝）
- 只读用户创建订单（应拒绝）
```

---

## 📁 测试文件结构

```
tests/
├── conftest.py                    # 全局pytest配置
├── fixtures/                      # 测试 fixtures
│   ├── __init__.py
│   ├── orders.py                  # 订单相关fixtures
│   ├── accounts.py                # 账户相关fixtures
│   ├── market_data.py             # 市场数据fixtures
│   └── database.py                # 数据库fixtures
├── unit/                          # 单元测试
│   ├── __init__.py
│   ├── test_order_state_machine.py
│   ├── test_matching_engine.py
│   ├── test_risk_management.py
│   ├── test_clearing.py
│   ├── test_crown_prince.py
│   ├── test_zhongshu_sheng.py
│   ├── test_menxia_sheng.py
│   ├── test_shangshu_sheng.py
│   ├── test_models.py
│   └── test_enums.py
├── integration/                   # 集成测试
│   ├── __init__.py
│   ├── test_order_lifecycle.py
│   ├── test_three_provinces.py
│   ├── test_api_endpoints.py
│   ├── test_database.py
│   └── test_websocket.py
├── e2e/                          # 端到端测试
│   ├── __init__.py
│   ├── test_backtest_workflow.py
│   ├── test_live_trading.py
│   └── test_deployment.py
├── performance/                  # 性能测试
│   ├── __init__.py
│   ├── test_matching_performance.py
│   ├── test_api_performance.py
│   ├── test_database_performance.py
│   └── benchmarks/
├── security/                     # 安全测试
│   ├── __init__.py
│   ├── test_input_validation.py
│   ├── test_authorization.py
│   └── test_rate_limiting.py
└── frontend/                     # 前端测试
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## ⚙️ 测试配置

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --tb=short
    --color=yes
    -v
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
    security: 安全测试
    performance: 性能测试
    skip_ci: CI环境跳过
```

### 测试数据库配置

```python
# tests/conftest.py

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 使用内存数据库进行单元测试
TEST_DATABASE_URL = "postgresql+asyncpg://quant_user:quant_pass@localhost:5432/quant_test"

@pytest_asyncio.fixture(scope="session")
async def engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(engine):
    """创建数据库会话"""
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
```

---

## 🚀 执行命令

```bash
# 运行所有测试
pytest

# 仅单元测试
pytest -m unit

# 仅集成测试
pytest -m integration

# 端到端测试
pytest -m e2e

# 性能测试
pytest -m performance --benchmark-only

# 安全测试
pytest -m security

# 带覆盖率报告
pytest --cov=src --cov-report=html --cov-report=term

# 并行执行
pytest -n auto

# 特定文件
pytest tests/unit/test_order_state_machine.py -v

# 特定测试
pytest tests/unit/test_order_state_machine.py::TestOrderStateMachine::test_created_to_pending -v
```

---

## 📊 测试覆盖率目标

| 模块 | 目标覆盖率 | 关键文件 |
|------|-----------|----------|
| 订单状态机 | 100% | `order_state_machine.py` |
| 撮合引擎 | 95% | `matching_engine.py` |
| 风控模块 | 95% | `menxia_sheng.py` |
| 资金清算 | 95% | `shangshu_sheng.py` |
| 策略信号 | 90% | `zhongshu_sheng.py` |
| API端点 | 90% | `endpoints/*.py` |
| 数据模型 | 90% | `models/*.py` |
| 整体 | >90% | - |

---

## 🔧 测试工具

| 工具 | 用途 | 版本 |
|------|------|------|
| pytest | 测试框架 | ^7.4 |
| pytest-asyncio | 异步测试 | ^0.21 |
| pytest-cov | 覆盖率 | ^4.1 |
| pytest-benchmark | 性能测试 | ^4.0 |
| pytest-xdist | 并行执行 | ^3.5 |
| factory-boy | 测试数据生成 | ^3.3 |
| faker | 假数据 | ^22.0 |
| httpx | 异步HTTP测试 | ^0.26 |
| websockets | WebSocket测试 | ^12.0 |

---

## 📝 测试规范

### 命名规范

- 测试文件: `test_<module_name>.py`
- 测试类: `Test<ClassName>` 或 `Test<Feature>`
- 测试函数: `test_<scenario>_<expected_result>`

### 示例

```python
# tests/unit/test_order_state_machine.py

class TestOrderStateMachine:
    """订单状态机测试"""

    def test_created_to_pending_on_submit(self):
        """提交事件：CREATED → PENDING"""
        # Arrange
        order = create_test_order()
        sm = OrderStateMachine(order)

        # Act
        result = sm.transition(OrderEvent.SUBMIT)

        # Assert
        assert result is True
        assert order.status == OrderStatus.PENDING

    def test_filled_to_cancelled_raises_error(self):
        """已成交订单撤单应抛出异常"""
        # Arrange
        order = create_test_order(status=OrderStatus.FILLED)
        sm = OrderStateMachine(order)

        # Act & Assert
        with pytest.raises(InvalidStateTransition):
            sm.transition(OrderEvent.CANCEL)
```

---

## 🐛 故障排查

### 常见问题

1. **异步测试失败**
   - 确保使用 `pytest-asyncio` 装饰器
   - 检查 `async/await` 使用正确

2. **数据库测试隔离失败**
   - 使用 `db_session` fixture
   - 确保每个测试后回滚事务

3. **性能测试不稳定**
   - 关闭其他应用程序
   - 使用专用测试环境
   - 多次运行取平均值

---

## 📅 测试计划时间线

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| Phase 1 | 单元测试框架搭建 + 核心模块测试 | 3天 |
| Phase 2 | 集成测试开发 | 2天 |
| Phase 3 | 端到端测试开发 | 2天 |
| Phase 4 | 性能测试基准建立 | 1天 |
| Phase 5 | 安全测试 | 1天 |
| Phase 6 | CI/CD集成 | 1天 |
| **总计** | | **10天** |

---

*最后更新: 2026-04-10*
