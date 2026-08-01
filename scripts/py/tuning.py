#!/usr/bin/env python3

import argparse
import glob
import math
import os
import re

SPP_CONFIGS = (
    "pf20_fill50", "pf20_fill70", "pf20_fill90", "pf20_fill100",
    "pf40_fill50", "pf40_fill70", "pf40_fill90", "pf40_fill100",
    "pf60_fill70", "pf60_fill90", "pf60_fill100",
    "pf80_fill90", "pf80_fill100",
)
DEGREE_CONFIGS = {
    "stride": ("2(default)", "1", "4", "8", "16"),
    "streamer": ("5(default)", "1", "2", "4", "16"),
}


def grab(text, key):
    match = re.search(
        rf"^Core_0_{re.escape(key)}\s+([0-9.]+)\s*$", text, re.M
    )
    return float(match.group(1)) if match else None


def required_ipc(path):
    if not os.path.exists(path):
        raise SystemExit(f"missing required output: {path}")
    with open(path) as source:
        value = grab(source.read(), "IPC")
    if value is None or value <= 0:
        raise SystemExit(f"invalid or missing IPC in required output: {path}")
    return value


def gmean(xs):
    values = list(xs)
    if not values or any(value <= 0 for value in values):
        raise ValueError("geometric mean requires a complete set of positive values")
    return math.exp(sum(map(math.log, values)) / len(values))

def analyze(
    results,
    traces,
    label,
    prefetcher,
    configs,
    filename,
    cfg_key,
    default_config=None,
):
    """Analyze a complete, explicitly enumerated tuning grid."""
    data = {}
    for trace in traces:
        baseline = required_ipc(f"{results}/{trace}__nopref.out")
        data[trace] = {}
        for config in configs:
            if config == default_config:
                path = f"{results}/{trace}__{prefetcher}.out"
            else:
                path = (
                    f"{results}/{trace}__{prefetcher}__{filename(config)}.out"
                )
            data[trace][config] = required_ipc(path) / baseline

    # per-trace optimum (ceiling)
    per_trace_best={t:max(data[t].values()) for t in traces}
    per_trace_pick={t:max(data[t],key=lambda c:data[t][c]) for t in traces}
    ceiling=gmean([per_trace_best[t] for t in traces])

    # best single fixed cfg (realizable): the cfg with highest geomean across traces
    geo={c:gmean(data[t][c] for t in traces) for c in configs}
    best_fixed=max(geo,key=lambda c:geo[c])
    realizable=geo[best_fixed]

    selection_gain=ceiling/realizable-1
    print(f"\n===== {label} =====")
    print(f"  best FIXED {cfg_key}: {best_fixed}  (geomean speedup {realizable:.4f})")
    print(f"  per-trace CEILING           :          {ceiling:.4f}")
    print(f"  TUNING SELECTION GAIN       :          {selection_gain*100:+.2f}%")
    print(f"  per-trace optimal {cfg_key} (heterogeneity):")
    for t in traces:
        flag="" if per_trace_pick[t]==best_fixed else "  <- differs from fixed"
        print(f"    {t:12s} {per_trace_pick[t]:14s} {per_trace_best[t]:.4f}{flag}")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--results",required=True); a=ap.parse_args()
    R=a.results
    traces = sorted(
        os.path.basename(path).split("__", 1)[0]
        for path in glob.glob(f"{R}/*__nopref.out")
    )
    if len(traces) != 13 or len(set(traces)) != 13:
        raise SystemExit(
            f"expected 13 unique default-baseline traces, found {len(set(traces))}"
        )

    # SPP pf x fill grid
    analyze(
        R, traces, "SPP pf x fill grid", "spp_dev2", SPP_CONFIGS,
        lambda config: config, "pf_fill"
    )
    # degree (data from Phase 6): stride/streamer __<knob>_<val>
    for pref, configs in DEGREE_CONFIGS.items():
        default_config = configs[0]
        analyze(
            R, traces, f"{pref} degree", pref, configs,
            lambda config, prefix=pref: f"{prefix}_pref_degree_{config}",
            "degree",
            default_config=default_config,
        )

if __name__=="__main__":
    main()
