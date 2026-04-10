"""
刑部 - 违规记录

职责：
- 记录违规交易
- 熔断记录
- 驳回记录
- 异常交易监控
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class XingBuJustice:
    """刑部：违规记录中心"""

    def __init__(self, config: dict):
        self.config = config
        self.violations: List[Dict] = []  # 违规记录
        self.circuit_breaks: List[Dict] = []  # 熔断记录

    def record_violation(
        self,
        signal: Dict[str, Any],
        rule_code: str,
        message: str,
        severity: str = "MEDIUM"
    ):
        """记录违规"""
        violation = {
            'code': signal.get('code'),
            'strategy_id': signal.get('strategy_id'),
            'direction': signal.get('direction'),
            'price': signal.get('price'),
            'qty': signal.get('qty'),
            'rule_code': rule_code,
            'message': message,
            'severity': severity,
            'recorded_at': datetime.now().isoformat()
        }

        self.violations.append(violation)
        logger.warning(f"违规记录: {rule_code}, {message}")

    def record_circuit_break(
        self,
        reason: str,
        triggered_by: str,
        details: Optional[Dict] = None
    ):
        """记录熔断"""
        circuit_break = {
            'reason': reason,
            'triggered_by': triggered_by,
            'details': details or {},
            'recorded_at': datetime.now().isoformat()
        }

        self.circuit_breaks.append(circuit_break)
        logger.error(f"熔断触发: {reason}")

    def get_violations(
        self,
        strategy_id: Optional[str] = None,
        code: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict]:
        """获取违规记录"""
        violations = self.violations

        if strategy_id:
            violations = [v for v in violations if v['strategy_id'] == strategy_id]

        if code:
            violations = [v for v in violations if v['code'] == code]

        if severity:
            violations = [v for v in violations if v['severity'] == severity]

        return violations

    def get_violation_stats(self) -> Dict[str, Any]:
        """获取违规统计"""
        total = len(self.violations)
        by_severity = {}
        by_rule = {}

        for v in self.violations:
            # 按严重程度统计
            sev = v['severity']
            by_severity[sev] = by_severity.get(sev, 0) + 1

            # 按规则统计
            rule = v['rule_code']
            by_rule[rule] = by_rule.get(rule, 0) + 1

        return {
            'total_violations': total,
            'by_severity': by_severity,
            'by_rule': by_rule,
            'total_circuit_breaks': len(self.circuit_breaks)
        }

    def clear_violations(self):
        """清空违规记录"""
        self.violations.clear()
        logger.info("违规记录已清空")
