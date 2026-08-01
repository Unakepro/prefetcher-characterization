#!/usr/bin/env python3

import argparse
import glob
import math
import os
import re

SIZES=[("1MB","_1MB"),("2MB",""),("4MB","_4MB")]
PREFS=["stride","streamer","spp_dev2","bingo","ipcp"]

def grab(t,k):
    m=re.search(rf"^Core_0_{re.escape(k)}\s+([0-9.]+)\s*$",t,re.M)
    return (float(m.group(1)) if m and "." in m.group(1) else int(m.group(1)) if m else None)
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
    return math.exp(sum(map(math.log, values))/len(values))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--results",required=True)
    ap.add_argument(
        "--sensitivity-threshold",
        type=float,
        default=0.10,
        help="absolute 1-to-4 MiB no-prefetch IPC change used for classification (default: 0.10)",
    )
    a=ap.parse_args()
    if a.sensitivity_threshold < 0:
        ap.error("--sensitivity-threshold must be nonnegative")
    R=a.results
    traces=sorted(os.path.basename(p).split("__")[0] for p in glob.glob(f"{R}/*__nopref.out"))
    if len(traces) != 13 or len(set(traces)) != 13:
        raise SystemExit(
            f"expected 13 unique default-baseline traces, found {len(set(traces))}"
        )

    # --- prefetch speedup vs LLC size (geomean per pref per size) ---
    print("== geomean prefetch speedup vs LLC size ==")
    print(f"{'pref':10s} {'1MB':>8s} {'2MB':>8s} {'4MB':>8s}   trend")
    for pref in PREFS:
        geos=[]
        for sname,suf in SIZES:
            sp=[]
            for t in traces:
                b=required_ipc(f"{R}/{t}__nopref{suf}.out")
                p=required_ipc(f"{R}/{t}__{pref}{suf}.out")
                sp.append(p/b)
            geos.append(gmean(sp))
        trend="shrinks" if geos[0]>geos[2] else "grows" if geos[0]<geos[2] else "flat"
        print(f"{pref:10s} {geos[0]:8.4f} {geos[1]:8.4f} {geos[2]:8.4f}   {trend} with cache")

    # --- cache-sensitivity per trace (nopref IPC swing 1->4 MB) ---
    print("\n== cache-sensitivity per trace (nopref IPC, 1MB -> 4MB) ==")
    print(f"{'trace':12s} {'1MB':>8s} {'2MB':>8s} {'4MB':>8s} {'swing':>8s}  class")
    for t in traces:
        i1=required_ipc(f"{R}/{t}__nopref_1MB.out")
        i2=required_ipc(f"{R}/{t}__nopref.out")
        i4=required_ipc(f"{R}/{t}__nopref_4MB.out")
        swing=i4/i1-1
        cls=(
            "CACHE-SENSITIVE"
            if abs(swing) >= a.sensitivity_threshold
            else "insensitive"
        )
        print(f"{t:12s} {i1:8.4f} {i2:8.4f} {i4:8.4f} {swing*100:+7.1f}%  {cls}")

if __name__=="__main__":
    main()
