---
layout: default
title: recording-ref
grand_parent: Documentation
parent: Checks
nav_order: 9
---

# recording-ref

**Severity:** error  
**Category:** dependency

## What it checks

An alert expression references a recording rule by its colon-notation name (e.g.
`job:http_error_rate:rate5m`) but that recording rule is not defined in any of the files
passed to par.

## Why it matters

If the referenced recording rule does not exist, the alert expression evaluates against a
metric that is never produced. The alert will never fire — silently. This is one of the
hardest failure modes to detect because the rule file is valid YAML and passes `promtool`
syntax checking.

Common causes:

- The recording rule file was not included in the lint run.
- The recording rule was renamed without updating the alert.
- The recording rule was planned but never written.

## Detection

par identifies recording rule references by the Prometheus naming convention: metric
names containing at least one colon (`job:metric:aggregation`) are treated as recording
rule references. This is the standard convention — regular metric names should not contain
colons.

## Examples

**Bad** — run with only the alerts file, not the recordings file:

```yaml
# alerts.yaml
- alert: HighSLOBurnRate
  expr: job:http_error_rate:rate5m{job="api"} > 0.01
  for: 5m
```

```shell
par alerts.yaml          # missing recordings.yaml → recording-ref fires
```

**Good**

```shell
par alerts.yaml recordings.yaml    # both files provided → resolved
```

## Suppression

```yaml
# par disable recording-ref
- alert: ExternalRecordingRule
  expr: external:slo:error_budget_remaining < 0.1
```
