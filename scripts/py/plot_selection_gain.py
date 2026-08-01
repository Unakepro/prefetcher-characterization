#!/usr/bin/env python3

import argparse
import csv
import math
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless (cluster nodes have no display)
import matplotlib.pyplot as plt

BASIS_PREFETCHERS = {
    "A": ["bingo", "spp_dev2", "streamer", "stride"],
    "B": ["bingo", "spp_dev2", "streamer", "stride", "ipcp"],
}
BASIS_LABELS = {
    "A": "same L2 placement",
    "B": "original implementations",
}
COLORS = {
    "bingo": "#4C78A8",
    "spp_dev2": "#F58518",
    "streamer": "#54A24B",
    "stride": "#E45756",
    "ipcp": "#B279A2",
}

def gmean(xs):
    xs = [x for x in xs if x is not None and x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else float("nan")

def load(path, allowed_prefs):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            sp = r.get("speedup", "")
            if r["prefetcher"] not in allowed_prefs or sp in ("", None):
                continue
            try:
                rows.append((r["trace"], r["prefetcher"], float(sp)))
            except ValueError:
                continue
    traces = sorted({t for t, _, _ in rows})
    prefs = [p for p in allowed_prefs if any(row[1] == p for row in rows)]
    M = {(t, p): s for t, p, s in rows}
    missing = [(t, p) for t in traces for p in allowed_prefs if (t, p) not in M]
    if missing:
        preview = ", ".join(f"{t}/{p}" for t, p in missing[:8])
        raise ValueError(
            f"incomplete basis: {len(missing)} missing trace/prefetcher rows "
            f"({preview})"
        )
    return traces, prefs, M

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default="selection_gain.png")
    ap.add_argument(
        "--basis",
        choices=sorted(BASIS_PREFETCHERS),
        default="B",
        help=(
            "A = common L2 placement (IPCP ineligible); "
            "B = released/native placements (default: B)"
        ),
    )
    a = ap.parse_args()

    traces, prefs, M = load(a.csv, BASIS_PREFETCHERS[a.basis])
    if not traces:
        sys.exit("no speedup rows found - is the CSV populated?")

    # Best tested prefetcher selected separately for each trace.
    best_by_trace = {
        t: max((M.get((t, p), float("nan")) for p in prefs))
        for t in traces
    }
    best_pick = {t: max(prefs, key=lambda p: M.get((t, p), -1)) for t in traces}

    # geomean speedup per fixed prefetcher across traces
    geo = {p: gmean([M.get((t, p)) for t in traces]) for p in prefs}
    best_fixed = max(geo, key=lambda p: geo[p])
    best_per_trace_geomean = gmean([best_by_trace[t] for t in traces])
    selection_gain = best_per_trace_geomean / geo[best_fixed] - 1.0

    # ---- console summary ----
    print("== per-trace winner ==")
    for t in traces:
        print(f"  {t:12s} {best_pick[t]:10s} {best_by_trace[t]:.4f}")
    print("\n== geomean speedup (fixed) ==")
    for p in sorted(prefs, key=lambda p: -geo[p]):
        star = "  <- best fixed" if p == best_fixed else ""
        print(f"  {p:10s} {geo[p]:.4f}{star}")
    print(f"\n  BEST-PER-TRACE geomean {best_per_trace_geomean:.4f}")
    print(
        f"  SELECTION GAIN         {selection_gain*100:+.2f}%  "
        f"(over best fixed '{best_fixed}')"
    )

    # ---- plot ----
    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(17.2, 7.2),
        gridspec_kw={"width_ratios": [3.15, 1.25]},
    )
    fig.subplots_adjust(
        left=0.06,
        right=0.975,
        top=0.84,
        bottom=0.23,
        wspace=0.18,
    )
    x = np.arange(len(traces)); w = 0.8 / len(prefs)
    for i, p in enumerate(prefs):
        vals = [M.get((t, p), np.nan) for t in traces]
        ax1.bar(
            x + i*w - 0.4 + w/2,
            vals,
            w,
            label=p,
            color=COLORS[p],
        )
    ax1.axhline(1.0, color="#666666", ls="--", lw=1.0)
    ax1.set_xticks(x)
    ax1.set_xticklabels(traces, rotation=32, ha="right", rotation_mode="anchor")
    ax1.tick_params(axis="x", pad=7)
    ax1.set_ylabel("speedup vs no-prefetch")
    ax1.set_title("Per-trace normalized performance", loc="left", weight="bold")
    ax1.grid(axis="y", color="#E5E5E5", lw=0.8)
    ax1.set_axisbelow(True)
    ax1.legend(fontsize=9, ncol=len(prefs), frameon=False, loc="upper right")
    ax1.set_ylim(0, max(best_by_trace.values()) + 0.16)

    order = sorted(prefs, key=lambda p: geo[p])
    lower = min([1.0] + list(geo.values())) - 0.025
    data_max = max([best_per_trace_geomean] + list(geo.values()))
    upper = data_max + 0.085
    label_x = upper - 0.012
    for position, p in enumerate(order):
        value = geo[p]
        left = min(1.0, value)
        width = abs(value - 1.0)
        ax2.barh(
            position,
            width,
            left=left,
            color=COLORS[p],
            alpha=1.0 if p == best_fixed else 0.72,
        )
        ax2.text(
            label_x,
            position,
            f"{value:.3f}",
            va="center",
            ha="right",
            fontsize=9,
            weight="bold" if p == best_fixed else "normal",
        )
    ax2.axvline(1.0, color="#666666", ls="--", lw=1.0)
    ax2.axvline(best_per_trace_geomean, color="black", ls=":", lw=1.5)
    ax2.set_yticks(range(len(order)))
    ax2.set_yticklabels(order)
    ax2.tick_params(axis="y", pad=6)
    ax2.set_xlabel("geomean speedup")
    ax2.set_title(
        "Suite aggregate\n"
        f"Best per trace: {best_per_trace_geomean:.3f}\n"
        f"Selection gain: {selection_gain*100:.2f}%",
        loc="left",
        weight="bold",
        pad=10,
    )
    ax2.set_xlim(lower, upper)
    ax2.grid(axis="x", color="#E5E5E5", lw=0.8)
    ax2.set_axisbelow(True)

    fig.suptitle(
        f"Basis {a.basis} - {BASIS_LABELS[a.basis]}",
        fontsize=16,
        weight="bold",
        y=0.955,
    )
    fig.text(
        0.5,
        0.025,
        "13 selected SPEC CPU2006 trace windows - matched no-prefetch "
        "baselines - 50M warmup + 150M measured instructions",
        ha="center",
        fontsize=9,
        color="#555555",
    )
    fig.savefig(a.out, dpi=150, facecolor="white")
    print(f"\n-> wrote {a.out}")

if __name__ == "__main__":
    main()
