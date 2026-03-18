.PHONY: setup install install-dev env check clean docker-build docker-up docker-down help

PYTHON ?= python
CONDA_ENV ?= graphrag-delete
CACHE_DIR ?= cache

# ============================================================
# 帮助信息
# ============================================================
help:  ## 显示所有可用命令
	@echo ""
	@echo "nano-graphrag 删除流程 - 部署和管理命令"
	@echo "=========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================================
# 环境配置（Anaconda）
# ============================================================
setup: conda-create env  ## 一键环境配置（conda 环境 + 依赖 + .env）
	@echo ""
	@echo "[OK] 环境配置完成！"
	@echo "     激活环境: conda activate $(CONDA_ENV)"
	@echo "     编辑 API 配置: vi .env"

conda-create:  ## 创建 conda 环境并安装所有依赖
	conda env create -f environment.yml || conda env update -f environment.yml
	@echo "[OK] conda 环境 '$(CONDA_ENV)' 已就绪"

conda-update:  ## 更新 conda 环境（依赖变更后执行）
	conda env update -f environment.yml --prune

install:  ## 在当前环境中用 pip 安装依赖（不创建 conda 环境）
	pip install -r requirements.txt

install-dev: install  ## 安装生产 + 开发依赖
	pip install -r requirements-dev.txt

env:  ## 从 .env.example 创建 .env 文件（如不存在）
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "[INFO] 已创建 .env 文件，请编辑填入 API 密钥"; \
	else \
		echo "[INFO] .env 文件已存在，跳过"; \
	fi

# ============================================================
# 检查
# ============================================================
check:  ## 检查运行环境是否就绪
	@echo "=== 环境检查 ==="
	@echo -n "Python 版本: " && $(PYTHON) --version
	@echo -n "conda 环境:  " && (conda info --envs 2>/dev/null | grep '\*' || echo "未检测到 conda")
	@echo ""
	@echo "--- 核心依赖 ---"
	@$(PYTHON) -c "import openai; print(f'openai:       {openai.__version__}')" 2>/dev/null || echo "openai:       [未安装]"
	@$(PYTHON) -c "import tiktoken; print(f'tiktoken:     OK')" 2>/dev/null || echo "tiktoken:     [未安装]"
	@$(PYTHON) -c "import networkx; print(f'networkx:     {networkx.__version__}')" 2>/dev/null || echo "networkx:     [未安装]"
	@$(PYTHON) -c "import numpy; print(f'numpy:        {numpy.__version__}')" 2>/dev/null || echo "numpy:        [未安装]"
	@$(PYTHON) -c "import graspologic; print(f'graspologic:  OK')" 2>/dev/null || echo "graspologic:  [未安装]"
	@$(PYTHON) -c "import nano_vectordb; print(f'nano_vectordb:OK')" 2>/dev/null || echo "nano_vectordb:[未安装]"
	@$(PYTHON) -c "import hnswlib; print(f'hnswlib:      OK')" 2>/dev/null || echo "hnswlib:      [未安装]"
	@$(PYTHON) -c "import tenacity; print(f'tenacity:     OK')" 2>/dev/null || echo "tenacity:     [未安装]"
	@echo ""
	@echo "--- 配置文件 ---"
	@test -f .env && echo ".env:         OK" || echo ".env:         [缺失] 请运行 make env"
	@echo ""
	@echo "--- 数据目录 ---"
	@test -d $(CACHE_DIR) && echo "cache/:       OK ($(shell ls $(CACHE_DIR)/*.graphml 2>/dev/null | wc -l) graphml 文件)" || echo "cache/:       [缺失]"
	@echo ""
	@echo "--- API 连接 ---"
	@if [ -f .env ]; then \
		. ./.env 2>/dev/null; \
		if [ -n "$$OPENAI_API_KEY" ] && [ "$$OPENAI_API_KEY" != "your-api-key-here" ]; then \
			echo "OPENAI_API_KEY: 已配置"; \
		else \
			echo "OPENAI_API_KEY: [未配置] 请编辑 .env 文件"; \
		fi; \
	else \
		echo "OPENAI_API_KEY: [未配置] 请先运行 make env"; \
	fi
	@echo "================"

# ============================================================
# 删除操作
# ============================================================
delete:  ## 交互式删除实体 (用法: make delete ENTITY=名称)
ifndef ENTITY
	@echo "用法: make delete ENTITY=实体名"
	@echo "示例: make delete ENTITY=Benjamin"
	@exit 1
endif
	$(PYTHON) "delete all.py" $(ENTITY)

delete-force:  ## 强制删除实体，跳过确认 (用法: make delete-force ENTITY=名称)
ifndef ENTITY
	@echo "用法: make delete-force ENTITY=实体名"
	@exit 1
endif
	$(PYTHON) "delete all.py" $(ENTITY) --yes

# ============================================================
# Docker
# ============================================================
docker-build:  ## 构建 Docker 镜像
	docker build -t nano-graphrag-delete .

docker-up:  ## 启动 Docker 容器
	docker compose up -d

docker-down:  ## 停止 Docker 容器
	docker compose down

# ============================================================
# 清理
# ============================================================
clean:  ## 清理临时文件和 Python 缓存
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -f one_hop_nodes.txt two_hop_nodes.txt three_hop_nodes.txt
	rm -f deleted_clusters_cache.json cluster_change_flags.json
	rm -f graph_chunk_entity_relation2.graphml graph_chunk_entity_relation3.graphml
	rm -f kv_store_community_reports3.json
	@echo "[OK] 临时文件已清理"

clean-all: clean  ## 清理所有（含 conda 环境和备份）
	conda env remove -n $(CONDA_ENV) -y 2>/dev/null || true
	rm -rf $(CACHE_DIR)/.deletion_backups
	@echo "[OK] 全部清理完成"
