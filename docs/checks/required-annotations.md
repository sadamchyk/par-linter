---
layout: default
title: required-annotations
parent: Checks
nav_order: 4
---

# required-annotations

**Severity:** error (`summary`, `runbook_url`), warning (`description`, `dashboard_url`)  
**Category:** metadata

## What it checks

One or more annotations configured as required are absent from the alert's `annotations`
block. The severity of each finding depends on which annotation is missing.

| Annotation | Severity | Why |
|------------|----------|-----|
| `summary` | error | First thing the on-call engineer reads in a notification |
| `description` | warning | Provides numerical context and the current metric value |
| `runbook_url` | error | Links directly to remediation steps |
| `dashboard_url` | warning | Links to the observability dashboard for the affected service |
| any other | warning | Configured as required by the team |

## Why it matters

Without a `summary`, the on-call engineer sees a raw PromQL expression in their PagerDuty
notification at 3am. Without a `description`, they lack the metric value and context needed
to triage quickly. Without a `runbook_url`, they rely on tribal knowledge to know what to do.

## Examples

**Bad**

```yaml
- alert: HighErrorRate
  expr: rate(http_errors_total{job="api"}[5m]) > 0.1
  for: 5m
  labels:
    severity: warning
```

**Good**

```yaml
- alert: HighErrorRate
  expr: rate(http_errors_total{job="api"}[5m]) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High error rate on {{ $labels.job }}"
    description: >
      Error rate is {{ $value | humanizePercentage }} for {{ $labels.job }},
      exceeding the 10% threshold.
    runbook_url: https://wiki.example.com/runbooks/high-error-rate
    dashboard_url: https://grafana.example.com/d/api-errors
```

## Configuration

```yaml
required_annotations:
  - summary
  - description
  - runbook_url
```

## Suppression

```yaml
# par disable required-annotations
- alert: WIPAlert
  expr: ...
```
