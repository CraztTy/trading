# 睿之兮量化交易系统 - 数据库设计文档

## 技术栈
- **数据库**: PostgreSQL 15+
- **ORM**: SQLAlchemy 2.0
- **迁移**: Alembic
- **缓存**: Redis 7+

---

## 核心表结构

### 1. account（账户表）

```sql
CREATE TABLE account (
    id              SERIAL PRIMARY KEY,
    account_no      VARCHAR(32) UNIQUE NOT NULL,    -- 账户编号
    name            VARCHAR(64) NOT NULL,            -- 账户名称
    account_type    VARCHAR(16) DEFAULT 'SIMULATE', -- SIMULATE/REAL
    
    -- 资金字段（单位：元，精确到分）
    total_balance   DECIMAL(18, 2) DEFAULT 0,       -- 总资产
    available       DECIMAL(18, 2) DEFAULT 0,       -- 可用资金
    frozen          DECIMAL(18, 2) DEFAULT 0,       -- 冻结资金
    market_value    DECIMAL(18, 2) DEFAULT 0,       -- 持仓市值
    
    -- 盈亏统计
    realized_pnl    DECIMAL(18, 2) DEFAULT 0,       -- 已实现盈亏
    unrealized_pnl  DECIMAL(18, 2) DEFAULT 0,       -- 浮动盈亏
    
    -- 配置
    initial_capital DECIMAL(18, 2) DEFAULT 1000000, -- 初始资金
    max_drawdown    DECIMAL(8, 4) DEFAULT 0,        -- 最大回撤率
    
    -- 状态
    status          VARCHAR(16) DEFAULT 'ACTIVE',   -- ACTIVE/SUSPENDED/CLOSED
    
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_account_no ON account(account_no);
CREATE INDEX idx_account_status ON account(status);
```

### 2. strategy（策略表）

```sql
CREATE TABLE strategy (
    id              SERIAL PRIMARY KEY,
    strategy_id     VARCHAR(32) UNIQUE NOT NULL,    -- 策略唯一标识
    name            VARCHAR(64) NOT NULL,            -- 策略名称
    description     TEXT,                            -- 策略描述
    
    -- 分类
    category        VARCHAR(32),                     -- 策略分类：趋势/均值回归/套利
    style           VARCHAR(32),                     -- 风格：趋势跟踪/统计套利
    
    -- 参数（JSON存储，灵活扩展）
    params          JSONB DEFAULT '{}',              -- 策略参数
    
    -- 风控参数
    max_position    DECIMAL(8, 4) DEFAULT 0.1,      -- 最大仓位比例
    stop_loss       DECIMAL(8, 4) DEFAULT 0.02,     -- 止损比例
    take_profit     DECIMAL(8, 4) DEFAULT 0.05,     -- 止盈比例
    
    -- 运行状态
    status          VARCHAR(16) DEFAULT 'INACTIVE', -- INACTIVE/ACTIVE/PAUSED/ERROR
    run_mode        VARCHAR(16) DEFAULT 'BACKTEST', -- BACKTEST/SIMULATE/LIVE
    
    -- 统计
    total_trades    INTEGER DEFAULT 0,              -- 总交易次数
    win_trades      INTEGER DEFAULT 0,              -- 盈利次数
    loss_trades     INTEGER DEFAULT 0,              -- 亏损次数
    total_return    DECIMAL(12, 4) DEFAULT 0,       -- 总收益率
    sharpe_ratio    DECIMAL(8, 4) DEFAULT 0,        -- 夏普比率
    max_drawdown    DECIMAL(8, 4) DEFAULT 0,        -- 最大回撤
    
    -- 关联
    account_id      INTEGER REFERENCES account(id),
    
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at    TIMESTAMP WITH TIME ZONE        -- 激活时间
);

-- 索引
CREATE INDEX idx_strategy_id ON strategy(strategy_id);
CREATE INDEX idx_strategy_status ON strategy(status);
CREATE INDEX idx_strategy_account ON strategy(account_id);
CREATE INDEX idx_strategy_params ON strategy USING GIN(params);
```

### 3. orders（订单表）

```sql
CREATE TABLE orders (
    id                  BIGSERIAL PRIMARY KEY,
    order_id            VARCHAR(32) UNIQUE NOT NULL,    -- 系统订单号
    exchange_order_id   VARCHAR(64),                     -- 交易所订单号（券商返回）
    
    -- 关联
    strategy_id         INTEGER REFERENCES strategy(id),
    account_id          INTEGER REFERENCES account(id),
    
    -- 标的
    symbol              VARCHAR(16) NOT NULL,            -- 股票代码 600519.SH
    symbol_name         VARCHAR(32),                     -- 股票名称
    
    -- 订单要素
    direction           VARCHAR(8) NOT NULL,             -- BUY/SELL
    order_type          VARCHAR(16) DEFAULT 'LIMIT',     -- LIMIT/MARKET/STOP
    qty                 INTEGER NOT NULL,                -- 委托数量（股）
    price               DECIMAL(12, 3),                  -- 委托价格
    
    -- 状态机
    status              VARCHAR(16) DEFAULT 'CREATED',   -- CREATED/PENDING/PARTIAL/FILLED/CANCELLED/REJECTED/EXPIRED
    
    -- 成交统计
    filled_qty          INTEGER DEFAULT 0,               -- 已成交数量
    filled_avg_price    DECIMAL(12, 3) DEFAULT 0,        -- 成交均价
    filled_amount       DECIMAL(18, 2) DEFAULT 0,        -- 成交金额
    
    -- 时间戳
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    submitted_at        TIMESTAMP WITH TIME ZONE,        -- 提交到交易所时间
    filled_at           TIMESTAMP WITH TIME ZONE,        -- 完全成交时间
    cancelled_at        TIMESTAMP WITH TIME ZONE,        -- 撤单时间
    
    -- 错误信息
    error_msg           TEXT,                            -- 拒绝/错误原因
    
    -- 备注
    remark              VARCHAR(256)
);

-- 索引（订单表是查询热点，索引要全）
CREATE INDEX idx_orders_order_id ON orders(order_id);
CREATE INDEX idx_orders_strategy ON orders(strategy_id);
CREATE INDEX idx_orders_account ON orders(account_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at);
CREATE INDEX idx_orders_filled ON orders(filled_at) WHERE filled_at IS NOT NULL;

-- 复合索引：策略+状态查询
CREATE INDEX idx_orders_strategy_status ON orders(strategy_id, status);
-- 复合索引：账户+日期查询
CREATE INDEX idx_orders_account_date ON orders(account_id, created_at);
```

### 4. trade（成交表）

```sql
CREATE TABLE trade (
    id              BIGSERIAL PRIMARY KEY,
    trade_id        VARCHAR(32) UNIQUE NOT NULL,    -- 成交编号
    
    -- 关联
    order_id        BIGINT REFERENCES orders(id),
    strategy_id     INTEGER REFERENCES strategy(id),
    account_id      INTEGER REFERENCES account(id),
    
    -- 标的
    symbol          VARCHAR(16) NOT NULL,
    symbol_name     VARCHAR(32),
    
    -- 成交要素
    direction       VARCHAR(8) NOT NULL,             -- BUY/SELL
    qty             INTEGER NOT NULL,                -- 成交数量
    price           DECIMAL(12, 3) NOT NULL,         -- 成交价格
    amount          DECIMAL(18, 2) NOT NULL,         -- 成交金额
    
    -- 费用明细
    commission      DECIMAL(12, 2) DEFAULT 0,       -- 佣金
    stamp_tax       DECIMAL(12, 2) DEFAULT 0,       -- 印花税
    transfer_fee    DECIMAL(12, 2) DEFAULT 0,       -- 过户费
    total_fee       DECIMAL(12, 2) DEFAULT 0,       -- 总费用
    
    -- 时间
    trade_time      TIMESTAMP WITH TIME ZONE NOT NULL, -- 成交时间
    
    -- 对账标记
    reconciled      BOOLEAN DEFAULT FALSE,          -- 是否已对账
    
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_trade_order ON trade(order_id);
CREATE INDEX idx_trade_strategy ON trade(strategy_id);
CREATE INDEX idx_trade_account ON trade(account_id);
CREATE INDEX idx_trade_symbol ON trade(symbol);
CREATE INDEX idx_trade_time ON trade(trade_time);
CREATE INDEX idx_trade_reconciled ON trade(reconciled) WHERE reconciled = FALSE;
```

### 5. position（持仓表）

```sql
CREATE TABLE position (
    id              BIGSERIAL PRIMARY KEY,
    
    -- 关联
    account_id      INTEGER REFERENCES account(id),
    strategy_id     INTEGER REFERENCES strategy(id), -- 可为NULL（非策略交易）
    
    -- 标的
    symbol          VARCHAR(16) NOT NULL,
    symbol_name     VARCHAR(32),
    
    -- 数量（T+1制度）
    total_qty       INTEGER DEFAULT 0,              -- 总持仓
    available_qty   INTEGER DEFAULT 0,              -- 可用持仓（可卖）
    frozen_qty      INTEGER DEFAULT 0,              -- 冻结数量
    
    -- 成本
    cost_price      DECIMAL(12, 3) DEFAULT 0,       -- 成本价
    cost_amount     DECIMAL(18, 2) DEFAULT 0,       -- 总成本
    
    -- 市值
    market_price    DECIMAL(12, 3) DEFAULT 0,       -- 当前市价
    market_value    DECIMAL(18, 2) DEFAULT 0,       -- 市值
    
    -- 盈亏
    unrealized_pnl  DECIMAL(18, 2) DEFAULT 0,       -- 浮动盈亏
    unrealized_pnl_pct DECIMAL(8, 4) DEFAULT 0,     -- 浮动盈亏率
    realized_pnl    DECIMAL(18, 2) DEFAULT 0,       -- 已实现盈亏（该标的）
    
    -- 时间
    opened_at       TIMESTAMP WITH TIME ZONE,       -- 首次建仓时间
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 唯一约束：一个账户一个标的只能有一条持仓
    UNIQUE(account_id, symbol)
);

-- 索引
CREATE INDEX idx_position_account ON position(account_id);
CREATE INDEX idx_position_strategy ON position(strategy_id);
CREATE INDEX idx_position_symbol ON position(symbol);
```

### 6. balance_flow（资金流水表）

```sql
CREATE TABLE balance_flow (
    id              BIGSERIAL PRIMARY KEY,
    
    -- 关联
    account_id      INTEGER REFERENCES account(id),
    order_id        BIGINT REFERENCES orders(id),   -- 可为NULL
    trade_id        BIGINT REFERENCES trade(id),    -- 可为NULL
    
    -- 变动类型
    flow_type       VARCHAR(32) NOT NULL,            -- DEPOSIT/WITHDRAW/ORDER_FROZEN/ORDER_UNFROZEN/TRADE_BUY/TRADE_SELL/FEE/DIVIDEND
    
    -- 金额（正数表示增加，负数表示减少）
    amount          DECIMAL(18, 2) NOT NULL,
    balance_before  DECIMAL(18, 2) NOT NULL,         -- 变动前余额
    balance_after   DECIMAL(18, 2) NOT NULL,         -- 变动后余额
    
    -- 说明
    description     VARCHAR(256),
    remark          TEXT,
    
    -- 时间
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_balance_flow_account ON balance_flow(account_id);
CREATE INDEX idx_balance_flow_type ON balance_flow(flow_type);
CREATE INDEX idx_balance_flow_created ON balance_flow(created_at);
-- 用于对账查询
CREATE INDEX idx_balance_flow_order ON balance_flow(order_id);
```

---

## 辅助表

### 7. daily_settlement（日终结算表）

```sql
CREATE TABLE daily_settlement (
    id              BIGSERIAL PRIMARY KEY,
    account_id      INTEGER REFERENCES account(id),
    trade_date      DATE NOT NULL,                   -- 交易日期
    
    -- 资金快照
    begin_balance   DECIMAL(18, 2),                  -- 日初资金
    end_balance     DECIMAL(18, 2),                  -- 日终资金
    deposit         DECIMAL(18, 2) DEFAULT 0,        -- 入金
    withdraw        DECIMAL(18, 2) DEFAULT 0,        -- 出金
    realized_pnl    DECIMAL(18, 2) DEFAULT 0,        -- 当日实现盈亏
    total_fee       DECIMAL(18, 2) DEFAULT 0,        -- 当日总费用
    
    -- 持仓快照
    position_count  INTEGER DEFAULT 0,               -- 持仓数量
    position_value  DECIMAL(18, 2) DEFAULT 0,        -- 持仓市值
    
    -- 对账状态
    reconciled      BOOLEAN DEFAULT FALSE,
    reconcile_diff  DECIMAL(18, 2) DEFAULT 0,        -- 对账差异
    
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(account_id, trade_date)
);

CREATE INDEX idx_settlement_date ON daily_settlement(trade_date);
```

### 8. market_data_snapshot（行情快照表）

```sql
CREATE TABLE market_data_snapshot (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(16) NOT NULL,
    snapshot_time   TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- 价格
    open            DECIMAL(12, 3),
    high            DECIMAL(12, 3),
    low             DECIMAL(12, 3),
    close           DECIMAL(12, 3),
    pre_close       DECIMAL(12, 3),
    
    -- 成交量额
    volume          BIGINT,
    amount          DECIMAL(18, 2),
    
    -- 买卖盘（简化存储）
    bid_price_1     DECIMAL(12, 3),
    bid_vol_1       INTEGER,
    ask_price_1     DECIMAL(12, 3),
    ask_vol_1       INTEGER,
    
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 分区表（按日期分区，保留最近30天）
-- 实际实现使用 PostgreSQL 表分区
CREATE INDEX idx_snapshot_symbol_time ON market_data_snapshot(symbol, snapshot_time);
```

---

## 状态枚举定义

### 订单状态（Order Status）
```python
class OrderStatus(str, Enum):
    CREATED = "CREATED"         # 已创建
    PENDING = "PENDING"         # 已报（提交到交易所）
    PARTIAL = "PARTIAL"         # 部成
    FILLED = "FILLED"           # 全成
    CANCELLED = "CANCELLED"     # 已撤
    REJECTED = "REJECTED"       # 已拒绝
    EXPIRED = "EXPIRED"         # 过期（条件单）
```

### 资金流水类型（Flow Type）
```python
class FlowType(str, Enum):
    # 出入金
    DEPOSIT = "DEPOSIT"                 # 入金
    WITHDRAW = "WITHDRAW"               # 出金
    
    # 订单相关
    ORDER_FROZEN = "ORDER_FROZEN"       # 委托冻结资金
    ORDER_UNFROZEN = "ORDER_UNFROZEN"   # 委托解冻资金
    
    # 成交相关
    TRADE_BUY = "TRADE_BUY"             # 买入成交
    TRADE_SELL = "TRADE_SELL"           # 卖出成交
    
    # 费用
    COMMISSION = "COMMISSION"           # 佣金
    STAMP_TAX = "STAMP_TAX"             # 印花税
    TRANSFER_FEE = "TRANSFER_FEE"       # 过户费
    
    # 其他
    DIVIDEND = "DIVIDEND"               # 分红
    RIGHTS_ISSUE = "RIGHTS_ISSUE"       # 配股
```

---

## 关键业务逻辑说明

### 1. 下单流程
```
1. 创建订单（CREATED）
   ↓ 校验资金/持仓
2. 冻结资金（balance_flow: ORDER_FROZEN）
   ↓ 提交到交易所
3. 订单状态更新（PENDING）
   ↓ 收到成交回报
4. 更新订单成交数量
   ↓ 完全成交
5. 订单状态更新（FILLED）
   ↓ 资金清算
6. 解冻剩余资金（ORDER_UNFROZEN）
   ↓ 扣减/增加资金（TRADE_BUY/TRADE_SELL）
7. 记录费用（COMMISSION/STAMP_TAX）
   ↓ 更新持仓
8. 更新/创建 position 记录
```

### 2. T+1 持仓处理
- 买入成交：total_qty 增加，available_qty 不变（当日不可卖）
- 日终清算：将 total_qty 同步到 available_qty
- 卖出委托：检查 available_qty 是否充足

### 3. 资金一致性保障
- 所有资金变动必须通过 balance_flow 记录
- 使用数据库事务保证原子性
- 日终对账：sum(balance_flow) = account.available + account.frozen + account.market_value - account.realized_pnl

---

## 下一步

1. 确认表结构设计
2. 编写 SQLAlchemy 2.0 模型代码
3. 配置 Alembic 迁移
4. 编写基础 CRUD 和事务封装
5. 实现订单状态机
6. 对接模拟撮合引擎

有什么需要调整的地方吗？
