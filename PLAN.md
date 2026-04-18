# par - Implementation Plan

## Goal

A CLI tool that reads one or more Prometheus alerting rule YAML files and produces an actionable
report of quality issues. The focus is on alerts that are noisy, missing context, or hard to act
on during an incident.

---

## Why These Checks Matter

Good alerting rules follow a few core principles:

- **Alerts should represent a user-visible problem**, not a raw metric crossing a threshold
- **Every alert must be actionable** - if you can't do anything about it, it shouldn't page
- **Alerts should fire only when the condition is sustained**, not on transient spikes
- **On-call engineers need context immediately** - no time to go hunting for what the alert means

The checks below are derived from these principles. Each one represents a real failure mode
observed in production alerting setups.

---

## Checks

### 1. Missing or Too-Short `for` Duration

**Severity:** WARNING

**Why it matters:**
An alert without a `for` clause fires on the very first evaluation cycle (typically 15-30s).
A single bad data point, a brief network blip, or a pod restart will trigger a page. This is
the leading cause of alert fatigue. A `for: 2m` or longer gives confidence the condition is
real and sustained.

**Edge case:** `absent()` alerts are exempt - you want to know immediately if a critical metric
stops being scraped, and adding `for` would delay detection of a monitoring gap.

**Rule of thumb:** Minimum `2m` for most alerts. High-severity/SLO alerts may go shorter with
explicit justification, but never zero.

---

### 2. Missing `summary` Annotation

**Severity:** ERROR

**Why it matters:**
`summary` is the first thing an on-call engineer reads in a PagerDuty/Alertmanager notification.
Without it, the alert shows a raw PromQL expression - useless at 3am. A good summary answers
"what is broken right now?" in one sentence.

**Best practice:**
```yaml
annotations:
  summary: "High error rate on {{ $labels.job }} in {{ $labels.namespace }}"
```

---

### 3. Missing `description` Annotation

**Severity:** WARNING

**Why it matters:**
While `summary` says what is broken, `description` says why it matters and gives numerical
context. It should include the current value using `{{ $value }}` and enough detail to
distinguish this from similar alerts.

**Best practice:**
```yaml
annotations:
  description: >
    Error rate is {{ $value | humanizePercentage }} for {{ $labels.job }},
    exceeding the 1% threshold for the past 5 minutes.
```

---

### 4. Missing `runbook_url` Annotation

**Severity:** ERROR

**Why it matters:**
A runbook links the alert directly to remediation steps. Without it, engineers guess or rely on
tribal knowledge. Even a stub runbook URL is better than none - it signals the alert has been
thought through.

**Best practice:**
```yaml
annotations:
  runbook_url: "https://wiki.example.com/runbooks/high-error-rate"
```

---

### 5. Missing `severity` Label

**Severity:** WARNING

**Why it matters:**
Alertmanager routing trees almost always branch on `severity`. Without it, the alert cannot
be routed to the right team, cannot be silenced by severity, and cannot be grouped correctly.
Standard values: `critical`, `warning`, `info`.

**Best practice:**
```yaml
labels:
  severity: warning
```

---

### 6. No Label Selectors in Expression

**Severity:** WARNING

**Why it matters:**
An expression like `up == 0` fires for **every** target that goes down across every job and
cluster. This generates noise, makes deduplication harder, and means the alert fires in
environments it was never intended for (e.g., staging triggering production runbooks).
Every alert should scope itself with at least `job=` or a namespace/cluster selector.

**Best practice:**
```promql
up{job="api-server", cluster="prod"} == 0
```

---

### 7. `absent()` Without Label Selectors

**Severity:** WARNING

**Why it matters:**
`absent(http_requests_total)` returns 1 whenever **no** time series with that name exists
anywhere. In a multi-cluster setup, this fires if the metric exists in cluster A but not B.
It also fires during metric renames. Selectors scope the absence check to a specific target.

**Best practice:**
```promql
absent(up{job="api-server", namespace="production"})
```

---

### 8. Short `rate()`/`irate()` Window

**Severity:** WARNING

**Why it matters:**
`rate(metric[1m])` with a 15s scrape interval uses only ~4 data points. This produces a very
noisy signal - a single slow scrape inflates the rate significantly. Prometheus docs recommend
windows of at least 4x the scrape interval. In practice, `[5m]` is the safe minimum for most
use cases. `irate()` is designed for fast-moving counters but is especially sensitive to gaps.

**Threshold:** Flag windows shorter than `2m`.

---

### 9. Duplicate Alert Names Within a Group

**Severity:** ERROR

**Why it matters:**
If two rules in the same group share a name, Prometheus silently uses the last definition.
This is almost always a copy-paste mistake and means one of the alerts is never evaluated.
It can also cause unexpected behavior in Alertmanager deduplication.

---

### 10. Expression Has No Comparison Operator

**Severity:** WARNING

**Why it matters:**
An expression like `process_open_fds` (no threshold) evaluates to the raw metric value.
Since any non-zero, non-NaN value is truthy in Prometheus alerting, this alert fires
constantly for every instance that reports this metric. These are usually work-in-progress
rules that were accidentally left in production.

**Exemptions:** Expressions using `absent()`, `changes()`, `time()`, or boolean modifiers
(`bool`) are excluded since they produce meaningful 0/1 results without a comparison.

---

## Architecture

```
par-linter/
├── par/
│   ├── cli.py          # Entry point, argparse, orchestration
│   ├── models.py       # AlertRule, RecordingRule, Finding dataclasses
│   ├── parser.py       # YAML loading and rule extraction
│   ├── config.py       # Config dataclass and .par.yaml loading
│   ├── reporter.py     # Text, JSON, and table output formatters
│   └── checks/
│       ├── base.py     # Abstract AlertCheck and CorpusCheck
│       ├── metadata.py # required-labels, required-annotations, invalid-owner
│       ├── stability.py# for-duration, absent-selector, rate-window
│       ├── selectors.py# broad-selector
│       ├── structure.py# no-comparison, counter-threshold, duplicate-alert, recording-ref
│       └── naming.py   # non-base-unit
├── tests/
├── examples/
│   └── bad_rules.yaml  # Sample file demonstrating all checks
├── pyproject.toml
└── README.md
```

---

## CLI Interface

```
Usage: par <command> [OPTIONS] PATH [PATH...]

Commands:
  lint     Check rule files and report findings
  summary  Print a per-owner summary table

Options:
  --format [text|json|table]  Output format (default: text)
  --min-severity LEVEL        Only report findings at or above this level: error|warning|info (default: info)
  --config FILE               Path to config file (default: .par.yaml)
  --label KEY=VALUE           Filter to alerts matching this label; repeatable
  --no-color                  Disable colored output
  --force-color               Force color output even when stdout is not a TTY
  -h, --help                  Show this message and exit
```

**Example output (text):**
```
ERRORS (2)
────────────────────────────────────────────────────────────
[required-annotations] HighCpuUsage  rules/nodes.yaml:4
       Alert is missing required annotations: summary, description, runbook_url
       Fix: add annotations block with summary, description, and runbook_url.

[duplicate-alert] DiskFull  rules/nodes.yaml:22
       Duplicate alert name 'DiskFull' in group 'node_alerts'. The later definition silently overrides the earlier one.
       Fix: Rename or remove the duplicate.

WARNINGS (4)
────────────────────────────────────────────────────────────
[for-duration] ApiErrors  rules/api.yaml:8
       Alert has no 'for' duration and will fire on the first evaluation cycle.
       Fix: Add 'for: 5m' or longer to filter transient conditions.

[broad-selector] HighMemory  rules/nodes.yaml:31
       Expression has no label selectors. It will fire across all targets.
       Fix: scope the selector with job, cluster, namespace, or service labels.

...

SUMMARY
-------
Files:          2
Alert rules:    12
Recording rules: 3
Errors:         2
Warnings:       4
Info:           1
```

---

## Checks Not Included (and Why)

| Check | Reason Excluded |
|-------|----------------|
| Alert inhibition coverage | Requires Alertmanager config, outside scope of rule files |
| PromQL syntax validation | Would require a live Prometheus or full PromQL parser library |
| Threshold reasonableness (e.g. CPU > 99.9%) | Too domain-specific without business context |
| Label cardinality in grouping | Requires metric metadata from a live instance |
| SLO burn rate alignment | Requires knowledge of SLO definitions |

These are meaningful checks but require external context that a static file analyzer
cannot reliably provide.

---

## Language and Dependencies

- **Python 3.9+** - available everywhere, good YAML support, no compile step
- **pyyaml** - only external dependency, widely available
- **No PromQL parser** - regex-based expression analysis is sufficient for the patterns
  we target and avoids a heavy dependency

---

## Testing Strategy

- Unit tests per check using pytest with inline YAML fixtures
- Integration test: feed `examples/bad_rules.yaml` and assert all expected findings appear
- CI step: `par lint --min-severity warning rules/` to gate on regressions
