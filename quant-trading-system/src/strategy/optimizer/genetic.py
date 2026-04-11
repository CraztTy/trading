"""
遗传算法优化器

使用遗传算法进行参数优化
适用于大规模参数空间
"""
import random
import copy
from datetime import datetime
from typing import Dict, List, Any, Tuple

from src.strategy.optimizer.base import (
    Optimizer, OptimizationResult, ParameterSpace, ParameterType
)
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class GeneticOptimizer(Optimizer):
    """
    遗传算法优化器

    特点：
    - 适用于大规模参数空间
    - 使用进化策略搜索全局最优
    - 支持离散和连续参数

    参数：
    - population_size: 种群大小
    - generations: 迭代代数
    - crossover_rate: 交叉概率
    - mutation_rate: 变异概率
    - elitism_ratio: 精英保留比例
    """

    def __init__(
        self,
        param_space: List[ParameterSpace],
        config,
        population_size: int = 30,
        generations: int = 50,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.1,
        elitism_ratio: float = 0.1
    ):
        super().__init__(param_space, config)
        self.population_size = population_size
        self.generations = min(generations, config.max_iterations // population_size)
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elitism_ratio = elitism_ratio

        # 种群和适应度
        self.population: List[Dict[str, Any]] = []
        self.fitness_scores: List[Tuple[Dict[str, Any], float]] = []

    def _initialize_population(self) -> None:
        """初始化种群"""
        self.population = []
        for _ in range(self.population_size):
            individual = self.sample_random_params()
            self.population.append(individual)

        logger.info(f"遗传算法: 初始化种群，大小 = {self.population_size}")

    async def _evaluate_population(
        self,
        strategy_class,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> None:
        """评估种群适应度"""
        self.fitness_scores = []

        for individual in self.population:
            try:
                score, metrics = await self._evaluate_params(
                    strategy_class, individual, symbols, start_date, end_date
                )
                self.fitness_scores.append((individual, score))
            except Exception as e:
                logger.error(f"评估个体失败: {e}")
                # 给失败的个体一个极差的分数
                bad_score = float('-inf') if self.config.direction == "maximize" else float('inf')
                self.fitness_scores.append((individual, bad_score))

        # 按适应度排序
        reverse = self.config.direction == "maximize"
        self.fitness_scores.sort(key=lambda x: x[1], reverse=reverse)

    def _select_parents(self, num_parents: int) -> List[Dict[str, Any]]:
        """
        选择父代（轮盘赌选择）

        Args:
            num_parents: 需要选择的父代数量

        Returns:
            父代列表
        """
        if not self.fitness_scores:
            return []

        # 使用锦标赛选择
        parents = []
        for _ in range(num_parents):
            # 随机选择3个进行锦标赛
            tournament = random.sample(self.fitness_scores, min(3, len(self.fitness_scores)))
            winner = max(tournament, key=lambda x: x[1])[0]
            parents.append(winner)

        return parents

    def _crossover(
        self,
        parent1: Dict[str, Any],
        parent2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        交叉操作

        Args:
            parent1: 父代1
            parent2: 父代2

        Returns:
            子代
        """
        if random.random() > self.crossover_rate:
            return copy.deepcopy(parent1)

        child = {}
        for param in self.param_space:
            # 均匀交叉：随机从两个父代中选择
            if random.random() < 0.5:
                child[param.name] = parent1[param.name]
            else:
                child[param.name] = parent2[param.name]

        return child

    def _mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """
        变异操作

        Args:
            individual: 个体

        Returns:
            变异后的个体
        """
        mutated = individual.copy()

        for param in self.param_space:
            if random.random() < self.mutation_rate:
                # 对该参数重新采样
                mutated[param.name] = param.sample()

        return mutated

    def _create_next_generation(self) -> None:
        """创建下一代"""
        new_population = []

        # 精英保留
        elite_count = int(self.population_size * self.elitism_ratio)
        elites = [ind for ind, _ in self.fitness_scores[:elite_count]]
        new_population.extend(copy.deepcopy(elites))

        # 生成新个体
        while len(new_population) < self.population_size:
            # 选择父代
            parents = self._select_parents(2)
            if len(parents) < 2:
                break

            # 交叉和变异
            child = self._crossover(parents[0], parents[1])
            child = self._mutate(child)

            new_population.append(child)

        self.population = new_population[:self.population_size]

    async def optimize(
        self,
        strategy_class,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> OptimizationResult:
        """
        执行遗传算法优化

        Args:
            strategy_class: 策略类
            symbols: 交易标的
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            OptimizationResult: 优化结果
        """
        start_time = datetime.now()

        # 初始化种群
        self._initialize_population()

        # 初始化结果
        result = OptimizationResult(
            best_params={},
            best_score=float('-inf') if self.config.direction == "maximize" else float('inf'),
            objective=self.config.objective
        )

        # 进化循环
        for generation in range(self.generations):
            logger.info(f"遗传算法: 第 {generation + 1}/{self.generations} 代")

            # 评估种群
            await self._evaluate_population(strategy_class, symbols, start_date, end_date)

            # 记录最佳个体
            best_individual, best_score = self.fitness_scores[0]
            result.add_iteration(
                iteration=generation + 1,
                params=best_individual,
                score=best_score
            )

            # 更新全局最优
            if self._is_better(best_score):
                self._update_best(best_score, best_individual)
                result.best_params = best_individual
                result.best_score = best_score
                logger.info(f"  找到更好的解，得分 = {best_score:.4f}")

            # 检查早停
            if self._should_stop_early():
                logger.info(f"早停触发，已进化 {generation + 1} 代")
                break

            # 创建下一代
            if generation < self.generations - 1:
                self._create_next_generation()

        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()
        result.duration_seconds = duration

        logger.info(
            f"遗传算法完成: 共 {result.total_iterations} 代, "
            f"耗时 {duration:.1f}秒, 最佳得分 = {result.best_score:.4f}"
        )

        return result
