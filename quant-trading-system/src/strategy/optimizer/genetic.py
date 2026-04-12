"""
遗传算法优化器
"""
import random
import asyncio
from typing import List, Dict, Any
from decimal import Decimal

from src.strategy.optimizer.base import BaseOptimizer, OptimizationResult, ParameterSpace


class GeneticOptimizer(BaseOptimizer):
    """遗传算法优化器"""

    def __init__(
        self,
        *args,
        population_size: int = 20,
        generations: int = 10,
        crossover_rate: float = 0.8,
        mutation_rate: float = 0.1,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate

        self.population: List[Dict[str, Any]] = []
        self.fitness_scores: List[float] = []

    async def optimize(self, max_iterations: int = None) -> List[OptimizationResult]:
        """
        执行遗传算法优化
        """
        print(f"遗传算法: 种群大小={self.population_size}, 迭代次数={self.generations}")

        # 初始化种群
        self._initialize_population()

        # 迭代进化
        for generation in range(self.generations):
            print(f"\n第 {generation + 1}/{self.generations} 代")

            # 评估适应度
            await self._evaluate_population()

            # 记录最优解
            best_idx = self.fitness_scores.index(max(self.fitness_scores))
            best_params = self.population[best_idx]
            best_fitness = self.fitness_scores[best_idx]
            print(f"  最优适应度: {best_fitness:.4f}, 参数: {best_params}")

            # 选择、交叉、变异
            if generation < self.generations - 1:  # 最后一代不进化
                self._evolve()

        # 最终评估并返回结果
        await self._evaluate_population()
        self._create_results()

        return self.results

    def _initialize_population(self):
        """初始化种群"""
        for _ in range(self.population_size):
            individual = {}
            for name, space in self.parameter_spaces.items():
                individual[name] = self._random_param_value(space)
            self.population.append(individual)

    def _random_param_value(self, space: ParameterSpace) -> Any:
        """生成随机参数值"""
        if space.param_type == "int":
            return random.randint(space.min_value, space.max_value)
        elif space.param_type == "float":
            return random.uniform(space.min_value, space.max_value)
        elif space.param_type == "choice":
            return random.choice(space.choices)

    async def _evaluate_population(self):
        """评估种群适应度"""
        self.fitness_scores = []

        for individual in self.population:
            try:
                metrics = await self.evaluation_func(individual)
                fitness = metrics.get(self.objective_metric, 0)
                self.fitness_scores.append(fitness)
            except Exception as e:
                print(f"评估失败: {e}")
                self.fitness_scores.append(float('-inf') if self.maximize else float('inf'))

    def _evolve(self):
        """进化一代"""
        new_population = []

        # 精英保留（保留前20%）
        elite_size = max(1, self.population_size // 5)
        sorted_indices = sorted(
            range(len(self.fitness_scores)),
            key=lambda i: self.fitness_scores[i],
            reverse=self.maximize
        )

        for i in range(elite_size):
            new_population.append(self.population[sorted_indices[i]].copy())

        # 生成新个体
        while len(new_population) < self.population_size:
            # 选择
            parent1 = self._tournament_select()
            parent2 = self._tournament_select()

            # 交叉
            if random.random() < self.crossover_rate:
                child = self._crossover(parent1, parent2)
            else:
                child = parent1.copy()

            # 变异
            if random.random() < self.mutation_rate:
                child = self._mutate(child)

            new_population.append(child)

        self.population = new_population

    def _tournament_select(self) -> Dict[str, Any]:
        """锦标赛选择"""
        tournament_size = 3
        tournament_indices = random.sample(range(len(self.population)), tournament_size)

        best_idx = tournament_indices[0]
        for idx in tournament_indices[1:]:
            if self.fitness_scores[idx] > self.fitness_scores[best_idx]:
                best_idx = idx

        return self.population[best_idx].copy()

    def _crossover(self, parent1: dict, parent2: dict) -> dict:
        """交叉操作"""
        child = {}
        for key in parent1.keys():
            if random.random() < 0.5:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        return child

    def _mutate(self, individual: dict) -> dict:
        """变异操作"""
        mutated = individual.copy()
        param_name = random.choice(list(self.parameter_spaces.keys()))
        space = self.parameter_spaces[param_name]
        mutated[param_name] = self._random_param_value(space)
        return mutated

    def _create_results(self):
        """创建结果列表"""
        # 去重
        unique_params = []
        for individual in self.population:
            if individual not in unique_params:
                unique_params.append(individual)

        # 评估所有唯一参数
        self.results = []
        for i, params in enumerate(unique_params):
            idx = self.population.index(params)
            result = OptimizationResult(
                parameters=params,
                metrics={self.objective_metric: self.fitness_scores[idx]},
                rank=0
            )
            self.results.append(result)

        # 排序
        self.results.sort(
            key=lambda r: r.metrics.get(self.objective_metric, 0),
            reverse=self.maximize
        )

        for i, r in enumerate(self.results):
            r.rank = i + 1
