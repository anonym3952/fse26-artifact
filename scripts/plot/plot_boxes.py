import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output"))
OUTPUT_DIR_PLOTS = OUTPUT_DIR / "plots" / "boxplots"
OUTPUT_DIR_PLOTS.mkdir(exist_ok=True, parents=True)

models = ["BusyBox", "Fiasco", "soletta", "uClibc"]  # "FinancialServices"
seeds = [16873]  # , 93022, 53581]
method = "tseitin"
no_reuse = False
drop_trivial = True
clipped = True  # set limits for Y axis
solver = "spur"
num_samples = 1000

figsize = (10, 4.5)
ylim = 0.055

reuse_str = "_no-reuse" if no_reuse else ""
drop_trivial_str = "_drop-trivial" if drop_trivial else ""
clipped_str = "_clipped" if clipped else ""


rename = {
    "uClibc": "uClibc",
    "soletta": "soletta",
    "Fiasco": "Fiasco",
    "BusyBox": "BusyBox",
    "FinancialServices": "FinancialServices",
}

algorithm_map = {
    "uniform": "Alg. 1 (uniform)",
    "expectation_uniform": "Alg. 2 (expectation-uniform)",
}

palette = {
    "Alg. 1 (uniform)": "#1f77b4",
    "Alg. 2 (expectation-uniform)": "#ff7f0e",
}


# Collect data
all_data = []
for model in models:
    skip = False
    for algorithm in ["uniform", "expectation_uniform"]:
        for seed in seeds:
            path = (
                OUTPUT_DIR
                / f"{model}_seed{seed}_{algorithm}_{method}_{solver}_{num_samples}{reuse_str}.csv"
            )
            if not path.exists():
                print("Missing:", path)
                skip = True
                break
            print("Reading", path)
    if skip:
        continue

    for algorithm in ["uniform", "expectation_uniform"]:
        for seed in seeds:
            df = pd.read_csv(
                OUTPUT_DIR
                / f"{model}_seed{seed}_{algorithm}_{method}_{solver}_{num_samples}{reuse_str}.csv"
            )
            if drop_trivial:
                df = df[
                    (df["num_retained_expected"] != 0.0)
                    & (df["num_retained_expected"] != float(num_samples))
                ]
            diffs = (df["num_retained"] - df["num_retained_expected"]) / num_samples
            for val in diffs:
                if clipped and abs(val) > ylim:
                    print(
                        f"Warning: Clipped datapoint for {model} ({algorithm_map[algorithm]}) at {val}"
                    )
                all_data.append({"Model": model, "Algorithm": algorithm, "Diff": val})

# Create a single boxplot
df_all = pd.DataFrame(all_data)
df_all["Renamed Model"] = df_all["Model"].map(rename)
df_all["Algorithm Name"] = df_all["Algorithm"].map(algorithm_map)

# Combine for hue grouping (e.g., for side-by-side coloring)
fig, ax = plt.subplots(figsize=figsize)
sns.boxplot(
    data=df_all,
    x="Renamed Model",
    y="Diff",
    hue="Algorithm Name",
    palette=palette,
    ax=ax,
    medianprops=dict(color="black", linewidth=1.5),
    gap=0.1,
    fill=False,
)
plt.legend()


ax.grid(which="major", axis="y", alpha=0.5)
ax.set_ylabel("Retainment: Actual - Expected")
ax.set_xlabel("")
# ax.set_ylabel("Retainment Difference")
plt.title("")
plt.suptitle("")  # Remove automatic title
if clipped:
    # ax.set_ylim(-51 / num_samples, 51 / num_samples)
    ax.set_ylim(-ylim, ylim)


output_path = (
    OUTPUT_DIR_PLOTS
    / f"boxplot_ALL_seed{'-'.join(map(str,seeds))}_{method}_{solver}_{num_samples}{reuse_str}{drop_trivial_str}{clipped_str}.pdf"
)
print("Writing to", output_path)
plt.tight_layout()
plt.savefig(output_path)
