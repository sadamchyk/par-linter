---
layout: default
title: rate-window
grand_parent: Documentation
parent: Checks
nav_order: 8
---

# rate-window

**Severity:** warning  
**Category:** promql

## What it checks

A `rate()` or `irate()` range vector window is shorter than 2 minutes.

## Why it matters

`rate()` computes the per-second rate of increase of a counter over a time window by
fitting a line through the samples in that window. With a typical 15-second scrape
interval, a `[1m]` window contains only about 4 data points. A single slow scrape, a
missed scrape, or a brief counter reset inflates the computed rate significantly, making
the alert trigger on noise.

Prometheus documentation recommends a range window of at least 4× the scrape interval.
In practice `[5m]` is the safe minimum for most alerting use cases.

`irate()` is even more sensitive: it uses only the last two samples in the window, making
it highly reactive to individual scrape variations.

## Examples

**Bad — only ~4 samples at 15s scrape interval**

```yaml
- alert: HighRequestRate
  expr: rate(http_requests_total{job="api"}[1m]) > 1000
```

**Bad — irate with short window**

```yaml
- alert: HighErrorRate
  expr: irate(http_errors_total{job="api"}[30s]) > 0.5
```

**Good**

```yaml
- alert: HighRequestRate
  expr: rate(http_requests_total{job="api"}[5m]) > 1000
  for: 5m
```

## Suppression

```yaml
# par disable rate-window
- alert: VeryFastBurn
  expr: irate(errors_total{job="api"}[1m]) > 10
```
