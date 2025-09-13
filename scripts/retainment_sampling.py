import math
import os
from pathlib import Path
import subprocess
import random
from enum import StrEnum, auto
import tempfile
import shutil

from numpy.random import binomial
from pysat.formula import CNF
from pysat.solvers import Solver

from retainment import compute_model_count, conjunction
from utils import Timer


class Sampler(StrEnum):
    spur = auto()
    kus = auto()


class Method(StrEnum):
    none = auto()
    rejection = auto()
    tseitin = auto()


class Algorithm(StrEnum):
    rounding = auto()
    uniform = auto()
    expectation_uniform = auto()


class UnsatError(Exception):
    """Constraints are unsatisfiable"""


SEED = 4711
VALIDATE_SAMPLES = False
DEFAULT_SAMPLER = Sampler.spur
DEFAULT_METHOD = Method.rejection
DEFAULT_ALGORITHM = Algorithm.uniform
SPUR = os.getenv("SPUR", "spur")

REJECTION_MAX_CANDIDATES = 10**4
"""In rejection sampling: the maximum number of candidate samples requested at once from the base sampler"""
REJECTION_TOTAL_MAX_CANDIDATES = 10**6
"""In rejection sampling: the maximum total number of candidate samples before rejection sampling is aborted"""


def parse_spur_output(file: Path) -> list[str]:
    samples = []
    recording = False

    with open(file, "r") as f:
        for line in f:
            line = line.strip()
            if line == "#START_SAMPLES":
                recording = True
                continue
            elif line == "#END_SAMPLES":
                break
            elif line == "UNSAT":
                raise UnsatError
            if recording and line:
                num_witness, sample = line.split(",", 1)  # Split at the first comma
                # https://github.com/ZaydH/spur?tab=readme-ov-file#output-format
                # add the sample as many times as the number of entailed witnesses
                for _ in range(int(num_witness)):
                    samples.append(sample)

    return samples


def get_samples_spur(file: Path, n: int) -> list[list[int]]:
    # run SPUR to generate samples
    with tempfile.TemporaryDirectory() as tmp:
        output_file = Path(tmp) / (file.name + ".samples")
        cmd = [
            str(SPUR),
            "-cnf",
            str(file),
            "-s",
            str(n),
            "-out",
            str(output_file),
            "-seed",
            str(random.randint(0, 10000)),
        ]
        # print("Running", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True)
        result.check_returncode()

        # parse SPUR output
        raw_samples = parse_spur_output(output_file)
        assert len(raw_samples) == n

    # randomly substitute '*' with 0 or 1
    samples = []
    for line in raw_samples:
        sample = []
        for i in range(len(line)):
            var = i + 1  # variables are 1-indexed
            if line[i] == "*":
                sample.append(random.choice([var, -var]))
            elif line[i] == "1":
                sample.append(var)
            elif line[i] == "0":
                sample.append(-var)
            else:
                raise ValueError
        samples.append(sample)
    return samples


def get_samples_kus(file: Path, n: int) -> list[list[int]]:
    kus_path = os.getenv("KUS")
    assert kus_path, "set environment variable 'KUS' to point to the KUS repository"
    with tempfile.TemporaryDirectory() as tmp:
        output_file = (Path(tmp) / (file.name + ".samples")).absolute()
        cmd = [
            "python3",
            "KUS.py",
            "--samples",
            str(n),
            "--outputfile",
            str(output_file),
            "--seed",
            str(random.randint(0, 10000)),
        ]
        # Re-use the d-DNNF if it has already been constructed
        nnf_file = file.with_name(file.name + ".nnf").absolute()
        if nnf_file.exists():
            cmd.extend(["--dDNNF", str(nnf_file)])
        else:
            cmd.append(str(file.absolute()))

        result = subprocess.run(cmd, capture_output=True, cwd=kus_path)
        result.check_returncode()
        samples = []
        with open(output_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    # lines look like "1, -20 4 5 -71"
                    _, line = line.split(", ", 1)  # Split at the first comma
                    samples.append([int(l) for l in line.split(" ")])
    return samples


def get_samples(file: Path, n: int, engine: Sampler) -> list[list[int]]:
    """Generate `n` samples for the given `file`, using the sampler specified by `engine`."""
    match engine:
        case Sampler.kus:
            return get_samples_kus(file, n)
        case Sampler.spur:
            return get_samples_spur(file, n)
        case _:
            raise ValueError(f"Unknown engine '{engine}'")


def rejection_sampling(
    engine: Sampler, file_old: Path, file_new: Path, n: int, hitrate=1.0, oversample=0.05
) -> tuple[list[list[int]], int]:
    """
    Sample `n` uniform configurations from the new model (`file_new`) that do not satisfy the old model (`file_old`).
    Candidate samples are provided by the sampler specified by `engine`.
    
    Returns the list of samples and the number of candidate configurations that where checked.

    If the expected hit rate is knonw, it can be provided to make a good guess how many candidate samples need to be requested to end up with `n` valid samples: in expectation, `n / hitrate` many candidates are reequired.
    To account for variance, `oversample` allows to specify a percentage of how many more candidates should be requested (default: 5%).
    
    Uses the global constants `REJECTION_MAX_CANDIDATES` and `REJECTION_TOTAL_MAX_CANDIDATES`.
    """
    assert n > 0

    # set up SAT solver for old model
    f_old = CNF(from_file=file_old)
    checker_old = Solver()
    is_sat = checker_old.append_formula(f_old.clauses, no_return=False)
    assert is_sat, f"{file_old} is UNSAT"

    # generate candidate samples for file_new and reject those that are valid for file_old
    samples = []
    num_samples = 0
    num_candidates = 0
    next_candidates = min(
        round(n / hitrate * (1 + oversample)), REJECTION_MAX_CANDIDATES
    )
    while num_samples < n and num_candidates < REJECTION_TOTAL_MAX_CANDIDATES:
        timer = Timer(enable_printing=False)
        candidates = get_samples(file_new, next_candidates, engine)
        checks = 0
        num_candidates += next_candidates
        for candidate in candidates:
            # reject samples valid for file_old
            checks += 1
            if not checker_old.solve(assumptions=candidate):
                samples.append(candidate)
                num_samples += 1
                if num_samples == n:
                    break
        else:  # no break
            # with m valid samples remaining, the hitrate is ~ m/n. We still need n-m samples, so we generate another (n-m)n/m candidate samples
            hitrate = num_samples / num_candidates
            if hitrate == 0.0:
                hitrate = 0.0001
            next_candidates = min(
                round((n - num_samples) / hitrate * (1 + oversample)) + 1,
                REJECTION_MAX_CANDIDATES,
            )
        check_time = timer.stop()
        # print(f"Generated & checked {checks/check_time} candidates per second")
    if num_samples < n:
        print(
            f"Warning: Rejection sampling aborted with {n} of {num_samples} samples found, after rejecting {num_candidates} candidate samples."
        )
    return samples, num_candidates


def tseitin_sampling(engine:Sampler, file_old: Path, file_new: Path, n: int) -> list[list[int]]:
    f_old = CNF(from_file=file_old)
    cnf = f_old.negate()  # not F
    if cnf.auxvars:
        assert list(range(min(cnf.auxvars), max(cnf.auxvars) + 1)) == cnf.auxvars
    # print("auxvars:", cnf.auxvars)
    f_new = CNF(from_file=file_new)
    cnf.extend(f_new.clauses)  # not F and F'

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"not_{file_old.stem}_and_{file_new.stem}.dimacs"
        cnf.to_file(path)
        samples = get_samples(path, n, engine)
        # trim away aux variables
        # samples = [sample[: min(cnf.auxvars) - 1] for sample in samples]
    return samples


def write_samples(samples: list[list[int]], path: Path):
    """Write samples to a file, one per line"""
    with path.open("w") as f:
        for clause in samples:
            f.write(" ".join(map(str, clause)) + "\n")


def read_samples(path: Path) -> list[list[int]]:
    """
    Read samples from a file.
    
    File format:
    ```
    1 -2 3
    -1 2 3
    1 2 3
    ```
    yields the sample list `[[1,-2,3], [-1,2,3], [1,2,3]]`
    """
    with path.open() as f:
        return [list(map(int, line.strip().split())) for line in f if line.strip()]


def retainment_sampling(
    engine: Sampler,
    method: Method,
    algorithm: Algorithm,
    file_old: Path,
    file_new: Path,
    num_samples: int,
    samples_old: list[list[int]]|None=None,
    count_old:int|None=None,
    count_new:int|None=None,
) -> tuple[list[list[int]], dict]:
    """Retainment sampling"""

    # compute model count of conjunction
    tmp_dir = Path(tempfile.mkdtemp())
    file_conj = conjunction(file_old, file_new, directory=tmp_dir)
    count_conj = compute_model_count(file_conj)
    assert count_conj is not None

    # check for empty intersection
    if count_conj == 0:
        # no retainment possible, fall back to regular sampling
        return get_samples(file_new, num_samples, engine), {
        "num_samples": num_samples,
        "num_valid_old_expected": 0,
        "num_valid_old": 0,
        "num_needed_old": 0,
        "num_retained": 0,
        "num_retained_expected": 0,
        "num_more_old": 0,
        "num_needed_new": num_samples,
        "num_candidates_new": 0,
        "update_type": "incompareable",
        "short_circuit": True,
    }

    # generate samples for old model
    if samples_old is None:
        samples_old = get_samples(file_old, num_samples, engine)
    assert len(samples_old) == num_samples

    # get model counts for old and new file
    if count_old is None:
        count_old = compute_model_count(file_old)
    assert count_old
    if count_new is None:
        count_new = compute_model_count(file_new)
    assert count_new

    # check for refactoring update (no change in configuration space)
    if count_conj == count_old and count_conj == count_new:
        return samples_old, {
        "num_samples": num_samples,
        "num_valid_old_expected": num_samples,
        "num_valid_old": num_samples,
        "num_needed_old": num_samples,
        "num_retained": num_samples,
        "num_retained_expected": num_samples,
        "num_more_old": 0,
        "num_needed_new": 0,
        "num_candidates_new": 0,
        "update_type": "refactoring",
        "short_circuit": True,
    }

    # determine update types
    if count_conj == count_old:
        update_type = "generalization"
    elif count_conj == count_new:
        update_type = "spezialization"
    else:
        update_type = "changing"

    # Create solvers for old and new CNF
    if VALIDATE_SAMPLES:
        f_old = CNF(from_file=file_old)
        checker_old = Solver()
        is_sat = checker_old.append_formula(f_old.clauses, no_return=False)
        assert is_sat, f"{file_old} is UNSAT"

    f_new = CNF(from_file=file_new)
    checker_new = Solver()
    is_sat = checker_new.append_formula(f_new.clauses, no_return=False)
    assert is_sat, f"{file_new} is UNSAT"

    # compute expected retainment
    max_keep = count_conj / count_old
    max_use = count_conj / count_new
    expected_retainment = min(max_keep, max_use)

    # check which samples can be kept
    samples_old_and_new = []
    for sample in samples_old:
        if checker_new.solve(assumptions=sample):
            samples_old_and_new.append(sample)

    # determine number of samples for new/old
    num_valid_old = len(samples_old_and_new)
    num_valid_old_expected = num_samples * max_keep
    match algorithm:
        case Algorithm.rounding:
            num_needed_old = math.ceil(num_samples * max_use)
        case Algorithm.expectation_uniform:
            nr = num_samples * max_use
            if nr == int(nr):
                num_needed_old = int(nr)
            else:
                num_needed_old = math.floor(nr)
                x = nr - math.floor(nr)
                if random.random() > x:
                    num_needed_old += 1
        case Algorithm.uniform:
            num_needed_old = binomial(n=num_samples, p=max_use)
    num_needed_new = num_samples - num_needed_old

    # samples for the conjunction (old)
    num_more_old = 0
    if num_valid_old < num_needed_old:
        # generate more samples for the conjunction
        num_more_old = num_needed_old - num_valid_old
        samples_conj = get_samples(file_conj, num_more_old, engine)
        if VALIDATE_SAMPLES:
            for sample in samples_conj:
                assert checker_new.solve(
                    assumptions=sample
                ), f"sample produced by {engine} for conjunction is invalid for {file_new}: {sample}"
        samples_old_and_new.extend(samples_conj)
    elif num_valid_old > num_needed_old:
        # drop superfluous samples
        samples_old_and_new = samples_old_and_new[:num_needed_old]
    assert len(samples_old_and_new) == num_needed_old

    # generate new samples
    if num_needed_new == 0:
        samples_new = []
        num_candidates_new = 0
    elif method == Method.rejection:
        samples_new, num_candidates_new = rejection_sampling(
            engine, file_old, file_new, n=num_needed_new, hitrate=1 - max_use
        )
        if len(samples_new) != num_needed_new:
            print(
                f"Rejection sampling failed, falling back to regular sampling with SPUR."
            )
            return get_samples_spur(file_new, num_samples), {"spur_fallback": True}
    elif method == Method.tseitin:
        samples_new = tseitin_sampling(engine, file_old, file_new, n=num_needed_new)
        num_candidates_new = 0
    if VALIDATE_SAMPLES:
        for sample in samples_new:
            assert not checker_old.solve(
                assumptions=sample
            ), f"{method} sampling (with {engine}) produced a sample valid for {file_old}, even though it shouldn't be"
            assert checker_new.solve(
                assumptions=sample
            ), f"{method} sampling (with {engine}) produced invalid sample for {file_new}"

    samples = samples_old_and_new + samples_new

    # remove tmp dir
    shutil.rmtree(tmp_dir)

    return samples, {
        "num_samples": num_samples,
        "num_valid_old_expected": num_valid_old_expected,
        "num_valid_old": num_valid_old,
        "num_needed_old": num_needed_old,
        "num_retained": min(num_valid_old, num_needed_old),
        "num_retained_expected": num_samples * expected_retainment,
        "num_more_old": num_more_old,
        "num_needed_new": num_needed_new,
        "num_candidates_new": num_candidates_new,
        "update_type": update_type,
        "short_circuit": False
    }


def main():
    import sys

    if len(sys.argv) < 4:
        print(
            f"Usage: python {sys.argv[0]} <old.dimacs> <new.dimacs> <num samples> [{'|'.join(Sampler._member_names_)}]"
        )
        exit(1)
    file_old = Path(sys.argv[1])
    file_new = Path(sys.argv[2])
    num_samples = int(sys.argv[3])
    sampler = DEFAULT_SAMPLER
    if len(sys.argv) == 5:
        try:
            sampler = Sampler[sys.argv[4]]
        except KeyError:
            print(
                f"Unknown sampler '{sys.argv[4]}', expected one of the following:",
                ", ".join(Sampler._member_names_),
            )
            exit(1)

    retainment_sampling(
        sampler, DEFAULT_METHOD, DEFAULT_ALGORITHM, file_old, file_new, num_samples
    )


if __name__ == "__main__":
    main()
