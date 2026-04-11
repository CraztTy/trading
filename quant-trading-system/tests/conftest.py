"""
Pytest 全局配置和 Fixtures
"""
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime
from decimal import Decimal
from typing import AsyncGenerator

# 设置异步模式
pytest_plugins = ("pytest_asyncio",)


# ==================== 测试环境配置 ====================

import os
# 设置测试模式环境变量
os.environ["TESTING"] = "true"


# ==================== HTTP Client Fixtures ====================

@pytest.fixture
def client():
    """FastAPI测试客户端 - 同步模式"""
    from fastapi.testclient import TestClient
    from src.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client):
    """带认证的测试客户端"""
    # 模拟认证token
    client.headers["Authorization"] = "Bearer test_token"
    return client


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== 模型 Fixtures ====================

@pytest.fixture
def sample_order_data():
    """样本订单数据"""
    return {
        "order_id": f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}001",
        "account_id": 1,
        "symbol": "000001.SZ",
        "symbol_name": "平安银行",
        "direction": "BUY",
        "qty": 1000,
        "price": Decimal("10.50"),
        "order_type": "LIMIT",
        "strategy_id": 1,
    }


@pytest.fixture
def sample_market_price():
    """样本市场价格数据"""
    from decimal import Decimal
    from dataclasses import dataclass
    from datetime import datetime

    @dataclass
    class MarketPrice:
        symbol: str
        last_price: Decimal
        bid_price: Decimal
        ask_price: Decimal
        bid_volume: int = 5000
        ask_volume: int = 5000
        high_limit: Decimal = None
        low_limit: Decimal = None
        timestamp: datetime = None

    return MarketPrice(
        symbol="000001.SZ",
        last_price=Decimal("10.50"),
        bid_price=Decimal("10.49"),
        ask_price=Decimal("10.51"),
        bid_volume=5000,
        ask_volume=5000,
        high_limit=Decimal("11.55"),  # 涨停价 +10%
        low_limit=Decimal("9.45"),    # 跌停价 -10%
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_portfolio():
    """样本账户持仓数据"""
    return {
        "cash": 1000000.0,
        "total_value": 1000000.0,
        "total_position": 0.0,
        "positions": {},
        "consecutive_losses": 0
    }


@pytest.fixture
def sample_signal():
    """样本交易信号"""
    return {
        "code": "000001.SZ",
        "direction": "BUY",
        "price": 10.50,
        "qty": 1000,
        "stop_loss": 9.50,
        "take_profit": 12.00,
        "strategy_id": "test_strategy"
    }


# ==================== 风控配置 Fixtures ====================

@pytest.fixture
def risk_config():
    """风控配置"""
    return {
        "max_position_per_stock": 0.10,      # 单票最大10%
        "max_total_position": 0.50,          # 总仓位最大50%
        "stop_loss_pct": 0.05,               # 止损比例5%
        "max_daily_loss_pct": 0.02,          # 日亏损熔断2%
        "max_consecutive_losses": 3          # 最大连续亏损3次
    }


@pytest.fixture
def clearing_config():
    """清算配置"""
    return {
        "initial_capital": 1_000_000.0,
        "commission_rate": 0.0003,           # 佣金率 0.03%
        "min_commission": 5.0,               # 最低佣金5元
        "stamp_tax_rate": 0.001,             # 印花税率 0.1%
        "transfer_fee_rate": 0.00002         # 过户费率 0.002%
    }


# ==================== 数据库 Fixtures ====================

@pytest.fixture
async def db_session():
    """模拟数据库会话"""
    from unittest.mock import AsyncMock
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = AsyncMock()
    return session


@pytest.fixture
async def account():
    """创建测试账户"""
    from decimal import Decimal
    from unittest.mock import MagicMock

    account = MagicMock()
    account.id = 1
    account.account_no = "TEST001"
    account.name = "测试账户"
    account.initial_capital = Decimal("1000000")
    account.available = Decimal("1000000")
    account.frozen = Decimal("0")
    account.total_balance = Decimal("1000000")
    account.market_value = Decimal("0")
    return account


# ==================== Mock Fixtures ====================

@pytest.fixture
def mock_order(mocker):
    """Mock订单对象"""
    order = mocker.MagicMock()
    order.order_id = "ORD20240101000001001"
    order.account_id = 1
    order.symbol = "000001.SZ"
    order.direction = mocker.MagicMock()
    order.direction.value = "BUY"
    order.qty = 1000
    order.price = Decimal("10.50")
    order.filled_qty = 0
    order.filled_avg_price = Decimal("0")
    order.filled_amount = Decimal("0")
    order.status = mocker.MagicMock()
    order.created_at = datetime.now()
    return order


@pytest.fixture
def mock_callback(mocker):
    """Mock回调函数"""
    return mocker.MagicMock()


# ==================== 测试标记 ====================

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "security: 安全测试")
    config.addinivalue_line("markers", "performance: 性能测试")
