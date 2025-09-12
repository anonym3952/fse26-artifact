import argparse
import os
from pathlib import Path
import random

import numpy.random
import pandas as pd
from tqdm import tqdm

from utils import Timer
from retainment import compute_model_count
from incremental_sampling import (
    get_samples,
    incremental_sampling,
    Sampler,
    Method,
    Algorithm,
)

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
DEFAULT_SAMPLER = Sampler.spur
DEFAULT_METHOD = Method.none
DEFAULT_ALGORITHM = Algorithm.uniform


def main():
    arg_parser = argparse.ArgumentParser(
        description="uniform sampling for feature model histories"
    )
    arg_parser.add_argument(
        "directory",
        help="the directory containing input files in DIMACS format",
    )
    arg_parser.add_argument(
        "-n",
        "--num_samples",
        action="store",
        type=int,
        default=100,
        help="The requested number of samples for each update",
    )
    arg_parser.add_argument(
        "-a",
        "--algorithm",
        action="store",
        type=str.lower,
        choices=Algorithm._member_names_,
        default=DEFAULT_ALGORITHM,
        help="Algorithm for number of samples per partition",
    )
    arg_parser.add_argument(
        "-m",
        "--method",
        action="store",
        type=str.lower,
        choices=Method._member_names_,
        default=DEFAULT_METHOD,
        help="Incremental sampling method",
    )
    arg_parser.add_argument(
        "-s",
        "--sampler",
        action="store",
        type=str.lower,
        choices=Sampler._member_names_,
        default=DEFAULT_SAMPLER,
        help="Which sampler to use as backend",
    )
    arg_parser.add_argument(
        "--read-model-count",
        action="store_true",
        help="read model counts from '<directory>/model_counts.csv'",
    )
    arg_parser.add_argument(
        "--csv",
        action="store_true",
        help="write results to a CSV file",
    )
    arg_parser.add_argument(
        "--seed",
        action="store",
        type=int,
        default=random.randint(0, 99999),
        help="random seed",
    )
    arg_parser.add_argument(
        "--no-sample-reuse",
        action="store_true",
        help="generate fresh samples instead of using the samples from the previous update",
    )

    # parse arguments
    args = arg_parser.parse_args()

    benchmark(
        directory=Path(args.directory),
        num_samples=int(args.num_samples),
        algorithm=Algorithm[args.algorithm],
        method=Method[args.method],
        sampler=Sampler[args.sampler],
        seed=args.seed,
        read_model_count=args.read_model_count,
        no_reuse=args.no_sample_reuse,
        write_csv=args.csv,
    )


def benchmark(
    directory: Path,
    num_samples: int,
    algorithm: Algorithm,
    method: Method,
    sampler: Sampler,
    seed: int,
    read_model_count=False,
    no_reuse=False,
    write_csv=False,
):
    print(directory)
    print(num_samples, "samples")
    print("method:", method)
    print("seed:", seed)
    random.seed(seed)
    numpy.random.seed(seed)

    # start timer
    timer = Timer()

    # collect all DIMACS files from directory
    dimacs_files = sorted(directory.glob("*.dimacs"))

    # model count
    model_count: dict[str, int | None] = dict()
    if read_model_count:
        model_count_path = directory / "model_counts.csv"
        assert (
            model_count_path.exists()
        ), f"{model_count_path} not found. Generate by running retainment.py"
        df_mc = pd.read_csv(model_count_path)
        model_count = {
            k: int(v)
            for k, v in df_mc.set_index("file")["model_count"].to_dict().items()
        }
    elif method not in [Method.none]:  # Method.bdd
        print("Computing model count of each file:")
        for file in tqdm(dimacs_files):
            count = compute_model_count(file)
            assert count
            model_count[file.name] = count

    # perform sampling according to the selected method
    all_samples: set[tuple[int]] = set()
    if method == Method.none:
        for file in tqdm(dimacs_files):
            samples = get_samples(file, num_samples, sampler)
            all_samples = all_samples.union(samples_to_set(samples))
    else:
        print("Processing pairs")
        records = []
        samples_old = None
        for i in tqdm(range(len(dimacs_files) - 1)):
            file_old, file_new = dimacs_files[i], dimacs_files[i + 1]
            timer = Timer(enable_printing=False)
            samples, results = incremental_sampling(
                sampler,
                method,
                algorithm,
                file_old,
                file_new,
                num_samples,
                samples_old=samples_old,
                count_old=model_count.get(file_old.name),
                count_new=model_count.get(file_new.name),
            )
            sampling_time = timer.stop()
            records.append(
                {
                    "directory": directory,
                    "seed": seed,
                    "file_old": file_old.name,
                    "file_new": file_new.name,
                    "sampler": sampler,
                    "method": method,
                    "algorithm": algorithm,
                    "sampling_time": sampling_time,
                    **results,
                }
            )
            if no_reuse:
                samples_old = get_samples(file_new, num_samples, sampler)
            else:
                if len(samples) != num_samples:
                    print(
                        f"Update {i}: Warning: number of samples is {len(samples)}, but should be {num_samples}"
                    )
                samples_old = samples if len(samples) == num_samples else None
            all_samples = all_samples.union(samples_to_set(samples))

    duration = timer.stop()
    total_samples = (len(dimacs_files) - 1) * num_samples
    print(f"Total samples: {total_samples}")
    unique_samples = len(all_samples)
    print(f"Unique samples: {unique_samples} (-{1-(unique_samples/total_samples):.2%})")
    # print("last sample:", hash(tuple(samples[-1])))

    if write_csv and method != Method.none:
        OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
        output_path = OUTPUT_DIR / (
            # directory.as_posix().replace("/", "_")
            directory.name
            + f"_seed{seed}_{algorithm}_{method}_{sampler}_{num_samples}{'_no-reuse' if no_reuse else ''}.csv"
        )
        df = pd.DataFrame(records)
        df.to_csv(output_path)
        print("wrote results to", output_path)

    results = {
        "directory": directory,
        "seed": seed,
        "algorithm": algorithm,
        "method": method,
        "sampler": sampler,
        "total_samples": total_samples,
        "unique_samples": unique_samples,
        "time": duration,
    }
    return results


def samples_to_set(samples: list[list[int]]) -> set[tuple[int]]:
    """
    >>> samples_to_set([[-1,3,2],[3,-2,1],[-3,2,-1]])
    {(-1, 2, -3), (-1, 2, 3), (1, -2, 3)}
    """
    sample_set = set()
    for s in samples:
        s.sort(key=abs)
        sample_set.add(tuple(s))
    return sample_set


if __name__ == "__main__":
    main()
