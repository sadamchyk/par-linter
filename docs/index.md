---
layout: default
title: Documentation
nav_order: 1
has_children: true
---

# Prometheus Alert Rule Linter (par)

par is a static analyzer for Prometheus alerting rule files.

## What it does

par reads one or more Prometheus rule YAML files and reports quality issues that make
alerts noisy, unreliable, or hard to act on during an incident.

It is designed as a **rule-quality analyzer**, not a syntax checker. It complements
[promtool](https://prometheus.io/docs/prometheus/latest/command-line/promtool/) by focusing
on the operational problems that matter in production:

- alerts that fire too aggressively or on transient conditions
- missing metadata that leaves the on-call engineer without context
- selectors that are too broad or too narrow
- PromQL patterns that are technically valid but operationally risky
- broken references between alerting rules and recording rules

## Goals

- Reduce alert noise before rules are merged
- Make alerts more actionable during incidents
- Give reviewers a CI-friendly quality gate
- Support team-specific policy via configuration

## Non-goals

- Replacing `promtool test rules`
- Replacing Alertmanager routing validation
- Automatically rewriting PromQL
- Simulating full production query cost in large clusters

## Requirements

par runs all checks offline by reading only the rule files you provide. It does not
connect to a Prometheus server and does not require any running infrastructure.

Python 3.9 or later is required. The only external dependency is `pyyaml`.

## Installation

```shell
git clone https://github.com/sadamchyk/par-linter.git
cd par-linter
make install
```

## Development

A `Makefile` is provided for common development tasks. Override `PYTHON` to use a
specific interpreter.

| Target | Description |
|--------|-------------|
| `make install` | Install package in editable mode |
| `make install-dev` | Install package plus dev tools (pytest, ruff) |
| `make test` | Run the test suite |
| `make cover` | Run tests with branch coverage report (XML) |
| `make coverhtml` | Run tests with HTML coverage report, opens in browser |
| `make lint` | Run ruff linter |
| `make format` | Run ruff formatter |
| `make build` | Build distribution wheel and sdist |
| `make example` | Run par against `examples/` in table mode |
| `make clean` | Remove build artefacts, coverage output, and caches |

```shell
# quick start for contributors
make install-dev
make test
make example
```

Use `PYTHON=python3.12 make test` to run against a specific interpreter.

## Usage

Lint one or more rule files:

```shell
par rules.yaml
par rules/*.yaml
par rules/api.yaml rules/infra.yaml
```

### Output formats

| Format | Description |
|--------|-------------|
| `text` | Human-readable grouped output (default) |
| `json` | Machine-readable findings for CI pipelines |
| `table` | Bordered table for quick review |
| `sarif` | SARIF v2.1.0 for GitHub Actions code scanning |

### Options

| Flag | Description |
|------|-------------|
| `--format text` | Human-readable output (default) |
| `--format table` | Compact table output |
| `--format json` | Machine-readable JSON, useful for CI pipelines |
| `--format sarif` | SARIF v2.1.0 output for code scanning integration |
| `--min-severity error\|warning\|info` | Only report findings at or above this level (default: `info`) |
| `--config FILE` | Path to config file (default: `.par.yaml` in current directory) |
| `--label KEY=VALUE` | Filter to alerts matching this label; repeatable |
| `--no-color` | Disable ANSI color output |
| `--force-color` | Force color output even when stdout is not a TTY |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | No findings at or above `--min-severity` |
| `1` | Warnings found, no errors |
| `2` | Errors found |
| `3` | Input, parse, or config error |

Exit codes `1` and `2` are distinct so CI pipelines can choose to block only on errors
while still reporting warnings.

### Examples

```shell
# Lint all rules, show everything
par rules/*.yaml

# Block CI on errors, show warnings too
par rules/*.yaml --min-severity warning
echo "exit code: $?"

# JSON output for downstream processing
par rules/*.yaml --format json | jq '.findings[] | select(.severity == "error")'

# Compact table for quick review
par rules/*.yaml --format table --min-severity warning
```

## Inline suppression

To suppress a specific check for one rule, add a comment on the line immediately above
the rule definition:

```yaml
# par disable broad-selector
- alert: GlobalScrapeFailure
  expr: up == 0
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: A scrape target is unreachable
```

Multiple rule IDs can be suppressed in one comment:

```yaml
# par disable broad-selector, for-duration
- alert: ...
```

Suppression comments apply only to the single rule directly below them.
They do not affect other rules in the file.

## Configuration file

Create `.par.yaml` in your repository root to customise which checks run and what
they require. See [Configuration](configuration.md) for a full reference.

A minimal configuration that sets a severity threshold and requires a `team` label:

```yaml
severity_threshold: warning

required_labels:
  - severity
  - team

required_annotations:
  - summary
  - description
  - runbook_url
```

## CI usage

Run par as a quality gate in any CI system that checks Prometheus rule files.

### GitHub Actions

```yaml
- name: Lint alerting rules
  run: par rules/*.yaml --format json --min-severity warning
```

To annotate pull requests with findings, pipe the JSON output to a formatter or use
`--format github` in a future release.

### GitHub Actions with SARIF

```yaml
name: par-lint
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install .
      - run: par rules/ --format sarif > par.sarif
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: par.sarif
```

### Docker

```shell
make docker-build
docker run --rm -v "$(pwd)/rules:/rules" par /rules
docker run --rm -v "$(pwd)/rules:/rules" par /rules --format sarif > par.sarif
```

### Pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: par
        name: par
        entry: par
        args: [--min-severity, warning]
        language: python
        files: \.ya?ml$
```

## Architecture

### 1. Parser layer

- Load YAML files
- Normalize rule groups and rules
- Preserve file and line positions

### 2. PromQL analysis layer

- Parse `expr`
- Walk the AST
- Extract selectors, binary operators, functions, and aggregations

### 3. Rule graph layer

- Collect alert names
- Collect recording-rule names
- Map dependencies across files

### 4. Policy engine

- Run offline checks
- Optionally run live checks against the Prometheus HTTP API

### 5. Reporter

- Text, JSON, table, and SARIF output
- Deterministic rule IDs
- CI-friendly summaries

## Checks

See [Checks](checks.md) for the full catalog. Each check has its own page with examples
and configuration options.

## Future enhancements

- Richer rule explanations with AST-aware suggestions
- Optional integration with `promtool test rules`
- Per-directory policy packs
- Query cost estimation in live mode
- Dashboards and runbook URL reachability checks
- Suggested remediations for common PromQL mistakes

## Release notes

See [CHANGELOG](https://github.com/sadamchyk/par-linter/releases) for history of changes.
