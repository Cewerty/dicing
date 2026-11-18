PROJECT_NAME = dicing
SRC_DIR = src
TESTS_DIR = tests

.PHONY: all install-hooks lint format typecheck typecheck-fast test build smoke release-check clean ci

all: install-hooks lint format typecheck test build

install-hooks:
	@echo "Установка pre-commit хуков (pre-commit и commit-msg)..."
	pre-commit install

lint:
	@echo "🔍 Запуск линтинга..."
	ruff check $(SRC_DIR) $(TESTS_DIR)

format:
	@echo "🎨 Форматирование кода..."
	ruff format $(SRC_DIR) $(TESTS_DIR)

typecheck:
	@echo "🧪 Проверка типов (mypy, строгий gate для CI)..."
	mypy $(SRC_DIR)
	PYTHONPATH=$(SRC_DIR) mypy $(TESTS_DIR)

typecheck-fast:
	@echo "⚡ Быстрая проверка типов (ty)..."
	ty check

test:
	@echo "🚀 Запуск тестов..."
	pytest -v --cov=$(SRC_DIR) --cov-report=term-missing

build:
	@echo "📦 Сборка пакета..."
	uv build --no-build-isolation

smoke: build
	@echo "💨 Smoke-тест CLI на собранном wheel..."
	bash scripts/cli_smoke_test.sh

release-check:
	@echo "🏷️  Проверка истории релизов и следующей версии..."
	python scripts/ci/validate_release_history.py
	uvx --from python-semantic-release==10.7.0 semantic-release --noop version --print

clean:
	@echo "🧹 Очистка артефактов..."
	rm -rf build dist .mypy_cache .pytest_cache .coverage coverage.xml .ruff_cache .hypothesis

ci: lint typecheck typecheck-fast test smoke
