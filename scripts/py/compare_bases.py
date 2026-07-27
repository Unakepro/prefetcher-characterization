#!/usr/bin/env python3

import os, re, glob, argparse, math

def grab(t,k):
    m=re.search(rf"^Core_0_{re.escape(k)}\s+([0-9.]+)\s*$",t,re.M)
    return (float(m.group(1)) if m and "." in m.group(1) else int(m.group(1)) if m else None)
def ipc(p):
    if not os.path.exists(p): return None
    return grab(open(p).read(),"IPC")
def gmean(xs):
    xs=[x for x in xs if x and x>0]
    return math.exp(sum(map(math.log,xs))/len(xs)) if xs else float("nan")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--results",required=True); a=ap.parse_args()
    R=a.results
    traces=sorted(os.path.basename(p).split("__")[0] for p in glob.glob(f"{R}/*__nopref.out"))
    if not traces: raise SystemExit(f"no *__nopref.out in {R}")
    def sp(t,pref):
        b=ipc(f"{R}/{t}__nopref.out"); p=ipc(f"{R}/{t}__{pref}.out")
        return (p/b) if (b and p) else None

    single=["bingo","spp_dev2","streamer","stride"]      # genuinely single-slot
    def basis(prefs):
        tbl={t:{p:sp(t,p) for p in prefs} for t in traces}
        win={t:max(prefs,key=lambda p:(tbl[t][p] or -1)) for t in traces}
        geo={p:gmean([tbl[t][p] for t in traces]) for p in prefs}
        bf=max(geo,key=lambda p:geo[p])
        orc={t:max((tbl[t][p] or -1) for p in prefs) for t in traces}
        go=gmean([orc[t] for t in traces]); gap=go/geo[bf]-1
        return tbl,win,geo,bf,go,gap,prefs

    A=basis(single)              # IPCP excluded
    B=basis(single+["ipcp"])     # native

    for label,(tbl,win,geo,bf,go,gap,prefs) in (("A (single-slot, IPCP excluded)",A),
                                                ("B (native, IPCP@L1D+L2)",B)):
        print(f"\n===== BASIS {label} =====")
        print(f"{'trace':12s} "+" ".join(f"{p:>11s}" for p in prefs)+"   winner")
        for t in traces:
            print(f"{t:12s} "+" ".join(f"{(tbl[t][p] or float('nan')):11.4f}" for p in prefs)+f"   {win[t]}")
        print("-- geomean --")
        for p in sorted(prefs,key=lambda p:-geo[p]):
            print(f"  {p:12s} {geo[p]:.4f}"+("  <- best fixed" if p==bf else ""))
        print(f"  ORACLE       {go:.4f}")
        print(f"  ORACLE-GAP   {gap*100:+.2f}%  (over best fixed '{bf}')")

    print(f"\n===== A vs B =====")
    print(f"  gap A (single-slot, honest): {A[5]*100:+.2f}%")
    print(f"  gap B (native)             : {B[5]*100:+.2f}%")

    # IPCP per-level decomposition
    print("\n===== IPCP per-level decomposition (why it can't be single-slot) =====")
    print(f"{'trace':12s} {'L1only':>8s} {'L2only':>8s} {'both':>8s}")
    for t in traces:
        l1=sp(t,"ipcp_L1only"); l2=sp(t,"ipcp_L2only"); bo=sp(t,"ipcp")
        f=lambda x:f"{x:8.4f}" if x else "     n/a"
        print(f"{t:12s} {f(l1)} {f(l2)} {f(bo)}")
    print("  (L2only ~1.0 everywhere = inert without L1 classifier -> IPCP inseparable)")

if __name__=="__main__": main()
