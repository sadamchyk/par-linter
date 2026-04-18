---
layout: default
title: counter-threshold
grand_parent: Documentation
parent: Checks
nav_order: 7
---

# counter-threshold

**Severity:** warning  
**Category:** promql

## What it checks

A counter metric — identified by a name ending in `_total` or `_count` — is compared
against an absolute threshold without a `rate()`, `increase()`, `irate()`, or `delta()`
wrapper.

## Why it matters

Prometheus counters only go up (except on process restart). Their absolute value reflects
the total number of events since the process started, not the recent rate. An alert like
`errors_total > 100` will fire permanently for any long-running process that has
accumulated 100 errors over its entire lifetime, regardless of whether those errors happened
today or six months ago.

The correct pattern is to compute the rate of change over a time window:

```promql
rate(errors_total[5m]) > 0.1
```

## Detection heuristic

This check uses the metric name as a heuristic: any metric ending in `_total` or `_count`
is assumed to be a counter. This correctly handles the Prometheus naming convention but may
produce false positives for non-standard metric names, and false negatives for counters with
unusual names.

## Examples

**Bad**

```yaml
- alert: TooManyErrors
  expr: http_errors_total{job="api"} > 100
  for: 5m
```

**Bad — aggregation without rate still uses raw counter**

```yaml
- alert: TooManyErrors
  expr: sum(http_errors_total{job="api"}) > 100
```

**Good**

```yaml
- alert: HighErrorRate
  expr: rate(http_errors_total{job="api"}[5m]) > 0.1
  for: 5m
```

## Suppression

```yaml
# par disable counter-threshold
- alert: TotalErrorsExceeded
  expr: http_errors_total{job="api"} > 1000000
```
