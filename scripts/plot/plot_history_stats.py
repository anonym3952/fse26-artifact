import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme()


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output")) / "plots"
IGNORE = ["automotive2"]
BARS = "total"
# BARS = "percentage"
LEGEND = False
ABBREVIATE = {"FinancialServices": "Fin.Serv.", "automotive2": "autom."}


def compute_stats(test_dirs: list[Path]) -> pd.DataFrame:
    stats_list = []
    # print(test_dirs)
    # print(sorted(test_dirs))
    for test_dir in sorted(test_dirs, key=lambda p: str(p).lower()):
        if test_dir.name in IGNORE:
            continue
        model_count_path = test_dir / "model_counts.csv"
        assert (
            model_count_path.exists()
        ), f"{model_count_path} not found. Generate by running retainment.py"
        df_mc = pd.read_csv(model_count_path)
        model_count = {
            k: int(v)
            for k, v in df_mc.set_index("file")["model_count"].to_dict().items()
        }

        updates_path = test_dir / "pairs.csv"
        assert (
            updates_path.exists()
        ), f"{updates_path} not found. Generate by running retainment.py"
        df_updates = pd.read_csv(updates_path)

        stats = {
            "path": test_dir,
            "updates": 0,
            "incomparable": 0,
            "unchanged": 0,
            "generalization": 0,
            "specialization": 0,
            "changed": 0,
        }
        for i, row in df_updates.iterrows():
            stats["updates"] += 1
            mc_old = int(model_count[row["file old"]])
            mc_new = int(model_count[row["file new"]])
            mc_conj = int(row["conjunction model count"])
            # s = 1 - mc_conj / mc_old
            # r = 1 - mc_conj / mc_new
            # retainment = s**2 + r**2 + min((1 - s) ** 2, (1 - r) ** 2)
            # print(retainment)

            if mc_conj == 0:
                stats["incomparable"] += 1
            elif mc_old == mc_conj and mc_new == mc_conj:
                stats["unchanged"] += 1
            elif mc_old == mc_conj and mc_new > mc_conj:
                stats["generalization"] += 1
            elif mc_new == mc_conj and mc_old > mc_conj:
                stats["specialization"] += 1
            else:
                stats["changed"] += 1
        stats_list.append(stats)

    return pd.DataFrame(stats_list)


def plot_stats(stats_df: pd.DataFrame, output_path: Path):
    # only keep final components of paths as categories
    categories = stats_df["path"].apply(os.path.basename)
    categories = [
        (ABBREVIATE[l] if l in ABBREVIATE else l.split("_")[0]) for l in categories
    ]

    # Compute raw counts
    incomparable = stats_df["incomparable"].to_numpy()
    unchanged = stats_df["unchanged"].to_numpy()
    generalization = stats_df["generalization"].to_numpy()
    specialization = stats_df["specialization"].to_numpy()
    changed = stats_df["changed"].to_numpy()
    total_updates = stats_df["updates"].to_numpy()

    if BARS == "percentage":
        # Convert to percentages
        incomparable = incomparable / total_updates * 100
        unchanged = unchanged / total_updates * 100
        generalization = generalization / total_updates * 100
        specialization = specialization / total_updates * 100
        changed = changed / total_updates * 100

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.grid(axis="y", linestyle="--", zorder=-1)
    ax.bar(
        categories,
        incomparable,
        label="Incomparable",
        color="gray",
        zorder=3,
    )
    ax.bar(
        categories,
        unchanged,
        bottom=incomparable,
        label="Refactoring",
        zorder=3,
    )
    ax.bar(
        categories,
        generalization,
        bottom=incomparable + unchanged,
        label="Generalization",
        zorder=3,
    )
    ax.bar(
        categories,
        specialization,
        bottom=incomparable + unchanged + generalization,
        label="Specialization",
        zorder=3,
    )
    ax.bar(
        categories,
        changed,
        bottom=incomparable + unchanged + generalization + specialization,
        label="Changing",
        zorder=3,
    )

    if BARS == "percentage":
        ax.set_ylabel("Percentage of updates")
    else:
        ax.set_ylabel("Updates")
    # plt.ylim((0, 250))

    if LEGEND:
        # reverse label order
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(list(reversed(handles)), list(reversed(labels)))

    # redraw horizontal lines that are clipped by the bars
    plt.axhline(0, color="black", linewidth=0.75, zorder=4)

    plt.tight_layout()
    print(f"Saving to {output_path}")
    plt.savefig(output_path)


def main():
    import sys

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <directory> [<output directory>]")
        exit(1)
    directory = Path(sys.argv[1])
    if len(sys.argv) == 3:
        output_dir = Path(sys.argv[2])
    else:
        output_dir = OUTPUT_DIR
    test_dirs = [path for path in directory.iterdir() if path.is_dir()]

    stats_df = compute_stats(test_dirs)
    print(stats_df)

    output_dir.mkdir(exist_ok=True, parents=True)
    output_path = output_dir / f"{directory.name}_evolution_stats.pdf"
    plot_stats(stats_df, output_path)


if __name__ == "__main__":
    main()
