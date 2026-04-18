PAR_BIN     := par
PAR_SRC     := $(shell find par -type f -name '*.py')
PAR_VERSION ?= $(shell git describe --tags --always --dirty='-dev' 2>/dev/null || echo 'dev')

COVER_DIR     = .cover
COVER_PROFILE = $(COVER_DIR)/coverage.xml

PYTHON ?= python3
PIP    := $(PYTHON) -m pip

# ── install ────────────────────────────────────────────────────────────────────

.PHONY: install
install:
	$(PIP) install -e .

.PHONY: install-dev
install-dev:
	$(PIP) install -e . pytest pytest-cov ruff

# ── quality ────────────────────────────────────────────────────────────────────

.PHONY: lint
lint:
	$(PYTHON) -m ruff check par tests

.PHONY: format
format:
	$(PYTHON) -m ruff format par tests

# ── test & coverage ───────────────────────────────────────────────────────────

.PHONY: test
test:
	$(PYTHON) -m pytest tests/ -v

.PHONY: cover
cover:
	mkdir -p $(COVER_DIR)
	$(PYTHON) -m pytest tests/ \
		--cov=par \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=xml:$(COVER_PROFILE)

.PHONY: coverhtml
coverhtml:
	mkdir -p $(COVER_DIR)
	$(PYTHON) -m pytest tests/ \
		--cov=par \
		--cov-branch \
		--cov-report=html:$(COVER_DIR)/html
	open $(COVER_DIR)/html/index.html

# ── build & dist ──────────────────────────────────────────────────────────────

.PHONY: build
build: $(PAR_SRC) pyproject.toml
	$(PYTHON) -m build

# ── example ───────────────────────────────────────────────────────────────────

.PHONY: example
example:
	$(PAR_BIN) lint examples/ --format table --force-color; true

.PHONY: example-json
example-json:
	$(PAR_BIN) lint examples/ --format json

.PHONY: example-summary
example-summary:
	$(PAR_BIN) summary examples/ --format table --force-color; true

# ── clean ─────────────────────────────────────────────────────────────────────

.PHONY: clean
clean:
	rm -rf dist/ build/ $(COVER_DIR)/ .pytest_cache/ .ruff_cache/
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

# ── all ───────────────────────────────────────────────────────────────────────

.PHONY: all
all: install test example
