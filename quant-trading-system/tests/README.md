# 睿之兮量化交易系统 - 测试套件

## 📋 测试计划概览

本测试套件覆盖L3级别量化交易系统的核心模块，包括三省六部架构、订单系统、撮合引擎等。

## 🗂️ 测试结构

```
tests/
├── conftest.py                    # 全局pytest配置和fixtures
├── unit/                          # 单元测试
│   ├── test_order_state_machine.py    # 订单状态机测试
│   ├── test_matching_engine.py        # 撮合引擎测试
│   ├── test_risk_management.py        # 风控模块测试
│   └── ...
├── integration/                   # 集成测试
│   ├── test_order_lifecycle.py        # 订单生命周期测试
│   ├── test_three_provinces.py        # 三省协同测试
│   └── ...
├── e2e/                          # 端到端测试
├── performance/                  # 性能测试
│   └── test_matching_performance.py   # 撮合性能测试
├── security/                     # 安全测试
│   └── test_input_validation.py       # 输入验证测试
└── frontend/                     # 前端测试 (位于web/src/)
```

## 🚀 快速开始

### 安装测试依赖

```bash
cd quant-trading-system
pip install -e ".[dev]"
```

### 运行测试

```bash
# 使用测试脚本
python scripts/run_tests.py unit          # 单元测试
python scripts/run_tests.py integration   # 集成测试
python scripts/run_tests.py fast          # 快速测试（推荐）
python scripts/run_tests.py coverage      # 测试+覆盖率

# 直接使用pytest
pytest -m unit              # 仅单元测试
pytest -m integration       # 仅集成测试
pytest -m "not slow"        # 排除慢速测试
pytest -n auto              # 并行执行
pytest -v                   # 详细输出
```

## 🧪 测试覆盖模块

| 模块 | 类型 | 测试文件 | 覆盖率目标 |
|------|------|----------|-----------|
| 订单状态机 | 单元 | `test_order_state_machine.py` | 100% |
| 撮合引擎 | 单元 | `test_matching_engine.py` | 95% |
| 风控模块 | 单元 | `test_risk_management.py` | 95% |
| 资金清算 | 单元 | `test_clearing.py` | 95% |
| 三省协同 | 集成 | `test_three_provinces.py` | 90% |
| 订单生命周期 | 集成 | `test_order_lifecycle.py` | 90% |
| 撮合性能 | 性能 | `test_matching_performance.py` | - |
| 输入验证 | 安全 | `test_input_validation.py` | - |

## 📊 性能测试指标

| 指标 | 目标值 | 测试文件 |
|------|--------|----------|
| 单笔撮合延迟 | < 1ms | `test_matching_performance.py` |
| P99延迟 | < 5ms | `test_matching_performance.py` |
| 吞吐量 | > 10000 TPS | `test_matching_performance.py` |
| 并发能力 | 10000订单/秒 | `test_matching_performance.py` |

## 🛡️ 安全测试覆盖

- SQL注入防护
- XSS防护
- 输入边界验证
- 速率限制
- 认证授权
- 跨账户访问控制

## 🔧 测试配置

### pytest.ini (已集成到pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: 单元测试",
    "integration: 集成测试",
    "e2e: 端到端测试",
    "slow: 慢速测试",
    "security: 安全测试",
    "performance: 性能测试",
]
```

## 📝 编写新测试

### 单元测试示例

```python
import pytest
from src.core.order_state_machine import OrderStateMachine, OrderEvent

@pytest.mark.unit
class TestOrderStateMachine:
    def test_created_to_pending_on_submit(self, mock_order):
        """测试: CREATED → PENDING"""
        sm = OrderStateMachine(mock_order)
        result = sm.transition(OrderEvent.SUBMIT)
        assert result is True
        assert mock_order.status == OrderStatus.PENDING
```

### 集成测试示例

```python
import pytest

@pytest.mark.integration
class TestOrderLifecycle:
    @pytest.mark.asyncio
    async def test_create_and_submit_order(self, order_service, account):
        """测试: 创建并提交订单"""
        order = await order_service.create_order(...)
        success = await order_service.submit_order(order)
        assert success is True
```

## 📈 覆盖率报告

```bash
# 生成HTML覆盖率报告
pytest --cov=src --cov-report=html

# 查看报告
open htmlcov/index.html
```

## 🐛 调试测试

```bash
# 在第一个失败处停止
pytest -x

# 进入PDB调试模式
pytest --pdb

# 详细输出
pytest -vvs

# 只运行特定测试
pytest tests/unit/test_order_state_machine.py::TestOrderStateMachine::test_created_to_pending
```

## 📅 CI/CD集成

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest -m "not slow" --cov=src --cov-fail-under=90
```

## 📚 参考文档

- [pytest文档](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [测试计划详情](../docs/TEST_PLAN.md)

---

*最后更新: 2026-04-10*
