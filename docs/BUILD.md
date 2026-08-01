# Build and Run Guide

Choose the section that matches what you want to do:

| Goal | Start with | Slurm required? |
|---|---|---|
| Check that the project works | Steps 1-4 | No |
| Run the complete 780 simulations | Steps 1-5 | Yes |
| Recreate reports from existing `.out` files | Step 6 | No |

The derived CSV files, text reports, and plots are included in the repository.
The 780 raw simulator outputs are ignored by Git and must be generated or
restored separately before running the complete analysis again.

## 1. Install the required tools

The simulator build and full experiment are intended for Linux. Required
tools:

- Git, CMake, Make, Perl, and curl;
- a C/C++ compiler toolchain;
- Bash;
- Python 3.8 or newer;
- Slurm commands `sbatch` and `squeue` for the complete experiment.

Run every command below from the repository root.

## 2. Build Pythia and the simulator variants

```bash
BUILD_JOBS=4 ./setup/bootstrap_pythia.sh
```

`BUILD_JOBS` is optional and defaults to 2. The script:

1. clones Pythia into `Pythia/`;
2. checks out the Pythia commit recorded in `setup/versions.env`;
3. clones and builds the pinned libbf commit;
4. builds the four simulator variants used by the experiment.

The resulting executables are:

```text
Pythia/bin/perceptron-multi-multi-no-ship-1core
Pythia/bin/perceptron-multi-multi-no-ship-1core-2ch
Pythia/bin/perceptron-multi-multi-no-ship-1core-1MB
Pythia/bin/perceptron-multi-multi-no-ship-1core-4MB
```

They represent the default system, the two-channel system, the 1 MiB LLC
system, and the 4 MiB LLC system.

The saved July 2026 outputs contain the simulator configuration, but not the
original source commit, compiler flags, or binary hashes. The exact historical
binary therefore cannot be reconstructed. The commits in
`setup/versions.env` define the reference build for a new run. New full runs
record commits, tool versions, binary hashes, and job settings in
`results/analysis/provenance.txt`.

## 3. Download and verify the traces

```bash
./setup/fetch_traces.sh
```

The script downloads the 13 files listed in `config/traces.csv`, stores them
in `traces/`, and checks their MD5 values.

To verify files that are already present without downloading anything:

```bash
./setup/fetch_traces.sh --verify-only
```

Do not replace these files with a different region from the same benchmark.
The exact filenames are part of the experiment definition.

## 4. Run a short local check

```bash
./scripts/run_debug.sh
```

This command runs one short trace with no prefetching and with all five tested
prefetchers. It checks that:

- the default simulator starts;
- the trace can be read;
- each prefetcher configuration runs;
- `parse_champsim.py` can create a CSV file.

The outputs are written to `results/debug/`. The default check uses one
million warmup and one million measured instructions, so these numbers are
not part of the reported experiment.

Useful overrides:

```bash
TRACE=/path/to/trace.xz \
TRACE_NAME=my_trace \
WARMUP=1000000 \
SIM=1000000 \
  ./scripts/run_debug.sh
```

## 5. Run the complete experiment on Slurm

The full experiment contains these arrays:

| Phase | Purpose | Jobs |
|---:|---|---:|
| 3 | Default prefetcher comparison | 78 |
| 4 | L1D/L2 placement checks | 39 |
| 5 | Two-channel comparison | 78 |
| 6 | One-parameter-at-a-time sensitivity screening | 260 |
| 7 | Follow-up joint SPP threshold grid | 169 |
| 8 | 1 MiB and 4 MiB LLC comparisons | 156 |
|  | **Total** | **780** |

Phase 6 changes one parameter at a time. Phase 7 comes after that screening:
it tests combinations of the two SPP thresholds that were sensitive in Phase
6. The Stride and Streamer degree comparisons in the tuning report reuse the
Phase-6 results and do not add more simulations.

### 5.1 Choose cluster settings

Install the plotting packages in the Python environment that will be available
to the Slurm analysis job:

```bash
python3 -m pip install -r requirements.txt
```

If the cluster should generate only CSV and text reports, set
`ANALYZE_PLOTS=0` when starting `run_all.sh` instead.

The driver requires three site-specific values:

- `PARTITION`: Slurm partition name;
- `JOB_MEMORY`: memory requested by each simulation;
- `ARRAY_LIMIT`: maximum number of simultaneous array tasks.

Example:

```bash
PARTITION=your-partition \
JOB_MEMORY=4G \
ARRAY_LIMIT=32 \
PYTHON=python3 \
  ./scripts/run_all.sh
```

Optional values:

- `ARRAY_LIMIT_LLC`: separate concurrency limit for the LLC arrays;
- `ANALYSIS_MEMORY`: memory for the final analysis job;
- `WARMUP`: warmup instructions, default `50000000`;
- `SIM`: measured instructions, default `150000000`;
- `OUTDIR`: raw output directory, default `results/slurm/`;
- `ANALYSIS_DIR`: report directory, default `results/analysis/`.

Changing `WARMUP` or `SIM` creates a different experiment and should use a
separate output directory.

### 5.2 What the driver does

`scripts/run_all.sh` performs these steps in order:

1. checks Python, Slurm, all four binaries, and all 13 traces;
2. creates seven Slurm job lists with 780 jobs in total;
3. records commits, tool versions, binary hashes, trace hashes, and job-list
   hashes in `results/analysis/provenance.txt`;
4. submits the simulation arrays;
5. submits `scripts/analyze.sh` with an `afterok` dependency, so analysis runs
   only if every simulation array succeeds.

Raw outputs are written to `results/slurm/`. Generated CSV files, reports, and
plots are written to `results/analysis/`.

Monitor the submitted work with:

```bash
squeue -u "$USER"
```

### 5.3 Inspect job lists before submission

This optional check creates the job lists without submitting them:

```bash
export PYTHIA_HOME="$PWD"

bash scripts/gen_joblist.sh
bash scripts/gen_joblist_p4.sh
bash scripts/gen_joblist_p5.sh
bash scripts/gen_joblist_p6.sh
bash scripts/gen_joblist_p7.sh
SIZE=1MB bash scripts/gen_joblist_p8.sh
SIZE=4MB bash scripts/gen_joblist_p8.sh

wc -l experiments/joblist*.txt
```

Expected counts are `78`, `39`, `78`, `260`, `169`, `78`, and `78`.

## 6. Reanalyze existing simulator outputs

This path does not rebuild Pythia and does not require Slurm. It requires all
780 raw `.out` files in `results/slurm/`.

### 6.1 Check the raw outputs

```bash
find results/slurm -type f -name '*.out' | wc -l
find results/slurm -type f -name '*.out' \
  -exec grep -l '^Core_0_IPC ' {} + | wc -l
```

Both commands must print `780`.

### 6.2 Install plotting packages

```bash
python3 -m pip install -r requirements.txt
```

Only NumPy and Matplotlib are needed, and only for the two PNG figures. The
CSV and text analyses use the Python standard library.

### 6.3 Run the analysis

```bash
PYTHON=python3 ./scripts/analyze.sh
```

Without NumPy and Matplotlib:

```bash
ANALYZE_PLOTS=0 PYTHON=python3 ./scripts/analyze.sh
```

The analysis wrapper:

1. checks that all 780 outputs exist and contain final IPC;
2. builds `characterization_all.csv` with 741 data rows;
3. builds `characterization_default.csv` with 78 data rows;
4. regenerates all text reports;
5. runs the prefix-stability and trace-resampling checks;
6. creates the Basis-A and Basis-B figures unless plotting is disabled.

Every candidate is compared with a no-prefetch run using the same hardware
configuration:

| Candidate suffix | No-prefetch reference |
|---|---|
| no suffix | `nopref` |
| `_2ch` | `nopref_2ch` |
| `_1MB` | `nopref_1MB` |
| `_4MB` | `nopref_4MB` |

## 7. Files produced by the workflow

| Path | Contents |
|---|---|
| `Pythia/` | Pinned simulator and libbf checkout |
| `traces/` | Downloaded benchmark traces |
| `experiments/joblist*.txt` | Generated Slurm job lists |
| `results/debug/` | Short local-check outputs |
| `results/slurm/` | Raw outputs from the 780 simulations |
| `results/analysis/` | CSV files, reports, plots, and provenance |

`Pythia/`, traces, job lists, and raw simulator outputs are intentionally
ignored by Git.
