#!/usr/bin/env python3
"""Summarize one-factor-at-a-time prefetcher knob sensitivity."""

import argparse
import glob
import os
import re

EXPECTED = {
    "stride_pref_degree": ("stride", ("1", "4", "8", "16")),
    "streamer_pref_degree": ("streamer", ("1", "2", "4", "16")),
    "spp_dev2_pf_threshold": ("spp_dev2", ("20", "60", "80")),
    "spp_dev2_fill_threshold": ("spp_dev2", ("50", "70", "100")),
    "bingo_l2c_thresh": ("bingo", ("0p5", "0p65", "0p95")),
    "bingo_pht_size": ("bingo", ("1024", "2048", "8192")),
}


def grab(text, key):
    match = re.search(
        rf"^Core_0_{re.escape(key)}\s+([0-9.]+)\s*$", text, re.M
    )
    if not match:
        return None
    return float(match.group(1))


def required_ipc(path):
    if not os.path.exists(path):
        raise SystemExit(f"missing required output: {path}")
    with open(path) as source:
        value = grab(source.read(), "IPC")
    if value is None or value <= 0:
        raise SystemExit(f"invalid or missing IPC in required output: {path}")
    return value


def setting_key(value):
    if value == "default":
        return (0, 0.0)
    return (1, float(value.replace("p", ".")))


def main():
    ap=argparse.ArgumentParser(
        description="Report max-minus-min speedup spans for Phase-6 knob sweeps."
    )
    ap.add_argument("--results", required=True)
    ap.add_argument(
        "--tune-threshold-pp",
        type=float,
        default=2.0,
        help="mean speedup span, in percentage points, at which a knob is marked for tuning (default: 2.0)",
    )
    a=ap.parse_args()
    if a.tune_threshold_pp < 0:
        ap.error("--tune-threshold-pp must be nonnegative")
    R=a.results

    traces = sorted(
        os.path.basename(path).split("__", 1)[0]
        for path in glob.glob(f"{R}/*__nopref.out")
    )
    if len(traces) != 13 or len(set(traces)) != 13:
        raise SystemExit(
            f"expected 13 unique default-baseline traces, found {len(set(traces))}"
        )

    # knob -> trace -> setting -> speedup. Every expected Phase-6 point and
    # Phase-3 default is required; a partial sweep must never look conclusive.
    data = {}
    for knob, (pref, values) in EXPECTED.items():
        data[knob] = {}
        for trace in traces:
            baseline = required_ipc(f"{R}/{trace}__nopref.out")
            settings = {
                value: required_ipc(
                    f"{R}/{trace}__{pref}__{knob}_{value}.out"
                ) / baseline
                for value in values
            }
            settings["default"] = (
                required_ipc(f"{R}/{trace}__{pref}.out") / baseline
            )
            data[knob][trace] = settings

    print(f"{'knob':26s} {'pref':9s} {'mean span':>12s} {'max span':>11s}  verdict")
    print(f"{'':26s} {'':9s} {'(pp)':>12s} {'(pp)':>11s}")
    print("-"*78)
    rows=[]
    for knob in sorted(data):
        spreads = [
            max(values.values()) - min(values.values())
            for values in data[knob].values()
        ]
        mean_sp=sum(spreads)/len(spreads); max_sp=max(spreads)
        verdict=("TUNE  (moves perf)"
                 if mean_sp*100 >= a.tune_threshold_pp
                 else "freeze (flat)")
        rows.append((mean_sp,knob,EXPECTED[knob][0],max_sp,verdict))
    for mean_sp,knob,pref,max_sp,verdict in sorted(rows,reverse=True):
        print(f"{knob:26s} {pref:9s} {mean_sp*100:>10.1f}pp  {max_sp*100:>9.1f}pp  {verdict}")
    print("\nspan = (maximum speedup - minimum speedup) x 100 percentage points;")
    print("it is not a relative percent change between the endpoint configurations.")

    # per-trace detail for the top knob
    top=sorted(rows,reverse=True)[0][1]
    print(f"\n== per-trace speedup across '{top}' values ==")
    tvals=data[top]
    allv=sorted({v for tr in tvals.values() for v in tr},
                key=setting_key)
    print(f"{'trace':12s} "+" ".join(f"{v:>8s}" for v in allv))
    for tr in sorted(tvals):
        print(f"{tr:12s} "+" ".join(f"{tvals[tr].get(v,float('nan')):8.4f}" for v in allv))

if __name__=="__main__":
    main()
