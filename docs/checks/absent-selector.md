---
layout: default
title: absent-selector
grand_parent: Documentation
parent: Checks
nav_order: 2
---

# absent-selector

**Severity:** warning  
**Category:** stability

## What it checks

`absent()` is called without label selectors in the metric selector expression.

## Why it matters

`absent(metric_name)` returns 1 whenever there is no time series with that name anywhere
in Prometheus — including jobs, clusters, and environments where you never expected it to
exist. In a multi-cluster setup this fires whenever the metric is absent from even one
target, even if it is healthy everywhere else.

Selectors scope the absence check to a specific job or namespace, making the alert fire
only for the target you actually care about.

## Examples

**Bad**

```yaml
- alert: MetricMissing
  expr: absent(up)
```

**Good**

```yaml
- alert: APIJobMissing
  expr: absent(up{job="api", namespace="production"})
```

## Suppression

```yaml
# par disable absent-selector
- alert: AnyTargetMissing
  expr: absent(up)
```
