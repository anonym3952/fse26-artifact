# FSE Artifact

Scripts for the evaluation and plots for the paper "Uniform Retainment Sampling for Evolving Software Configuration Spaces".

## Setup
Create Python environment:
```sh
python3 -m venv .venv
source .venv/bin/activate
```
Install required python packages:
```sh
pip install -r requirements.txt
```
Set environment variable `OUTPUT_DIR` to the directory where the plots and experiment results should go:
```sh
export OUTPUT_DIR=output/
```

### SharpSAT TD
Get and compile the model counter [SharpSAT TD](https://github.com/Laakeri/sharpsat-td):
```sh
git clone https://github.com/Laakeri/sharpsat-td.git
cd sharpsat-td
./setupdev.sh
cd ..
export SHARPSAT=sharpsat-td/bin/sharpSAT
```

### SPUR
Set up the uniform sampler [SPUR](https://github.com/ZaydH/spur):
```sh
git clone https://github.com/ZaydH/spur
cd spur
./build.sh
cd ..
export SPUR=spur/build/Release/spur
```

### Rust Setup
Compile the Rust library `unified-cli`:
```sh
cd unified-cli
cargo build --release
```
Add `unified-cli/target/release/` to PATH: (Add to `.bashrc` to keep permanently in PATH)
```sh
export PATH="unified-cli/target/release/:$PATH"
```
Test with `unified-cli --help`.

## Evaluation

### Preparation
The original DIMACS files collected from the [feature model benchmark](https://github.com/SoftVarE-Group/feature-model-benchmark) by [Sundermann et al.](https://dl.acm.org/doi/abs/10.1145/3646548.3672590) are in `data/histories/`:
```
$ tree -d data/histories/
data/histories/
├── automotive2
├── BusyBox
├── Fiasco
├── FinancialServices
├── soletta
└── uClibc
```
For `BusyBox`, we removed the empty snapshot `2008-11-06_23-41-38.dimacs`.

Unify files with `./scripts/unify.sh data/histories/`:
```
$ ./scripts/unify.sh data/histories/
Processing automotive2...
number of unified variables: 24053
Time for automotive2: 1s
Processing BusyBox...
number of unified variables: 710
Time for BusyBox: 0s
Processing Fiasco...
number of unified variables: 285
Time for Fiasco: 0s
Processing FinancialServices...
number of unified variables: 1082
Time for FinancialServices: 0s
Processing soletta...
number of unified variables: 493
Time for soletta: 1s
Processing uClibc...
number of unified variables: 320
Time for uClibc: 0s
```
This creates a folder `data/histories_unified`.

Run [`pmc`](https://www.cril.univ-artois.fr/KC/pmc.html) with `python scripts/run_pmc.py data/histories_unified/`: 
```
$ python scripts/run_pmc.py data/histories_unified/
Processing BusyBox...
Time for BusyBox: 2.7s
Processing Fiasco...
Time for Fiasco: 0.6s
Processing FinancialServices...
Time for FinancialServices: 3.3s
Processing automotive2...
Time for automotive2: 42.4s
Processing soletta...
Time for soletta: 0.8s
Processing uClibc...
Time for uClibc: 2.0s
```

The files used for the experiments are in `data/histories_unified_pmc/`.


### Main Experiment

Run the main experiment (on 5 cores in parallel) with a timeout of 2h per feature model history: (takes ~30 minutes)
```sh
python scripts/benchmark.py -t 7200 --cores 5 --param-file experiments/params.txt --batch-file experiments/batch.txt -- python scripts/history_sampling.py -n 1000 --csv
```
Results are in `results/2025-09-12_09-45-37_batch`.


### RQ1: Retainment
Compute model count and predicted expected retainment:
```sh
for dir in data/histories_unified_pmc/*/; do python scripts/retainment.py "$dir"; done
```
<!-- python scripts/retainment.py data/histories_unified_pmc/Fiasco/
python scripts/retainment.py data/histories_unified_pmc/BusyBox 
python scripts/retainment.py data/histories_unified_pmc/soletta 
python scripts/retainment.py data/histories_unified_pmc/uClibc 
python scripts/retainment.py data/histories_unified_pmc/FinancialServices
python scripts/retainment.py data/histories_unified_pmc/automotive2 -->
Takes about 3-10s for `Fiasco`, `soletta`, and `uClibc`, ~40s for `BusyBox`, ~2min for `FinancialServices`, and ~20min for `automotive2`.

Compute & plot model statistics (Fig 5.):
```sh
$ python scripts/plot/plot_history_stats.py data/histories_unified_pmc/
                                           path  updates  incomparable  unchanged  generalization  specialization  changed
0            data/histories_unified_pmc/BusyBox      247             5         63             125              24       30
1             data/histories_unified_pmc/Fiasco       30             2          1               4               4       19
2  data/histories_unified_pmc/FinancialServices        9             7          0               0               0        2
3            data/histories_unified_pmc/soletta      131            27         25              36               9       34
4             data/histories_unified_pmc/uClibc      139             7         25              44              23       40
Saving to output/plots/histories_unified_pmc_evolution_stats.pdf
```

Expected retainment plots with `plot_updates.py`:
```sh
python scripts/plot/plot_updates.py data/histories_unified_pmc/uClibc/pairs.csv uClibc
python scripts/plot/plot_updates.py data/histories_unified_pmc/Fiasco/pairs.csv Fiasco 5
python scripts/plot/plot_updates.py data/histories_unified_pmc/FinancialServices/pairs.csv FinancialServices 5
python scripts/plot/plot_updates.py data/histories_unified_pmc/BusyBox/pairs.csv BusyBox
python scripts/plot/plot_updates.py data/histories_unified_pmc/soletta/pairs.csv Soletta
```
Fig. 6a is `output/plots/bars/Fiasco_ER*.pdf`.

Average expected retainment ratio (Fig. 6b): `python scripts/plot/plot_retainment.py data/histories_unified_pmc/`
```
$ python scripts/plot/plot_retainment.py data/histories_unified_pmc/
                   0         1
0            BusyBox  0.602234
1             Fiasco  0.730909
2  FinancialServices  0.094947
3            soletta  0.520036
4             uClibc  0.668934
Saving to output/plots/bars/histories_unified_pmc_avg_retainment.pdf
```


Boxplots (Fig. 7): `python scripts/plot/plot_boxes.py`
```
$ python scripts/plot/plot_boxes.py
Reading output/BusyBox_seed16873_uniform_tseitin_spur_1000.csv
Reading output/BusyBox_seed16873_expectation_uniform_tseitin_spur_1000.csv
Warning: Clipped datapoint for BusyBox (Alg. 2 (expectation-uniform)) at -0.06734059147341089
Reading output/Fiasco_seed16873_uniform_tseitin_spur_1000.csv
Reading output/Fiasco_seed16873_expectation_uniform_tseitin_spur_1000.csv
Reading output/soletta_seed16873_uniform_tseitin_spur_1000.csv
Reading output/soletta_seed16873_expectation_uniform_tseitin_spur_1000.csv
Reading output/uClibc_seed16873_uniform_tseitin_spur_1000.csv
Reading output/uClibc_seed16873_expectation_uniform_tseitin_spur_1000.csv
Warning: Clipped datapoint for uClibc (Alg. 1 (uniform)) at 0.17299600253072822
Warning: Clipped datapoint for uClibc (Alg. 2 (expectation-uniform)) at 0.16799600253072822
Warning: Clipped datapoint for uClibc (Alg. 2 (expectation-uniform)) at 0.05831595398912316
Writing to output/plots/boxplots/boxplot_ALL_seed16873_tseitin_spur_1000_drop-trivial_clipped.pdf
```


### RQ2: Scalability

Generate artificial histories:
```sh
./scripts/generate_histories.sh
```

Run benchmarks (takes ~2h):
```sh
python scripts/benchmark.py -t 7200 --cores 5 --param-file experiments/paramsRQ3.txt --batch-file experiments/batch_gen.txt -- python scripts/history_sampling.py -n 1000 --csv
```

The results are in `results/2025-09-10_11-22-04_batch_gen`.


### RQ4: Sample-and-Test Performance

Run `python scripts/prepare_results.py` on the respective benchmark results folder to create `full_results.csv`.
Then, run `python scripts/plot/plot_benchmarks.py` on `full_results.csv` for the plots.

```
$ python scripts/prepare_results.py results/2025-09-12_09-45-37_batch
wrote to results/2025-09-12_09-45-37_batch/full_results.csv
$ python scripts/plot/plot_benchmarks.py results/2025-05-28_14-40-14_bench/full_results.csv 
```
Fig. 8 are `output/plots/benchmark_sweetspot_BusyBox.pdf` and `output/plots/benchmark_sweetspot_FinancialServices.pdf`.