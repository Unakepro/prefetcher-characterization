#!/usr/bin/env python3
"""parse_champsim.py — strict prefetcher metrics from ChampSim (Pythia fork) output.
demand_misses = L2C_load_miss + L2C_RFO_miss   (NOT total_miss)
coverage = (base_demand - pref_demand)/base_demand   [needs paired no-pref run]
speedup  = IPC_pref / IPC_nopref
accuracy_issued = useful/prefetch_issued   accuracy_filled = useful/prefetch_filled
"""
import re, os, argparse, csv

LEVEL = "L2C"

def grab(text, key):
    m = re.search(rf"^Core_0_{re.escape(key)}\s+([0-9.]+)\s*$", text, re.MULTILINE)
    if not m: return None
    v = m.group(1)
    return float(v) if "." in v else int(v)

def parse_file(path):
    with open(path) as f: t = f.read()
    d = {"instructions": grab(t,"instructions"), "IPC": grab(t,"IPC")}
    for lvl in ("L2C","LLC"):
        for fld in ("load_miss","RFO_miss","prefetch_issued","prefetch_filled",
                    "prefetch_useful","prefetch_late","total_miss"):
            d[f"{lvl}_{fld}"] = grab(t, f"{lvl}_{fld}")
    for lvl in ("L2C","LLC"):
        lm, rm = d.get(f"{lvl}_load_miss"), d.get(f"{lvl}_RFO_miss")
        d[f"{lvl}_demand_misses"] = (lm or 0)+(rm or 0) if lm is not None else None
    return d

def sd(a,b): return (a/b) if (a is not None and b not in (None,0)) else None

def compute(pref, base=None):
    lvl=LEVEL; instr=pref["instructions"]; demand=pref[f"{lvl}_demand_misses"]
    useful=pref[f"{lvl}_prefetch_useful"]; issued=pref[f"{lvl}_prefetch_issued"]
    filled=pref[f"{lvl}_prefetch_filled"]; late=pref[f"{lvl}_prefetch_late"]
    row={"IPC":pref["IPC"],"L2_demand_misses":demand,
         "L2_MPKI_demand":round(sd(1000.0*demand,instr),4) if demand is not None else None,
         "accuracy_issued":round(sd(useful,issued),4) if issued else None,
         "accuracy_filled":round(sd(useful,filled),4) if filled else None,
         "late_frac":round(sd(late,(useful or 0)+(late or 0)),5) if (useful or late) else None}
    if base is not None:
        b=base[f"{lvl}_demand_misses"]
        row["speedup"]=round(sd(pref["IPC"],base["IPC"]),4)
        row["coverage"]=round(sd(b-demand,b),4) if b else None
        row["baseline_demand_misses"]=b
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("run"); ap.add_argument("--baseline")
    ap.add_argument("--trace",default="?"); ap.add_argument("--pref",default="?")
    ap.add_argument("--csv"); a=ap.parse_args()
    pref=parse_file(a.run); base=parse_file(a.baseline) if a.baseline else None
    m=compute(pref,base)
    order=["trace","prefetcher","IPC","speedup","coverage","accuracy_issued",
           "accuracy_filled","L2_demand_misses","baseline_demand_misses",
           "L2_MPKI_demand","late_frac"]
    m["trace"],m["prefetcher"]=a.trace,a.pref
    row={k:m.get(k) for k in order}
    print(f"\n== {a.trace} / {a.pref} ==")
    for k in order: print(f"  {k:24s} {row[k]}")
    if a.csv:
        new=not os.path.exists(a.csv)
        with open(a.csv,"a",newline="") as f:
            w=csv.DictWriter(f,fieldnames=order)
            if new: w.writeheader()
            w.writerow(row)
        print(f"\n-> appended to {a.csv}")

if __name__=="__main__": main()
