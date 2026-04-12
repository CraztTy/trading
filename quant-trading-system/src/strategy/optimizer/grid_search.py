"""
网格搜索优化器
"""
import asyncio
from typing import List
from decimal import Decimal

from src.strategy.optimizer.base import BaseOptimizer, OptimizationResult, ParameterSpace


class GridSearchOptimizer(BaseOptimizer):
    """网格搜索优化器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_iteration = 0
        self.total_iterations = 0

    async def optimize(self, max_iterations: int = None) -> List[OptimizationResult]:
        """
        执行网格搜索优化

        遍历所有参数组合，评估性能，返回排序后的结果
        """
        # 生成所有参数组合
        combinations = self.generate_all_combinations()
        self.total_iterations = len(combinations)

        if max_iterations and self.total_iterations > max_iterations:
            # 如果组合太多，随机采样
            import random
            combinations = random.sample(combinations, max_iterations)
            self.total_iterations = len(combinations)

        print(f"网格搜索: 共 {self.total_iterations} 组参数需要评估")

        # 评估每个参数组合
        for params in combinations:
            self.current_iteration += 1

            try:
                # 执行回测评估
                metrics = await self._evaluate_params(params)

                result = OptimizationResult(
                    parameters=params,
                    metrics=metrics,
                    rank=0  # 稍后计算
                )
                self.results.append(result)

                print(f"  [{self.current_iteration}/{self.total_iterations}] "
                      f"Params: {params} -> {self.objective_metric}: {metrics.get(self.objective_metric, 'N/A')}")

            except Exception as e:
                print(f"  [{self.current_iteration}/{self.total_iterations}] 评估失败: {e}")
                continue

        # 排序结果
        self._rank_results()

        return self.results

    async def _evaluate_params(self, params: dict) -> dict:
        """评估一组参数"""
        # 调用评估函数
        return await self.evaluation_func(params)

    def _rank_results(self):
        """对结果进行排名"""
        if not self.results:
            return

        # 按目标指标排序
        sorted_results = sorted(
            self.results,
            key=lambda r: r.metrics.get(self.objective_metric, float('-inf') if self.maximize else float('inf')),
            reverse=self.maximize
        )

        # 设置排名
        for i, result in enumerate(sorted_results):
            result.rank = i + 1

        self.results = sorted_results

    def get_best_result(self) -> OptimizationResult:
        """获取最优结果"""
        if not self.results:
            return None
        return self.results[0]

    def get_top_results(self, n: int = 10) -> List[OptimizationResult]:
        """获取前N个结果"""
        return self.results[:n]
