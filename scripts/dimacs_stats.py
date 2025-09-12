import os
import csv
import argparse

EXTENSIONS = [".cnf", ".dimacs"]


def parse_dimacs(path):
    """Parse DIMACS file, returning (filename, vars, clauses)."""
    n_vars = 0
    n_clauses = 0
    found_header = False
    n_vars_header = 0
    n_clauses_header = 0

    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("p cnf"):
                found_header = True
                parts = line.strip().split()
                n_vars_header = int(parts[2])
                n_clauses_header = int(parts[3])
                continue
            # Clause lines: integers ending with 0
            lits = [int(x) for x in line.split() if x]
            if lits:
                if lits[-1] != 0:
                    raise ValueError(f"Malformed clause in {path}: {line}")
                n_clauses += 1
                for lit in lits[:-1]:
                    n_vars = max(n_vars, abs(lit))
    if not found_header:
        raise ValueError(f"Missing header 'p cnf' in {path}")
    if n_vars != n_vars_header:
        print(
            f"Warning: Mismatching variable count in {path}: {n_vars_header} in header but {n_vars} in file."
        )
    if n_clauses != n_clauses_header:
        print(
            f"Warning: Mismatching clause count in {path}: {n_clauses_header} in header but {n_clauses} in file."
        )
    return os.path.basename(path), n_vars, n_clauses


def collect_stats(path):
    """Collect stats from a file or directory."""
    if os.path.isdir(path):
        files = [
            os.path.join(path, f)
            for f in os.listdir(path)
            if any(f.endswith(ext) for ext in EXTENSIONS)
        ]
    else:
        files = [path]
    return [parse_dimacs(f) for f in files]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to DIMACS file or folder")
    ap.add_argument("--csv", help="Output CSV file", default=None)
    args = ap.parse_args()

    stats = collect_stats(args.path)

    # Print to console
    print(f"{'File':30} {'Vars':>8} {'Clauses':>8}")
    num_vars_list = []
    num_clauses_list = []
    for name, vars, clauses in sorted(stats):
        num_vars_list.append(vars)
        num_clauses_list.append(clauses)
        print(f"{name:30} {vars:8} {clauses:8}")

    print(f"Vars: Min - Max\n{min(num_vars_list)} {max(num_vars_list)}")
    print(f"Clauses: Min - Max\n{min(num_clauses_list)} {max(num_clauses_list)}")

    # Export CSV if requested
    if args.csv:
        with open(args.csv, "w", newline="") as out:
            writer = csv.writer(out)
            writer.writerow(["File", "Vars", "Clauses"])
            writer.writerows(stats)


if __name__ == "__main__":
    main()
