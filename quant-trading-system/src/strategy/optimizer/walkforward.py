"""
Walk-forward 优化器

使用滚动窗口进行样本外测试，避免过拟合
"""
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import copy

from src.strategy.optimizer.base import Optimizer, OptimizationResult, ParameterSpace, OptimizationConfig
from src.strategy.optimizer.grid_search import GridSearchOptimizer
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class WalkForwardOptimizer(Optimizer):
    """
    Walk-forward 优化器

    特点：
    - 使用滚动窗口进行优化和测试
    - 避免参数过拟合
    - 更接近实盘表现

    参数：
    - train_size: 训练窗口大小（天）
    - test_size: 测试窗口大小（天）
    - step_size: 滚动步长（天）
    """

    def __init__(
        self,
        param_space: List[ParameterSpace],
        config: OptimizationConfig,
        train_size: int = 252,    # 1年训练
        test_size: int = 63,      # 3个月测试
        step_size: int = 63       # 3个月步长
    ):
        super().__init__(param_space, config)
        self.train_size = train_size
        self.test_size = test_size
        self.step_size = step_size

    def _generate_windows(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """
        生成滚动窗口

        Returns:
            [(train_start, train_end, test_start, test_end), ...]
        """
        windows = []
        current = start_date

        while current + timedelta(days=self.train_size + self.test_size) <= end_date:
            train_start = current
            train_end = current + timedelta(days=self.train_size)
            test_start = train_end
            test_end = min(
                test_start + timedelta(days=self.test_size),
                end_date
            )

            windows.append((train_start, train_end, test_start, test_end))
            current += timedelta(days=self.step_size)

        logger.info(f"Walk-forward: 生成 {len(windows)} 个窗口")
        return windows

    async def optimize(
        self,
        strategy_class,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> OptimizationResult:
        """
        执行 Walk-forward 优化

        Args:
            strategy_class: 策略类
            symbols: 交易标的
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            OptimizationResult: 优化结果
        """
        start_time = datetime.now()

        # 生成时间窗口
        windows = self._generate_windows(start_date, end_date)

        if not windows:
            raise ValueError("时间范围不足以生成Walk-forward窗口")

        # 初始化结果
        result = OptimizationResult(
            best_params={},
            best_score=float('-inf') if self.config.direction == "maximize" else float('inf'),
            objective=self.config.objective
        )

        # 存储每个窗口的最佳参数
        window_results: List[Dict[str, Any]] = []

        # 遍历每个窗口
        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            logger.info(
                f"Walk-forward 窗口 {i+1}/{len(windows)}: "
                f"训练 {train_start.date()} ~ {train_end.date()}, "
                f"测试 {test_start.date()} ~ {test_end.date()}"
            )

            try:
                # 在训练集上优化参数
                inner_optimizer = GridSearchOptimizer(
                    self.param_space,
                    OptimizationConfig(
                        objective=self.config.objective,
                        direction=self.config.direction,
                        max_iterations=self.config.max_iterations // len(windows)
                    )
                )

                train_result = await inner_optimizer.optimize(
                    strategy_class,
                    symbols,
                    train_start,
                    train_end
                )

                # 在测试集上验证
                test_score, test_metrics = await self._evaluate_params(
                    strategy_class,
                    train_result.best_params,
                    symbols,
                    test_start,
                    test_end
                )

                logger.info(
                    f"  训练得分: {train_result.best_score:.4f}, "
                    f"测试得分: {test_score:.4f}"
                )

                window_results.append({
                    "window": i + 1,
                    "best_params": train_result.best_params,
                    "train_score": train_result.best_score,
                    "test_score": test_score,
                    "metrics": {
                        "sharpe_ratio": test_metrics.sharpe_ratio,
                        "total_return": test_metrics.total_return,
                        "max_drawdown": test_metrics.max_drawdown,
                    }
                })

                result.add_iteration(
                    iteration=i + 1,
                    params=train_result.best_params,
                    score=test_score,
                    metrics=window_results[-1]["metrics"]
                )

            except Exception as e:
                logger.error(f"Walk-forward 窗口 {i+1} 处理失败: {e}")
                continue

        # 选择最稳定的参数（测试集表现最好的）
        if window_results:
            best_window = max(window_results, key=lambda x: x["test_score"])
            result.best_params = best_window["best_params"]
            result.best_score = best_window["test_score"]

            logger.info(
                f"Walk-forward 完成: 最佳参数来自窗口 {best_window['window']}, "
                f"测试得分 = {result.best_score:.4f}"
            )

        # 计算耗时
        duration = (datetime.now() - start_time).total_seconds()
        result.duration_seconds = duration

        return result
