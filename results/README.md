# Analysis Files

These files contain the processed results of the experiment.

| File | What it contains |
|---|---|
| [characterization_all.csv](analysis/characterization_all.csv) | All collected results in one table. |
| [characterization_default.csv](analysis/characterization_default.csv) | Default prefetcher results used for the main plots. |
| [characterization_summary.txt](analysis/characterization_summary.txt) | Main results, winners, and gains from choosing per trace. |
| [compare_bases.txt](analysis/compare_bases.txt) | Basis A and Basis B results for every trace. |
| [channel_count.txt](analysis/channel_count.txt) | How results change with one or two memory channels. |
| [llc_size.txt](analysis/llc_size.txt) | How results change with 1, 2, or 4 MiB LLC. |
| [prefetch_diagnostics.txt](analysis/prefetch_diagnostics.txt) | Useful, late, and extra prefetch traffic. |
| [resource_pressure.txt](analysis/resource_pressure.txt) | Extra memory requests and memory-system congestion. |
| [sensitivity.txt](analysis/sensitivity.txt) | How strongly each tested parameter changes performance. |
| [tuning.txt](analysis/tuning.txt) | Best fixed setting and best setting for each trace. |
| [prefix_stability.txt](analysis/prefix_stability.txt) | Whether the main result changes at 50M, 100M, and 150M instructions. |
| [suite_bootstrap.txt](analysis/suite_bootstrap.txt) | How much the result depends on the selected 13 traces. |
| [validation.txt](analysis/validation.txt) | Checks that all expected outputs and CSV rows are present. |
| [selection_gain_basis_A.png](analysis/selection_gain_basis_A.png) | Main plot for prefetchers placed at L2. |
| [selection_gain_basis_B.png](analysis/selection_gain_basis_B.png) | Main plot for the released prefetcher configurations. |
