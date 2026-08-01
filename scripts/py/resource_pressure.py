#!/usr/bin/env python3
"""Relate channel-count sensitivity to observed off-chip request pressure.

The Pythia outputs expose serviced DRAM row-buffer hits/misses and data-bus
congestion by channel. Summing those counters gives total DRAM transactions,
not an origin-separated overprediction metric. This analysis therefore reports
net traffic and correlation without assigning a pollution/overprediction cause.
"""

import argparse
import glob
import math
import os
import re


PREFETCHERS = ("stride", "streamer", "spp_dev2", "bingo", "ipcp")


def core_counter(text, key):
    match = re.search(
        rf"^Core_0_{re.escape(key)}[ \t]+([0-9.]+)[ \t]*$",
        text,
        re.MULTILINE,
    )
    if not match:
        return None
    value = match.group(1)
    return float(value) if "." in value else int(value)


def channel_sum(text, key):
    values = re.findall(
        rf"^Channel_[0-9]+_{re.escape(key)}[ \t]+([0-9]+)[ \t]*$",
        text,
        re.MULTILINE,
    )
    return sum(int(value) for value in values) if values else None


def parse(path):
    with open(path, encoding="utf-8", errors="replace") as source:
        text = source.read()
    instructions = core_counter(text, "instructions")
    ipc = core_counter(text, "IPC")
    components = [
        channel_sum(text, "RQ_row_buffer_hit"),
        channel_sum(text, "RQ_row_buffer_miss"),
        channel_sum(text, "WQ_row_buffer_hit"),
        channel_sum(text, "WQ_row_buffer_miss"),
    ]
    congested = channel_sum(text, "dbus_congested")
    if (
        instructions in (None, 0)
        or ipc is None
        or any(value is None for value in components)
        or congested is None
    ):
        raise ValueError(f"missing IPC/instruction/DRAM counters in {path}")
    transactions = sum(components)
    return {
        "ipc": ipc,
        "dram_bpki": 1000.0 * transactions / instructions,
        "dbus_congested_pki": 1000.0 * congested / instructions,
    }


def pearson(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        return float("nan")
    xmean = sum(xs) / len(xs)
    ymean = sum(ys) / len(ys)
    numerator = sum((x - xmean) * (y - ymean) for x, y in zip(xs, ys))
    xnorm = math.sqrt(sum((x - xmean) ** 2 for x in xs))
    ynorm = math.sqrt(sum((y - ymean) ** 2 for y in ys))
    return numerator / (xnorm * ynorm) if xnorm and ynorm else float("nan")


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Report net DRAM-transaction pressure alongside paired one/two-"
            "channel prefetch-benefit sensitivity."
        )
    )
    parser.add_argument("--results", required=True)
    args = parser.parse_args()

    traces = sorted(
        os.path.basename(path).split("__")[0]
        for path in glob.glob(f"{args.results}/*__nopref.out")
    )
    if not traces:
        raise SystemExit(f"no default no-prefetch outputs in {args.results}")

    print("== observed resource pressure (serviced DRAM transactions) ==")
    print(
        "extra DRAM BPKI is candidate total minus matched nopref total; it "
        "does not separate useful prefetches, overprediction, or pollution."
    )
    print(
        f"{'trace':12s} {'pref':10s} {'benefit delta':>10s} "
        f"{'extra1 BPKI':>12s} {'extra2 BPKI':>12s} {'dbus1 delta/ki':>12s}"
    )

    summaries = {prefetcher: [] for prefetcher in PREFETCHERS}
    for trace in traces:
        baseline_1 = parse(f"{args.results}/{trace}__nopref.out")
        baseline_2 = parse(f"{args.results}/{trace}__nopref_2ch.out")
        for prefetcher in PREFETCHERS:
            candidate_1 = parse(f"{args.results}/{trace}__{prefetcher}.out")
            candidate_2 = parse(f"{args.results}/{trace}__{prefetcher}_2ch.out")
            speedup_1 = candidate_1["ipc"] / baseline_1["ipc"]
            speedup_2 = candidate_2["ipc"] / baseline_2["ipc"]
            benefit_delta = speedup_1 / speedup_2 - 1
            extra_1 = candidate_1["dram_bpki"] - baseline_1["dram_bpki"]
            extra_2 = candidate_2["dram_bpki"] - baseline_2["dram_bpki"]
            congestion_delta = (
                candidate_1["dbus_congested_pki"]
                - baseline_1["dbus_congested_pki"]
            )
            summaries[prefetcher].append(
                (benefit_delta, extra_1, extra_2, congestion_delta)
            )
            print(
                f"{trace:12s} {prefetcher:10s} {benefit_delta:>+9.1%} "
                f"{extra_1:>12.3f} {extra_2:>12.3f} "
                f"{congestion_delta:>12.3f}"
            )

    print("\n== arithmetic means and trace-level correlations ==")
    print(
        f"{'pref':10s} {'benefit delta':>10s} {'extra1':>10s} {'extra2':>10s} "
        f"{'corr(delta,extra1)':>16s} {'corr(delta,cong1)':>15s}"
    )
    for prefetcher, rows in summaries.items():
        deltas = [row[0] for row in rows]
        extra_1 = [row[1] for row in rows]
        extra_2 = [row[2] for row in rows]
        congestion = [row[3] for row in rows]
        print(
            f"{prefetcher:10s} {sum(deltas)/len(rows):>+9.1%} "
            f"{sum(extra_1)/len(rows):>10.3f} "
            f"{sum(extra_2)/len(rows):>10.3f} "
            f"{pearson(deltas, extra_1):>16.3f} "
            f"{pearson(deltas, congestion):>15.3f}"
        )


if __name__ == "__main__":
    main()
