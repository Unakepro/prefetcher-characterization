#!/usr/bin/env python3

import csv, sys, argparse, math
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless (cluster nodes have no display)
import matplotlib.pyplot as plt

def gmean(xs):
    xs = [x for x in xs if x is not None and x > 0]
    return math.exp(sum(math.log(x) for x in xs) / len(xs)) if xs else float("nan")

def load(path):
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            sp = r.get("speedup", "")
            if r["prefetcher"] == "nopref" or sp in ("", None):
                continue
            try:
                rows.append((r["trace"], r["prefetcher"], float(sp)))
            except ValueError:
                continue
    traces = sorted({t for t, _, _ in rows})
    prefs  = sorted({p for _, p, _ in rows})
    M = {(t, p): s for t, p, s in rows}
    return traces, prefs, M

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default="oracle_gap.png")
    a = ap.parse_args()

    traces, prefs, M = load(a.csv)
    if not traces:
        sys.exit("no speedup rows found — is the CSV populated?")

    # oracle = best prefetcher per trace
    oracle = {t: max((M.get((t, p), float("nan")) for p in prefs)) for t in traces}
    oracle_pick = {t: max(prefs, key=lambda p: M.get((t, p), -1)) for t in traces}

    # geomean speedup per fixed prefetcher across traces
    geo = {p: gmean([M.get((t, p)) for t in traces]) for p in prefs}
    best_fixed = max(geo, key=lambda p: geo[p])
    geo_oracle = gmean([oracle[t] for t in traces])
    gap = geo_oracle / geo[best_fixed] - 1.0

    # ---- console summary ----
    print("== per-trace winner ==")
    for t in traces:
        print(f"  {t:12s} {oracle_pick[t]:10s} {oracle[t]:.4f}")
    print("\n== geomean speedup (fixed) ==")
    for p in sorted(prefs, key=lambda p: -geo[p]):
        star = "  <- best fixed" if p == best_fixed else ""
        print(f"  {p:10s} {geo[p]:.4f}{star}")
    print(f"\n  ORACLE geomean   {geo_oracle:.4f}")
    print(f"  ORACLE-GAP       {gap*100:+.2f}%  (headroom over best fixed '{best_fixed}')")

    # ---- plot ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.2),
                                   gridspec_kw={"width_ratios": [3, 1]})
    x = np.arange(len(traces)); w = 0.8 / len(prefs)
    for i, p in enumerate(prefs):
        vals = [M.get((t, p), np.nan) for t in traces]
        ax1.bar(x + i*w - 0.4 + w/2, vals, w, label=p)
    # oracle markers
    ax1.scatter(x, [oracle[t] for t in traces], marker="_", s=600,
                color="black", zorder=5, label="oracle (best/trace)")
    ax1.axhline(1.0, color="grey", ls="--", lw=0.8)
    ax1.set_xticks(x); ax1.set_xticklabels(traces)
    ax1.set_ylabel("speedup vs no-prefetch")
    ax1.set_title("Per-trace speedup by prefetcher (oracle = best per trace)")
    ax1.legend(fontsize=8, ncol=2)

    order = sorted(prefs, key=lambda p: geo[p])
    ax2.barh(range(len(order)), [geo[p] for p in order],
             color=["#c44" if p == best_fixed else "#89a" for p in order])
    ax2.axvline(geo_oracle, color="black", ls="--", lw=1.2)
    ax2.text(geo_oracle, -0.6, f"oracle {geo_oracle:.3f}", fontsize=8, ha="center")
    ax2.set_yticks(range(len(order))); ax2.set_yticklabels(order)
    ax2.set_xlabel("geomean speedup")
    ax2.set_title(f"Oracle-gap: {gap*100:+.1f}%")
    ax2.axvline(1.0, color="grey", ls="--", lw=0.8)

    fig.tight_layout()
    fig.savefig(a.out, dpi=130, metadata={"Software": "Matplotlib"})
    print(f"\n-> wrote {a.out}")

if __name__ == "__main__":
    main()
