# 数据库 + 模拟盘 快速启动指南

## 环境要求

- Docker & Docker Compose
- Python 3.11+
- PostgreSQL 15+（Docker自动安装）
- Redis 7+（Docker自动安装）

## 第一步：启动数据库

```bash
# 进入项目目录
cd quant-trading-system

# 启动 PostgreSQL 和 Redis
docker-compose -f docker-compose.dev.yml up -d

# 检查状态
docker-compose -f docker-compose.dev.yml ps
```

## 第二步：安装 Python 依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 第三步：配置环境变量

创建 `.env` 文件：

```bash
# 应用配置
APP_ENV=development
APP_DEBUG=true

# 数据库配置（与docker-compose一致）
DATABASE__HOST=localhost
DATABASE__PORT=5432
DATABASE__NAME=quant_trading
DATABASE__USER=quant_user
DATABASE__PASSWORD=quant_pass

# Redis配置
REDIS__HOST=localhost
REDIS__PORT=6379

# 其他配置保持默认...
```

## 第四步：初始化数据库

```bash
# 创建所有表结构 + 默认数据
python -m src.scripts.init_db
```

**预期输出：**
```
INFO  [database] 数据库初始化完成
INFO  [init_db] 创建默认模拟账户: SIM001, 初始资金: 1000000
INFO  [init_db] 创建策略: MA_CROSS - 双均线突破
INFO  [init_db] 创建策略: MACD_MOM - MACD动量
INFO  [init_db] 创建策略: BOLL_MEAN - 布林带均值回归
INFO  [init_db] 数据库初始化全部完成
```

## 第五步：运行迁移（可选）

```bash
# 生成迁移脚本（模型变更后）
alembic revision --autogenerate -m "initial migration"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 第六步：启动服务

```bash
# 启动后端 API
python -m src.main

# 或者使用 uvicorn 直接启动
uvicorn src.main:app --host 0.0.0.0 --port 9000 --reload
```

## 第七步：验证

### 检查 API 健康状态

```bash
curl http://localhost:9000/health
```

预期响应：
```json
{
  "status": "healthy",
  "timestamp": "2025-01-20T10:30:00.000000"
}
```

### 查看账户信息

```bash
curl http://localhost:9000/api/v1/accounts
```

### 查看策略列表

```bash
curl http://localhost:9000/api/v1/strategies
```

## 数据库管理

### pgAdmin 访问

- URL: http://localhost:5050
- 邮箱: admin@quant.com
- 密码: admin

添加服务器配置：
- Host: postgres
- Port: 5432
- Database: quant_trading
- Username: quant_user
- Password: quant_pass

### 常用 SQL 查询

```sql
-- 查看账户资金
SELECT account_no, total_balance, available, frozen, market_value 
FROM account;

-- 查看活跃策略
SELECT strategy_id, name, status, run_mode 
FROM strategy 
WHERE status = 'ACTIVE';

-- 查看今日订单
SELECT * FROM orders 
WHERE DATE(created_at) = CURRENT_DATE;

-- 查看持仓
SELECT symbol, total_qty, available_qty, cost_price, market_price 
FROM position;
```

## 常见问题

### 1. 数据库连接失败

检查 Docker 服务状态：
```bash
docker logs quant-postgres
```

### 2. 表未创建

手动初始化：
```bash
# 删除现有卷（会丢失数据！）
docker-compose -f docker-compose.dev.yml down -v

# 重新启动
docker-compose -f docker-compose.dev.yml up -d

# 重新初始化
python -m src.scripts.init_db
```

### 3. 端口冲突

修改 `docker-compose.dev.yml` 中的端口映射：
```yaml
ports:
  - "5433:5432"  # 使用 5433 替代 5432
```

同时更新 `.env` 中的 `DATABASE__PORT=5433`

## 下一步

数据库跑通后，继续实现：
1. **模拟撮合引擎** - 处理限价单成交逻辑
2. **订单状态机** - 完整的订单生命周期管理
3. **日终清算任务** - T+1持仓结算、对账

详见 [docs/IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
