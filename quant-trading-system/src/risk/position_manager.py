"""
仓位管理器

提供实时仓位控制功能：
- 单票仓位限制
- 总仓位限制
- 行业/板块仓位限制
- 实时仓位计算
"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Set, Callable
from enum import Enum

from src.common.logger import TradingLogger

logger = TradingLogger(__name__)


class PositionLimitType(Enum):
    """仓位限制类型"""
    SINGLE_STOCK = "single_stock"      # 单票限制
    TOTAL = "total"                     # 总仓位限制
    INDUSTRY = "industry"               # 行业限制
    SECTOR = "sector"                   # 板块限制


@dataclass
class PositionLimit:
    """仓位限制配置"""
    limit_type: PositionLimitType
    max_ratio: Decimal                    # 最大仓位比例 (0-1)
    target_ratio: Optional[Decimal] = None # 目标仓位比例
    warning_ratio: Optional[Decimal] = None # 预警比例
    symbols: Optional[Set[str]] = None    # 适用标的（单票/行业/板块）

    def __post_init__(self):
        if self.warning_ratio is None:
            self.warning_ratio = self.max_ratio * Decimal("0.9")  # 默认90%预警


@dataclass
class PositionSnapshot:
    """仓位快照"""
    symbol: str
    quantity: int
    avg_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    weight: Decimal                       # 占总资产比例
    unrealized_pnl: Decimal
    unrealized_pnl_pct: Decimal
    updated_at: datetime


class PositionManager:
    """
    仓位管理器

    职责：
    - 实时计算各层级仓位
    - 检查开仓/加仓是否超限
    - 提供仓位预警
    - 支持动态调整限制
    """

    def __init__(
        self,
        initial_capital: Decimal = Decimal("1000000"),
        limits: Optional[List[PositionLimit]] = None
    ):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # 仓位限制
        self._limits: Dict[PositionLimitType, List[PositionLimit]] = {
            PositionLimitType.SINGLE_STOCK: [],
            PositionLimitType.TOTAL: [],
            PositionLimitType.INDUSTRY: [],
            PositionLimitType.SECTOR: [],
        }
        if limits:
            for limit in limits:
                self._limits[limit.limit_type].append(limit)

        # 持仓数据: symbol -> PositionSnapshot
        self._positions: Dict[str, PositionSnapshot] = {}

        # 行业/板块映射: symbol -> (industry, sector)
        self._symbol_classifications: Dict[str, tuple] = {}

        # 预警回调
        self._warning_callbacks: List[Callable] = []

        logger.info(f"仓位管理器初始化: 初始资金 {initial_capital}")

    # ============ 配置管理 ============

    def add_limit(self, limit: PositionLimit) -> None:
        """添加仓位限制"""
        self._limits[limit.limit_type].append(limit)
        logger.info(f"添加仓位限制: {limit.limit_type.value}, 最大{limit.max_ratio:.1%}")

    def remove_limit(self, limit_type: PositionLimitType, index: int = 0) -> None:
        """移除仓位限制"""
        if self._limits[limit_type] and index < len(self._limits[limit_type]):
            removed = self._limits[limit_type].pop(index)
            logger.info(f"移除仓位限制: {removed.limit_type.value}")

    def set_default_limits(
        self,
        max_single_stock: Decimal = Decimal("0.10"),
        max_total: Decimal = Decimal("0.80")
    ) -> None:
        """设置默认仓位限制"""
        # 单票限制
        self._limits[PositionLimitType.SINGLE_STOCK] = [
            PositionLimit(
                limit_type=PositionLimitType.SINGLE_STOCK,
                max_ratio=max_single_stock,
                target_ratio=max_single_stock * Decimal("0.8")
            )
        ]

        # 总仓位限制
        self._limits[PositionLimitType.TOTAL] = [
            PositionLimit(
                limit_type=PositionLimitType.TOTAL,
                max_ratio=max_total,
                target_ratio=max_total * Decimal("0.9")
            )
        ]

        logger.info(
            f"设置默认限制: 单票{max_single_stock:.0%}, 总仓位{max_total:.0%}"
        )

    # ============ 持仓更新 ============

    def update_position(
        self,
        symbol: str,
        quantity: int,
        avg_cost: Decimal,
        market_price: Decimal
    ) -> PositionSnapshot:
        """更新持仓"""
        market_value = market_price * quantity
        weight = market_value / self.current_capital if self.current_capital > 0 else Decimal("0")

        unrealized_pnl = Decimal("0")
        unrealized_pnl_pct = Decimal("0")

        if quantity > 0:
            cost = avg_cost * quantity
            unrealized_pnl = market_value - cost
            if cost > 0:
                unrealized_pnl_pct = unrealized_pnl / cost

        snapshot = PositionSnapshot(
            symbol=symbol,
            quantity=quantity,
            avg_cost=avg_cost,
            market_price=market_price,
            market_value=market_value,
            weight=weight,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            updated_at=datetime.now()
        )

        self._positions[symbol] = snapshot

        # 检查是否需要预警
        self._check_warnings(symbol, snapshot)

        return snapshot

    def update_market_price(self, symbol: str, price: Decimal) -> None:
        """更新市场价格"""
        if symbol in self._positions:
            pos = self._positions[symbol]
            self.update_position(symbol, pos.quantity, pos.avg_cost, price)

    def remove_position(self, symbol: str) -> None:
        """移除持仓（清仓）"""
        if symbol in self._positions:
            del self._positions[symbol]
            logger.info(f"移除持仓: {symbol}")

    def update_capital(self, capital: Decimal) -> None:
        """更新总资产"""
        self.current_capital = capital
        # 重新计算所有持仓权重
        for symbol, pos in self._positions.items():
            self.update_position(symbol, pos.quantity, pos.avg_cost, pos.market_price)

    # ============ 仓位查询 ============

    def get_position(self, symbol: str) -> Optional[PositionSnapshot]:
        """获取单个持仓"""
        return self._positions.get(symbol)

    def get_all_positions(self) -> Dict[str, PositionSnapshot]:
        """获取所有持仓"""
        return self._positions.copy()

    def get_total_position_value(self) -> Decimal:
        """获取总持仓市值"""
        return sum(pos.market_value for pos in self._positions.values())

    def get_total_position_weight(self) -> Decimal:
        """获取总仓位比例"""
        total_value = self.get_total_position_value()
        return total_value / self.current_capital if self.current_capital > 0 else Decimal("0")

    def get_industry_weight(self, industry: str) -> Decimal:
        """获取行业仓位比例"""
        total = Decimal("0")
        for symbol, pos in self._positions.items():
            if self._get_symbol_industry(symbol) == industry:
                total += pos.market_value
        return total / self.current_capital if self.current_capital > 0 else Decimal("0")

    # ============ 风控检查 ============

    def can_open_position(
        self,
        symbol: str,
        quantity: int,
        price: Decimal
    ) -> tuple[bool, Optional[str]]:
        """
        检查是否可以开仓/加仓

        Returns:
            (是否允许, 拒绝原因)
        """
        new_value = price * quantity

        # 检查单票限制
        for limit in self._limits[PositionLimitType.SINGLE_STOCK]:
            current_value = self._positions.get(symbol, PositionSnapshot(
                symbol=symbol, quantity=0, avg_cost=Decimal("0"),
                market_price=price, market_value=Decimal("0"),
                weight=Decimal("0"), unrealized_pnl=Decimal("0"),
                unrealized_pnl_pct=Decimal("0"), updated_at=datetime.now()
            )).market_value

            total_value = current_value + new_value
            new_weight = total_value / self.current_capital

            if new_weight > limit.max_ratio:
                return False, f"单票仓位超限: {new_weight:.1%} > {limit.max_ratio:.1%}"

        # 检查总仓位限制
        for limit in self._limits[PositionLimitType.TOTAL]:
            current_total = self.get_total_position_value()
            new_total = current_total + new_value
            new_weight = new_total / self.current_capital

            if new_weight > limit.max_ratio:
                return False, f"总仓位超限: {new_weight:.1%} > {limit.max_ratio:.1%}"

        return True, None

    def check_position_health(self, symbol: str) -> Dict[str, any]:
        """检查持仓健康状态"""
        pos = self._positions.get(symbol)
        if not pos:
            return {"status": "NO_POSITION"}

        health = {
            "status": "HEALTHY",
            "symbol": symbol,
            "weight": pos.weight,
            "unrealized_pnl_pct": pos.unrealized_pnl_pct,
            "warnings": []
        }

        # 检查单票限制
        for limit in self._limits[PositionLimitType.SINGLE_STOCK]:
            if pos.weight > limit.warning_ratio:
                health["warnings"].append({
                    "type": "SINGLE_STOCK_HIGH",
                    "message": f"单票仓位较高: {pos.weight:.1%}",
                    "severity": "WARNING" if pos.weight < limit.max_ratio else "CRITICAL"
                })
                if pos.weight >= limit.max_ratio:
                    health["status"] = "OVER_LIMIT"

        return health

    # ============ 预警机制 ============

    def on_warning(self, callback: Callable) -> None:
        """注册预警回调"""
        self._warning_callbacks.append(callback)

    def _check_warnings(self, symbol: str, snapshot: PositionSnapshot) -> None:
        """检查并触发预警"""
        warnings = []

        # 检查单票限制
        for limit in self._limits[PositionLimitType.SINGLE_STOCK]:
            if snapshot.weight > limit.warning_ratio:
                warning = {
                    "type": "POSITION_WARNING",
                    "symbol": symbol,
                    "current_weight": float(snapshot.weight),
                    "warning_threshold": float(limit.warning_ratio),
                    "max_threshold": float(limit.max_ratio),
                    "message": f"{symbol} 仓位 {snapshot.weight:.1%} 接近限制 {limit.max_ratio:.1%}"
                }
                warnings.append(warning)

        # 触发回调
        if warnings:
            for callback in self._warning_callbacks:
                try:
                    callback(warnings)
                except Exception as e:
                    logger.error(f"预警回调失败: {e}")

    # ============ 辅助方法 ============

    def _get_symbol_industry(self, symbol: str) -> Optional[str]:
        """获取标的行业"""
        if symbol in self._symbol_classifications:
            return self._symbol_classifications[symbol][0]
        return None

    def set_symbol_classification(
        self,
        symbol: str,
        industry: Optional[str] = None,
        sector: Optional[str] = None
    ) -> None:
        """设置标的行业/板块分类"""
        self._symbol_classifications[symbol] = (industry, sector)

    def get_position_report(self) -> Dict:
        """获取仓位报告"""
        total_value = self.get_total_position_value()
        total_weight = self.get_total_position_weight()

        return {
            "summary": {
                "current_capital": float(self.current_capital),
                "total_position_value": float(total_value),
                "total_position_weight": float(total_weight),
                "available_cash": float(self.current_capital - total_value),
                "position_count": len(self._positions)
            },
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_cost": float(p.avg_cost),
                    "market_price": float(p.market_price),
                    "market_value": float(p.market_value),
                    "weight": float(p.weight),
                    "unrealized_pnl": float(p.unrealized_pnl),
                    "unrealized_pnl_pct": float(p.unrealized_pnl_pct)
                }
                for p in self._positions.values()
            ],
            "limits": {
                k.value: [
                    {
                        "max_ratio": float(l.max_ratio),
                        "warning_ratio": float(l.warning_ratio)
                    }
                    for l in v
                ]
                for k, v in self._limits.items()
            }
        }
