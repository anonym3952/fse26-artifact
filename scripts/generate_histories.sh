#!/bin/bash

# defaults
STEPS=50
P_REMOVE_CLAUSE=0.4
P_ADD_CLAUSE=0.9
P_REMOVE_VAR=0.3
P_RENAME_VAR=0.1
SEED=56926

# parse options
while [[ $# -gt 0 ]]; do
  case "$1" in
    --steps) STEPS="$2"; shift 2 ;;
    --p_remove_clause) P_REMOVE_CLAUSE="$2"; shift 2 ;;
    --p_add_clause) P_ADD_CLAUSE="$2"; shift 2 ;;
    --p_remove_var) P_REMOVE_VAR="$2"; shift 2 ;;
    --p_rename_var) P_RENAME_VAR="$2"; shift 2 ;;
    --seed) SEED="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

INPUTS=(
  "data/unwise/ea2468.dimacs"
  "data/unwise/uclinux-base.dimacs"
  "data/unwise/adderii.dimacs"
  "data/unwise/automotive01.dimacs"
)

for f in "${INPUTS[@]}"; do
  python scripts/generate.py \
    --steps "$STEPS" \
    --p_remove_clause "$P_REMOVE_CLAUSE" \
    --p_add_clause "$P_ADD_CLAUSE" \
    --p_remove_var "$P_REMOVE_VAR" \
    --p_rename_var "$P_RENAME_VAR" \
    --seed "$SEED" \
    "$f"
done


# Unify
./scripts/unify.sh data/generated/

# Run pmc
python scripts/run_pmc.py data/generated_unified/

# Create batch_gen.txt
find data/generated_unified_pmc/ -mindepth 1 -maxdepth 1 > experiments/batch_gen.txt

# Compute predicted retainment & plot history stats
for dir in data/generated_unified_pmc/*/; do python scripts/retainment.py "$dir"; done
python scripts/plot/plot_history_stats.py data/generated_unified_pmc/
python scripts/plot/plot_retainment.py data/generated_unified_pmc/
