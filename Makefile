.PHONY: help install dev-install run clean test lint format check pre-commit

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the project dependencies
	uv sync

dev-install: ## Install the project with development dependencies
	uv sync --extra dev

run: ## Run the application (use ARGS="--help" for options)
	uv run python -m src.main $(ARGS)

test: ## Run tests with pytest
	uv run pytest

lint: ## Run linting checks
	uv run ruff check src tests
	uv run mypy src

format: ## Format code with black and ruff
	uv run black src tests
	uv run ruff format src tests
	uv run ruff check --fix src tests

check: ## Run all checks (lint + test)
	$(MAKE) lint
	$(MAKE) test

pre-commit: ## Run pre-commit hooks
	uv run pre-commit run --all-files

clean: ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Setup commands for new environment
setup: ## Initial setup for development
	uv sync --extra dev
	uv run pre-commit install

# Build and publish commands
build: ## Build the package
	uv build

publish-test: ## Publish to test PyPI
	uv publish --publish-url https://test.pypi.org/legacy/

publish: ## Publish to PyPI
	uv publish

# Environment management
lock: ## Update the lock file
	uv lock

sync: ## Sync dependencies from lock file
	uv sync

outdated: ## Show outdated dependencies
	uv tree --outdated

# Development shortcuts
audit: ## Run a full audit (shortcut for run with --audit)
	uv run python -m src.main --audit

setup-config: ## Run setup to configure API tokens
	uv run python -m src.main --setup