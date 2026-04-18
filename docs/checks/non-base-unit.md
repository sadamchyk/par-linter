---
layout: default
title: non-base-unit
parent: Checks
nav_order: 11
---

# non-base-unit

**Severity:** info  
**Category:** naming

## What it checks

A metric referenced in the alert expression uses a non-base unit suffix — for example
`_milliseconds` instead of `_seconds`, or `_megabytes` instead of `_bytes`.

## Why it matters

[Prometheus naming best practices](https://prometheus.io/docs/practices/naming/) require
base units so that metrics from different exporters stay interoperable and PromQL expressions
remain unambiguous. When two metrics measure the same thing in different units they cannot
be compared or aggregated without a conversion factor embedded in every query, dashboard,
and alert. This is easy to get wrong silently.

Common mistakes:

| Non-base (avoid) | Base (use instead) |
|------------------|-------------------|
| `_milliseconds` | `_seconds` |
| `_microseconds` | `_seconds` |
| `_minutes` / `_hours` / `_days` | `_seconds` |
| `_kilobytes` / `_megabytes` / `_gigabytes` | `_bytes` |
| `_kilobits` / `_megabits` | `_bytes` |
| `_percent` / `_percentage` | `_ratio` (values 0–1) |
| `_kilometers` / `_centimeters` | `_meters` |
| `_millivolts` | `_volts` |
| `_milliamperes` | `_amperes` |
| `_milligrams` | `_grams` |

**Note on percent vs ratio:** Prometheus uses ratios in the range 0–1, not 0–100. Use
the `humanizePercentage` template function in annotations to display the value as a
human-readable percentage.

## Examples

**Bad**

```yaml
- alert: HighLatency
  expr: http_request_duration_milliseconds{job="api"} > 500
  for: 5m
```

**Finding**

```
INFO [non-base-unit] HighLatency  rules/api.yaml:2
     Metric 'http_request_duration_milliseconds' uses non-base unit 'milliseconds'.
     Prometheus recommends 'seconds' for interoperability.
     Fix: Rename to 'http_request_duration_seconds' and update the exporter.
```

**Good**

```yaml
- alert: HighLatency
  expr: http_request_duration_seconds{job="api"} > 0.5
  for: 5m
```

**Bad — percent instead of ratio**

```yaml
- alert: HighDiskUsage
  expr: disk_usage_percent{job="node"} > 90
```

**Good — ratio with humanizePercentage in annotation**

```yaml
- alert: HighDiskUsage
  expr: disk_usage_ratio{job="node"} > 0.9
  for: 5m
  annotations:
    summary: "Disk usage is {{ $value | humanizePercentage }}"
```

## Scope

This check inspects metric names found in the alert expression. It does not validate
the exporter or the time series in a live Prometheus instance — it only flags names
that match known non-base unit patterns.

If the metric name is outside your control (third-party exporter), suppress the check.

## Suppression

```yaml
# par disable non-base-unit
- alert: ThirdPartyHighLatency
  expr: vendor_request_duration_milliseconds{job="vendor"} > 500
```
