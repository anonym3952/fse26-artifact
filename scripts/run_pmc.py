import os
import platform
import subprocess
import time
import sys

# Select pmc binary
current_os = platform.system()
if current_os == "Linux":
    PMC = "bin/pmc_linux"
elif current_os == "Darwin":
    PMC = "bin/pmc_mac"
else:
    raise OSError(f"Unsupported operating system: {current_os}")


def run_pmc(input_dir):
    input_dir = input_dir.rstrip("/")
    output_dir = f"{input_dir}_pmc"

    os.makedirs(output_dir, exist_ok=True)

    def process_dir(in_subdir, out_subdir, label):
        os.makedirs(out_subdir, exist_ok=True)
        print(f"Processing {label}...")
        start = time.time()

        for fname in os.listdir(in_subdir):
            if not (fname.endswith(".cnf") or fname.endswith(".dimacs")):
                continue

            in_file = os.path.join(in_subdir, fname)
            out_file = os.path.join(out_subdir, fname)

            with open(in_file) as f:
                original_lines = f.readlines()

            header = [line for line in original_lines if line.startswith("c ")]
            p_line = next(
                (line for line in original_lines if line.startswith("p cnf")), None
            )
            clauses = [
                line
                for line in original_lines
                if not line.startswith("c ") and not line.startswith("p cnf")
            ]

            result = subprocess.run(
                [
                    PMC,
                    "-vivification",
                    "-eliminateLit",
                    "-litImplied",
                    "-iterate=10",
                    "-verb=0",
                    in_file,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )

            pmc_lines = result.stdout.splitlines()
            solved_line = next(
                (line for line in pmc_lines if line.startswith("s ")), None
            )

            with open(out_file, "w") as f:
                f.writelines(header)
                f.write("\n")

                if solved_line:
                    # Keep original problem — pmc solved it prematurely
                    if p_line:
                        f.write(p_line + "\n")
                    f.writelines(clauses)
                else:
                    # Use pmc-rewritten CNF
                    body = [line for line in pmc_lines if not line.startswith("c ")]
                    for line in body:
                        f.write(line + "\n")

        end = time.time()
        print(f"Time for {label}: {end - start:.1f}s")

    # Decide if input_dir is a direct CNF directory or a container of directories
    entries = [os.path.join(input_dir, e) for e in os.listdir(input_dir)]
    cnf_files = [
        e
        for e in entries
        if os.path.isfile(e) and (e.endswith(".cnf") or e.endswith(".dimacs"))
    ]
    subdirs = [e for e in entries if os.path.isdir(e)]

    if cnf_files:
        # Direct CNF files in input_dir
        process_dir(input_dir, output_dir, os.path.basename(input_dir))
    else:
        # Subdirectories
        for subdir in sorted(subdirs):
            subname = os.path.basename(subdir)
            process_dir(subdir, os.path.join(output_dir, subname), subname)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_pmc.py <input_dir>")
        sys.exit(1)
    run_pmc(sys.argv[1])
