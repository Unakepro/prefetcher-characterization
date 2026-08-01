#!/usr/bin/env python3
"""Extract explicitly named prefetch metrics from Pythia/ChampSim output.

``coverage`` is L2 demand-miss reduction, using load + RFO misses rather
than total misses. ``on_time_issue_yield`` and ``fill_utilization`` describe
different pipeline stages; the legacy ``accuracy_*`` aliases are retained for
CSV compatibility.

Native multilevel IPCP is a special case: L2-issued and L2-filled counters can
cover different request origins in this Pythia fork. Do not compare its L2
ratios with standalone L2 prefetchers as though they were an origin-matched
cohort.
"""
import argparse
import csv
import os
import re

LEVEL = "L2C"

def grab(text, key):
    m = re.search(
        rf"^Core_0_{re.escape(key)}[ \t]+([0-9.]+)[ \t]*$",
        text,
        re.MULTILINE,
    )
    if not m: return None
    v = m.group(1)
    return float(v) if "." in v else int(v)

def parse_file(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        t = f.read()
    d = {"instructions": grab(t,"instructions"), "IPC": grab(t,"IPC")}
    for lvl in ("L2C","LLC"):
        for fld in (
            "load_miss",
            "RFO_miss",
            "prefetch_requested",
            "prefetch_dropped",
            "prefetch_issued",
            "prefetch_filled",
            "prefetch_useful",
            "prefetch_useless",
            "prefetch_late",
            "prefetch_miss",
            "total_miss",
        ):
            d[f"{lvl}_{fld}"] = grab(t, f"{lvl}_{fld}")
    for lvl in ("L2C","LLC"):
        lm, rm = d.get(f"{lvl}_load_miss"), d.get(f"{lvl}_RFO_miss")
        d[f"{lvl}_demand_misses"] = (
            lm + rm if lm is not None and rm is not None else None
        )
    return d

def sd(a,b): return (a/b) if (a is not None and b not in (None,0)) else None

def compute(pref, base=None):
    lvl=LEVEL
    instr=pref["instructions"]
    demand=pref[f"{lvl}_demand_misses"]
    if instr in (None, 0) or pref["IPC"] is None or demand is None:
        raise ValueError("run is missing instructions, IPC, or L2 demand-miss counters")

    requested=pref[f"{lvl}_prefetch_requested"]
    dropped=pref[f"{lvl}_prefetch_dropped"]
    useful=pref[f"{lvl}_prefetch_useful"]
    useless=pref[f"{lvl}_prefetch_useless"]
    issued=pref[f"{lvl}_prefetch_issued"]
    filled=pref[f"{lvl}_prefetch_filled"]
    late=pref[f"{lvl}_prefetch_late"]
    on_time=sd(useful,issued)
    fill_utilization=sd(useful,filled)
    prediction_accuracy=sd((useful or 0)+(late or 0),issued)
    late_fraction=sd(late,(useful or 0)+(late or 0))
    row={
         "IPC":pref["IPC"],
         "L2_demand_misses":demand,
         "L2_MPKI_demand":round(1000.0*demand/instr,4),
         "L2_prefetch_requested":requested,
         "L2_prefetch_dropped":dropped,
         "L2_prefetch_issued":issued,
         "L2_prefetch_filled":filled,
         "L2_prefetch_useful":useful,
         "L2_prefetch_useless":useless,
         "L2_prefetch_late":late,
         "prediction_accuracy_issued":round(prediction_accuracy,4)
            if prediction_accuracy is not None else None,
         "on_time_issue_yield":round(on_time,4) if on_time is not None else None,
         "fill_utilization":round(fill_utilization,4)
            if fill_utilization is not None else None,
         # Compatibility aliases; prefer the explicitly named fields above.
         "accuracy_issued":round(on_time,4) if on_time is not None else None,
         "accuracy_filled":round(fill_utilization,4)
            if fill_utilization is not None else None,
         "late_frac":round(late_fraction,5)
            if late_fraction is not None else None,
    }
    if base is not None:
        b=base[f"{lvl}_demand_misses"]
        if base["IPC"] is None or b in (None,0):
            raise ValueError("baseline is missing IPC or L2 demand-miss counters")
        row["speedup"]=round(sd(pref["IPC"],base["IPC"]),4)
        row["coverage"]=round(sd(b-demand,b),4) if b else None
        row["baseline_demand_misses"]=b

        # Pythia/MICRO'21 reports coverage at the LLC using demand-load misses,
        # and overprediction as extra LLC read misses relative to no-prefetch.
        # In this output format LLC read misses are load misses plus prefetch
        # misses; RFO and writeback misses are deliberately excluded.
        base_llc_load=base.get("LLC_load_miss")
        pref_llc_load=pref.get("LLC_load_miss")
        pref_llc_pf_miss=pref.get("LLC_prefetch_miss")
        if (
            base_llc_load not in (None,0)
            and pref_llc_load is not None
            and pref_llc_pf_miss is not None
        ):
            row["pythia_llc_load_coverage"]=round(
                (base_llc_load-pref_llc_load)/base_llc_load,4
            )
            row["pythia_llc_read_overprediction"]=round(
                (
                    pref_llc_load
                    + pref_llc_pf_miss
                    - base_llc_load
                )/base_llc_load,
                4,
            )
        else:
            row["pythia_llc_load_coverage"]=None
            row["pythia_llc_read_overprediction"]=None
    return row

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("run"); ap.add_argument("--baseline")
    ap.add_argument("--trace",default="?"); ap.add_argument("--pref",default="?")
    ap.add_argument("--csv"); a=ap.parse_args()
    pref=parse_file(a.run); base=parse_file(a.baseline) if a.baseline else None
    m=compute(pref,base)
    order=[
        "trace",
        "prefetcher",
        "IPC",
        "speedup",
        "coverage",
        "pythia_llc_load_coverage",
        "pythia_llc_read_overprediction",
        "prediction_accuracy_issued",
        "on_time_issue_yield",
        "fill_utilization",
        "late_frac",
        "accuracy_issued",
        "accuracy_filled",
        "L2_demand_misses",
        "baseline_demand_misses",
        "L2_MPKI_demand",
        "L2_prefetch_requested",
        "L2_prefetch_dropped",
        "L2_prefetch_issued",
        "L2_prefetch_filled",
        "L2_prefetch_useful",
        "L2_prefetch_useless",
        "L2_prefetch_late",
    ]
    m["trace"],m["prefetcher"]=a.trace,a.pref
    row={k:m.get(k) for k in order}
    print(f"\n== {a.trace} / {a.pref} ==")
    for k in order: print(f"  {k:24s} {row[k]}")
    if a.csv:
        new=not os.path.exists(a.csv) or os.path.getsize(a.csv) == 0
        with open(a.csv,"a",newline="") as f:
            w=csv.DictWriter(f,fieldnames=order,lineterminator="\n")
            if new: w.writeheader()
            w.writerow(row)
        print(f"\n-> appended to {a.csv}")

if __name__=="__main__": main()
