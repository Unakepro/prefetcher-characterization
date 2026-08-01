# Findings

These results cover 13 selected CPU2006 traces and the simulator settings in
this repository. They should not be treated as results for every workload or
every hardware design.

## Main result

Different traces prefer different prefetchers and settings. However, one
fixed choice already gets most of the available performance:

| Comparison | Best fixed choice | Fixed result | Best choice for each trace | Extra gain |
|---|---|---:|---:|---:|
| Basis A: common L2 position | Bingo | 1.2468x | 1.2914x | 3.58% |
| Basis B: released configurations | IPCP | 1.3262x | 1.3375x | 0.85% |

The last two columns use results after all traces have been measured. They
show how much room there is for per-trace selection, not a ready-to-use
selection system.

## Default prefetchers

Average speedups over no prefetching are:

| Prefetcher | Position used here | Speedup |
|---|---|---:|
| IPCP | L1D+L2 | 1.3262x |
| Bingo | L2 | 1.2468x |
| SPP-dev2 | L2 | 1.2408x |
| Streamer | L2 | 1.2382x |
| Stride | L2 | 1.1168x |

There are two ways to read this table:

- Basis A compares Stride, Streamer, SPP-dev2, and Bingo in the same L2
  prefetcher position. Bingo is the best fixed choice.
- Basis B also includes IPCP in its released L1D+L2 setup. IPCP is the best
  fixed released configuration.

Basis A uses the same cache position, but the prefetchers do not have the same
storage or hardware cost. Basis B does not use the same position. The table is
therefore a performance comparison, not an area or cost comparison.

Many trace-level differences are small. In Basis A, seven of 13 winning
margins are below 1%. With a 1% margin rule, only six traces have a clear
winner: Bingo wins three, Streamer two, and SPP-dev2 one. The other seven are
near-ties. Basis B has four near-ties.

### IPCP placement

The saved IPCP L1-only setup gets most of the full IPCP gain. Its L2-only
setup gives almost no gain. In this Pythia implementation, the L2 part expects
information created at L1, so it is not directly comparable to the standalone
L2 prefetchers. This is a property of this implementation, not a general rule
about every possible IPCP design.

## Parameter tuning

Phase 6 changed one parameter at a time. Phase 7 then reused the Stride and
Streamer degree results and tested combinations of the two SPP thresholds.

The table below shows how far results moved between the lowest and highest
tested values for each trace:

| Parameter | Average range | Largest range |
|---|---:|---:|
| Stride degree | 27.3 points | 91.0 points |
| Streamer degree | 17.9 points | 70.8 points |
| SPP fill threshold | 17.2 points | 67.0 points |
| SPP prefetch threshold | 16.1 points | 44.8 points |
| Bingo PHT entries | 2.4 points | 9.1 points |
| Bingo L2 threshold | 0.9 points | 4.7 points |

Degree and SPP thresholds matter much more than the two tested Bingo
parameters. The best value also changes between traces. More aggressive
settings are not always better.

### Fixed setting versus a setting chosen for each trace

| Settings tested | Best fixed setting | Fixed result | Per-trace result | Extra gain |
|---|---|---:|---:|---:|
| Stride degree | 8 | 1.2182x | 1.2312x | 1.07% |
| Streamer degree | 5 | 1.2382x | 1.2630x | 2.00% |
| SPP threshold grid | pf20/fill50 | 1.2858x | 1.2886x | 0.22% |

Streamer degree 5 is the measured default and must be included. Degree 8 was
not tested. The SPP grid is the only experiment here that changed two settings
together. The results do not tell us which combination of prefetcher, degree,
channel count, and LLC size would be best because that full combination was
not tested.

### Bingo PHT size

| PHT entries | Speedup |
|---:|---:|
| 1024 | 1.2442x |
| 2048 | 1.2465x |
| 4096, default | 1.2468x |
| 8192 | 1.2505x |

Changing from 4096 to 1024 entries reduces the result by only about 0.21%.
This only says that the tested PHT can be smaller with little performance
loss. It does not say that the complete Bingo prefetcher becomes four times
smaller.

## Memory channels

The next table shows how each prefetcher's gain changes when the system has
one memory channel instead of two. Each result uses a no-prefetch baseline
with the same channel count.

| Prefetcher | Change with one channel |
|---|---:|
| Bingo | -4.3% |
| IPCP | -2.4% |
| Streamer | -2.2% |
| SPP-dev2 | -1.7% |
| Stride | -0.7% |

Bingo loses the most average benefit in the one-channel setup. This alone
does not prove that Bingo uses the most bandwidth. Changing the channel count
also changes address mapping and how many requests the memory system can work
on at once.

The saved counters show extra memory transactions and LLC read
overprediction, but neither one clearly moves with the one-channel slowdown.
Bingo's high average traffic is also heavily affected by one trace, `mcf`.
The current data therefore does not show that overprediction caused the
channel-count result.

## LLC size

Each value below is compared with no prefetching at the same LLC size:

| Prefetcher | 1 MiB | 2 MiB | 4 MiB |
|---|---:|---:|---:|
| Stride | 1.1186x | 1.1168x | 1.1142x |
| Streamer | 1.2405x | 1.2382x | 1.2352x |
| SPP-dev2 | 1.2478x | 1.2408x | 1.2227x |
| Bingo | 1.2370x | 1.2468x | 1.2572x |
| IPCP | 1.3231x | 1.3262x | 1.3306x |

Stride, Streamer, and SPP-dev2 lose a little normalized benefit as the LLC
gets larger. Bingo and IPCP gain a little. Bingo's overall increase is driven
mainly by `mcf` and `lbm`; several other traces move in the opposite direction.

This shows that LLC size interacts with prefetching. It does not prove that a
larger LLC fixes cache pollution because the experiment did not count
prefetch-caused evictions and later demand refetches.

Without prefetching, only `mcf` and `soplex` change by more than 10% between
the 1 MiB and 4 MiB setups. That statement applies only to these 13 traces and
this chosen 10% boundary.
