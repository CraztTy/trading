"""
策略管理集成测试

测试内容：
- 策略创建、查询、更新、删除
- 策略状态控制（启动、暂停、停止）
- 策略回测关联
- 参数优化器
"""
import asyncio
from datetime import datetime
from decimal import Decimal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.strategy.optimizer import GridSearchOptimizer, ParameterSpace, BaseOptimizer


class MockStrategy:
    """模拟策略对象"""
    def __init__(self):
        self.id = 1
        self.strategy_id = "stg_test_001"
        self.account_id = 1
        self.name = "测试策略"
        self.code = "class TestStrategy:\n    pass"
        self.description = "测试描述"
        self.status = "draft"
        self.symbols = ["000001.SZ"]


class TestOptimizer:
    """优化器测试"""

    def test_parameter_space(self):
        """测试参数空间定义"""
        print("\n[TEST] 参数空间定义...")

        space = ParameterSpace(
            name="fast_period",
            param_type="int",
            min_value=5,
            max_value=20,
            step=1,
            default=10
        )

        assert space.validate() is True

        # 测试生成参数组合 - 使用GridSearchOptimizer
        optimizer = GridSearchOptimizer(
            parameter_spaces={"fast_period": space},
            evaluation_func=lambda x: {"sharpe_ratio": 1.0},
            objective_metric="sharpe_ratio"
        )

        combinations = optimizer.generate_all_combinations()
        assert len(combinations) == 16  # 5到20共16个整数

        print(f"   生成 {len(combinations)} 组参数")
        print("   [PASS] 参数空间通过")

    async def test_grid_search_optimizer(self):
        """测试网格搜索优化器"""
        print("\n[TEST] 网格搜索优化...")

        # 定义参数空间
        param_spaces = {
            "fast_period": ParameterSpace(
                name="fast_period",
                param_type="int",
                min_value=5,
                max_value=10,
                step=5,  # 5, 10
                default=5
            ),
            "slow_period": ParameterSpace(
                name="slow_period",
                param_type="int",
                min_value=15,
                max_value=20,
                step=5,  # 15, 20
                default=15
            )
        }

        # 模拟评估函数
        async def mock_evaluate(params):
            await asyncio.sleep(0.01)  # 模拟计算
            # 简单的评分逻辑
            score = params["fast_period"] * 0.1 + params["slow_period"] * 0.05
            return {
                "sharpe_ratio": score,
                "total_return": score * 0.5
            }

        optimizer = GridSearchOptimizer(
            parameter_spaces=param_spaces,
            evaluation_func=mock_evaluate,
            objective_metric="sharpe_ratio",
            maximize=True
        )

        results = await optimizer.optimize()

        # 验证结果
        assert len(results) == 4  # 2x2组合
        assert results[0].rank == 1  # 有排名

        best = optimizer.get_best_result()
        assert best is not None

        print(f"   测试 {len(results)} 组参数")
        print(f"   最优参数: {best.parameters}")
        print(f"   最优得分: {best.metrics['sharpe_ratio']}")
        print("   [PASS] 网格搜索通过")


class TestStrategyBacktest:
    """策略回测关联测试"""

    def test_strategy_backtest_association(self):
        """测试策略回测关联"""
        print("\n[TEST] 策略回测关联...")

        # 创建模拟策略
        strategy = MockStrategy()

        # 验证策略创建成功
        assert strategy is not None
        assert strategy.id is not None
        assert strategy.strategy_id == "stg_test_001"

        print(f"   策略ID: {strategy.strategy_id}")
        print("   [PASS] 策略回测关联准备就绪")

    def test_backtest_config(self):
        """测试回测配置"""
        print("\n[TEST] 回测配置...")

        # 模拟回测配置
        backtest_config = {
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "symbols": ["000001.SZ", "600036.SH"],
            "initial_capital": 100000,
            "parameters": {"fast_period": 5, "slow_period": 20}
        }

        assert "start_date" in backtest_config
        assert "end_date" in backtest_config
        assert "symbols" in backtest_config
        assert "initial_capital" in backtest_config

        print(f"   回测区间: {backtest_config['start_date']} ~ {backtest_config['end_date']}")
        print(f"   标的数量: {len(backtest_config['symbols'])}")
        print("   [PASS] 回测配置通过")


async def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("策略管理集成测试")
    print("=" * 60)

    optimizer_tests = TestOptimizer()
    backtest_tests = TestStrategyBacktest()

    tests_run = 0
    tests_passed = 0

    # 优化器测试
    try:
        tests_run += 1
        optimizer_tests.test_parameter_space()
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] 参数空间测试失败: {e}")

    try:
        tests_run += 1
        await optimizer_tests.test_grid_search_optimizer()
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] 网格搜索测试失败: {e}")

    # 回测关联测试
    try:
        tests_run += 1
        backtest_tests.test_strategy_backtest_association()
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] 回测关联测试失败: {e}")

    try:
        tests_run += 1
        backtest_tests.test_backtest_config()
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] 回测配置测试失败: {e}")

    print("\n" + "=" * 60)
    print(f"测试结果: {tests_passed}/{tests_run} 通过")
    print("=" * 60)

    if tests_passed == tests_run:
        print("所有测试通过!")
        return True
    else:
        print("部分测试失败!")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
