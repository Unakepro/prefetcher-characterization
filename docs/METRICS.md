# Metrics

This file defines the calculations used in the reports. Every comparison is
matched by trace, seed, warmup, measured interval, channel count, and LLC size.
`P` is a prefetcher, `N` is no prefetching, and `C` is the remaining
configuration.

## Performance

```text
speedup(P, C) = IPC(P, C) / IPC(N, C)
```

The reference must use the same hardware configuration:

| Candidate configuration | Reference |
|---|---|
| Default | `nopref` |
| Two channels | `nopref_2ch` |
| 1 MiB LLC | `nopref_1MB` |
| 4 MiB LLC | `nopref_4MB` |

Suite results use the geometric mean:

```text
geomean(s) = exp(sum(log(s_i)) / n)
```

Each trace has equal weight. Missing or invalid results fail the analysis
instead of being silently omitted.

## L2 demand misses

```text
L2 demand misses = L2C_load_miss + L2C_RFO_miss
L2 demand MPKI   = 1000 * L2 demand misses / measured instructions

L2 demand-miss reduction =
    (L2_demand_misses(N, C) - L2_demand_misses(P, C))
    / L2_demand_misses(N, C)
```

The CSV keeps the historical column name `coverage` for the last metric. A
negative value means that the candidate produced more L2 demand misses than
its matched reference. This is an aggregate miss reduction, not the fraction
of individual misses covered by a prefetch.

## Prefetch diagnostics

```text
issued yield     = prefetch_useful / prefetch_issued
fill utilization = prefetch_useful / prefetch_filled
late fraction    = prefetch_late / (prefetch_useful + prefetch_late)
```

The CSV uses the older names `accuracy_issued` and `accuracy_filled`. Native
IPCP generates prefetches at both L1 and L2, so its L2 issued and filled
counters do not describe the same request cohort. Do not rank its issued yield
or fill utilization directly against standalone L2 prefetchers.

The secondary LLC metrics follow the Pythia artifact:

```text
LLC load coverage =
    (baseline LLC load misses - candidate LLC load misses)
    / baseline LLC load misses

LLC read overprediction =
    (candidate LLC load misses + candidate LLC prefetch misses
     - baseline LLC load misses)
    / baseline LLC load misses
```

LLC read overprediction measures excess read traffic. It is not a cache
pollution counter.

## Fixed choice and per-trace selection

For tested options `O`:

```text
best fixed = argmax over o in O of geomean_i(speedup(i, o))

best_per_trace_i = max over o in O of speedup(i, o)

selection gain =
    geomean_i(best_per_trace_i)
    / geomean_i(speedup(i, best fixed)) - 1
```

Best per trace is calculated after seeing all results. It is a descriptive
upper bound over the tested options, not a deployable policy. Prefetcher
choice, degree, and the SPP parameter grid are reported separately because a
joint combination of all settings was not tested.

## Comparison groups

- Basis A compares Stride, Streamer, SPP-dev2, and Bingo in the common L2
  prefetcher position.
- Basis B adds IPCP in its released L1D+L2 configuration and therefore
  compares the released packages rather than equal placements.

Neither group equalizes storage, ports, queues, or traffic.

## Sensitivity summaries

For one parameter on one trace:

```text
spread = max(tested speedups) - min(tested speedups)
```

For channel count:

```text
channel-count change =
    speedup(P, one channel) / speedup(P, two channels) - 1
```

A negative channel-count change means that the normalized benefit is smaller
with one channel. It is not a direct bandwidth measurement.

LLC-capacity results always use the no-prefetch reference with the same LLC
size. The no-prefetch comparison is:

```text
baseline LLC swing = IPC(N, 4 MiB) / IPC(N, 1 MiB) - 1
```
