# par

A CLI that analyzes Prometheus alerting rule files and flags quality issues that make alerts noisy, flaky, or hard to act on during an incident.

`par` is designed as a **rule-quality analyzer**, not just a syntax checker. It complements `promtool` by focusing on the operational problems that matter in production:

- alerts that fire too aggressively or on transient conditions
- missing metadata that leaves the on-call engineer without context
- selectors that are too broad or too narrow
- broken relationships between alerts and recording rules
- PromQL patterns that are technically valid but operationally risky

## Why this tool exists

Prometheus already provides `promtool` to validate rule files and test alert behavior. That is the right baseline, but it does not go far enough for alert quality policy.

This tool borrows the strongest ideas from existing rule-quality linters such as `pint`:

- offline linting of YAML structure, labels, annotations

## Goals

- reduce alert noise before rules are merged
- make alerts more actionable during incidents
- give reviewers a CI-friendly quality gate
- support team-specific policy via configuration

## Non-goals

- replacing `promtool test rules`
- replacing Alertmanager routing validation
- automatically rewriting PromQL
- simulating full production query cost in large clusters

## Quick start

### Using pip and venv

```bash
make install          # creates .venv/ and installs par
make test             # runs the test suite
.venv/bin/par lint rules/*.yaml
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
par lint rules/*.yaml
```

### Using Docker

```bash
make docker-build
docker run --rm -v "$(pwd)/rules:/rules" par lint /rules
docker run --rm -v "$(pwd)/rules:/rules" par lint /rules --format sarif > par.sarif
```

## Example usage

```bash
par lint rules/*.yaml
par lint rules/*.yaml --format json
par lint rules/*.yaml --format sarif > par.sarif
par lint rules/*.yaml --config .par.yaml
par lint rules/*.yaml --label team=sre
par summary rules/*.yaml
```

## Exit codes

- `0` — no findings
- `1` — warnings only
- `2` — errors found
- `3` — invalid input, parse failure, or config failure

## Output formats

- `text` (default) — human-readable grouped output
- `json` — machine-readable findings
- `table` — bordered table format
- `sarif` — SARIF v2.1.0 for GitHub Actions code scanning

## What it checks

### Stability

These checks focus on alerts that fire too easily or behave unreliably.

- missing `for` duration
- `absent()` used without a safe delay
- dynamic labels that change alert identity
- optional live alert fanout estimation

### Metadata and actionability

These checks enforce the minimum context needed during an incident.

- required labels such as `severity` and `team`
- required annotations such as `summary`, `description`, and `runbook_url`
- optional link validation
- ownership enforcement

### Selector quality

These checks catch rules that are too broad, too narrow, or silently broken.

- missing scoping labels such as `job`, `cluster`, `namespace`, or `service`
- selectors that return no live series
- suspicious regex matchers

### PromQL quality

These checks catch patterns that are valid PromQL but weak alert design.

- alert expressions with no explicit comparison
- counters used as absolute thresholds
- suspicious `rate()` windows
- likely vector matching problems

### Relationships between rules

These checks need a view across multiple files.

- broken recording-rule dependencies
- duplicate alerting or recording rules
- fanout risk across time in live mode

## Check catalog

| Check | Severity | Category | Description |
|---|---|---|---|
| `for-duration` | warning | stability | Alert has no `for` duration |
| `absent-selector` | warning | stability | `absent()` used without label selectors |
| `rate-window` | warning | stability | `rate()`/`irate()` window shorter than 2 minutes |
| `required-labels` | error | metadata | Missing required labels |
| `required-annotations` | error | metadata | Missing required annotations |
| `invalid-owner` | error | metadata | `owner` label not in the configured allowlist |
| `broad-selector` | warning | selector | Selector too broad or missing scoping labels |
| `no-comparison` | warning | promql | Alert expression lacks a comparison operator |
| `counter-threshold` | warning | promql | Counter used as an absolute threshold |
| `non-base-unit` | info | naming | Metric uses a non-base unit suffix |
| `recording-ref` | error | dependency | Recording rule referenced but not defined |
| `duplicate-alert` | error | dependency | Duplicate alert name in the same group |

## Example findings

### 1. Missing `for`

**Bad**

```yaml
- alert: InstanceDown
  expr: up{job="api"} == 0
```

**Finding**

```text
WARN for-duration rules/api.yaml:12 alert=InstanceDown
  Alert has no 'for' duration.
  Why it matters: transient scrape failures can trigger noisy pages.
  Suggestion: add for: 5m
```

**Better**

```yaml
- alert: InstanceDown
  expr: up{job="api"} == 0
  for: 5m
```

### 2. Missing actionability metadata

**Bad**

```yaml
- alert: APIErrorRateHigh
  expr: rate(api_errors_total[5m]) > 10
  labels:
    severity: page
```

**Finding**

```text
ERROR required-annotations rules/api.yaml:24 alert=APIErrorRateHigh
  Alert is missing required annotations: summary, description, runbook_url
  Why it matters: on-call engineers do not have enough context to investigate quickly.
  Suggestion: add annotations with a short summary, operator-facing description, and runbook link.
```

**Better**

```yaml
- alert: APIErrorRateHigh
  expr: rate(api_errors_total[5m]) > 10
  for: 10m
  labels:
    severity: page
    team: api
  annotations:
    summary: API error rate is high
    description: Error rate has exceeded 10 req/s for 10 minutes.
    runbook_url: https://runbooks.example.com/api-errors
```

### 3. Broad selector

**Bad**

```yaml
- alert: TargetDown
  expr: up == 0
  for: 5m
```

**Finding**

```text
WARN broad-selector rules/node.yaml:8 alert=TargetDown
  Selector is too broad: up
  Why it matters: the rule may alert on unrelated services or generate excessive fanout.
  Suggestion: scope the selector with job, cluster, namespace, or service labels.
```

**Better**

```yaml
- alert: TargetDown
  expr: up{job="node-exporter", cluster="prod"} == 0
  for: 5m
```

### 4. Counter used as absolute threshold

**Bad**

```yaml
- alert: TooManyErrors
  expr: errors_total > 10
```

**Finding**

```text
WARN counter-threshold rules/api.yaml:37 alert=TooManyErrors
  Counter used as an absolute threshold: errors_total > 10
  Why it matters: raw counter values depend on process lifetime.
  Suggestion: use rate(errors_total[15m]) > 10
```

**Better**

```yaml
- alert: TooManyErrors
  expr: rate(errors_total[15m]) > 10
  for: 10m
```

### 5. Live selector failure

**Bad**

```yaml
- alert: DBLatencyHigh
  expr: histogram_quantile(0.99, sum by (le) (rate(db_latency_seconds_bucket{service="db-api"}[5m]))) > 1
  for: 10m
```

**Finding**

```text
ERROR broad-selector rules/db.yaml:8 alert=DBLatencyHigh
  Selector returned no live series: db_latency_seconds_bucket{service="db-api"}
  Why it matters: the alert will never fire and may indicate a renamed metric, bad label, or broken dependency.
  Suggestion: verify metric name, labels, or recording-rule dependency.
```

## Configuration

Create a `.par.yaml` file in the repo root.

```yaml
severity_threshold: warning

required_labels:
  - severity
  - team

required_annotations:
  - summary
  - description
  - runbook_url

selector_policy:
  require_one_of:
    - job
    - cluster
    - namespace
    - service

for_policy:
  required_for_alerts: true
  min: 2m

```

Save this file as `.par.yaml` in the repo root and adjust to taste.

## Inline suppression

Use inline comments for narrow, documented exceptions.

```yaml
# par disable broad-selector reason="global rule by design"
- alert: GlobalScrapeFailure
  expr: up == 0
  for: 1m
```

## Architecture

### 1. Parser layer

- load YAML files
- normalize rule groups and rules
- preserve file and line positions

### 2. PromQL analysis layer

- parse `expr`
- walk the AST
- extract selectors, binary operators, functions, and aggregations

### 3. Rule graph layer

- collect alert names
- collect recording-rule names
- map dependencies across files

### 4. Policy engine

- run offline checks
- optionally run live checks against the Prometheus HTTP API

### 5. Reporter

- text, JSON, and SARIF output
- deterministic rule IDs
- CI-friendly summaries

## CI usage

### Basic CI gate

```bash
par lint rules/*.yaml --min-severity warning
```

### JSON filtering

```bash
par lint rules/*.yaml --format json | jq '.findings[] | select(.severity == "error")'
```

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
      - run: par lint rules/ --format sarif > par.sarif
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: par.sarif
```

### GitHub Actions with Docker

```yaml
- run: docker build -t par .
- run: docker run --rm -v "${{ github.workspace }}/rules:/rules" par lint /rules --format sarif > par.sarif
  continue-on-error: true
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: par.sarif
```

### Makefile targets

```bash
make install        # create venv and install par
make install-dev    # install with test/lint dependencies
make test           # run tests
make lint           # run ruff linter
make cover          # test with coverage
make docker-build   # build Docker image
make docker-run     # run against examples/
make clean          # remove build artifacts
make clean-all      # also remove .venv/
```

## Future enhancements

- richer rule explanations with AST-aware suggestions
- optional integration with `promtool test rules`
- per-directory policy packs
- query cost estimation in live mode
- dashboards and runbook URL reachability checks
- suggested remediations for common PromQL mistakes

## Summary

`par` is intended to catch the kinds of problems that make alerts noisy, unreliable, or hard to act on during incidents. The design emphasizes:

- stable alert behavior
- actionable metadata
- safe selector patterns
- dependency awareness
- CI-friendly policy enforcement
