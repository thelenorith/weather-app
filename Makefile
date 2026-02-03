.PHONY: install install-dev uninstall clean format lint typecheck test test-verbose coverage default help

# Default Python
PYTHON := python

# Package name
PACKAGE = weather_events

# Source directories
SRC_DIR = src
TEST_DIR = tests

# Default target runs all quality checks
default: format lint coverage test typecheck

## Installation targets
install:
	$(PYTHON) -m pip install -e .

install-dev:
	$(PYTHON) -m pip install -e ".[dev]"

uninstall:
	$(PYTHON) -m pip uninstall -y weather-event-recommendations || true

## Code quality targets
format: install-dev
	@echo "==> Formatting code with black..."
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m ruff check --fix $(SRC_DIR) $(TEST_DIR) || true

lint: install-dev
	@echo "==> Running linters..."
	$(PYTHON) -m flake8 $(SRC_DIR) $(TEST_DIR) --max-line-length=88 --ignore=E203,W503
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m black --check $(SRC_DIR) $(TEST_DIR)

typecheck: install-dev
	@echo "==> Running type checker..."
	$(PYTHON) -m mypy $(SRC_DIR)

## Testing targets
test: install-dev
	@echo "==> Running tests..."
	$(PYTHON) -m pytest $(TEST_DIR) -v

test-verbose: install-dev
	@echo "==> Running tests with verbose output..."
	$(PYTHON) -m pytest $(TEST_DIR) -v --tb=long

coverage: install-dev
	@echo "==> Running tests with coverage..."
	$(PYTHON) -m pytest $(TEST_DIR) \
		--cov=$(SRC_DIR)/$(PACKAGE) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		--cov-fail-under=80
	@echo "==> Coverage report generated in htmlcov/index.html"

## Utility targets
clean:
	@echo "==> Cleaning build artifacts..."
	rm -rf build/ || true
	rm -rf dist/ || true
	rm -rf *.egg-info/ || true
	rm -rf $(SRC_DIR)/*.egg-info/ || true
	rm -rf .pytest_cache/ || true
	rm -rf .mypy_cache/ || true
	rm -rf .ruff_cache/ || true
	rm -rf htmlcov/ || true
	rm -rf .coverage || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

## Help target
help:
	@echo "Weather Event Recommendations - Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install      Install package"
	@echo "  make install-dev  Install package with dev dependencies"
	@echo "  make uninstall    Uninstall package"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format       Format code with black and ruff"
	@echo "  make lint         Run linters (flake8, ruff, black --check)"
	@echo "  make typecheck    Run mypy type checker"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run tests"
	@echo "  make test-verbose Run tests with verbose output"
	@echo "  make coverage     Run tests with coverage (requires 80%)"
	@echo ""
	@echo "Other:"
	@echo "  make default      Run all checks (format, lint, typecheck, test, coverage)"
	@echo "  make clean        Remove build artifacts"
	@echo "  make help         Show this help message"
