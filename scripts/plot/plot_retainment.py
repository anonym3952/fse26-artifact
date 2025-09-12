import os
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

"""
Plot total predicted expected retainment
`python plot_retainment.py test/unified`
"""

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output")) / "plots" / "bars"
IGNORE = ["automotive2"]
ABBREVIATE = {"FinancialServices": "Fin.Serv."}
COLUMN = "retainment"
# COLUMN = "percentage of old"
# COLUMN = "percentage of new"
COLOR_MAP = {
    "retainment": "#8CC400",
    "percentage of old": "#bc1401",
    "percentage of new": "#2a87e5",
}


def calculate_er(test_dirs: list[Path]) -> pd.DataFrame:
    er_data: dict[str, float] = dict()
    for path in sorted(test_dirs, key=lambda p: str(p).lower()):
        if path.name in IGNORE:
            continue
        csv_path = path / "pairs.csv"
        assert (
            csv_path.exists()
        ), f"{csv_path} not found. Generate by running retainment.py"
        update_df = pd.read_csv(csv_path)
        er_data[path.name] = update_df[COLUMN].mean()
    return pd.DataFrame(er_data.items())


def plot_er(df: pd.DataFrame):
    figure = plt.figure(figsize=(5, 3))
    num_bars = len(df)
    bar_width = 0.9
    plt.grid(
        axis="y",
        linestyle="--",
        linewidth=0.5,
        zorder=1,
    )
    plt.bar(
        x=range(1, 1 + num_bars),
        height=[1] * num_bars,
        width=bar_width,
        zorder=0.5,
        color="#EDEDED",
    )
    plt.bar(
        x=range(1, 1 + num_bars),
        height=df[1],
        tick_label=[
            (ABBREVIATE[l] if l in ABBREVIATE else l.split("_")[0]) for l in df[0]
        ],
        width=bar_width,
        zorder=3,
        color=COLOR_MAP[COLUMN],
    )

    # redraw horizontal lines that are clipped by the bars
    plt.axhline(0, color="black", linewidth=0.75, zorder=4)
    plt.axhline(1, color="black", linewidth=0.75, zorder=4)

    plt.ylabel("Average ER*")
    plt.ylim((0, 1))
    plt.xlim(left=0.5 - (1 - bar_width) / 2, right=num_bars + 0.5 + (1 - bar_width) / 2)
    if num_bars < 14:
        ticks = range(1, num_bars + 1)
    else:
        ticks = np.linspace(1, num_bars, 7, dtype=int)
    plt.xticks(ticks)
    # plt.show()
    plt.tight_layout()
    return figure


def main():
    import sys

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <directory>")
        exit(1)
    directory = Path(sys.argv[1])
    test_dirs = [path for path in directory.iterdir() if path.is_dir()]
    df = calculate_er(test_dirs)
    print(df)
    fig = plot_er(df)

    # save figure
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    output_path = OUTPUT_DIR / f"{directory.name}_avg_{COLUMN}.pdf"
    print(f"Saving to {output_path}")
    fig.savefig(output_path)


if __name__ == "__main__":
    main()
