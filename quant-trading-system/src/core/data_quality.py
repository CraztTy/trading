"""
数据质量监控模块

职责：
- 评估市场数据质量（完整性、及时性、准确性）
- 检测异常数据（价格跳空、成交量异常等）
- 记录数据质量问题并告警
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from collections import deque

from src.market_data.models import TickData
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


@dataclass
class DataQualityScore:
    """数据质量评分"""
    symbol: str
    timestamp: datetime
    completeness: float  # 0-1
    timeliness: float   # 0-1
    accuracy: float     # 0-1
    overall: float      # 加权平均
    issues: List[str] = field(default_factory=list)  # 发现的问题

    def __post_init__(self):
        if not 0 <= self.completeness <= 1:
            raise ValueError(f"completeness must be in [0, 1], got {self.completeness}")
        if not 0 <= self.timeliness <= 1:
            raise ValueError(f"timeliness must be in [0, 1], got {self.timeliness}")
        if not 0 <= self.accuracy <= 1:
            raise ValueError(f"accuracy must be in [0, 1], got {self.accuracy}")
        if not 0 <= self.overall <= 1:
            raise ValueError(f"overall must be in [0, 1], got {self.overall}")


class AnomalyDetector(ABC):
    """异常检测器基类"""

    @abstractmethod
    def is_anomaly(self, tick: TickData) -> bool:
        """检测是否为异常数据"""
        pass

    @abstractmethod
    def get_issue_description(self, tick: TickData) -> str:
        """获取问题描述"""
        pass


class PriceJumpDetector(AnomalyDetector):
    """价格跳空检测器"""

    def __init__(self, max_jump_pct: float = 0.1):
        self.max_jump_pct = max_jump_pct
        self._last_prices: Dict[str, Decimal] = {}

    def is_anomaly(self, tick: TickData) -> bool:
        """检查价格跳变是否超过阈值"""
        if tick.symbol not in self._last_prices:
            self._last_prices[tick.symbol] = tick.price
            return False

        last_price = self._last_prices[tick.symbol]
        if last_price == 0:
            self._last_prices[tick.symbol] = tick.price
            return False

        price_change = abs(tick.price - last_price) / last_price
        is_anomaly = price_change > Decimal(str(self.max_jump_pct))

        # 更新最后价格
        self._last_prices[tick.symbol] = tick.price

        return is_anomaly

    def get_issue_description(self, tick: TickData) -> str:
        """获取价格跳空问题描述"""
        last_price = self._last_prices.get(tick.symbol)
        if last_price and last_price != 0:
            change_pct = float((tick.price - last_price) / last_price * 100)
            return f"价格跳空: {change_pct:+.2f}% (阈值: {self.max_jump_pct*100:.1f}%)"
        return "价格跳空检测"


class VolumeSpikeDetector(AnomalyDetector):
    """成交量异常检测器"""

    def __init__(self, spike_factor: float = 5.0, window_size: int = 20):
        self.spike_factor = spike_factor
        self.window_size = window_size
        self._volume_history: Dict[str, deque] = {}

    def is_anomaly(self, tick: TickData) -> bool:
        """检查成交量是否异常"""
        if tick.symbol not in self._volume_history:
            self._volume_history[tick.symbol] = deque(maxlen=self.window_size)

        history = self._volume_history[tick.symbol]

        # 历史数据不足时，只记录不检测
        if len(history) < 5:
            history.append(tick.volume)
            return False

        # 计算平均成交量
        avg_volume = sum(history) / len(history)
        history.append(tick.volume)

        if avg_volume == 0:
            return False

        # 检查是否超过阈值
        return tick.volume > avg_volume * self.spike_factor

    def get_issue_description(self, tick: TickData) -> str:
        """获取成交量异常描述"""
        history = self._volume_history.get(tick.symbol, deque())
        if len(history) > 1:
            avg_volume = sum(list(history)[:-1]) / (len(history) - 1)
            if avg_volume > 0:
                factor = tick.volume / avg_volume
                return f"成交量异常: {factor:.1f}倍于均值 (阈值: {self.spike_factor}倍)"
        return "成交量异常检测"


class DelayDetector(AnomalyDetector):
    """数据延迟检测器"""

    def __init__(self, max_delay_seconds: float = 5.0):
        self.max_delay_seconds = max_delay_seconds

    def is_anomaly(self, tick: TickData) -> bool:
        """检查数据是否延迟"""
        if not tick.timestamp:
            return True

        delay = (datetime.now() - tick.timestamp).total_seconds()
        return delay > self.max_delay_seconds

    def get_issue_description(self, tick: TickData) -> str:
        """获取延迟问题描述"""
        if not tick.timestamp:
            return "数据时间戳缺失"

        delay = (datetime.now() - tick.timestamp).total_seconds()
        return f"数据延迟: {delay:.1f}秒 (阈值: {self.max_delay_seconds}秒)"


class DataQualityMonitor:
    """数据质量监控器"""

    # 质量评分权重
    COMPLETENESS_WEIGHT = 0.4
    TIMELINESS_WEIGHT = 0.3
    ACCURACY_WEIGHT = 0.3

    # 低质量告警阈值
    LOW_QUALITY_THRESHOLD = 0.6

    def __init__(self, max_history_per_symbol: int = 100):
        self._scores: Dict[str, List[DataQualityScore]] = {}
        self._anomaly_detectors: List[AnomalyDetector] = []
        self._max_history = max_history_per_symbol

        # 注册默认检测器
        self.register_detector(PriceJumpDetector())
        self.register_detector(VolumeSpikeDetector())
        self.register_detector(DelayDetector())

        logger.info("数据质量监控器初始化完成")

    def register_detector(self, detector: AnomalyDetector):
        """注册异常检测器"""
        self._anomaly_detectors.append(detector)
        logger.info(f"注册异常检测器: {detector.__class__.__name__}")

    def unregister_detector(self, detector: AnomalyDetector):
        """注销异常检测器"""
        if detector in self._anomaly_detectors:
            self._anomaly_detectors.remove(detector)

    def evaluate_tick(self, tick: TickData) -> DataQualityScore:
        """评估Tick数据质量"""
        issues: List[str] = []

        # 1. 完整性检查
        completeness = self._check_completeness(tick, issues)

        # 2. 及时性检查
        timeliness = self._check_timeliness(tick, issues)

        # 3. 准确性检查
        accuracy = self._check_accuracy(tick, issues)

        # 4. 异常检测
        for detector in self._anomaly_detectors:
            if detector.is_anomaly(tick):
                issue = detector.get_issue_description(tick)
                issues.append(issue)
                accuracy = max(0, accuracy - 0.2)  # 异常降低准确性评分

        # 计算综合评分
        overall = (
            completeness * self.COMPLETENESS_WEIGHT +
            timeliness * self.TIMELINESS_WEIGHT +
            accuracy * self.ACCURACY_WEIGHT
        )

        score = DataQualityScore(
            symbol=tick.symbol,
            timestamp=datetime.now(),
            completeness=completeness,
            timeliness=timeliness,
            accuracy=accuracy,
            overall=round(overall, 4),
            issues=issues
        )

        # 存储评分
        self._store_score(score)

        # 低质量告警
        if overall < self.LOW_QUALITY_THRESHOLD:
            logger.warning(f"数据质量告警 [{tick.symbol}]: 评分={overall:.2f}, 问题={issues}")

        return score

    def _check_completeness(self, tick: TickData, issues: List[str]) -> float:
        """检查数据完整性"""
        required_fields = ['symbol', 'timestamp', 'price', 'volume']
        missing_fields = []

        if not tick.symbol:
            missing_fields.append('symbol')
        if not tick.timestamp:
            missing_fields.append('timestamp')
        if tick.price is None or tick.price <= 0:
            missing_fields.append('price')
        if tick.volume is None or tick.volume < 0:
            missing_fields.append('volume')

        if missing_fields:
            issues.append(f"缺失字段: {', '.join(missing_fields)}")
            return max(0, 1.0 - len(missing_fields) * 0.25)

        return 1.0

    def _check_timeliness(self, tick: TickData, issues: List[str]) -> float:
        """检查数据及时性"""
        if not tick.timestamp:
            issues.append("时间戳缺失")
            return 0.0

        delay = (datetime.now() - tick.timestamp).total_seconds()

        # 延迟评分：0秒=1.0, 5秒=0.8, 30秒=0.5, 60秒=0.0
        if delay < 0:
            issues.append("时间戳为未来时间")
            return 0.5

        if delay <= 5:
            return 1.0
        elif delay <= 30:
            score = 1.0 - (delay - 5) / 25 * 0.2
            return round(score, 4)
        elif delay <= 60:
            score = 0.8 - (delay - 30) / 30 * 0.3
            return round(score, 4)
        else:
            issues.append(f"数据延迟: {delay:.1f}秒")
            return max(0, 0.5 - (delay - 60) / 60 * 0.5)

    def _check_accuracy(self, tick: TickData, issues: List[str]) -> float:
        """检查数据准确性"""
        score = 1.0

        # 价格合理性检查
        if tick.price is not None:
            if tick.price <= 0:
                issues.append(f"价格无效: {tick.price}")
                return 0.0
            if tick.price > 100000:
                issues.append(f"价格异常高: {tick.price}")
                score -= 0.3

        # 成交量合理性检查
        if tick.volume is not None:
            if tick.volume < 0:
                issues.append(f"成交量无效: {tick.volume}")
                return 0.0
            if tick.volume > 100000000:
                issues.append(f"成交量异常大: {tick.volume}")
                score -= 0.2

        # 涨跌幅检查
        if tick.change_pct is not None:
            if abs(tick.change_pct) > 20:
                issues.append(f"涨跌幅异常: {tick.change_pct}%")
                score -= 0.2
            elif abs(tick.change_pct) > 10:
                score -= 0.1

        return max(0, score)

    def _store_score(self, score: DataQualityScore):
        """存储评分记录"""
        if score.symbol not in self._scores:
            self._scores[score.symbol] = []

        self._scores[score.symbol].append(score)

        # 限制历史记录数量
        if len(self._scores[score.symbol]) > self._max_history:
            self._scores[score.symbol].pop(0)

    def get_latest_score(self, symbol: str) -> Optional[DataQualityScore]:
        """获取最新评分"""
        scores = self._scores.get(symbol, [])
        return scores[-1] if scores else None

    def get_score_history(self, symbol: str, limit: int = 10) -> List[DataQualityScore]:
        """获取评分历史"""
        scores = self._scores.get(symbol, [])
        return scores[-limit:] if scores else []

    def get_average_score(self, symbol: str, window: int = 10) -> Optional[float]:
        """获取平均评分"""
        scores = self._get_recent_scores(symbol, window)
        if not scores:
            return None
        return sum(s.overall for s in scores) / len(scores)

    def _get_recent_scores(self, symbol: str, window: int) -> List[DataQualityScore]:
        """获取最近评分记录"""
        scores = self._scores.get(symbol, [])
        return scores[-window:] if scores else []

    def get_quality_summary(self, symbol: str) -> Dict[str, Any]:
        """获取质量汇总报告"""
        scores = self._scores.get(symbol, [])

        if not scores:
            return {
                "symbol": symbol,
                "has_data": False,
                "message": "无质量评分记录"
            }

        recent_scores = scores[-20:]  # 最近20条

        return {
            "symbol": symbol,
            "has_data": True,
            "latest_score": scores[-1].overall,
            "avg_score": sum(s.overall for s in recent_scores) / len(recent_scores),
            "min_score": min(s.overall for s in recent_scores),
            "max_score": max(s.overall for s in recent_scores),
            "total_records": len(scores),
            "recent_issues": [issue for s in recent_scores for issue in s.issues],
            "completeness_avg": sum(s.completeness for s in recent_scores) / len(recent_scores),
            "timeliness_avg": sum(s.timeliness for s in recent_scores) / len(recent_scores),
            "accuracy_avg": sum(s.accuracy for s in recent_scores) / len(recent_scores),
        }

    def clear_history(self, symbol: Optional[str] = None):
        """清除历史记录"""
        if symbol:
            self._scores.pop(symbol, None)
            logger.info(f"清除 {symbol} 的质量评分历史")
        else:
            self._scores.clear()
            logger.info("清除所有质量评分历史")

    def get_monitored_symbols(self) -> List[str]:
        """获取监控中的标的列表"""
        return list(self._scores.keys())
