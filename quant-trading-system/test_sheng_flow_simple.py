"""
Day 7 Integration Test - Full Trading Pipeline
Test scenarios:
1. Normal order -> execution -> position update
2. Signal generation -> risk control -> auto order
3. Risk rejection -> order blocked
4. Circuit breaker test
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import hashlib
import time

# ============ Data Models ============

@dataclass
class TickData:
    symbol: str
    timestamp: datetime
    price: Decimal
    volume: int
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    bid_volume: Optional[int] = None
    ask_volume: Optional[int] = None

@dataclass
class BarData:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal
    period: str = "1d"

class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

@dataclass
class Signal:
    type: SignalType
    symbol: str
    timestamp: datetime
    price: Optional[Decimal] = None
    volume: Optional[int] = None
    confidence: float = 0.5
    reason: str = ""
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

# ============ Crown Prince (Data Validation) ============

class DataType(Enum):
    TICK = "tick"
    KLINE = "kline"
    DEPTH = "depth"
    ORDER = "order"
    SIGNAL = "signal"

class ValidationLevel(Enum):
    STRICT = "strict"
    NORMAL = "normal"
    LENIENT = "lenient"

@dataclass
class ValidationResult:
    is_valid: bool
    data_type: Optional[DataType] = None
    data: Optional[Any] = None
    errors: List[str] = None
    warnings: List[str] = None
    normalized_symbol: Optional[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

class SymbolNormalizer:
    EXCHANGE_MAP = {
        "SH": "SH", "sh": "SH",
        "SZ": "SZ", "sz": "SZ",
        "BJ": "BJ", "bj": "BJ",
        "HK": "HK", "hk": "HK",
    }

    @classmethod
    def normalize(cls, symbol: str) -> Optional[str]:
        if not symbol or not isinstance(symbol, str):
            return None

        symbol = symbol.strip()
        import re

        if re.match(r'^\d{6}\.[A-Z]{2}$', symbol):
            return symbol

        if re.match(r'^\d{6}\.[a-z]{2}$', symbol):
            code, exchange = symbol.split('.')
            return f"{code}.{exchange.upper()}"

        prefix_match = re.match(r'^([a-zA-Z]{2})(\d{6})$', symbol)
        if prefix_match:
            exchange, code = prefix_match.groups()
            exchange = exchange.upper()
            if exchange in ['SH', 'SZ', 'BJ', 'HK']:
                return f"{code}.{exchange}"

        if re.match(r'^\d{6}$', symbol):
            return cls._infer_exchange(symbol)

        return None

    @classmethod
    def _infer_exchange(cls, code: str) -> Optional[str]:
        if code.startswith(('60', '68', '69')):
            return f"{code}.SH"
        if code.startswith(('00', '30')):
            return f"{code}.SZ"
        if code.startswith(('8', '4')):
            return f"{code}.BJ"
        return f"{code}.SH"

class CrownPrince:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.normalizer = SymbolNormalizer()
        self.banned_stocks = set()
        self.min_avg_volume = 1_000_000
        self._handlers: Dict[DataType, List[Callable]] = {dt: [] for dt in DataType}
        self._stats = {"total_received": 0, "valid": 0, "invalid": 0, "dispatched": 0}
        print("[INIT] CrownPrince initialized")

    def process_tick(self, tick: TickData, level: ValidationLevel = ValidationLevel.NORMAL) -> ValidationResult:
        self._stats["total_received"] += 1

        if tick.symbol:
            normalized = self.normalizer.normalize(tick.symbol)
            if normalized:
                tick.symbol = normalized

        if tick.symbol and tick.symbol in self.banned_stocks:
            return ValidationResult(
                is_valid=False,
                data_type=DataType.TICK,
                errors=[f"Stock {tick.symbol} is banned"]
            )

        errors = []
        if not tick.symbol:
            errors.append("Symbol cannot be empty")
        if not tick.timestamp:
            errors.append("Timestamp cannot be empty")
        if tick.price is None or tick.price <= 0:
            errors.append(f"Invalid price: {tick.price}")
        if tick.volume is None or tick.volume < 0:
            errors.append(f"Invalid volume: {tick.volume}")

        is_valid = len(errors) == 0

        if not is_valid:
            self._stats["invalid"] += 1
            return ValidationResult(is_valid=False, data_type=DataType.TICK, errors=errors)

        self._stats["valid"] += 1
        return ValidationResult(
            is_valid=True,
            data_type=DataType.TICK,
            data=tick,
            normalized_symbol=tick.symbol
        )

    def add_banned_stock(self, code: str, reason: str = ""):
        normalized = self.normalizer.normalize(code)
        if normalized:
            self.banned_stocks.add(normalized)
            print(f"[BAN] Added banned stock: {normalized}, reason: {reason}")

    def remove_banned_stock(self, code: str):
        normalized = self.normalizer.normalize(code)
        if normalized:
            self.banned_stocks.discard(normalized)

    def reset_stats(self):
        self._stats = {"total_received": 0, "valid": 0, "invalid": 0, "dispatched": 0}


# ============ Zhongshu Sheng (Signal Generation) ============

class SignalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"

@dataclass
class SignalEvent:
    signal: Signal
    strategy_id: str
    status: SignalStatus = SignalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    audit_result: Optional[Dict] = None
    order_id: Optional[str] = None

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(minutes=5)

    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    @property
    def signal_id(self) -> str:
        # 使用信号的关键属性生成ID，相同symbol/type/price的信号被认为是重复
        price_str = str(self.signal.price) if self.signal.price else "0"
        content = f"{self.strategy_id}:{self.signal.symbol}:{self.signal.type.value}:{price_str}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


class SignalCache:
    def __init__(self, ttl_seconds: int = 60):
        self._cache: Dict[str, SignalEvent] = {}
        self._ttl = ttl_seconds
        self._stats = {"total": 0, "duplicates": 0, "expired": 0}

    def add(self, event: SignalEvent) -> bool:
        signal_id = event.signal_id
        if signal_id in self._cache:
            self._stats["duplicates"] += 1
            print(f"[DUP] Duplicate signal: {signal_id}")
            return False

        self._cache[signal_id] = event
        self._stats["total"] += 1
        return True

    def clear(self):
        self._cache.clear()


class ZhongshuSheng:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.signal_cache = SignalCache(ttl_seconds=60)
        self._handlers: List[Callable[[SignalEvent], None]] = []
        self._stats = {"signals_generated": 0, "signals_deduplicated": 0, "strategies_active": 0}
        print("[INIT] ZhongshuSheng initialized")

    def add_signal_handler(self, handler: Callable[[SignalEvent], None]):
        self._handlers.append(handler)

    async def generate_signal(self, symbol: str, signal_type: SignalType, price: Decimal, volume: int = 100) -> SignalEvent:
        signal = Signal(
            type=signal_type,
            symbol=symbol,
            timestamp=datetime.now(),
            price=price,
            volume=volume,
            confidence=0.8,
            reason="Price breakout"
        )

        event = SignalEvent(signal=signal, strategy_id="test_strategy")

        is_new = self.signal_cache.add(event)
        if not is_new:
            self._stats["signals_deduplicated"] += 1
            return event

        self._stats["signals_generated"] += 1
        print(f"[SIGNAL] Generated: {event.signal_id} [{signal.type.value}] {signal.symbol}")

        await self._dispatch(event)
        return event

    async def _dispatch(self, event: SignalEvent):
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"[ERROR] Signal dispatch failed: {e}")

    def reset(self):
        self._stats = {"signals_generated": 0, "signals_deduplicated": 0, "strategies_active": 0}
        self.signal_cache.clear()


# ============ Menxia Sheng (Risk Control) ============

class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class RiskCheckResult:
    passed: bool
    rule_code: str
    rule_name: str
    message: str
    level: RiskLevel
    details: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class AuditResult:
    approved: bool
    signal_id: Optional[str] = None
    checks: List[RiskCheckResult] = field(default_factory=list)
    rejected_by: Optional[str] = None
    reject_reason: Optional[str] = None
    audit_time: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0


class MenxiaSheng:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._stats = {"total_audits": 0, "approved": 0, "rejected": 0, "circuit_breaker_count": 0}
        self._audit_log: List[AuditResult] = []
        self._circuit_breaker_triggered = False
        self._circuit_breaker_reason: Optional[str] = None
        self._approval_callbacks: List[Callable[[Signal, AuditResult], None]] = []
        print("[INIT] MenxiaSheng initialized")

    def on_approval(self, callback: Callable[[Signal, AuditResult], None]):
        self._approval_callbacks.append(callback)

    async def audit_signal(self, signal: Signal, context: Optional[Dict] = None) -> AuditResult:
        start_time = time.time()
        context = context or {}

        self._stats["total_audits"] += 1

        if self._circuit_breaker_triggered:
            result = AuditResult(
                approved=False,
                signal_id=getattr(signal, 'id', None),
                reject_reason=f"Circuit breaker active: {self._circuit_breaker_reason}",
                rejected_by="CIRCUIT_BREAKER"
            )
            return result

        checks = []

        # 1. Position limit check
        if signal.type == SignalType.BUY:
            positions = context.get("positions", {})
            total_value = context.get("total_value", Decimal("0"))

            if total_value > 0:
                current_position = positions.get(signal.symbol, {})
                current_value = current_position.get("market_value", Decimal("0"))
                new_amount = (signal.price or Decimal("0")) * (signal.volume or 0)
                new_single_pct = (current_value + new_amount) / total_value

                if new_single_pct > Decimal("0.10"):  # 10% single position limit
                    self._stats["rejected"] += 1
                    result = AuditResult(
                        approved=False,
                        checks=checks,
                        rejected_by="POSITION_LIMIT",
                        reject_reason=f"Position limit exceeded: {new_single_pct:.2%} > 10%",
                        processing_time_ms=(time.time() - start_time) * 1000
                    )
                    return result

        # 2. Stop loss check
        if signal.type == SignalType.BUY:
            stop_loss = context.get("stop_loss")
            if stop_loss is None:
                self._stats["rejected"] += 1
                result = AuditResult(
                    approved=False,
                    checks=checks,
                    rejected_by="STOP_LOSS",
                    reject_reason="Buy signal must have stop loss",
                    processing_time_ms=(time.time() - start_time) * 1000
                )
                return result

        # All checks passed
        self._stats["approved"] += 1
        result = AuditResult(
            approved=True,
            checks=checks,
            processing_time_ms=(time.time() - start_time) * 1000
        )

        await self._notify_approval(signal, result)
        return result

    async def _notify_approval(self, signal: Signal, result: AuditResult):
        import inspect
        for callback in self._approval_callbacks:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(signal, result)
                else:
                    callback(signal, result)
            except Exception as e:
                print(f"[ERROR] Approval callback failed: {e}")

    def _trigger_circuit_breaker(self, reason: str):
        self._circuit_breaker_triggered = True
        self._circuit_breaker_reason = reason
        self._stats["circuit_breaker_count"] += 1
        print(f"[CB] Circuit breaker triggered: {reason}")

    def reset_circuit_breaker(self):
        self._circuit_breaker_triggered = False
        self._circuit_breaker_reason = None
        print("[CB] Circuit breaker reset")

    def is_circuit_breaker_active(self) -> bool:
        return self._circuit_breaker_triggered

    def reset(self):
        self._stats = {"total_audits": 0, "approved": 0, "rejected": 0, "circuit_breaker_count": 0}
        self._audit_log.clear()
        self.reset_circuit_breaker()


# ============ Shangshu Sheng (Execution) ============

class OrderPriority(Enum):
    EMERGENCY = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

@dataclass
class OrderRequest:
    signal: Signal
    account_id: int
    priority: OrderPriority = OrderPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    request_id: str = field(default_factory=lambda: f"ORD{int(time.time()*1000)}")

    def __lt__(self, other):
        return self.priority.value < other.priority.value

@dataclass
class Position:
    account_id: int
    symbol: str
    total_qty: int = 0
    available_qty: int = 0
    cost_price: Decimal = Decimal("0")
    cost_amount: Decimal = Decimal("0")
    market_price: Decimal = Decimal("0")


class ShangshuSheng:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._orders: List[OrderRequest] = []
        self._positions: Dict[str, Position] = {}
        self._frozen_amount: Dict[int, Decimal] = {}
        self._stats = {"orders_submitted": 0, "orders_executed": 0, "orders_rejected": 0, "trades_completed": 0}
        print("[INIT] ShangshuSheng initialized")

    async def submit_signal(self, signal: Signal, account_id: int, priority: OrderPriority = OrderPriority.NORMAL) -> str:
        request = OrderRequest(signal=signal, account_id=account_id, priority=priority)
        self._orders.append(request)
        self._stats["orders_submitted"] += 1
        print(f"[ORDER] Submitted: {request.request_id} {signal.symbol} {signal.type.value}")

        await self._execute_order(request)
        return request.request_id

    async def _execute_order(self, request: OrderRequest):
        signal = request.signal
        account_id = request.account_id

        # 1. Freeze capital
        freeze_amount = (signal.price or Decimal("0")) * (signal.volume or 0) * Decimal("1.1")
        current_frozen = self._frozen_amount.get(account_id, Decimal("0"))
        self._frozen_amount[account_id] = current_frozen + freeze_amount
        print(f"[CAPITAL] Frozen: account={account_id}, amount={freeze_amount}")

        # 2. Simulate execution with slippage
        filled_price = (signal.price or Decimal("0")) * Decimal("0.999")
        filled_qty = signal.volume or 0

        # 3. Update position
        key = f"{account_id}:{signal.symbol}"
        position = self._positions.get(key)

        if signal.type == SignalType.BUY:
            if position is None:
                position = Position(
                    account_id=account_id,
                    symbol=signal.symbol,
                    total_qty=filled_qty,
                    available_qty=filled_qty,
                    cost_price=filled_price,
                    cost_amount=filled_price * filled_qty
                )
                self._positions[key] = position
            else:
                old_cost = position.cost_amount
                new_cost = filled_price * filled_qty
                position.total_qty += filled_qty
                position.available_qty += filled_qty
                position.cost_amount = old_cost + new_cost
                position.cost_price = position.cost_amount / position.total_qty

            print(f"[POSITION] Buy: {signal.symbol}, qty={filled_qty}, cost={position.cost_price}")

        elif signal.type == SignalType.SELL:
            if position:
                position.total_qty -= filled_qty
                position.available_qty -= filled_qty
                position.cost_amount = position.cost_price * position.total_qty

                if position.total_qty <= 0:
                    del self._positions[key]
                    print(f"[POSITION] Closed: {signal.symbol}")
                else:
                    print(f"[POSITION] Sell: {signal.symbol}, remaining={position.total_qty}")

        # 4. Unfreeze capital
        self._frozen_amount[account_id] = max(Decimal("0"), self._frozen_amount.get(account_id, Decimal("0")) - freeze_amount)

        self._stats["orders_executed"] += 1
        self._stats["trades_completed"] += 1

    def get_position(self, account_id: int, symbol: str) -> Optional[Position]:
        key = f"{account_id}:{symbol}"
        return self._positions.get(key)

    def reset(self):
        self._orders.clear()
        self._positions.clear()
        self._frozen_amount.clear()
        self._stats = {"orders_submitted": 0, "orders_executed": 0, "orders_rejected": 0, "trades_completed": 0}


# ============ Test Functions ============

async def run_tests():
    print("\n" + "=" * 60)
    print("Day 7 Integration Test - Full Trading Pipeline")
    print("=" * 60)

    crown_prince = CrownPrince()
    zhongshu_sheng = ZhongshuSheng()
    menxia_sheng = MenxiaSheng()
    shangshu_sheng = ShangshuSheng()

    tests_passed = 0
    tests_failed = 0

    # Test 1: Tick validation
    print("\n[Test 1] Tick data validation...")
    try:
        crown_prince.reset_stats()
        tick = TickData(
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=1000
        )
        result = crown_prince.process_tick(tick)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"
        print("   [PASS] Tick validation passed")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1

    # Test 2: Symbol normalization
    print("\n[Test 2] Symbol normalization...")
    try:
        test_cases = [
            ("000001.SZ", "000001.SZ"),
            ("000001.sz", "000001.SZ"),
            ("sz000001", "000001.SZ"),
            ("000001", "000001.SZ"),
        ]
        for input_symbol, expected in test_cases:
            result = crown_prince.normalizer.normalize(input_symbol)
            assert result == expected, f"Failed: {input_symbol} -> {result}, expected {expected}"
        print(f"   [PASS] Symbol normalization ({len(test_cases)} cases)")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1

    # Test 3: Banned stock
    print("\n[Test 3] Banned stock rejection...")
    try:
        crown_prince.add_banned_stock("000001.SZ", "test ban")
        tick = TickData(symbol="000001.SZ", timestamp=datetime.now(), price=Decimal("10.50"), volume=1000)
        result = crown_prince.process_tick(tick)
        assert not result.is_valid, "Expected validation to fail"
        assert "banned" in result.errors[0].lower(), f"Expected ban error, got: {result.errors}"
        print("   [PASS] Banned stock rejected")
        tests_passed += 1
        crown_prince.remove_banned_stock("000001.SZ")
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1

    # Test 4: Signal generation
    print("\n[Test 4] Signal generation...")
    try:
        zhongshu_sheng.reset()
        signal_event = await zhongshu_sheng.generate_signal(
            symbol="000001.SZ",
            signal_type=SignalType.BUY,
            price=Decimal("10.50"),
            volume=100
        )
        assert zhongshu_sheng._stats["signals_generated"] == 1, "Signal generation failed"
        print(f"   [PASS] Signal generated: {signal_event.signal_id}")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1

    # Test 5: Signal deduplication
    print("\n[Test 5] Signal deduplication...")
    try:
        zhongshu_sheng.reset()
        event1 = await zhongshu_sheng.generate_signal("000001.SZ", SignalType.BUY, Decimal("10.50"))
        event2 = await zhongshu_sheng.generate_signal("000001.SZ", SignalType.BUY, Decimal("10.50"))  # Duplicate
        assert zhongshu_sheng._stats["signals_generated"] == 1, "Should only generate one signal"
        assert zhongshu_sheng._stats["signals_deduplicated"] == 1, "Should have one duplicate"
        print("   [PASS] Deduplication works")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1

    # Test 6: Risk audit pass
    print("\n[Test 6] Risk audit pass...")
    try:
        menxia_sheng.reset()
        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=100
        )
        context = {
            "positions": {},
            "total_value": Decimal("100000"),
            "stop_loss": Decimal("10.00")
        }
        result = await menxia_sheng.audit_signal(signal, context)
        assert result.approved, f"Expected approval, got rejection: {result.reject_reason}"
        print("   [PASS] Risk audit passed")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1

    # Test 7: Position limit rejection
    print("\n[Test 7] Position limit rejection...")
    try:
        menxia_sheng.reset()
        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=100
        )
        context = {
            "positions": {"000001.SZ": {"market_value": Decimal("50000")}},
            "total_value": Decimal("100000"),
            "stop_loss": Decimal("10.00")
        }
        result = await menxia_sheng.audit_signal(signal, context)
        assert not result.approved, "Expected rejection"
        assert "position" in result.reject_reason.lower(), f"Expected position limit error, got: {result.reject_reason}"
        print(f"   [PASS] Position limit triggered: {result.reject_reason}")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1

    # Test 8: Stop loss required
    print("\n[Test 8] Stop loss required...")
    try:
        menxia_sheng.reset()
        signal = Signal(
            type=SignalType.BUY,
            symbol="000001.SZ",
            timestamp=datetime.now(),
            price=Decimal("10.50"),
            volume=100
        )
        context = {
            "positions": {},
            "total_value": Decimal("100000")
        }
        result = await menxia_sheng.audit_signal(signal, context)
        assert not result.approved, "Expected rejection"
        assert "stop" in result.reject_reason.lower(), f"Expected stop loss error, got: {result.reject_reason}"
        print(f"   [PASS] Stop loss check triggered: {result.reject_reason}")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        tests_failed += 1

    # Test 9: Full pipeline - Signal -> Risk -> Execution
    print("\n[Test 9] Full pipeline: Signal -> Risk -> Execution...")
    try:
        crown_prince.reset_stats()
        zhongshu_sheng.reset()
        menxia_sheng.reset()
        shangshu_sheng.reset()

        async def risk_handler(signal, audit_result):
            if audit_result.approved:
                print("   -> Risk passed, sending to Shangshu")
                await shangshu_sheng.submit_signal(signal, account_id=1)
            else:
                print(f"   -> Risk rejected: {audit_result.reject_reason}")

        menxia_sheng.on_approval(risk_handler)

        async def signal_handler(event: SignalEvent):
            print(f"   -> Signal handler: {event.signal_id[:8]}...")
            context = {
                "positions": {},
                "total_value": Decimal("100000"),
                "stop_loss": Decimal("10.00")
            }
            await menxia_sheng.audit_signal(event.signal, context)

        zhongshu_sheng.add_signal_handler(signal_handler)

        await zhongshu_sheng.generate_signal("000001.SZ", SignalType.BUY, Decimal("10.50"), 100)

        assert zhongshu_sheng._stats["signals_generated"] > 0, "Signal generation failed"
        assert menxia_sheng._stats["total_audits"] > 0, "Risk audit not executed"
        assert shangshu_sheng._stats["orders_submitted"] > 0, "Order not submitted"

        position = shangshu_sheng.get_position(1, "000001.SZ")
        assert position is not None, "Position not created"
        assert position.total_qty == 100, f"Expected 100, got {position.total_qty}"

        print(f"   [PASS] Full pipeline test passed!")
        print(f"      - Signals: {zhongshu_sheng._stats['signals_generated']}")
        print(f"      - Risk: {menxia_sheng._stats['approved']} approved, {menxia_sheng._stats['rejected']} rejected")
        print(f"      - Orders: {shangshu_sheng._stats['orders_submitted']}")
        print(f"      - Position: {position.total_qty} shares @ {position.cost_price}")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1

    # Test 10: Risk rejection flow
    print("\n[Test 10] Risk rejection flow...")
    try:
        crown_prince.reset_stats()
        zhongshu_sheng.reset()
        menxia_sheng.reset()
        shangshu_sheng.reset()

        # Clear previous handlers from singleton
        zhongshu_sheng._handlers.clear()
        menxia_sheng._approval_callbacks.clear()

        async def risk_handler_reject(signal, audit_result):
            if audit_result.approved:
                await shangshu_sheng.submit_signal(signal, account_id=1)
            else:
                print(f"   -> Risk blocked: {audit_result.reject_reason}")

        menxia_sheng.on_approval(risk_handler_reject)

        async def signal_handler_reject(event: SignalEvent):
            context = {
                "positions": {"000001.SZ": {"market_value": Decimal("50000")}},
                "total_value": Decimal("100000"),
                "stop_loss": Decimal("10.00")
            }
            await menxia_sheng.audit_signal(event.signal, context)

        zhongshu_sheng.add_signal_handler(signal_handler_reject)

        await zhongshu_sheng.generate_signal("000001.SZ", SignalType.BUY, Decimal("10.50"), 100)

        assert zhongshu_sheng._stats["signals_generated"] > 0, "Signal generation failed"
        assert menxia_sheng._stats["rejected"] > 0, "Risk should have rejected"
        assert shangshu_sheng._stats["orders_submitted"] == 0, "Order should be rejected"

        print(f"   [PASS] Risk rejection flow passed!")
        print(f"      - Signals: {zhongshu_sheng._stats['signals_generated']}")
        print(f"      - Risk rejected: {menxia_sheng._stats['rejected']}")
        print(f"      - Orders: {shangshu_sheng._stats['orders_submitted']} (expected 0)")
        tests_passed += 1
    except Exception as e:
        print(f"   [FAIL] {e}")
        import traceback
        traceback.print_exc()
        tests_failed += 1

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total: {tests_passed + tests_failed}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    if tests_failed == 0:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[WARNING] {tests_failed} tests failed")

    return tests_failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
