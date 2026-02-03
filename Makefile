.PHONY: all install install-dev format lint test coverage clean help

# Default Python version
PYTHON ?= python3

# Package name
PACKAGE = weather_events

# Source directories
SRC_DIR = src
TEST_DIR = tests

all: format lint test

## Installation targets
install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

## Code quality targets
format:
	@echo "==> Formatting code with black and ruff..."
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m ruff check --fix $(SRC_DIR) $(TEST_DIR)

lint:
	@echo "==> Running linters..."
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m black --check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m mypy $(SRC_DIR)

## Testing targets
test:
	@echo "==> Running tests..."
	$(PYTHON) -m pytest $(TEST_DIR) -v

test-fast:
	@echo "==> Running tests (fast, no coverage)..."
	$(PYTHON) -m pytest $(TEST_DIR) -v --no-cov -x

coverage:
	@echo "==> Running tests with coverage..."
	$(PYTHON) -m pytest $(TEST_DIR) \
		--cov=$(SRC_DIR)/$(PACKAGE) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80
	@echo "==> Coverage report generated in htmlcov/index.html"

coverage-report:
	@echo "==> Generating coverage report..."
	$(PYTHON) -m coverage report --show-missing
	$(PYTHON) -m coverage html
	@echo "==> Open htmlcov/index.html to view the report"

## Utility targets
clean:
	@echo "==> Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf $(SRC_DIR)/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

typecheck:
	@echo "==> Running type checker..."
	$(PYTHON) -m mypy $(SRC_DIR)

## Development targets
dev: install-dev
	@echo "==> Development environment ready"

check: format lint typecheck test
	@echo "==> All checks passed"

## Help target
help:
	@echo "Weather Event Recommendations - Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install      Install package"
	@echo "  make install-dev  Install package with dev dependencies"
	@echo "  make dev          Set up development environment"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format       Format code with black and ruff"
	@echo "  make lint         Run linters (ruff, black --check, mypy)"
	@echo "  make typecheck    Run mypy type checker"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run tests"
	@echo "  make test-fast    Run tests without coverage, stop on first failure"
	@echo "  make coverage     Run tests with coverage (requires 80%)"
	@echo ""
	@echo "Other:"
	@echo "  make clean        Remove build artifacts"
	@echo "  make check        Run all checks (format, lint, typecheck, test)"
	@echo "  make help         Show this help message"
