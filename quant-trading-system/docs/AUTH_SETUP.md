# 用户认证与数据库集成 - 快速启动指南

## 概述

本系统已集成完整的用户认证模块，包括：
- JWT Token认证（访问令牌 + 刷新令牌）
- 用户注册/登录/登出
- 密码强度验证
- 用户状态管理（激活/锁定/超级用户）

## 技术栈

**后端:**
- FastAPI + SQLAlchemy 2.0 (异步)
- MySQL + aiomysql
- JWT (python-jose)
- bcrypt密码哈希

**前端:**
- Vue3 + TypeScript
- Pinia状态管理
- Element Plus UI
- Axios + 拦截器自动刷新Token

## 快速开始

### 1. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd web
npm install
```

### 2. 配置环境变量

确保 `.env` 文件配置正确：

```env
# 数据库配置
DATABASE__HOST=localhost
DATABASE__PORT=3306
DATABASE__NAME=quant_trading
DATABASE__USER=your_user
DATABASE__PASSWORD=your_password

# JWT配置
SECURITY__JWT_SECRET_KEY=your-secret-key-must-be-at-least-32-char-long
SECURITY__JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
SECURITY__JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3. 初始化数据库

```bash
# 创建数据库表和初始用户
python scripts/init_database.py
```

这将创建：
- 所有数据表（包括用户表）
- 超级用户 `admin` / `Admin@123456`
- 演示用户 `demo` / `Demo@123456`（开发环境）

### 4. 启动服务

```bash
# 启动后端API
python -m src.main

# 启动前端（新终端）
cd web
npm run dev
```

### 5. 访问应用

- 前端: http://localhost:5173
- 后端API文档: http://localhost:9000/docs

## API端点

### 认证相关

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/refresh` | 刷新Token |
| POST | `/api/v1/auth/logout` | 用户登出 |
| GET | `/api/v1/auth/me` | 获取当前用户 |
| POST | `/api/v1/auth/password` | 修改密码 |

### 请求示例

**登录:**
```bash
curl -X POST http://localhost:9000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin@123456"}'
```

**响应:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## 前端认证流程

1. **首次访问**: 检查localStorage中的token
2. **已登录**: 自动获取用户信息，进入应用
3. **未登录/Token过期**: 重定向到登录页
4. **Token刷新**: 在token过期前自动刷新

## 密码策略

- 最少8个字符
- 至少包含一个大写字母
- 至少包含一个小写字母
- 至少包含一个数字

## 安全特性

- ✅ JWT双Token机制（访问令牌 + 刷新令牌）
- ✅ bcrypt密码哈希（自动截断72字符）
- ✅ Token自动刷新
- ✅ 登录失败次数限制
- ✅ 账户锁定机制
- ✅ 密码修改记录

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | Admin@123456 | 超级管理员 |
| demo | Demo@123456 | 演示用户 |

**注意**: 生产环境请立即修改默认密码！
