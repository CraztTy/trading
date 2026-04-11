"""
策略选择器测试

测试覆盖：
1. 市场状态识别
2. 策略性能评估
3. 动态策略选择
4. 选择历史记录
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
from unittest.mock import Mock, AsyncMock, patch

from src.strategy.selector import (
    StrategySelector, MarketState, SelectionRule,
    StrategyScore, SelectionHistory, SelectorConfig
)
from src.strategy.base import StrategyBase
from src.backtest.metrics import BacktestMetrics


class TestMarketState:
    """市场状态测试"""

    def test_state_values(self):
        """测试状态值"""
        assert MarketState.TRENDING_UP.value == "trending_up"
        assert MarketState.TRENDING_DOWN.value == "trending_down"
        assert MarketState.RANGING.value == "ranging"
        assert MarketState.VOLATILE.value == "volatile"
        assert MarketState.LOW_VOLATILITY.value == "low_volatility"


class TestSelectorConfig:
    """选择器配置测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SelectorConfig()
        assert config.lookback_days == 30
        assert config.min_trades == 10
        assert config.score_threshold == 0.5

    def test_custom_config(self):
        """测试自定义配置"""
        config = SelectorConfig(
            lookback_days=60,
            min_trades=20,
            score_threshold=0.6
        )
        assert config.lookback_days == 60
        assert config.min_trades == 20


class TestStrategyScore:
    """策略评分测试"""

    def test_score_creation(self):
        """测试评分创建"""
        score = StrategyScore(
            strategy_id="ma_cross",
            overall_score=0.75,
            sharpe_score=0.8,
            return_score=0.7,
            drawdown_score=0.9,
            consistency_score=0.6
        )
        assert score.strategy_id == "ma_cross"
        assert score.overall_score == 0.75

    def test_score_weights(self):
        """测试评分权重"""
        from src.strategy.selector import calculate_weighted_score

        scores = {
            "sharpe": 0.8,
            "return": 0.7,
            "drawdown": 0.9,
        }
        weights = {
            "sharpe": 0.4,
            "return": 0.3,
            "drawdown": 0.3,
        }

        weighted = calculate_weighted_score(scores, weights)
        expected = 0.8 * 0.4 + 0.7 * 0.3 + 0.9 * 0.3

        assert abs(weighted - expected) < 0.001


class TestSelectionRule:
    """选择规则测试"""

    def test_rule_evaluation(self):
        """测试规则评估"""
        rule = SelectionRule(
            name="min_sharpe",
            condition=lambda metrics, state: metrics.sharpe_ratio > 1.0,
            weight=1.0
        )

        mock_metrics = Mock(spec=BacktestMetrics)
        mock_metrics.sharpe_ratio = 1.5

        assert rule.evaluate(mock_metrics, MarketState.TRENDING_UP) is True

        mock_metrics.sharpe_ratio = 0.5
        assert rule.evaluate(mock_metrics, MarketState.TRENDING_UP) is False


class TestStrategySelector:
    """策略选择器测试"""

    @pytest.fixture
    def selector(self):
        return StrategySelector(SelectorConfig())

    @pytest.fixture
    def mock_strategies(self):
        """模拟策略列表"""
        strategies = []
        for i in range(3):
            mock_strategy = Mock(spec=StrategyBase)
            mock_strategy.strategy_id = f"strategy_{i}"
            mock_strategy.name = f"Strategy {i}"
            strategies.append(mock_strategy)
        return strategies

    def test_selector_initialization(self, selector):
        """测试选择器初始化"""
        assert selector.config is not None
        assert len(selector.selection_history) == 0

    def test_detect_market_state_trending_up(self, selector):
        """测试检测上涨趋势"""
        # 模拟上涨数据
        prices = [10, 11, 12, 13, 14, 15]
        state = selector._detect_market_state(prices)

        assert state == MarketState.TRENDING_UP

    def test_detect_market_state_trending_down(self, selector):
        """测试检测下跌趋势"""
        prices = [15, 14, 13, 12, 11, 10]
        state = selector._detect_market_state(prices)

        assert state == MarketState.TRENDING_DOWN

    def test_detect_market_state_ranging(self, selector):
        """测试检测震荡趋势"""
        prices = [10, 11, 10, 11, 10, 11]
        state = selector._detect_market_state(prices)

        assert state == MarketState.RANGING

    def test_score_strategy(self, selector):
        """测试策略评分"""
        mock_metrics = Mock(spec=BacktestMetrics)
        mock_metrics.sharpe_ratio = 1.5
        mock_metrics.total_return = 0.2
        mock_metrics.max_drawdown = -0.1
        mock_metrics.win_rate = 0.55

        score = selector._score_strategy(mock_metrics)

        assert isinstance(score, StrategyScore)
        assert score.overall_score > 0

    def test_select_strategy(self, selector, mock_strategies):
        """测试策略选择"""
        # 模拟策略性能
        strategy_metrics = {
            "strategy_0": Mock(sharpe_ratio=1.0, total_return=0.1),
            "strategy_1": Mock(sharpe_ratio=1.5, total_return=0.2),
            "strategy_2": Mock(sharpe_ratio=0.8, total_return=0.05),
        }

        with patch.object(selector, '_get_strategy_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = strategy_metrics

            selected = selector.select(
                strategies=mock_strategies,
                market_data={"prices": [10, 11, 12, 13, 14]}
            )

            assert selected is not None
            # 应该选择表现最好的 strategy_1
            assert selected.strategy_id == "strategy_1"

    def test_select_strategy_with_filters(self, selector, mock_strategies):
        """测试带过滤条件的策略选择"""
        # 添加过滤规则
        selector.add_rule(SelectionRule(
            name="min_return",
            condition=lambda m, s: m.total_return > 0.15,
            weight=1.0
        ))

        strategy_metrics = {
            "strategy_0": Mock(sharpe_ratio=1.0, total_return=0.1),
            "strategy_1": Mock(sharpe_ratio=1.5, total_return=0.2),
        }

        with patch.object(selector, '_get_strategy_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = strategy_metrics

            selected = selector.select(
                strategies=mock_strategies[:2],
                market_data={"prices": [10, 11, 12]}
            )

            # strategy_0 因为收益率不够被过滤
            assert selected.strategy_id == "strategy_1"

    def test_selection_history(self, selector, mock_strategies):
        """测试选择历史记录"""
        with patch.object(selector, '_get_strategy_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = {
                "strategy_0": Mock(sharpe_ratio=1.0, total_return=0.1),
            }

            selector.select(
                strategies=mock_strategies[:1],
                market_data={"prices": [10, 11, 12]}
            )

            history = selector.get_selection_history()
            assert len(history) == 1

    def test_get_top_strategies(self, selector, mock_strategies):
        """测试获取Top策略"""
        strategy_metrics = {
            "strategy_0": Mock(sharpe_ratio=1.0, total_return=0.1),
            "strategy_1": Mock(sharpe_ratio=1.5, total_return=0.2),
            "strategy_2": Mock(sharpe_ratio=0.8, total_return=0.05),
        }

        with patch.object(selector, '_get_strategy_metrics') as mock_get_metrics:
            mock_get_metrics.return_value = strategy_metrics

            top = selector.get_top_strategies(
                strategies=mock_strategies,
                market_data={"prices": [10, 11, 12]},
                n=2
            )

            assert len(top) == 2
            assert top[0].strategy_id == "strategy_1"


class TestMarketStateTransitions:
    """市场状态转换测试"""

    def test_state_transition_tracking(self):
        """测试状态转换跟踪"""
        from src.strategy.selector import StateTransitionTracker

        tracker = StateTransitionTracker()

        tracker.record_state(datetime.now(), MarketState.TRENDING_UP)
        tracker.record_state(datetime.now() + timedelta(hours=1), MarketState.RANGING)
        tracker.record_state(datetime.now() + timedelta(hours=2), MarketState.TRENDING_DOWN)

        transitions = tracker.get_transitions()
        assert len(transitions) == 2

        stats = tracker.get_state_statistics()
        assert MarketState.TRENDING_UP in stats


class TestSelectionPersistence:
    """选择持久化测试"""

    @pytest.mark.asyncio
    async def test_save_selection_history(self):
        """测试保存选择历史"""
        from src.strategy.selector import SelectionHistoryStore

        store = SelectionHistoryStore()

        history = SelectionHistory(
            timestamp=datetime.now(),
            selected_strategy="strategy_1",
            market_state=MarketState.TRENDING_UP,
            scores=[
                StrategyScore("strategy_1", 0.8),
                StrategyScore("strategy_2", 0.6),
            ]
        )

        await store.save(history)

        loaded = await store.load_latest()
        assert loaded is not None
        assert loaded.selected_strategy == "strategy_1"


class TestAdaptiveWeights:
    """自适应权重测试"""

    def test_adaptive_weight_adjustment(self):
        """测试自适应权重调整"""
        from src.strategy.selector import AdaptiveWeightAdjuster

        adjuster = AdaptiveWeightAdjuster()

        # 初始权重
        initial_weights = {
            "sharpe_ratio": 0.4,
            "total_return": 0.3,
            "max_drawdown": 0.3,
        }

        # 模拟历史表现
        historical_performance = {
            "sharpe_ratio": [1.0, 1.2, 0.8, 1.1],  # 稳定
            "total_return": [0.1, 0.2, -0.05, 0.15],  # 波动大
            "max_drawdown": [-0.1, -0.15, -0.08, -0.12],  # 稳定
        }

        adjusted = adjuster.adjust_weights(initial_weights, historical_performance)

        assert sum(adjusted.values()) == pytest.approx(1.0, abs=0.001)
        # 稳定指标应该获得更高权重
