"""
网格搜索优化器

通过穷举参数空间中的所有组合来找到最优参数
适用于参数空间较小的情况
"""
from datetime import datetime
from itertools import product
from typing import Dict, List, Any
import asyncio

from src.strategy.optimizer.base import Optimizer, OptimizationResult, ParameterSpace
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class GridSearchOptimizer(Optimizer):
    """
    网格搜索优化器

    特点：
    - 穷举所有参数组合
    - 找到全局最优解（在离散网格上）
    - 计算成本高，适合小参数空间
    """

    def __init__(self, param_space: List[ParameterSpace], config):
        super().__init__(param_space, config)
        self._iteration = 0

    def _generate_combinations(self) -> List[Dict[str, Any]]:
        """
        生成所有参数组合

        Returns:
            参数组合列表
        """
        # 获取每个参数的网格值
        grid_values = [p.get_grid_values() for p in self.param_space]

        # 生成笛卡尔积
        combinations = []
        for values in product(*grid_values):
            params = {
                self.param_space[i].name: values[i]
                for i in range(len(self.param_space))
            }
            combinations.append(params)

        logger.info(f"网格搜索: 生成 {len(combinations)} 个参数组合")
        return combinations

    async def optimize(
        self,
        strategy_class,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> OptimizationResult:
        """
        执行网格搜索优化

        Args:
            strategy_class: 策略类
            symbols: 交易标的
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            OptimizationResult: 优化结果
        """
        start_time = datetime.now()

        # 生成所有参数组合
        combinations = self._generate_combinations()

        # 限制迭代次数
        if len(combinations) > self.config.max_iterations:
            logger.warning(
                f"参数组合数 ({len(combinations)}) 超过最大迭代次数 "
                f"({self.config.max_iterations})，将随机采样"
            )
            import random
            combinations = random.sample(combinations, self.config.max_iterations)

        # 初始化结果
        result = OptimizationResult(
            best_params={},
            best_score=float('-inf') if self.config.direction == "maximize" else float('inf'),
            objective=self.config.objective
        )

        # 遍历所有组合
        for i, params in enumerate(combinations):
            self._iteration = i + 1

            try:
                # 评估参数
                score, metrics = await self._evaluate_params(
                    strategy_class, params, symbols, start_date, end_date
                )

                # 记录迭代
                result.add_iteration(
                    iteration=self._iteration,
                    params=params,
                    score=score,
                    metrics={
                        "sharpe_ratio": metrics.sharpe_ratio,
                        "total_return": metrics.total_return,
                        "max_drawdown": metrics.max_drawdown,
                    }
                )

                # 更新最佳结果
                if self._is_better(score):
                    self._update_best(score, params)
                    result.best_params = params
                    result.best_score = score

                    logger.info(
                        f"第 {self._iteration}/{len(combinations)} 轮: "
                        f"找到更好的参数，得分 = {score:.4f}"
                    )

                # 检查早停
                if self._should_stop_early():
                    logger.info(f"早停触发，已迭代 {self._iteration} 次")
                    break

            except Exception as e:
                logger.error(f"评估参数失败: {e}, params={params}")
                continue
        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()
        result.duration_seconds = duration

        logger.info(
            f"网格搜索完成: 共 {result.total_iterations} 次迭代, "
            f"耗时 {duration:.1f}秒, 最佳得分 = {result.best_score:.4f}"
        )

        return result
