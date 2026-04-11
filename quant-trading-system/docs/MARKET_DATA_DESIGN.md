# 实时行情系统设计

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     数据源层 (Data Sources)                   │
├─────────────────────────────────────────────────────────────┤
│  东方财富      同花顺        腾讯财经       其他数据源...       │
│  (WebSocket)  (WebSocket)   (HTTP/WS)                      │
└──────────────────┬──────────────────────────────────────────┘
                   │ 原始行情数据
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                     网关层 (Gateway)                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Eastmoney   │  │  Tushare    │  │  Tencent/Other      │  │
│  │  Gateway    │  │  Gateway    │  │  Gateways           │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          └────────────────┴────────────────────┘
                           │ 标准化行情数据
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   数据处理层 (Processor)                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Data       │  │  K-Line     │  │  Real-time          │  │
│  │  Norm.      │  │  Builder    │  │  Cache              │  │
│  │  数据标准化  │  │  K线合成    │  │  实时缓存            │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          └────────────────┴────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │   Redis    │  │ PostgreSQL │  │  WebSocket │
    │   Cache    │  │  History   │  │   Server   │
    │  (实时数据) │  │  (历史数据) │  │  (推送前端) │
    └────────────┘  └────────────┘  └────────────┘
```

## 核心组件

### 1. 行情网关 (MarketDataGateway)

```python
class MarketDataGateway(ABC):
    """行情网关基类"""
    
    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass
    
    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> None:
        """订阅标的"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> None:
        """取消订阅"""
    
    @abstractmethod
    async def on_tick(self, tick: TickData) -> None:
        """收到tick数据回调"""
        pass
```

### 2. 标准化数据结构

```python
@dataclass
class TickData:
    """标准化Tick数据"""
    symbol: str                    # 标的代码
    timestamp: datetime           # 时间戳
    price: Decimal                # 最新价
    volume: int                   # 成交量
    bid_price: Decimal            # 买一价
    bid_volume: int               # 买一量
    ask_price: Decimal            # 卖一价
    ask_volume: int               # 卖一量
    open: Decimal                 # 开盘价
    high: Decimal                 # 最高价
    low: Decimal                  # 最低价
    pre_close: Decimal            # 昨收价
    source: str                   # 数据源

@dataclass  
class KLineData:
    """标准化K线数据"""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    amount: Decimal
    period: str                   # 1m, 5m, 15m, 1h, 1d, 1w, 1M
```

### 3. K线合成器

```python
class KLineBuilder:
    """K线数据合成器"""
    
    def __init__(self, period: str):
        self.period = period       # 周期: 1m, 5m, 15m, 1h, 1d
        self.current_bar: Optional[KLineData] = None
    
    def on_tick(self, tick: TickData) -> Optional[KLineData]:
        """处理tick，返回完整的K线"""
        pass
```

### 4. 实时数据管理器

```python
class MarketDataManager:
    """行情数据管理器 - 中央协调"""
    
    def __init__(self):
        self.gateways: Dict[str, MarketDataGateway] = {}
        self.cache: RedisCache
        self.kline_builders: Dict[str, KLineBuilder] = {}
        self.subscribers: Dict[str, Set[WebSocket]] = {}  # symbol -> ws集合
    
    async def subscribe(self, symbol: str, websocket: WebSocket):
        """前端订阅"""
        pass
    
    async def publish_tick(self, tick: TickData):
        """分发tick到所有订阅者"""
        pass
```

## API设计

### REST API

```
GET /api/v1/market/tick/{symbol}        # 获取最新tick
GET /api/v1/market/kline/{symbol}       # 获取K线历史
    ?period=1m&start=2024-01-01&end=2024-01-31&limit=1000

GET /api/v1/market/depth/{symbol}       # 获取深度行情
GET /api/v1/market/snapshot/{symbol}    # 获取完整快照
```

### WebSocket API

```javascript
// 连接
ws://localhost:9000/ws/market

// 订阅
{
    "action": "subscribe",
    "symbols": ["000001.SZ", "600519.SH"],
    "data_types": ["tick", "kline_1m", "kline_5m"]
}

// 收到数据
{
    "type": "tick",
    "data": {
        "symbol": "000001.SZ",
        "price": 10.50,
        "volume": 1500,
        "timestamp": "2024-01-15T09:30:00.000Z"
    }
}
```

## 数据流

```
1. 用户打开Dashboard，自动订阅自选股
   ↓
2. WebSocket连接建立，发送订阅请求
   ↓
3. MarketDataManager将symbol加入活跃列表
   ↓
4. Gateway开始从数据源获取数据
   ↓
5. 收到原始数据 → 标准化 → Redis缓存
   ↓
6. K线合成器更新K线数据
   ↓
7. WebSocket推送到前端
   ↓
8. 前端更新UI (价格跳动、K线图更新)
```

## 技术选型

| 组件 | 选型 | 原因 |
|------|------|------|
| WebSocket库 | `websockets` | 成熟稳定，支持asyncio |
| K线图库 | `lightweight-charts` | TradingView出品，性能优秀 |
| 缓存 | Redis | 支持pub/sub，高性能 |
| 数据源SDK | `akshare` / `tushare` | 免费A股数据源 |

## 目录结构

```
src/
├── market_data/              # 行情数据模块
│   ├── __init__.py
│   ├── gateway/              # 网关实现
│   │   ├── __init__.py
│   │   ├── base.py           # 网关基类
│   │   ├── eastmoney.py      # 东方财富网关
│   │   └── tushare.py        # Tushare网关
│   ├── models.py             # 数据模型
│   ├── builder.py            # K线合成器
│   ├── manager.py            # 数据管理器
│   └── cache.py              # 缓存管理
├── api/v1/endpoints/
│   └── market.py             # 行情API
└── core/
    └── websocket_server.py   # WebSocket服务
```

## 性能指标

- **延迟**: < 100ms (数据源 → 前端)
- **并发**: 支持1000+标的同时订阅
- **存储**: K线数据保留2年，tick数据保留7天
- **可用性**: 99.9% (支持多源failover)
