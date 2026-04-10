# 本地开发环境搭建指南（无 Docker）

## 前置条件

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

---

## 第一步：安装 PostgreSQL

### Windows

1. 下载安装包：https://www.postgresql.org/download/windows/
2. 安装时记住设置的密码
3. 安装完成后，打开 **pgAdmin 4** 或 **psql**

### macOS

```bash
# 使用 Homebrew 安装
brew install postgresql@15

# 启动服务
brew services start postgresql@15

# 创建数据库
createdb quant_trading

# 创建用户（可选）
createuser -s quant_user
```

### Linux (Ubuntu/Debian)

```bash
# 安装
sudo apt update
sudo apt install postgresql-15 postgresql-contrib

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres psql -c "CREATE DATABASE quant_trading;"
sudo -u postgres psql -c "CREATE USER quant_user WITH PASSWORD 'quant_pass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE quant_trading TO quant_user;"
```

---

## 第二步：安装 Redis

### Windows

1. 下载：https://github.com/microsoftarchive/redis/releases
2. 解压到 `C:\Redis`
3. 运行 `redis-server.exe`

或使用 WSL2：
```bash
# WSL2 Ubuntu
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

### macOS

```bash
brew install redis
brew services start redis
```

### Linux

```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

验证：
```bash
redis-cli ping
# 应返回: PONG
```

---

## 第三步：配置项目

### 1. 创建虚拟环境

```bash
cd quant-trading-system

# 创建虚拟环境
python -m venv venv

# Windows 激活
venv\Scripts\activate

# macOS/Linux 激活
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 复制配置文件

```bash
# Windows
copy .env.local .env

# macOS/Linux
cp .env.local .env
```

### 4. 修改数据库配置

编辑 `.env` 文件，修改数据库连接信息：

```bash
# 根据你的 PostgreSQL 配置修改
DATABASE__HOST=localhost
DATABASE__PORT=5432
DATABASE__NAME=quant_trading
DATABASE__USER=postgres          # 或你创建的用户名
DATABASE__PASSWORD=your_password  # 你的密码
```

---

## 第四步：初始化数据库

### 方法1：使用初始化脚本（推荐）

```bash
python -m src.scripts.init_db
```

这会：
1. 创建所有表结构
2. 创建默认模拟账户（SIM001，初始资金100万）
3. 创建示例策略（双均线、MACD、布林带）

### 方法2：使用 Alembic 迁移

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "initial migration"

# 执行迁移
alembic upgrade head

# 然后手动初始化数据
python -m src.scripts.init_data
```

---

## 第五步：启动服务

### 启动后端 API

```bash
# 开发模式（热重载）
python -m src.main

# 或使用 uvicorn
uvicorn src.main:app --host 0.0.0.0 --port 9000 --reload
```

### 验证服务

```bash
# 健康检查
curl http://localhost:9000/health

# 查看 API 文档
open http://localhost:9000/docs
```

### 启动前端（可选）

```bash
cd web
npm install
npm run dev
```

访问 http://localhost:9001

---

## 常见问题

### 1. PostgreSQL 连接失败

**错误**: `connection refused`

解决：
```bash
# 检查服务状态
# Windows:  services.msc 中找到 postgresql-x64-15
# macOS:   brew services list
# Linux:   sudo systemctl status postgresql

# 检查端口
# Windows: netstat -an | findstr 5432
# macOS/Linux: netstat -tlnp | grep 5432
```

### 2. 密码错误

**错误**: `password authentication failed`

解决：
```bash
# 修改 PostgreSQL 密码
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'new_password';"

# 然后更新 .env 文件
```

### 3. 数据库不存在

```bash
# 手动创建
createdb -U postgres quant_trading

# 或使用 psql
psql -U postgres -c "CREATE DATABASE quant_trading;"
```

### 4. Redis 连接失败

```bash
# 检查 Redis 是否运行
redis-cli ping

# 手动启动
redis-server
```

### 5. 端口被占用

```bash
# 查找占用端口的进程
# Windows: netstat -ano | findstr 9000
# macOS/Linux: lsof -i :9000

# 修改 .env 中的端口
APP_URL=http://localhost:9002
```

---

## 开发工作流

```bash
# 1. 确保数据库和 Redis 已启动
redis-cli ping
psql -U postgres -d quant_trading -c "SELECT 1;"

# 2. 激活虚拟环境
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 3. 启动后端
python -m src.main

# 4. 另开终端启动前端（可选）
cd web && npm run dev
```

---

## 数据库管理

### 使用命令行

```bash
# 连接数据库
psql -U postgres -d quant_trading

# 查看表
\dt

# 查看账户
SELECT * FROM account;

# 查看策略
SELECT strategy_id, name, status FROM strategy;

# 退出
\q
```

### 使用 DBeaver（推荐）

1. 下载：https://dbeaver.io/
2. 新建连接 → PostgreSQL
3. 配置：
   - Host: localhost
   - Port: 5432
   - Database: quant_trading
   - User: postgres
   - Password: your_password

---

## 下一步

数据库跑通后，继续实现：
1. **订单状态机** - 见 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
2. **模拟撮合引擎**
3. **交易服务层**
