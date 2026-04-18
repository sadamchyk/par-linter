PAR_BIN     := par
PAR_SRC     := $(shell find par -type f -name '*.py')
PAR_VERSION ?= $(shell git describe --tags --always --dirty='-dev' 2>/dev/null || echo 'dev')

COVER_DIR     = .cover
COVER_PROFILE = $(COVER_DIR)/coverage.xml

PYTHON ?= python3
VENV   := .venv
PIP    := $(VENV)/bin/pip
VENV_PYTHON := $(VENV)/bin/python

DOCKER_IMAGE ?= par
DOCKER_TAG   ?= $(PAR_VERSION)

# ── venv ─────────────────────────────────────────────────────────────────────

$(VENV)/bin/activate:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

.PHONY: venv
venv: $(VENV)/bin/activate

# ── install ──────────────────────────────────────────────────────────────────

.PHONY: install
install: venv
	$(PIP) install -e .

.PHONY: install-dev
install-dev: venv
	$(PIP) install -e '.[dev]'

# ── quality ──────────────────────────────────────────────────────────────────

.PHONY: lint
lint: install-dev
	$(VENV_PYTHON) -m ruff check par tests

.PHONY: format
format: install-dev
	$(VENV_PYTHON) -m ruff format par tests

# ── test & coverage ─────────────────────────────────────────────────────────

.PHONY: test
test: install-dev
	$(VENV_PYTHON) -m pytest tests/ -v

.PHONY: cover
cover: install-dev
	mkdir -p $(COVER_DIR)
	$(VENV_PYTHON) -m pytest tests/ \
		--cov=par \
		--cov-branch \
		--cov-report=term-missing \
		--cov-report=xml:$(COVER_PROFILE)

.PHONY: coverhtml
coverhtml: install-dev
	mkdir -p $(COVER_DIR)
	$(VENV_PYTHON) -m pytest tests/ \
		--cov=par \
		--cov-branch \
		--cov-report=html:$(COVER_DIR)/html
	open $(COVER_DIR)/html/index.html

# ── build & dist ─────────────────────────────────────────────────────────────

.PHONY: build
build: $(PAR_SRC) pyproject.toml venv
	$(VENV_PYTHON) -m build

# ── docker ───────────────────────────────────────────────────────────────────

.PHONY: docker-build
docker-build:
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) -t $(DOCKER_IMAGE):latest .

.PHONY: docker-run
docker-run:
	docker run --rm -v "$$(pwd)/examples:/rules" $(DOCKER_IMAGE):latest lint /rules --format table

.PHONY: docker-sarif
docker-sarif:
	docker run --rm -v "$$(pwd)/examples:/rules" $(DOCKER_IMAGE):latest lint /rules --format sarif

# ── example ──────────────────────────────────────────────────────────────────

.PHONY: example
example: install
	$(VENV)/bin/par lint examples/ --format table --force-color; true

.PHONY: example-json
example-json: install
	$(VENV)/bin/par lint examples/ --format json

.PHONY: example-summary
example-summary: install
	$(VENV)/bin/par summary examples/ --format table --force-color; true

.PHONY: example-sarif
example-sarif: install
	$(VENV)/bin/par lint examples/ --format sarif

# ── clean ────────────────────────────────────────────────────────────────────

.PHONY: clean
clean:
	rm -rf dist/ build/ $(COVER_DIR)/ .pytest_cache/ .ruff_cache/
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

.PHONY: clean-all
clean-all: clean
	rm -rf $(VENV)/

# ── all ──────────────────────────────────────────────────────────────────────

.PHONY: all
all: install test example
