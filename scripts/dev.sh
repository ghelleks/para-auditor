#!/usr/bin/env bash
#
# Development helper script for PARA Auditor
#
# Common development tasks using uv
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

usage() {
    echo "Usage: $0 <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  setup          Initial development setup"
    echo "  install        Install dependencies"
    echo "  run [args...]  Run para-auditor with arguments"
    echo "  test           Run tests"
    echo "  lint           Run linting"
    echo "  format         Format code"
    echo "  check          Run all checks"
    echo "  clean          Clean build artifacts"
    echo "  shell          Open a shell in the uv environment"
    echo ""
    echo "Examples:"
    echo "  $0 setup"
    echo "  $0 run --help"
    echo "  $0 run --audit"
    echo "  $0 test"
}

case "${1:-}" in
    setup)
        echo "Setting up development environment..."
        uv sync --extra dev
        if command -v pre-commit >/dev/null 2>&1; then
            uv run pre-commit install
        fi
        echo "Development environment ready!"
        ;;
    install)
        uv sync
        ;;
    run)
        shift
        uv run python -m src.main "$@"
        ;;
    test)
        uv run pytest
        ;;
    lint)
        uv run ruff check src tests
        uv run mypy src
        ;;
    format)
        uv run black src tests
        uv run ruff format src tests
        uv run ruff check --fix src tests
        ;;
    check)
        echo "Running all checks..."
        uv run ruff check src tests
        uv run mypy src
        uv run pytest
        echo "All checks passed!"
        ;;
    clean)
        rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        echo "Cleaned build artifacts"
        ;;
    shell)
        uv run bash
        ;;
    help|--help|-h)
        usage
        ;;
    "")
        echo "Error: No command specified"
        echo ""
        usage
        exit 1
        ;;
    *)
        echo "Error: Unknown command '$1'"
        echo ""
        usage
        exit 1
        ;;
esac