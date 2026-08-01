#!/usr/bin/env python3
"""Measure paired prefetch-benefit sensitivity to DRAM channel count.

This analysis compares each prefetcher's speedup over a no-prefetch baseline
at the *same* channel count.  It does not measure bandwidth consumption:
changing the number of channels also changes address mapping and available
memory-level parallelism.
"""

import argparse
import glob
import os
import re

def grab(t, k):
    m = re.search(rf"^Core_0_{re.escape(k)}\s+([0-9.]+)\s*$", t, re.M)
    return (float(m.group(1)) if m and "." in m.group(1)
            else int(m.group(1)) if m else None)
def ipc(p):
    if not os.path.exists(p): return None
    return grab(open(p).read(), "IPC")
def main():
    ap=argparse.ArgumentParser(
        description="Compare paired prefetch speedups at one and two DRAM channels."
    )
    ap.add_argument("--results", required=True)
    a=ap.parse_args()
    R=a.results
    traces=sorted(os.path.basename(p).split("__")[0] for p in glob.glob(f"{R}/*__nopref.out"))
    if not traces:
        raise SystemExit(f"no default no-prefetch outputs in {R}")
    prefs=["stride","streamer","spp_dev2","bingo","ipcp"]

    def sp(t,pref,two):
        suf="_2ch" if two else ""
        base=ipc(f"{R}/{t}__nopref{suf}.out")
        p=ipc(f"{R}/{t}__{pref}{suf}.out")
        return (p/base) if (base and p) else None

    print("== paired prefetch speedup by DRAM channel count ==")
    print(f"{'trace':12s} {'pref':10s} {'2ch':>8s} {'1ch':>8s} {'rel_delta':>10s}")
    rows={p:[] for p in prefs}
    for t in traces:
        for p in prefs:
            s2=sp(t,p,True); s1=sp(t,p,False)
            if not (s1 and s2):
                raise ValueError(f"missing paired one/two-channel result for {t}/{p}")
            delta=s1/s2-1
            rows[p].append(delta)
            print(f"{t:12s} {p:10s} {s2:8.4f} {s1:8.4f} {delta*100:+9.1f}%")
    print("\n== arithmetic-mean relative speedup change (2 channels -> 1 channel) ==")
    print("   negative = lower normalized prefetch benefit with one channel")
    print("   this is channel-count sensitivity, not a measure of traffic or bandwidth demand")
    for p in sorted(prefs, key=lambda p: (sum(rows[p])/len(rows[p])) if rows[p] else 0):
        if rows[p]:
            m=sum(rows[p])/len(rows[p])
            print(f"  {p:10s} {m*100:+7.1f}%   (n={len(rows[p])})")

if __name__=="__main__":
    main()
