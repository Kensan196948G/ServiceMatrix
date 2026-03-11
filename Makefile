# ServiceMatrix Development Makefile

.PHONY: help setup seed dev dev-backend dev-frontend test lint format clean

PYTHON := python3
PIP := pip
DOCKER_COMPOSE := docker compose

## help: このヘルプを表示
help:
	@echo "ServiceMatrix - Available Commands"
	@echo "======================================"
	@grep -E '^## [a-z]' Makefile | sed 's/## /  make /'

## setup: 開発環境を全自動セットアップ（5分以内）
setup:
	@echo "🚀 ServiceMatrix 開発環境セットアップ開始..."
	@$(PIP) install -e ".[dev]" -q
	@$(DOCKER_COMPOSE) up -d postgres redis
	@echo "⏳ DB起動待機中..."
	@for i in $$(seq 1 30); do \
		$(DOCKER_COMPOSE) exec -T postgres pg_isready -U servicematrix && break; \
		sleep 2; \
	done
	@$(PYTHON) -m alembic upgrade head
	@$(MAKE) seed
	@echo "✅ セットアップ完了！ make dev でサーバー起動"

## seed: サンプルデータを投入
seed:
	@echo "🌱 サンプルデータ投入中..."
	@$(PYTHON) scripts/seed_data.py || true
	@echo "✅ サンプルデータ投入完了"

## dev: バックエンド + フロントエンド を起動
dev:
	@$(MAKE) -j2 dev-backend dev-frontend

## dev-backend: バックエンドのみ起動
dev-backend:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

## dev-frontend: フロントエンドのみ起動
dev-frontend:
	cd frontend && npm run dev

## test: テストを実行
test:
	pytest tests/ --asyncio-mode=auto --tb=short -v

## lint: Lint チェック
lint:
	ruff check src/ tests/
	cd frontend && npm run lint || true

## format: コードフォーマット
format:
	ruff format src/ tests/
	cd frontend && npm run format || true

## clean: 開発環境をクリーンアップ
clean:
	@$(DOCKER_COMPOSE) down -v
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ クリーンアップ完了"

## docker-up: Docker サービスを起動（DB + Redis）
docker-up:
	$(DOCKER_COMPOSE) up -d postgres redis

## docker-down: Docker サービスを停止
docker-down:
	$(DOCKER_COMPOSE) down

## migrate: DB マイグレーション実行
migrate:
	$(PYTHON) -m alembic upgrade head

## migration: 新規マイグレーション作成（例: make migration name=add_foo）
migration:
	$(PYTHON) -m alembic revision --autogenerate -m "$(name)"
