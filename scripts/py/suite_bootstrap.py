#!/usr/bin/env python3
"""Deterministic trace-resampling diagnostic for selection gains.

This non-parametric bootstrap resamples the observed traces with replacement.
It measures sensitivity to the composition of this 13-trace suite; it is not a
population confidence interval and does not address SimPoint/ROI uncertainty.
"""

import argparse
import math
import os
import random
from collections import Counter

from characterize import BASIS_A, BASIS_B, selection_summary, speedup


def gmean(values):
    values = list(values)
    return math.exp(sum(math.log(value) for value in values) / len(values))


def percentile(sorted_values, probability):
    """Linearly interpolated percentile (NumPy's default convention)."""
    if not sorted_values:
        return float("nan")
    location = (len(sorted_values) - 1) * probability
    lower = math.floor(location)
    upper = math.ceil(location)
    if lower == upper:
        return sorted_values[lower]
    fraction = location - lower
    return (
        sorted_values[lower] * (1 - fraction)
        + sorted_values[upper] * fraction
    )


def bootstrap(results, traces, options, samples, seed):
    table = {
        trace: {option: speedup(results, trace, option) for option in options}
        for trace in traces
    }
    missing = [
        f"{trace}:{option}"
        for trace in traces
        for option in options
        if table[trace][option] is None
    ]
    if missing:
        raise ValueError(
            f"cannot bootstrap an incomplete matrix; missing {', '.join(missing[:8])}"
        )

    rng = random.Random(seed)
    selection_gains = []
    fixed_winners = Counter()
    for _ in range(samples):
        draw = rng.choices(traces, k=len(traces))
        fixed = {
            option: gmean(table[trace][option] for trace in draw)
            for option in options
        }
        best_fixed = max(options, key=lambda option: fixed[option])
        best_per_trace = gmean(max(table[trace].values()) for trace in draw)
        selection_gains.append(best_per_trace / fixed[best_fixed] - 1)
        fixed_winners[best_fixed] += 1

    return sorted(selection_gains), fixed_winners


def report(results, traces, label, options, samples, seed):
    point = selection_summary(results, traces, options)
    selection_gains, fixed_winners = bootstrap(
        results, traces, options, samples=samples, seed=seed
    )
    print(f"\n[{label}]")
    print(
        f"  observed selection gain: {point['selection_gain']:.2%}"
        f"  bootstrap median: {percentile(selection_gains, 0.5):.2%}"
        f"  central 95% interval: "
        f"[{percentile(selection_gains, 0.025):.2%}, "
        f"{percentile(selection_gains, 0.975):.2%}]"
    )
    winner_rates = ", ".join(
        f"{option} {fixed_winners[option]/samples:.1%}"
        for option in sorted(
            fixed_winners, key=fixed_winners.get, reverse=True
        )
    )
    print(f"  best-fixed selection frequency: {winner_rates}")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Bootstrap traces to diagnose how suite composition affects "
            "prefetcher-choice selection gains."
        )
    )
    parser.add_argument("--results", required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20_260_728)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be at least 1")

    traces = sorted(
        name.split("__")[0]
        for name in os.listdir(args.results)
        if name.endswith("__nopref.out")
    )
    if not traces:
        raise SystemExit(f"no default no-prefetch outputs found in {args.results}")

    print("== deterministic trace-resampling suite-composition diagnostic ==")
    print(
        f"traces={len(traces)} resamples={args.samples} seed={args.seed}\n"
        "Interpret the interval as sensitivity to this observed trace suite, "
        "not as a population confidence interval."
    )
    report(args.results, traces, "Basis A: common L2 placement", BASIS_A, args.samples, args.seed)
    report(
        args.results,
        traces,
        "Basis B: released/native placements",
        BASIS_B,
        args.samples,
        args.seed,
    )


if __name__ == "__main__":
    main()
