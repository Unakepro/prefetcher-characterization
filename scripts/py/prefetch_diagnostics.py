#!/usr/bin/env python3
"""Report first-class prefetch traffic, usefulness, and lateness diagnostics.

The Pythia-style LLC overprediction metric is an observable traffic outcome:
extra LLC read misses relative to the matched no-prefetch run. It is not a
cache-pollution counter and does not identify which request delayed demand.
"""

import argparse
import glob
import math
import os

from parse_champsim import compute, parse_file


PREFETCHERS = ("stride", "streamer", "spp_dev2", "bingo", "ipcp")


def mean(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None


def ratio(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def correlation(xs, ys):
    pairs = [
        (x, y)
        for x, y in zip(xs, ys)
        if x is not None and y is not None
    ]
    if len(pairs) < 2:
        return None
    x_mean = sum(x for x, _ in pairs) / len(pairs)
    y_mean = sum(y for _, y in pairs) / len(pairs)
    numerator = sum((x-x_mean)*(y-y_mean) for x, y in pairs)
    x_norm = math.sqrt(sum((x-x_mean)**2 for x, _ in pairs))
    y_norm = math.sqrt(sum((y-y_mean)**2 for _, y in pairs))
    return numerator/(x_norm*y_norm) if x_norm and y_norm else None


def fmt(value, scale=1.0, suffix=""):
    if value is None:
        return "n/a"
    return f"{value * scale:.3f}{suffix}"


def main():
    parser = argparse.ArgumentParser(
        description="Summarize default-configuration prefetch diagnostics."
    )
    parser.add_argument("--results", required=True)
    args = parser.parse_args()

    traces = sorted(
        os.path.basename(path).split("__", 1)[0]
        for path in glob.glob(f"{args.results}/*__nopref.out")
    )
    if not traces:
        raise SystemExit(f"no default no-prefetch outputs found in {args.results}")

    rows = {prefetcher: [] for prefetcher in PREFETCHERS}
    for trace in traces:
        base_path = f"{args.results}/{trace}__nopref.out"
        if not os.path.exists(base_path):
            raise SystemExit(f"missing required output: {base_path}")
        base = parse_file(base_path)
        base_2ch_path = f"{args.results}/{trace}__nopref_2ch.out"
        if not os.path.exists(base_2ch_path):
            raise SystemExit(f"missing required output: {base_2ch_path}")
        base_2ch = parse_file(base_2ch_path)

        for prefetcher in PREFETCHERS:
            path = f"{args.results}/{trace}__{prefetcher}.out"
            if not os.path.exists(path):
                raise SystemExit(f"missing required output: {path}")
            parsed = parse_file(path)
            derived = compute(parsed, base)
            path_2ch = f"{args.results}/{trace}__{prefetcher}_2ch.out"
            if not os.path.exists(path_2ch):
                raise SystemExit(f"missing required output: {path_2ch}")
            derived_2ch = compute(parse_file(path_2ch), base_2ch)
            instructions = parsed["instructions"]
            if instructions in (None, 0):
                raise SystemExit(f"invalid instruction count in {path}")
            per_ki = 1000.0 / instructions
            rows[prefetcher].append(
                {
                    "issued_bpki": parsed["L2C_prefetch_issued"] * per_ki,
                    "filled_bpki": parsed["L2C_prefetch_filled"] * per_ki,
                    "useful_bpki": parsed["L2C_prefetch_useful"] * per_ki,
                    "useless_bpki": parsed["L2C_prefetch_useless"] * per_ki,
                    "issued_yield": ratio(
                        parsed["L2C_prefetch_useful"],
                        parsed["L2C_prefetch_issued"],
                    ),
                    "fill_utilization": ratio(
                        parsed["L2C_prefetch_useful"],
                        parsed["L2C_prefetch_filled"],
                    ),
                    "late_share": ratio(
                        parsed["L2C_prefetch_late"],
                        (
                            parsed["L2C_prefetch_useful"]
                            + parsed["L2C_prefetch_late"]
                        ),
                    ),
                    "overprediction": derived[
                        "pythia_llc_read_overprediction"
                    ],
                    "channel_delta": (
                        derived["speedup"]/derived_2ch["speedup"]-1
                    ),
                }
            )

    print("== default-configuration prefetch diagnostics ==")
    print(
        "values are arithmetic means of per-trace ratios/rates over "
        f"{len(traces)} selected traces"
    )
    print(
        f"{'pref':10s} {'issued':>9s} {'filled':>9s} {'useful':>9s} "
        f"{'useless':>9s} {'issue-yld':>10s} {'fill-util':>10s} "
        f"{'late':>8s} {'LLC overpred':>12s}"
    )
    for prefetcher in PREFETCHERS:
        data = rows[prefetcher]
        issue_yield = mean(row["issued_yield"] for row in data)
        fill_utilization = mean(row["fill_utilization"] for row in data)
        if prefetcher == "ipcp":
            issue_yield = None
            fill_utilization = None
        print(
            f"{prefetcher:10s} "
            f"{fmt(mean(row['issued_bpki'] for row in data)):>9s} "
            f"{fmt(mean(row['filled_bpki'] for row in data)):>9s} "
            f"{fmt(mean(row['useful_bpki'] for row in data)):>9s} "
            f"{fmt(mean(row['useless_bpki'] for row in data)):>9s} "
            f"{fmt(issue_yield, 100.0, '%'):>10s} "
            f"{fmt(fill_utilization, 100.0, '%'):>10s} "
            f"{fmt(mean(row['late_share'] for row in data), 100.0, '%'):>8s} "
            f"{fmt(mean(row['overprediction'] for row in data), 100.0, '%'):>12s}"
        )

    print(
        "\nrates are L2 events per 1,000 measured instructions. LLC overpred is "
        "(candidate LLC load misses + candidate LLC prefetch misses - baseline "
        "LLC load misses) / baseline LLC load misses."
    )
    print(
        "Native IPCP's L2 issued/fill cohorts mix request origins, so its "
        "issue-yield and fill-utilization are intentionally reported as n/a."
    )
    print(
        "Overprediction measures extra read traffic; it does not prove cache "
        "pollution or explain channel-count sensitivity by itself."
    )
    print("\n== trace-level association with channel-count sensitivity ==")
    print(
        "Pearson r(overprediction, one-channel/two-channel normalized-benefit "
        "change), n=13 per prefetcher:"
    )
    for prefetcher in PREFETCHERS:
        data = rows[prefetcher]
        observed = correlation(
            [row["overprediction"] for row in data],
            [row["channel_delta"] for row in data],
        )
        print(f"  {prefetcher:10s} {fmt(observed):>7s}")
    print(
        "These small-sample correlations are descriptive and do not establish "
        "a causal overprediction mechanism."
    )


if __name__ == "__main__":
    main()
