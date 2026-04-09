# 🛠️ 量化交易系统 Makefile

# 颜色定义
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

# 项目变量
PROJECT_NAME := quant-trading-system
PYTHON := python3.11
PIP := pip3.11
DOCKER_COMPOSE := docker-compose -f docker-compose.yml
K8S_NAMESPACE := quant-trading
REGISTRY := registry.your-org.com

.PHONY: help setup install format lint test build clean

# 显示帮助信息
help:
	@echo "$(GREEN)量化交易系统构建工具$(NC)"
	@echo ""
	@echo "可用命令:"
	@echo "  $(YELLOW)开发环境$(NC)"
	@echo "    make setup          - 安装系统依赖和工具"
	@echo "    make install        - 安装Python依赖"
	@echo "    make dev-up         - 启动开发环境"
	@echo "    make dev-down       - 停止开发环境"
	@echo ""
	@echo "  $(YELLOW)代码质量$(NC)"
	@echo "    make format         - 格式化代码"
	@echo "    make lint           - 代码检查"
	@echo "    make type-check     - 类型检查"
	@echo "    make test           - 运行测试"
	@echo "    make coverage       - 生成测试覆盖率报告"
	@echo ""
	@echo "  $(YELLOW)安全扫描$(NC)"
	@echo "    make security-scan  - 安全扫描"
	@echo "    make dependency-scan - 依赖扫描"
	@echo "    make secret-scan    - 密钥扫描"
	@echo ""
	@echo "  $(YELLOW)构建部署$(NC)"
	@echo "    make docker-build   - 构建Docker镜像"
	@echo "    make docker-push    - 推送镜像到仓库"
	@echo "    make k8s-deploy     - 部署到Kubernetes"
	@echo "    make k8s-undeploy   - 从Kubernetes卸载"
	@echo ""
	@echo "  $(YELLOW)运维管理$(NC)"
	@echo "    make status         - 查看服务状态"
	@echo "    make logs           - 查看日志"
	@echo "    make backup         - 备份数据"
	@echo "    make restore        - 恢复数据"
	@echo "    make health-check   - 健康检查"

# 开发环境
setup:
	@echo "$(GREEN)安装系统依赖...$(NC)"
	# Python 3.11
	sudo apt-get update
	sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
	# Docker
	sudo apt-get install -y docker.io docker-compose
	# 工具
	sudo apt-get install -y git curl wget make
	@echo "$(GREEN)安装完成$(NC)"

install:
	@echo "$(GREEN)安装Python依赖...$(NC)"
	$(PYTHON) -m venv venv
	. venv/bin/activate && $(PIP) install --upgrade pip
	. venv/bin/activate && $(PIP) install -r requirements.txt
	. venv/bin/activate && $(PIP) install -r requirements-dev.txt
	@echo "$(GREEN)依赖安装完成$(NC)"

dev-up:
	@echo "$(GREEN)启动开发环境...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)开发环境已启动$(NC)"
	@echo "访问以下服务:"
	@echo "  - 前端: http://localhost:3000"
	@echo "  - API: http://localhost:8000"
	@echo "  - API文档: http://localhost:8000/docs"
	@echo "  - 监控: http://localhost:3001"
	@echo "  - 数据库管理: http://localhost:8080"

dev-down:
	@echo "$(GREEN)停止开发环境...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)开发环境已停止$(NC)"

# 代码质量
format:
	@echo "$(GREEN)格式化代码...$(NC)"
	. venv/bin/activate && black src tests
	. venv/bin/activate && isort src tests
	@echo "$(GREEN)代码格式化完成$(NC)"

lint:
	@echo "$(GREEN)代码检查...$(NC)"
	. venv/bin/activate && flake8 src tests
	. venv/bin/activate && pylint src
	@echo "$(GREEN)代码检查完成$(NC)"

type-check:
	@echo "$(GREEN)类型检查...$(NC)"
	. venv/bin/activate && mypy src
	@echo "$(GREEN)类型检查完成$(NC)"

test:
	@echo "$(GREEN)运行测试...$(NC)"
	. venv/bin/activate && pytest tests/unit -v
	@echo "$(GREEN)测试完成$(NC)"

coverage:
	@echo "$(GREEN)生成测试覆盖率报告...$(NC)"
	. venv/bin/activate && pytest tests/unit --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)覆盖率报告生成完成$(NC)"
	@echo "查看报告: file://$(PWD)/htmlcov/index.html"

# 安全扫描
security-scan:
	@echo "$(GREEN)运行安全扫描...$(NC)"
	. venv/bin/activate && bandit -r src
	. venv/bin/activate && safety check
	@echo "$(GREEN)安全扫描完成$(NC)"

dependency-scan:
	@echo "$(GREEN)扫描依赖漏洞...$(NC)"
	. venv/bin/activate && pip-audit
	@echo "$(GREEN)依赖扫描完成$(NC)"

secret-scan:
	@echo "$(GREEN)扫描密钥泄露...$(NC)"
	detect-secrets scan src
	@echo "$(GREEN)密钥扫描完成$(NC)"

# 构建部署
docker-build:
	@echo "$(GREEN)构建Docker镜像...$(NC)"
	docker build -t $(PROJECT_NAME)-api:latest -f docker/api.Dockerfile .
	docker build -t $(PROJECT_NAME)-web:latest -f docker/web.Dockerfile .
	docker build -t $(PROJECT_NAME)-worker:latest -f docker/worker.Dockerfile .
	@echo "$(GREEN)Docker镜像构建完成$(NC)"

docker-push:
	@echo "$(GREEN)推送Docker镜像...$(NC)"
	docker tag $(PROJECT_NAME)-api:latest $(REGISTRY)/$(PROJECT_NAME)-api:latest
	docker tag $(PROJECT_NAME)-web:latest $(REGISTRY)/$(PROJECT_NAME)-web:latest
	docker tag $(PROJECT_NAME)-worker:latest $(REGISTRY)/$(PROJECT_NAME)-worker:latest
	docker push $(REGISTRY)/$(PROJECT_NAME)-api:latest
	docker push $(REGISTRY)/$(PROJECT_NAME)-web:latest
	docker push $(REGISTRY)/$(PROJECT_NAME)-worker:latest
	@echo "$(GREEN)Docker镜像推送完成$(NC)"

k8s-deploy:
	@echo "$(GREEN)部署到Kubernetes...$(NC)"
	kubectl create namespace $(K8S_NAMESPACE) || true
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configs.yaml
	kubectl apply -f k8s/secrets.yaml
	kubectl apply -f k8s/databases.yaml
	kubectl apply -f k8s/services.yaml
	kubectl apply -f k8s/deployments.yaml
	kubectl apply -f k8s/ingress.yaml
	@echo "$(GREEN)Kubernetes部署完成$(NC)"

k8s-undeploy:
	@echo "$(GREEN)从Kubernetes卸载...$(NC)"
	kubectl delete -f k8s/ingress.yaml || true
	kubectl delete -f k8s/deployments.yaml || true
	kubectl delete -f k8s/services.yaml || true
	kubectl delete -f k8s/databases.yaml || true
	kubectl delete -f k8s/secrets.yaml || true
	kubectl delete -f k8s/configs.yaml || true
	kubectl delete namespace $(K8S_NAMESPACE) || true
	@echo "$(GREEN)Kubernetes卸载完成$(NC)"

# 运维管理
status:
	@echo "$(GREEN)服务状态:$(NC)"
	$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "$(GREEN)数据库连接:$(NC)"
	. venv/bin/activate && python scripts/check_db.py
	@echo ""
	@echo "$(GREEN)API健康检查:$(NC)"
	curl -f http://localhost:8000/health || echo "$(RED)API不可用$(NC)"

logs:
	@echo "$(GREEN)查看服务日志...$(NC)"
	$(DOCKER_COMPOSE) logs -f --tail=100

backup:
	@echo "$(GREEN)备份数据...$(NC)"
	./scripts/backup.sh
	@echo "$(GREEN)数据备份完成$(NC)"

restore:
	@echo "$(RED)恢复数据...$(NC)"
	@read -p "确认要恢复数据吗？这将覆盖现有数据 [y/N]: " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		./scripts/restore.sh; \
		echo "$(GREEN)数据恢复完成$(NC)"; \
	else \
		echo "$(YELLOW)取消恢复操作$(NC)"; \
	fi

health-check:
	@echo "$(GREEN)运行健康检查...$(NC)"
	. venv/bin/activate && python scripts/health_check.py
	@echo "$(GREEN)健康检查完成$(NC)"

# 数据库管理
db-init:
	@echo "$(GREEN)初始化数据库...$(NC)"
	. venv/bin/activate && python scripts/init_db.py
	@echo "$(GREEN)数据库初始化完成$(NC)"

db-migrate:
	@echo "$(GREEN)执行数据库迁移...$(NC)"
	. venv/bin/activate && alembic upgrade head
	@echo "$(GREEN)数据库迁移完成$(NC)"

# 清理
clean:
	@echo "$(GREEN)清理构建文件...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/ dist/ *.egg-info htmlcov/ .coverage
	@echo "$(GREEN)清理完成$(NC)"