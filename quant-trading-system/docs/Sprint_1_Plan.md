# 📅 Sprint 1 详细执行计划

> **Sprint目标**：实现交易闭环核心链路  
> **时间周期**：Week 1（7天）  
> **核心产出**：信号能触发订单，风控能拦截订单，成交能更新持仓

---

## 🗓️ 每日任务分解

### Day 1（周一）：数据库基础设施

#### 任务1.1：数据库连接管理
```
文件：src/common/database.py [NEW]
预估：2h
```
- [ ] 创建异步数据库连接池
- [ ] 配置数据库URL（从settings读取）
- [ ] 实现get_db依赖函数
- [ ] 数据库会话生命周期管理

**验收标准**：
```python
# 能在API中正常使用
@router.post("/test")
async def test(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account))
    return result.scalars().all()
```

#### 任务1.2：模型基础完善
```
文件：src/models/base.py [MODIFY]
预估：1h
```
- [ ] 确保get_db导出
- [ ] 添加常用模型方法（to_dict等）

#### 任务1.3：数据库初始化脚本
```
文件：scripts/init_database.py [MODIFY]
预估：2h
```
- [ ] 创建所有表结构
- [ ] 初始化基础数据（如系统账户）
- [ ] 支持幂等执行（重复执行不报错）

**Day 1 交付**：能运行 `python scripts/init_database.py` 成功创建表

---

### Day 2（周二）：数据校验与分发（太子院）

#### 任务2.1：太子院核心实现
```
文件：src/core/crown_prince.py [NEW]
预估：4h
```
- [ ] 数据校验规则（价格/数量有效性）
- [ ] 数据标准化（代码格式统一）
- [ ] 数据分发路由（转发到不同部门）

**核心类**：
```python
class CrownPrince:
    """太子院 - 数据前置校验与分发"""
    
    def validate_order(self, order: Order) -> ValidationResult:
        """订单数据校验"""
        pass
    
    def normalize_symbol(self, symbol: str) -> str:
        """代码标准化"""
        pass
    
    def dispatch(self, data: MarketData) -> DispatchResult:
        """数据分发到各部门"""
        pass
```

#### 任务2.2：集成MarketDataManager
```
文件：src/market_data/manager.py [MODIFY]
预估：2h
```
- [ ] WebSocket连接管理
- [ ] 实时数据订阅/取消订阅
- [ ] 数据分发到太子院

**Day 2 交付**：行情数据能经过校验后分发

---

### Day 3（周三）：信号生成引擎（中书省）

#### 任务3.1：策略信号生成
```
文件：src/core/zhongshu_sheng.py [NEW]
预估：4h
```
- [ ] 策略加载器
- [ ] 信号计算引擎
- [ ] 信号缓存与去重
- [ ] 信号分发到风控

**核心类**：
```python
class ZhongshuSheng:
    """中书省 - 策略信号生成"""
    
    def load_strategies(self, account_id: int) -> List[Strategy]:
        """加载活跃策略"""
        pass
    
    def generate_signals(self, tick: TickData) -> List[Signal]:
        """生成交易信号"""
        pass
    
    def on_tick(self, tick: TickData):
        """处理实时tick数据"""
        pass
```

#### 任务3.2：策略基类完善
```
文件：src/strategy/base.py [MODIFY]
预估：2h
```
- [ ] on_tick方法标准化
- [ ] generate_signal返回值规范
- [ ] 支持参数配置

**Day 3 交付**：策略能根据行情生成买卖信号

---

### Day 4（周四）：风控审核（门下省）

#### 任务4.1：风控规则引擎
```
文件：src/core/menxia_sheng.py [NEW]
预估：4h
```
- [ ] 风控规则链
- [ ] 单规则检查实现
- [ ] 组合规则检查
- [ ] 审核结果记录

**核心类**：
```python
class MenxiaSheng:
    """门下省 - 风控审核与拦截"""
    
    def __init__(self):
        self.rules: List[RiskRule] = []
    
    def add_rule(self, rule: RiskRule):
        """添加风控规则"""
        pass
    
    def audit_order(self, order: Order, account: Account) -> AuditResult:
        """审核订单"""
        pass
    
    def audit_signal(self, signal: Signal, account: Account) -> AuditResult:
        """审核信号"""
        pass
```

#### 任务4.2：风控规则实现
```
文件：src/risk/risk_manager.py [MODIFY]
预估：2h
```
- [ ] 仓位限制规则
- [ ] 单日亏损限制规则
- [ ] 价格异常波动规则

**Day 4 交付**：订单和信号经过风控审核，违规被拦截

---

### Day 5（周五）：执行调度（尚书省）

#### 任务5.1：执行调度引擎
```
文件：src/core/shangshu_sheng.py [NEW]
预估：4h
```
- [ ] 订单队列管理
- [ ] 资金冻结/解冻
- [ ] 订单路由到执行算法
- [ ] 成交结果处理

**核心类**：
```python
class ShangshuSheng:
    """尚书省 - 执行调度与资金清算"""
    
    def __init__(self):
        self.order_queue = OrderQueue()
        self.capital_manager = CapitalManager()
    
    async def submit_order(self, order: Order) -> SubmitResult:
        """提交订单"""
        pass
    
    async def on_trade(self, trade: Trade):
        """处理成交"""
        pass
    
    async def update_position(self, trade: Trade):
        """更新持仓"""
        pass
```

#### 任务5.2：资金与持仓联动
```
文件：src/finance/capital_manager.py [MODIFY]
预估：2h
```
- [ ] 委托时冻结资金
- [ ] 成交时扣减/增加资金
- [ ] 费用计算（佣金/印花税）

**Day 5 交付**：订单能正确触发资金变动和持仓更新

---

### Day 6（周六）：前端联动

#### 任务6.1：WebSocket服务
```
文件：web/src/services/websocket.ts [MODIFY]
预估：3h
```
- [ ] 连接后端WebSocket
- [ ] 实时tick数据处理
- [ ] 信号推送接收
- [ ] 订单状态推送

#### 任务6.2：交易视图完善
```
文件：web/src/views/TradeView.vue [MODIFY]
预估：3h
```
- [ ] 下单后实时更新订单状态
- [ ] 显示可用资金（实时）
- [ ] 显示持仓（实时）

**Day 6 交付**：前端能实时看到下单、成交、持仓变化

---

### Day 7（周日）：联调测试

#### 任务7.1：完整链路测试
```
预估：4h
```
测试场景：
- [ ] 正常下单 → 成交 → 持仓更新
- [ ] 信号生成 → 风控通过 → 自动下单
- [ ] 风控拦截 → 订单拒绝
- [ ] 资金不足 → 下单失败

#### 任务7.2：Bug修复
```
预估：4h
```
- [ ] 修复联调中发现的问题
- [ ] 完善错误处理

**Day 7 交付**：完整交易链路跑通

---

## 📝 文件清单（Sprint 1）

### 新增文件
```
src/common/database.py          [NEW] 数据库连接管理
src/core/crown_prince.py        [NEW] 太子院-数据校验
src/core/zhongshu_sheng.py      [NEW] 中书省-信号生成
src/core/menxia_sheng.py        [NEW] 门下省-风控审核
src/core/shangshu_sheng.py      [NEW] 尚书省-执行调度
```

### 修改文件
```
src/models/base.py              [MODIFY] 完善get_db
scripts/init_database.py        [MODIFY] 初始化脚本
src/market_data/manager.py      [MODIFY] WebSocket完善
src/strategy/base.py            [MODIFY] 策略基类
src/risk/risk_manager.py        [MODIFY] 风控规则
src/finance/capital_manager.py  [MODIFY] 资金联动
web/src/services/websocket.ts   [MODIFY] WebSocket服务
web/src/views/TradeView.vue     [MODIFY] 交易视图
```

---

## 🎯 验收标准

### 功能验收
- [ ] 行情数据能实时推送到前端
- [ ] 策略能根据行情生成信号
- [ ] 信号经过风控审核
- [ ] 审核通过的信号生成订单
- [ ] 订单成交后更新持仓
- [ ] 订单成交后更新资金

### 接口验收
```bash
# 测试WebSocket连接
wscat -c ws://localhost:8000/api/v1/market/ws

# 测试下单
POST /api/v1/orders/
{"symbol": "000001.SZ", "side": "buy", "quantity": 100, "price": 10.5}

# 测试持仓查询
GET /api/v1/positions/

# 测试资金查询
GET /api/v1/capital/{account_id}/snapshot
```

---

## ⚠️ 风险与应对

| 风险 | 可能性 | 影响 | 应对策略 |
|------|--------|------|----------|
| WebSocket不稳定 | 中 | 高 | 准备降级到轮询方案 |
| 数据库性能瓶颈 | 低 | 高 | 提前设计缓存策略 |
| 风控规则复杂 | 中 | 中 | 先实现核心3条规则 |
| 前端实时更新卡顿 | 中 | 中 | 使用虚拟滚动+防抖 |

---

## 📊 工作量统计

| 类别 | 文件数 | 预估工时 | 实际工时 |
|------|--------|----------|----------|
| 新增 | 5 | 22h | - |
| 修改 | 8 | 16h | - |
| 测试 | - | 8h | - |
| **总计** | **13** | **46h** | - |

**建议**：每天工作6-7小时，预留缓冲时间

---

## ✅ 每日Check-in

每天结束前列行检查：
1. 今天完成了哪些任务？
2. 有阻塞问题吗？
3. 明天计划做什么？
4. 需要调整计划吗？

---

**Sprint 1 成功标志**：在TradeView页面下单，能在PositionsView看到持仓变化！
