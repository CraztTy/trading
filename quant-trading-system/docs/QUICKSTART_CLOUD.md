# 云服务器环境快速启动指南

## 环境信息

- **云服务器 IP**: 8.130.110.224
- **PostgreSQL**: 端口 5432
- **Redis**: 端口 6379

## 检查清单

启动前请确保：

- [ ] 云服务器 PostgreSQL 已运行并可远程访问
- [ ] 云服务器 Redis 已运行并可远程访问
- [ ] 本地可连通云服务器（`ping 8.130.110.224`）
- [ ] 防火墙已开放 5432 和 6379 端口

---

## 云服务器准备

### 1. PostgreSQL 配置远程访问

SSH 登录云服务器，修改配置：

```bash
# 编辑 postgresql.conf
sudo vi /etc/postgresql/15/main/postgresql.conf
# 找到并修改：
listen_addresses = '*'

# 编辑 pg_hba.conf
sudo vi /etc/postgresql/15/main/pg_hba.conf
# 添加以下行（允许远程连接）：
host    all             all             0.0.0.0/0               scram-sha-256

# 重启 PostgreSQL
sudo systemctl restart postgresql
```

创建数据库和用户：

```bash
sudo -u postgres psql

CREATE DATABASE quant_trading;
CREATE USER quant_user WITH PASSWORD 'quant_pass';
GRANT ALL PRIVILEGES ON DATABASE quant_trading TO quant_user;
\q
```

### 2. Redis 配置远程访问

```bash
# 编辑 redis.conf
sudo vi /etc/redis/redis.conf

# 修改以下配置：
bind 0.0.0.0
protected-mode no
# 如需密码，取消注释并设置：
# requirepass your_redis_password

# 重启 Redis
sudo systemctl restart redis
```

### 3. 防火墙配置

```bash
# 开放 PostgreSQL 和 Redis 端口
sudo ufw allow 5432/tcp
sudo ufw allow 6379/tcp

# 或 iptables
sudo iptables -A INPUT -p tcp --dport 5432 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 6379 -j ACCEPT
```

---

## 本地开发机配置

### 1. 测试连接

```bash
# 测试 PostgreSQL 连接
psql -h 8.130.110.224 -U quant_user -d quant_trading -c "SELECT 1;"

# 测试 Redis 连接
redis-cli -h 8.130.110.224 ping
```

### 2. 配置项目

```bash
cd quant-trading-system

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 复制云服务器配置
copy .env.cloud .env    # Windows
cp .env.cloud .env      # macOS/Linux
```

### 3. 修改配置（如需要）

编辑 `.env` 文件：

```bash
# 如果云服务器数据库密码不同，修改此处
DATABASE__PASSWORD=实际密码

# 如果 Redis 设置了密码，修改此处
REDIS__PASSWORD=redis密码
```

---

## 启动服务

### 方式1：一键启动（推荐）

```bash
python start_local.py
```

### 方式2：分步启动

```bash
# 初始化数据库（首次运行）
python -m src.scripts.init_db

# 启动服务
python -m src.main
```

---

## 验证

```bash
# 健康检查
curl http://localhost:9000/health

# 查看 API 文档
open http://localhost:9000/docs

# 查看账户信息
curl http://localhost:9000/api/v1/accounts
```

---

## 常见问题

### 连接超时

检查云服务器安全组/防火墙：

```bash
# 本地测试端口连通性
telnet 8.130.110.224 5432
telnet 8.130.110.224 6379

# 云服务器检查监听
netstat -tlnp | grep -E '5432|6379'
```

### PostgreSQL 认证失败

```bash
# 云服务器上重置密码
sudo -u postgres psql -c "ALTER USER quant_user WITH PASSWORD 'quant_pass';"

# 检查 pg_hba.conf 配置
cat /etc/postgresql/15/main/pg_hba.conf | grep -v '^#' | grep -v '^$'
```

### Redis 连接被拒绝

```bash
# 检查 Redis 配置
redis-cli INFO | grep bind

# 检查防火墙
sudo ufw status
```

---

## 安全建议

⚠️ **生产环境必须注意**：

1. **修改默认密码**
   - PostgreSQL 不要使用 `quant_pass`
   - Redis 设置强密码

2. **限制访问 IP**
   - pg_hba.conf 中 `0.0.0.0/0` 改为具体 IP 段
   - 云服务器安全组限制来源 IP

3. **使用 SSL**
   - PostgreSQL 启用 SSL 连接
   - Redis 启用 TLS

4. **VPN/内网**
   - 最佳实践：数据库不暴露公网
   - 通过 VPN 或跳板机访问

---

## 架构图

```
本地开发机                          云服务器 (8.130.110.224)
+---------------+                   +-------------------------+
| Python 代码   |  <-- 网络 -->     | PostgreSQL (port 5432)  |
| FastAPI 服务  |                   | Redis (port 6379)       |
| (port 9000)   |                   |                         |
+---------------+                   +-------------------------+
```

本地只运行 Python 代码，数据全部存储在云服务器。
