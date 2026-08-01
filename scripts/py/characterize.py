#!/usr/bin/env python3
"""Report per-axis selection gains for the completed characterization sweeps.

Each result changes one analysis axis at a time. The output is therefore not
a joint best-case selection over prefetcher, placement, tuning, channel count,
and cache capacity.
"""

import argparse
import glob
import math
import os
import re
from collections import Counter


BASIS_A = ["bingo", "spp_dev2", "streamer", "stride"]
BASIS_B = BASIS_A + ["ipcp"]


def grab(text, key):
    match = re.search(
        rf"^Core_0_{re.escape(key)}\s+([0-9.]+)\s*$", text, re.MULTILINE
    )
    if not match:
        return None
    value = match.group(1)
    return float(value) if "." in value else int(value)


def ipc(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as stream:
        return grab(stream.read(), "IPC")


def gmean(values):
    values = list(values)
    if not values or any(value is None or value <= 0 for value in values):
        return float("nan")
    return math.exp(sum(math.log(value) for value in values) / len(values))


def speedup(results, trace, run):
    baseline = ipc(f"{results}/{trace}__nopref.out")
    candidate = ipc(f"{results}/{trace}__{run}.out")
    return candidate / baseline if baseline and candidate else None


def selection_summary(results, traces, options):
    """Return a one-axis selection summary over a complete trace cohort."""
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
        preview = ", ".join(missing[:8])
        suffix = " ..." if len(missing) > 8 else ""
        raise ValueError(
            f"incomplete comparison ({len(missing)} missing trace/run pairs): "
            f"{preview}{suffix}"
        )

    fixed_geomeans = {
        option: gmean(table[trace][option] for trace in traces)
        for option in options
    }
    best_fixed = max(options, key=lambda option: fixed_geomeans[option])
    best_per_trace = gmean(max(table[trace].values()) for trace in traces)

    winners = Counter()
    margins = []
    for trace in traces:
        ranked = sorted(
            options, key=lambda option: table[trace][option], reverse=True
        )
        winner, runner_up = ranked[:2]
        relative_margin = table[trace][winner] / table[trace][runner_up] - 1
        winners[winner] += 1
        margins.append((trace, winner, runner_up, relative_margin))

    return {
        "best_fixed": best_fixed,
        "fixed_geomean": fixed_geomeans[best_fixed],
        "best_per_trace_geomean": best_per_trace,
        "selection_gain": best_per_trace / fixed_geomeans[best_fixed] - 1,
        "winners": dict(winners),
        "margins": margins,
    }


def print_prefetcher_selection(label, summary, tie_threshold):
    print(f"\n[{label}]")
    print(
        f"  best fixed: {summary['best_fixed']} ({summary['fixed_geomean']:.4f})"
        f"  best per trace {summary['best_per_trace_geomean']:.4f}"
        f"  selection gain {summary['selection_gain']*100:+.2f}%"
    )
    print(f"  raw argmax counts: {summary['winners']}")

    near_ties = [
        row for row in summary["margins"] if row[3] <= tie_threshold
    ]
    decisive = Counter(
        winner
        for _, winner, _, margin in summary["margins"]
        if margin > tie_threshold
    )
    print(
        f"  decisive argmax counts (winner margin > {tie_threshold:.2%}): "
        f"{dict(decisive)}"
    )
    if near_ties:
        details = ", ".join(
            f"{trace} {winner}/{runner_up} {margin:.2%}"
            for trace, winner, runner_up, margin in near_ties
        )
        print(
            f"  near-ties (winner margin <= {tie_threshold:.2%}): "
            f"{len(near_ties)}/{len(summary['margins'])}"
        )
        print(f"    {details}")
    else:
        print(
            f"  near-ties (winner margin <= {tie_threshold:.2%}): "
            f"0/{len(summary['margins'])}"
        )


def response_cohort(results, traces, threshold):
    """Select traces with a sufficiently large default Basis-A response."""
    selected = []
    for trace in traces:
        values = [speedup(results, trace, option) for option in BASIS_A]
        if any(value is None for value in values):
            raise ValueError(f"incomplete Basis-A data while classifying {trace}")
        if max(values) >= threshold:
            selected.append(trace)
    return selected


def print_degree_selection(results, traces, prefetcher, default_degree):
    values = set()
    pattern = f"{results}/*__{prefetcher}__{prefetcher}_pref_degree_*.out"
    for path in glob.glob(pattern):
        match = re.search(rf"{prefetcher}_pref_degree_(\d+)\.out$", path)
        if match:
            values.add(match.group(1))

    labels = [f"default({default_degree})"] + sorted(values, key=int)
    table = {trace: {} for trace in traces}
    for trace in traces:
        table[trace][labels[0]] = speedup(results, trace, prefetcher)
        for value in sorted(values, key=int):
            table[trace][value] = speedup(
                results, trace, f"{prefetcher}__{prefetcher}_pref_degree_{value}"
            )

    complete = [
        trace
        for trace in traces
        if all(table[trace][label] is not None for label in labels)
    ]
    if len(complete) != len(traces):
        raise ValueError(
            f"incomplete {prefetcher}-degree grid: "
            f"{len(complete)}/{len(traces)} traces are complete"
        )

    fixed_geomeans = {
        label: gmean(table[trace][label] for trace in traces)
        for label in labels
    }
    best_fixed = max(labels, key=lambda label: fixed_geomeans[label])
    best_per_trace = gmean(max(table[trace].values()) for trace in traces)
    print(f"\n[degree - {prefetcher}]")
    print(
        f"  best fixed degree: {best_fixed} ({fixed_geomeans[best_fixed]:.4f})"
        f"  best per trace {best_per_trace:.4f}"
        f"  selection gain {best_per_trace/fixed_geomeans[best_fixed]-1:+.2%}"
    )


def print_storage_curve(results, traces):
    print("\n" + "=" * 70)
    print("BINGO PHT-ENTRY CURVE (pht_size; not whole-prefetcher storage)")
    print("=" * 70)
    sizes = set()
    for path in glob.glob(f"{results}/*__bingo__bingo_pht_size_*.out"):
        match = re.search(r"bingo_pht_size_(\d+)\.out$", path)
        if match:
            sizes.add(match.group(1))
    if not sizes:
        print("  no pht_size runs found")
        return

    print(f"  {'pht_size':>10s} {'geomean speedup':>16s}")
    rows = [("4096(def)", gmean(speedup(results, trace, "bingo") for trace in traces))]
    for size in sorted(sizes, key=int):
        rows.append(
            (
                size,
                gmean(
                    speedup(results, trace, f"bingo__bingo_pht_size_{size}")
                    for trace in traces
                ),
            )
        )
    for size, geo in sorted(rows, key=lambda row: int(row[0].split("(")[0])):
        print(f"  {size:>10s} {geo:>16.4f}")
    print(
        "  This local curve changes PHT entry count only; it does not quantify "
        "total storage, area, or access cost."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Report separate per-axis selection gains."
    )
    parser.add_argument("--results", required=True)
    parser.add_argument(
        "--response-threshold",
        type=float,
        default=1.20,
        help=(
            "include a trace in the response cohort when its best default Basis-A "
            "speedup is at least this ratio (default: 1.20)"
        ),
    )
    parser.add_argument(
        "--tie-threshold",
        type=float,
        default=0.01,
        help=(
            "classify a per-trace winner as a near-tie when its relative margin "
            "over the runner-up is at most this ratio (default: 0.01)"
        ),
    )
    args = parser.parse_args()
    if args.response_threshold <= 0:
        parser.error("--response-threshold must be positive")
    if args.tie_threshold < 0:
        parser.error("--tie-threshold must be non-negative")

    results = args.results
    traces = sorted(
        os.path.basename(path).split("__")[0]
        for path in glob.glob(f"{results}/*__nopref.out")
    )
    if not traces:
        raise SystemExit(f"no default no-prefetch outputs found in {results}")

    print("=" * 70)
    print("SELECTION GAINS (ONE AXIS AT A TIME)")
    print("These are not a joint best-case selection across all experimental axes.")
    print("=" * 70)

    summaries = (
        (
            "prefetcher choice - Basis A (common L2 placement; IPCP ineligible)",
            selection_summary(results, traces, BASIS_A),
        ),
        (
            "prefetcher choice - Basis B (released/native placements)",
            selection_summary(results, traces, BASIS_B),
        ),
    )
    for label, summary in summaries:
        print_prefetcher_selection(label, summary, args.tie_threshold)

    print_degree_selection(results, traces, "stride", default_degree="2")
    print_degree_selection(results, traces, "streamer", default_degree="5")

    combinations = set()
    for path in glob.glob(f"{results}/*__spp_dev2__pf*_fill*.out"):
        match = re.search(r"(pf\d+_fill\d+)\.out$", path)
        if match:
            combinations.add(match.group(1))
    if combinations:
        options = [f"spp_dev2__{combo}" for combo in sorted(combinations)]
        summary = selection_summary(results, traces, options)
        print("\n[SPP pf x fill grid]")
        print(
            f"  best fixed: {summary['best_fixed'].split('__')[1]}"
            f" ({summary['fixed_geomean']:.4f})"
            f"  best per trace {summary['best_per_trace_geomean']:.4f}"
            f"  selection gain {summary['selection_gain']*100:+.2f}%"
        )

    cohort = response_cohort(results, traces, args.response_threshold)
    print("\n" + "=" * 70)
    print("SELECTION GAIN FOR DEFAULT-PREFETCHER-RESPONSE COHORT")
    print(
        "criterion: best default Basis-A speedup >= "
        f"{args.response_threshold:.3f}x"
    )
    print(f"cohort ({len(cohort)}/{len(traces)}): {', '.join(cohort) or '(empty)'}")
    print("=" * 70)
    if cohort:
        summary = selection_summary(results, cohort, BASIS_A)
        print(
            f"  Basis A: best {summary['best_fixed']} "
            f"({summary['fixed_geomean']:.4f})"
            f" best per trace {summary['best_per_trace_geomean']:.4f}"
            f" selection gain {summary['selection_gain']*100:+.2f}%"
        )
    else:
        print("  no trace meets the response criterion")

    print_storage_curve(results, traces)


if __name__ == "__main__":
    main()
