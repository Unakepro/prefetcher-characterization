#!/usr/bin/env python3
"""Check whether default prefetcher-choice conclusions stabilize within the ROI."""

import argparse
import glob
import math
import os
import re


BASES = {
    "A": ("stride", "streamer", "spp_dev2", "bingo"),
    "B": ("stride", "streamer", "spp_dev2", "bingo", "ipcp"),
}
PREFIXES = (50_000_000, 100_000_000, 150_000_000)
HEARTBEAT = re.compile(
    r"^Heartbeat CPU\s+0 instructions:\s+([0-9]+).*?"
    r"cumulative IPC:\s+([0-9.]+)",
    re.MULTILINE,
)
WARMUP = re.compile(r"^warmup_instructions[ \t]+([0-9]+)[ \t]*$", re.MULTILINE)


def geomean(values):
    values = list(values)
    return math.exp(sum(math.log(value) for value in values) / len(values))


def prefix_ipcs(path):
    with open(path, encoding="utf-8", errors="replace") as source:
        text = source.read()
    marker = text.find("Warmup complete CPU")
    warmup_match = WARMUP.search(text)
    if marker < 0 or not warmup_match:
        raise ValueError("missing warmup marker/configuration in {}".format(path))
    warmup = int(warmup_match.group(1))
    samples = [
        (int(instructions), float(ipc))
        for instructions, ipc in HEARTBEAT.findall(text[marker:])
    ]
    if not samples:
        raise ValueError("missing post-warmup heartbeat IPC in {}".format(path))

    result = {}
    for prefix in PREFIXES:
        target = warmup + prefix
        instructions, ipc = min(samples, key=lambda sample: abs(sample[0] - target))
        if abs(instructions - target) > 10:
            raise ValueError(
                "{} has no heartbeat near {} instructions".format(path, target)
            )
        result[prefix] = ipc
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Recompute default-choice selection gains at ROI prefixes."
    )
    parser.add_argument("--results", required=True)
    args = parser.parse_args()

    traces = sorted(
        os.path.basename(path).split("__")[0]
        for path in glob.glob(os.path.join(args.results, "*__nopref.out"))
    )
    if not traces:
        raise SystemExit("no default no-prefetch outputs in {}".format(args.results))

    required = {"nopref"}
    for candidates in BASES.values():
        required.update(candidates)
    ipc = {}
    for trace in traces:
        for prefetcher in required:
            path = os.path.join(
                args.results, "{}__{}.out".format(trace, prefetcher)
            )
            ipc[trace, prefetcher] = prefix_ipcs(path)

    print("== cumulative-prefix stability of default prefetcher choice ==")
    print(
        "prefix IPC is taken from ChampSim's post-warmup cumulative heartbeat; "
        "this checks within-ROI stability, not phase representativeness."
    )
    print("{:>8s} {:>10s} {:>10s}".format("ROI", "Basis A", "Basis B"))

    winners = {basis: {} for basis in BASES}
    for prefix in PREFIXES:
        selection_gains = {}
        for basis, candidates in BASES.items():
            fixed = {
                candidate: geomean(
                    ipc[trace, candidate][prefix] / ipc[trace, "nopref"][prefix]
                    for trace in traces
                )
                for candidate in candidates
            }
            fixed_winner = max(fixed, key=fixed.get)
            best_per_trace = geomean(
                max(
                    ipc[trace, candidate][prefix]
                    / ipc[trace, "nopref"][prefix]
                    for candidate in candidates
                )
                for trace in traces
            )
            selection_gains[basis] = 100.0 * (
                best_per_trace / fixed[fixed_winner] - 1.0
            )
            winners[basis][prefix] = tuple(
                max(
                    candidates,
                    key=lambda candidate: ipc[trace, candidate][prefix]
                    / ipc[trace, "nopref"][prefix],
                )
                for trace in traces
            )
        print(
            "{:>7d}M {:>9.2f}% {:>9.2f}%".format(
                prefix // 1_000_000,
                selection_gains["A"],
                selection_gains["B"],
            )
        )

    for basis in BASES:
        stable = len(set(winners[basis].values())) == 1
        print(
            "Basis {} per-trace raw argmax vector stable across prefixes: {}".format(
                basis, "yes" if stable else "no"
            )
        )


if __name__ == "__main__":
    main()
