---
layout: default
title: for-duration
grand_parent: Documentation
parent: Checks
nav_order: 1
---

# for-duration

**Severity:** warning  
**Category:** stability

## What it checks

An alert fires as soon as its expression evaluates to a non-empty result. Without a `for`
clause, a single bad data point — a brief network blip, a pod restart, a slow scrape — is
enough to page the on-call engineer.

This check flags alerts that have no `for` clause at all, or whose `for` duration is shorter
than the configured minimum (default: 2 minutes).

## Why it matters

A `for` duration requires the condition to be continuously true before the alert fires. This
filters out transient spikes and significantly reduces false positives. Most production
alerting configurations use at least `5m` for non-critical alerts and `2m` for critical ones.

## Exception

Alerts whose expression uses `absent()` are exempt. A missing-metric alert should page
immediately — the whole point is to catch a gap in monitoring as soon as it appears.

## Examples

**Bad — no `for` clause**

```yaml
- alert: InstanceDown
  expr: up{job="api"} == 0
  labels:
    severity: critical
```

**Bad — `for` too short**

```yaml
- alert: HighErrorRate
  expr: rate(http_errors_total{job="api"}[5m]) > 0.1
  for: 30s
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
```

## Configuration

```yaml
for_policy:
  required_for_alerts: true   # set false to disable this check entirely
  min: 2m                     # minimum acceptable 'for' duration
```

## Suppression

```yaml
# par disable for-duration
- alert: FastBurnSLO
  expr: job:error_rate:rate1m{job="api"} > 0.1
```
