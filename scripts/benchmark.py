import argparse
import concurrent.futures
import datetime
import math
import multiprocessing
import os
import subprocess
import pathlib
from pathlib import Path
import signal

from utils import (
    Timer,
    file_or_dir_name,
    human_duration,
    label,
    strip_ansi,
    get_extension,
)

TIMEOUT = 600  # in seconds
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "")) / "results"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def main():
    timer = Timer(enable_printing=False)
    # set up argument parsing
    arg_parser = argparse.ArgumentParser(
        prog="benchmark",
        description="Benchmark programs with timeouts",
    )
    arg_parser.add_argument(
        "input",
        help="the input file, or a folder containing input files",
    )
    arg_parser.add_argument(
        "-t",
        "--timeout",
        action="store",
        type=int,
        default=TIMEOUT,
        help=f"time-out in seconds (default: {TIMEOUT})",
    )
    arg_parser.add_argument(
        "--batch-file",
        action="store_true",
        help="input file contains a list of paths (one per line)",
    )
    arg_parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="include files in subdirectories",
    )
    arg_parser.add_argument(
        "--param-file",
        type=str,
        help="file with extra command-line argument sets to test, one per line",
    )
    arg_parser.add_argument(
        "-c",
        "--cores",
        action="store",
        type=int,
        default=0,
        help="number of cores to use. A value of 0 (default) tries to choose as many cores as are available",
    )
    arg_parser.add_argument(
        "-e",
        "--file-extension",
        metavar="EXT",
        action="store",
        type=str,
        help="file extension of input files, all other files will be ignored",
    )
    arg_parser.add_argument(
        "-n",
        "--name",
        action="store",
        type=str,
        help="name used for results folder",
    )
    arg_parser.add_argument(
        "-w",
        "--work-dir",
        action="store",
        type=str,
        help="working directory for the program",
    )
    # use REMAINDER to capture everything after `--`
    arg_parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="command and arguments of the program"
    )

    # parse arguments
    args = arg_parser.parse_args()

    # timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print("started:", timestamp)

    # current & working directory
    current_dir = pathlib.Path().resolve()
    if args.work_dir:
        work_dir = args.work_dir
    else:
        work_dir = current_dir

    # collect input files
    input_path = args.input
    input_file_paths = []
    if args.batch_file:
        with open(input_path) as batch_file:
            for line in batch_file:
                line = line.strip()
                if line:
                    input_file_paths.append(line)
    elif os.path.isdir(input_path):
        if args.recursive:
            for root, dirs, files in os.walk(input_path):
                for file in files:
                    if (
                        args.file_extension is None
                        or get_extension(file) == args.file_extension
                    ):
                        input_file_paths.append(os.path.join(root, file))
        else:
            for file in os.listdir(input_path):
                if (
                    args.file_extension is None
                    or get_extension(file) == args.file_extension
                ):
                    input_file_paths.append(os.path.join(input_path, file))
    else:
        input_file_paths.append(input_path)
    # input_file_paths = [str(pathlib.Path(p).resolve()) for p in input_file_paths]
    input_file_paths = [str(pathlib.Path(p)) for p in input_file_paths]

    num_files = len(input_file_paths)
    if num_files < 1:
        print(
            "No files to process found. (Use the '-r' flag to process files in subdirectories)"
        )
        exit(0)
    # print("testing the following files:\n" + "\n".join(input_file_paths))

    # Parse param file
    if args.param_file:
        with open(args.param_file) as f:
            param_sets = [line.strip().split() for line in f if line.strip()]
    else:
        param_sets = [[]]  # default: no extra params

    # get name of file or directory
    if args.name:
        basename = args.name
    else:
        basename = file_or_dir_name(input_path)
    output_dir = timestamp + "_" + basename

    output_path = os.path.join(current_dir, OUTPUT_DIR, output_dir)
    os.makedirs(output_path)

    # get the number of available CPU cores
    if args.cores == 0:
        num_cores = multiprocessing.cpu_count()
    else:
        num_cores = args.cores

    # print rough estimate of worst-case runtime
    num_jobs = num_files * len(param_sets)
    wc_time = math.ceil(num_jobs / num_cores) * args.timeout
    print(
        f"{label(num_jobs, 'job')} scheduled with a timeout of {human_duration(args.timeout)} on {label(num_cores, 'core')}"
    )
    print(f"{human_duration(wc_time)} worst-case runtime")

    # result dict: file name -> result
    results: dict[str, str] = dict()

    os.chdir(work_dir)
    # process files in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_cores) as executor:
        # Submit all file processing tasks to the executor
        futures = {
            executor.submit(process_file, file, output_path, params, args): file
            for file in input_file_paths
            for params in param_sets
        }

        # collect results as they are completed
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            file = futures[future]
            try:
                name, test_result = future.result()
                results[name] = test_result
            except Exception as exc:
                print(f"{file} raised an exception: {exc}")
            finally:
                completed += 1
                print(
                    f"completed {completed}/{num_jobs} ({(completed/num_jobs) * 100:.2f}%) after {human_duration(timer.stop())}"
                )
    os.chdir(current_dir)

    # write CSV file
    header = "name;runtime"
    csv_path = os.path.join(output_path, basename + ".csv")
    with open(csv_path, "w") as csv_file:
        csv_file.write(header + "\n")
        for name, result in results.items():
            csv_file.write(f"{name};{result}\n")
    print("Wrote results:", csv_path)


def process_file(file_path, output_path, params, args):
    file_name = file_or_dir_name(file_path)
    name = f"{file_path}" + (f" ({' '.join(params)})" if params else "")
    print(f"{name}: started")
    dir = os.path.split(os.path.dirname(file_path))[1]
    output_file = os.path.join(
        output_path,
        f"{dir}_{file_name}" + ("_" + "_".join(params) if params else "") + ".log",
    )
    command = args.command + params + file_path.split(" ")

    with open(output_file, "a") as file:
        file.write("Running command: " + " ".join(command) + "\n")
    try:
        timer = Timer(enable_printing=False)
        process = subprocess.Popen(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # preexec_fn=os.setsid,  # Unix-based systems
            start_new_session=True,
        )
        try:  # to catch timeout
            stdout, stderr = process.communicate(timeout=args.timeout)
            timing = timer.stop()
            returncode = process.returncode
            # write output to log file
            with open(output_file, "a") as file:
                if stdout:
                    file.write(strip_ansi(stdout))
                if stderr:
                    file.write(strip_ansi(stderr))
                file.write(f"overall time: {human_duration(timing)}\n")
            # check return code
            if returncode == 0:
                test_result = str(timing)
                print(f"{name}: finished")
            elif returncode == -6:
                test_result = "memout"
                print(f"{name}: memout")
            else:
                test_result = f"error ({returncode})"
                print(f"{name}: error {returncode}")
        except subprocess.TimeoutExpired as e:
            # Send SIGTERM to the entire process group (pgid = -pid) to end all child processes
            os.killpg(process.pid, signal.SIGTERM)
            with open(output_file, "a") as file:
                if e.stdout:
                    file.write(e.stdout.decode())
                file.write(f"timeout of {args.timeout}s reached\n")
            test_result = f"timeout"
            print(f"{name}: timeout after {args.timeout}s")
    except Exception as e:
        with open(output_file, "a") as file:
            file.write(str(e) + "\n")
        raise e

    return name, test_result


if __name__ == "__main__":
    main()
