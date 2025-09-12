import csv
import numpy as np
import pandas as pd
import os
import re
import subprocess
from pathlib import Path
from tqdm import tqdm

"""
Process pairs of feature models and compute several stats and *retainment*, the expected percentage of samples of the first model that can be re-used after the update.
"""


def compute_model_count(file: Path) -> int | None:
    sharpSAT_executable = os.getenv("SHARPSAT", "sharpSAT")
    cmd = [
        sharpSAT_executable,
        "-decot",
        "1",
        "-decow",
        "100",
        "-tmpdir",
        ".",
        file,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    match = re.search(r"c s exact arb int (\d+)", result.stdout)
    if match:
        return int(match.group(1))
    else:
        print("Error computing model count: \n", result.stdout, result.stderr)
        return None


def read_dimacs(file: Path):
    with file.open("r") as f:
        lines = f.readlines()
    header = []
    clauses = []
    comments = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("p cnf"):
            header.append(line)
        elif line.startswith("c"):
            comments.append(line)
        else:
            clauses.append(line)
    if not header:
        raise ValueError(f"Missing header in {file}")
    num_vars, num_clauses = map(int, header[0].split()[2:])
    return num_vars, clauses, comments


def conjunction(
    file_old: Path, file_new: Path, directory: Path = Path("conjunctions")
) -> Path:
    directory.mkdir(exist_ok=True)
    num_vars1, clauses1, comments1 = read_dimacs(file_old)
    num_vars2, clauses2, _ = read_dimacs(file_new)

    assert num_vars1 == num_vars2
    clauses = clauses1 + clauses2
    num_clauses = len(clauses)

    output_file = directory / f"{file_old.stem}_and_{file_new.stem}.dimacs"
    with output_file.open("w") as f:
        for line in comments1:
            f.write(line + "\n")
        f.write(f"p cnf {num_vars1} {num_clauses}\n")
        for line in clauses:
            f.write(line + "\n")

    return output_file


def main(directory: Path):
    # collect all dimacs files
    dimacs_files = sorted(directory.glob("*.dimacs"))
    print(directory)
    print(f"dimacs files: {len(dimacs_files)}")

    # compute model count for each and save as CSV
    output_file = directory / "model_counts.csv"
    if output_file.exists():
        print(f"Reading model count from {output_file}")
        df = pd.read_csv(output_file)
        model_count = {
            file: int(count)
            for file, count in zip(
                df["file"], df["model_count"]
            )  # use this to avoid overflows
        }
    else:
        print("Computing model count of each file:")
        model_count: dict[str, int | None] = dict()
        for file in tqdm(dimacs_files):
            model_count[file.name] = compute_model_count(file)
        print(f"Writing {output_file}")
        with output_file.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["file", "model_count"])
            for file in dimacs_files:
                writer.writerow([file.name, model_count[file.name]])

    # process pairs
    conjunctions_dir = directory / "conjunctions"
    conjunctions_dir.mkdir(exist_ok=True)
    results = []
    print("Processing pairs:")
    for i in tqdm(range(len(dimacs_files) - 1)):
        file1, file2 = dimacs_files[i], dimacs_files[i + 1]
        conj_file = conjunction(file1, file2, conjunctions_dir)
        conj_count = compute_model_count(conj_file)
        if conj_count == 0:
            percentage1 = 0
            percentage2 = 0
        else:
            percentage1 = (
                # np.divide(conj_count, model_count[file1.name])  # type: ignore
                conj_count / model_count[file1.name]  # type: ignore
                if model_count[file1.name] is not None
                else np.nan
            )
            percentage2 = (
                # np.divide(conj_count, model_count[file2.name])  # type: ignore
                conj_count / model_count[file2.name]  # type: ignore
                if model_count[file2.name] is not None
                else np.nan
            )
        retainment = np.nanmin([percentage1, percentage2])

        results.append(
            (file1.name, file2.name, conj_count, percentage1, percentage2, retainment)
        )

    df = pd.DataFrame(
        # results,
        [
            (a, b, int(c), float(d), float(e), float(f))
            for (a, b, c, d, e, f) in results
        ],
        columns=[
            "file old",
            "file new",
            "conjunction model count",
            "percentage of old",
            "percentage of new",
            "retainment",
        ],
        dtype=object,
    )

    output_file = directory / "pairs.csv"
    print(f"Writing {output_file}")
    df.to_csv(output_file, index=False, na_rep="NaN")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <directory>")
        sys.exit(1)

    main(Path(sys.argv[1]))
