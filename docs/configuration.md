---
layout: default
title: Configuration
nav_order: 3
parent: Documentation
---

# Configuration

par looks for a configuration file at `.par.yaml` (or `.par.yml`) in the current working directory.
You can specify a different path with the `--config` flag:

```shell
par --config /etc/par.yaml rules/*.yaml
```

If no configuration file is found, par runs with built-in defaults.

All fields are optional. You only need to include fields where you want to override the default.

---

## Full example

```yaml
severity_threshold: info

required_labels:
  - severity
  - owner

valid_owners:
  - sre
  - dctech
  - infra

required_annotations:
  - summary
  - description
  - runbook_url
  - dashboard_url

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

---

## Fields

### `severity_threshold`

**Type:** string  
**Default:** `info`  
**Allowed values:** `error`, `warning`, `info`

Only report findings at or above this severity level. Equivalent to `--min-severity` on the
command line. The command-line flag takes precedence over this setting.

```yaml
severity_threshold: warning
```

---

### `required_labels`

**Type:** list of strings  
**Default:** `[severity, owner]`

Alert rules must have all of these labels defined in their `labels` block. Missing labels
are reported as **required-labels** with severity `error`.

```yaml
required_labels:
  - severity
  - team
```

Common choices for `required_labels`:

| Label | Purpose |
|-------|---------|
| `severity` | Alertmanager routing and grouping |
| `team` | Ownership and routing to the correct receiver |
| `env` | Environment scoping (prod/staging) |
| `service` | Service-level grouping |

---

### `valid_owners`

**Type:** list of strings  
**Default:** `[]` (disabled)

An allowlist of valid values for the `owner` label. When this list is non-empty, any alert
whose `owner` label does not match one of the listed values is reported as **invalid-owner**
with severity `error`. When the list is empty (the default), owner values are not validated.

```yaml
valid_owners:
  - sre
  - dctech
  - infra
```

---

### `required_annotations`

**Type:** list of strings  
**Default:** `[summary, description, runbook_url, dashboard_url]`

Alert rules must have all of these annotations defined. Missing annotations are reported
as **required-annotations**. The severity of each finding depends on which annotation is missing:

| Annotation | Default severity |
|------------|-----------------|
| `summary` | error |
| `description` | warning |
| `runbook_url` | error |
| `dashboard_url` | warning |
| any other | warning |

```yaml
required_annotations:
  - summary
  - description
  - runbook_url
  - dashboard_url
```

To require only a summary (minimum viable annotation set):

```yaml
required_annotations:
  - summary
```

---

### `selector_policy`

**Type:** object

Controls the **broad-selector** broad-selector check.

#### `selector_policy.require_one_of`

**Type:** list of strings  
**Default:** `[job, cluster, namespace, service]`

At least one of these label names must appear in the alert expression's selectors.
If an expression has selectors but none of the required scoping labels, the finding
is reported at `info` severity. If the expression has no selectors at all, it is
reported at `warning` severity.

```yaml
selector_policy:
  require_one_of:
    - job
    - cluster
    - namespace
    - service
```

To require only `job` and `namespace`:

```yaml
selector_policy:
  require_one_of:
    - job
    - namespace
```

---

### `for_policy`

**Type:** object

Controls the **for-duration** missing-`for`-duration check.

#### `for_policy.required_for_alerts`

**Type:** boolean  
**Default:** `true`

When `true`, alert rules without a `for` clause are flagged. Set to `false` to disable
the check entirely — useful if your team uses recording rules to pre-aggregate and only
alerts on stable signals.

```yaml
for_policy:
  required_for_alerts: true
```

#### `for_policy.min`

**Type:** Prometheus duration string  
**Default:** `2m`

The minimum acceptable `for` duration. Any rule with a `for` value shorter than this
is flagged. Accepts the same duration format as Prometheus: `30s`, `2m`, `1h30m`.

```yaml
for_policy:
  min: 5m
```

For SLO-based alerting where burn-rate alerts need very short `for` durations, lower or
disable this threshold:

```yaml
for_policy:
  required_for_alerts: true
  min: 0s      # only flag missing 'for', not short ones
```

---

## Minimal configuration

For teams adopting par incrementally, start with a configuration that only blocks on
the most critical issues:

```yaml
severity_threshold: error

required_labels:
  - severity

required_annotations:
  - summary
```

Then tighten the policy over time as your rule files improve.

---

## Per-rule suppression

Individual findings can be suppressed for a specific rule by adding a comment on the line
immediately above the rule definition. This is useful for intentional exceptions that would
otherwise generate noise.

```yaml
# par disable broad-selector
- alert: GlobalHealthCheck
  expr: up == 0
  for: 1m
  labels:
    severity: info
  annotations:
    summary: A target is unreachable
```

Multiple check IDs can be suppressed in a single comment:

```yaml
# par disable broad-selector, for-duration
- alert: ...
```

Suppression comments follow these rules:

- They apply to exactly one rule — the one immediately below.
- They are scoped to the rule ID(s) listed; all other checks still run on that rule.
- They have no effect on other rules in the same file.
