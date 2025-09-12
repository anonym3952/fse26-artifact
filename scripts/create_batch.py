import sys
from pathlib import Path

"""
Given an input directory of feature models forming a history, create a batch file with both file paths per update:
```
data/test_preprocessed/history1
├── 2017-09-26_11-30-56.dimacs
├── 2018-02-09_09-07-40.dimacs
└── 2018-02-09_09-07-43.dimacs
```
creates a file `data/test_preprocessed/history1.batch` with content:
```
2017-09-26_11-30-56.dimacs 2018-02-09_09-07-40.dimacs
2018-02-09_09-07-40.dimacs 2018-02-09_09-07-43.dimacs
```
To be used with `benchmark.py` and the `--batch-file` option.
"""

if len(sys.argv) != 2:
    print(f"Usage: python {sys.argv[0]} <input_dir>")
    sys.exit(1)

input_dir = Path(sys.argv[1])
assert input_dir.exists()

output_path = input_dir.parent / (input_dir.name + ".batch")

# collect all DIMACS files from directory
dimacs_files = sorted(input_dir.glob("*.dimacs"))

with open(output_path, "w") as file:
    for i in range(len(dimacs_files) - 1):
        file.write(f"{dimacs_files[i]} {dimacs_files[i+1]}\n")
print(f"Wrote batch file to", output_path)
