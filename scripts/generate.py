import os
import json
import random
import argparse
from pysat.formula import CNF
from pathlib import Path

OUTPUT_DIR = Path("data") / "generated"


def remove_clauses(clauses: list[list[int]], indices: list[int]):
    return [cl for i, cl in enumerate(clauses) if i not in indices]


def remove_variables(clauses: list[list[int]], vars_to_remove: list[int]):
    return [
        [lit for lit in cl if abs(lit) not in vars_to_remove]
        for cl in clauses
        if all(abs(lit) not in vars_to_remove for lit in cl)
    ]


def write_cnf(clauses: list[list[int]], path, var_names):
    num_vars = max((abs(l) for cl in clauses for l in cl), default=0)
    with open(path, "w") as f:
        for vid in sorted(var_names):
            f.write(f"c {vid} {var_names[vid]}\n")
        f.write(f"p cnf {num_vars} {len(clauses)}\n")
        for cl in clauses:
            f.write(" ".join(map(str, cl)) + " 0\n")


def apply_random_steps(
    name: str,
    base_clauses: list[list[int]],
    base_var_names: dict[int, str],
    steps: int,
    out_dir,
    prob_remove_clause: float,
    prob_add_clause: float,
    prob_remove_var: float,
    prob_rename_var: float,
    seed: int,
):
    full_out_dir = OUTPUT_DIR / out_dir
    full_out_dir.mkdir(exist_ok=True, parents=True)
    random.seed(seed)

    clauses = base_clauses[:]
    var_names = base_var_names.copy()
    history = []
    snapshots = [(clauses[:], var_names.copy())]
    all_removed_clauses = []

    for _ in range(steps):
        step = {}
        clause_count = len(clauses)
        var_set = set(abs(l) for cl in clauses for l in cl)

        # Remove clauses
        if clause_count > 0 and random.random() < prob_remove_clause:
            n = random.randint(
                1, max(1, clause_count // 10)
            )  # remove up to 10% of clauses
            to_remove_ids = random.sample(range(clause_count), n)
            remaining_clauses = []
            removed_clauses = []
            for i, clause in enumerate(clauses):
                if i in to_remove_ids:
                    removed_clauses.append(clause)
                else:
                    remaining_clauses.append(clause)
            # clauses = remove_clauses(clauses, to_remove)
            # removed_clauses.append(to_remove[:])
            step["remove_clauses"] = removed_clauses
            clauses = remaining_clauses
            all_removed_clauses.extend(removed_clauses)

        # Add clauses
        elif all_removed_clauses and random.random() < prob_add_clause:
            n = random.randint(
                1, max(1, len(removed_clauses) // 3)
            )  # re-add up to 33% of removed clauses
            to_add = []
            for _ in range(n):
                i = random.randint(0, len(all_removed_clauses) - 1)
                if all(
                    [abs(l) in var_set for l in all_removed_clauses[i]]
                ):  # only add the clause if all variables still exist
                    clause = all_removed_clauses.pop(i)
                    clauses.append(clause)
                    to_add.append(clause)
            step["add_clauses"] = to_add

        # Remove variables
        if random.random() < prob_remove_var and var_set:
            n = random.randint(1, max(1, len(var_set) // 10))
            to_remove = random.sample(list(var_set), n)
            clauses = remove_variables(clauses, to_remove)
            for v in to_remove:
                var_names.pop(v, None)
            step["remove_vars"] = to_remove

        # Rename variables (just change names)
        if random.random() < prob_rename_var and var_names:
            n = min(5, len(var_names))
            to_rename = random.sample(list(var_names.keys()), n)
            mapping = {
                vid: f"{var_names[vid]}_{random.randint(100,999)}" for vid in to_rename
            }
            for vid, new_name in mapping.items():
                var_names[vid] = new_name
            step["rename_vars"] = mapping

        snapshots.append((clauses[:], var_names.copy()))
        history.append(step)

    padding = len(str(steps))
    for i, (snapshot_clauses, snapshot_names) in enumerate(reversed(snapshots)):
        out_file = os.path.join(full_out_dir, f"{name}_{i:0{padding}d}.dimacs")
        write_cnf(snapshot_clauses, out_file, snapshot_names)

    metadata = {
        "seed": seed,
        "steps": steps,
        "prob_remove_clause": prob_remove_clause,
        "prob_remove_var": prob_remove_var,
        "prob_rename_var": prob_rename_var,
        "history": history,
    }
    with open(os.path.join(full_out_dir, "history.json"), "w") as f:
        json.dump(metadata, f, indent=2)


def parse_var_names(cnf_file) -> dict[int, str]:
    var_names = {}
    with open(cnf_file) as f:
        for line in f:
            if line.startswith("c"):
                parts = line.strip().split()
                if len(parts) >= 3 and parts[1].isdigit():
                    var_names[int(parts[1])] = " ".join(parts[2:])
            elif line.startswith("p"):
                break
    return var_names


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cnf_file")
    parser.add_argument(
        "--steps", type=int, default=10, help="number of snapshots to generate"
    )
    parser.add_argument("--out_dir", default=None)
    parser.add_argument("--p_remove_clause", type=float, default=0.7)
    parser.add_argument("--p_add_clause", type=float, default=0.5)
    parser.add_argument("--p_remove_var", type=float, default=0.4)
    parser.add_argument("--p_rename_var", type=float, default=0.3)
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    args = parser.parse_args()

    if args.seed is None:
        args.seed = random.randint(0, 99999)

    base_name = Path(args.cnf_file).stem
    out_dir = (
        args.out_dir
        or f"{base_name}_seed{args.seed}_pc{args.p_remove_clause}_pa{args.p_add_clause}_pv{args.p_remove_var}_pr{args.p_rename_var}"
    )
    print("Saving generated history to", out_dir)

    cnf = CNF(from_file=args.cnf_file)
    var_names = parse_var_names(args.cnf_file)
    apply_random_steps(
        name=base_name,
        base_clauses=cnf.clauses,
        base_var_names=var_names,
        steps=args.steps,
        out_dir=out_dir,
        prob_remove_clause=args.p_remove_clause,
        prob_add_clause=args.p_add_clause,
        prob_remove_var=args.p_remove_var,
        prob_rename_var=args.p_rename_var,
        seed=args.seed,
    )
