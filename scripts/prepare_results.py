import csv
from pathlib import Path


def main(log_dir: Path):
    bench_csv = log_dir / "batch.csv"
    output_file = log_dir / "full_results.csv"

    # Load runtimes from bench.csv
    runtime_map = {}
    with bench_csv.open() as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # runtime_map[row["name"]] = float(row["runtime"])
            runtime_map[row["name"]] = row["runtime"]

    rows = []
    for file in log_dir.glob("*.log"):
        with file.open() as f:
            lines = [line.strip() for line in f if line.strip()]

        data = {
            "directory": lines[1],  # second non-empty line is always the directory
            "algorithm": None,
            "method": None,
            "seed": None,
            "time": None,
            "total_samples": None,
            "unique_samples": None,
            "sampler": "spur",
        }
        if "-a expectation_uniform" in lines[0]:
            data["algorithm"] = "expectation_uniform"
        elif "-a uniform" in lines[0]:
            data["algorithm"] = "uniform"
        else:
            data["algorithm"] = "none"

        for line in lines:
            if line.startswith("method:"):
                data["method"] = line.split(":", 1)[1].strip()
            elif line.startswith("seed:"):
                data["seed"] = int(line.split(":", 1)[1].strip())
            elif line.startswith("Elapsed time:"):
                data["time"] = float(line.split(":")[1].split()[0])
            elif line.startswith("Total samples:"):
                data["total_samples"] = int(line.split(":")[1].strip())
            elif line.startswith("Unique samples:"):
                data["unique_samples"] = int(line.split(":")[1].strip().split()[0])

        # if None in data.values():
        #     print(f"Missing fields in {file.name}: {data}")
        #     # print(f"Skipping {file.name}, missing fields: {data}")
        #     # continue

        # Compose key for runtime lookup
        if data["method"] == "none":
            key = f"{data['directory']} (-m none)"
        else:
            key = f"{data['directory']} (-a uniform -m {data['method']})"
        data["runtime"] = runtime_map.get(key)

        rows.append(data)

    # Write to CSV
    with output_file.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "directory",
                "seed",
                "algorithm",
                "method",
                "sampler",
                "total_samples",
                "unique_samples",
                "time",
                "runtime",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("wrote to", output_file)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <benchmarks.csv>")
        sys.exit(1)

    main(Path(sys.argv[1]))
