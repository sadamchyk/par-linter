---
layout: default
title: no-comparison
grand_parent: Documentation
parent: Checks
nav_order: 6
---

# no-comparison

**Severity:** warning  
**Category:** promql

## What it checks

The alert expression contains no comparison operator (`==`, `!=`, `>`, `<`, `>=`, `<=`).

## Why it matters

In Prometheus alerting, an expression evaluates to a set of time series. Any series with a
non-zero, non-NaN value is considered "firing". An expression with no comparison — such as
`process_open_fds{job="api"}` — fires for every instance that reports the metric, every
single evaluation cycle. This creates permanent noise with no actionable signal.

These are almost always incomplete rules left over from copy-paste or a refactoring that
was never finished.

## Exceptions

- Expressions using `absent()` return 0 or 1 based on metric presence — no comparison needed.
- Expressions using the `bool` modifier return 0 or 1 explicitly.

## Examples

**Bad**

```yaml
- alert: OpenFileDescriptors
  expr: process_open_fds{job="api"}
  for: 5m
```

**Good**

```yaml
- alert: TooManyOpenFileDescriptors
  expr: process_open_fds{job="api"} > 900
  for: 5m
```

## Suppression

```yaml
# par disable no-comparison
- alert: ...
```
