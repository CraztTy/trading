# 本地开发快速启动（无 Docker）

## 检查清单

启动前请确保：

- [ ] PostgreSQL 已安装并运行
- [ ] Redis 已安装并运行
- [ ] Python 3.11+ 已安装

---

## 5 分钟启动

### 1. 启动 PostgreSQL 和 Redis

**Windows:**
```powershell
# 启动 PostgreSQL（服务方式）
net start postgresql-x64-15

# 启动 Redis（命令行方式，保持窗口打开）
redis-server
```

**macOS:**
```bash
brew services start postgresql@15
brew services start redis
```

**Linux:**
```bash
sudo systemctl start postgresql
sudo systemctl start redis
```

### 2. 创建数据库

```bash
# 连接 PostgreSQL 并创建数据库
psql -U postgres -c "CREATE DATABASE quant_trading;"
```

如果提示密码，输入安装时设置的密码。

### 3. 配置项目

```bash
cd quant-trading-system

# 创建虚拟环境
python -m venv venv

# Windows 激活
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制配置文件
copy .env.local .env    # Windows
cp .env.local .env      # macOS/Linux
```

编辑 `.env` 文件，修改数据库密码：
```bash
DATABASE__PASSWORD=你的postgres密码
```

### 4. 启动服务

```bash
# 方式1：一键启动（推荐）
python start_local.py

# 方式2：分步启动
# 4.1 初始化数据库
python -m src.scripts.init_db

# 4.2 启动服务
python -m src.main
```

### 5. 验证

```bash
# 健康检查
curl http://localhost:9000/health

# 查看 API 文档
http://localhost:9000/docs
```

---

## 常见错误

### ImportError: No module named 'src'

解决：确保在项目根目录运行，并使用 `python -m` 方式
```bash
python -m src.main        # ✓ 正确
python src/main.py        # ✗ 错误
```

### Connection refused (PostgreSQL)

```bash
# 检查 PostgreSQL 是否运行
# Windows: services.msc 查看 postgresql 服务状态
# macOS: brew services list
# Linux: sudo systemctl status postgresql

# 检查端口
netstat -an | findstr 5432    # Windows
lsof -i :5432                  # macOS/Linux
```

### password authentication failed

```bash
# 修改 pg_hba.conf 文件（Windows 在 PostgreSQL 安装目录/data）
# 将 scram-sha-256 改为 trust 进行本地开发
# 或正确配置密码
```

### asyncpg 安装失败

Windows 可能需要 Visual C++ 构建工具：
```bash
# 或安装预编译版本
pip install asyncpg --only-binary :all:
```

---

## 项目结构

```
quant-trading-system/
├── src/
│   ├── models/           # 数据库模型
│   │   ├── base.py       # SQLAlchemy 配置
│   │   ├── account.py    # 账户模型
│   │   ├── strategy.py   # 策略模型
│   │   ├── order.py      # 订单模型
│   │   ├── trade.py      # 成交模型
│   │   ├── position.py   # 持仓模型
│   │   └── ...
│   ├── api/              # API 路由
│   ├── core/             # 核心逻辑（三省六部）
│   └── scripts/          # 工具脚本
├── docs/                 # 文档
├── .env.local            # 本地配置模板
└── start_local.py        # 一键启动脚本
```

---

## 后续步骤

服务启动成功后，继续开发：

1. **订单状态机** - 实现状态流转
2. **模拟撮合引擎** - 限价单撮合
3. **交易服务层** - 完整买卖流程

详见 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
