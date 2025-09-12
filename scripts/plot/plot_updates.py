import os
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

"""
python scripts/plot_pairs.py test/unified/uClibc/pairs.csv uClibc
python scripts/plot_pairs.py test/unified/Fiasco/pairs.csv Fiasco 7
python scripts/plot_pairs.py test/unified/FinancialServices/pairs.csv FinancialServices 7
python scripts/plot_pairs.py test/unified/BusyBox/pairs.csv BusyBox
python scripts/plot_pairs.py test/unified/soletta/pairs.csv Soletta         
"""


OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "output")) / "plots"
# COLOR_MAP = {
#     "retainment": "#1976D2",
#     "percentage of old": "#388E3C",
#     "percentage of new": "#FF9800",
# }
COLOR_MAP = {
    "retainment": "#8CC400",
    "percentage of old": "#bc1401",
    "percentage of new": "#2a87e5",
}
COLOR_MAP_DARK = {
    "retainment": "#8CC400",
    "percentage of old": "#7a0d01",
    "percentage of new": "#1359a0",
}
LIGHT_GRAY = "#EDEDED"
MODE = "bars"  # "histograms"
TITLE = False


def plot_histogram(data, key, display_name, title, width, height):
    figure = plt.figure(figsize=(width, height))

    plt.grid(
        True,
        which="major",
        axis="y",
        linestyle="--",
        linewidth=0.5,
        zorder=1,
    )
    plt.hist(
        data[key],
        bins=10,
        range=(0, 1),
        zorder=2,
        color=COLOR_MAP[key],
    )
    plt.ylim(top=len(data[key]))
    plt.ylabel("updates")
    plt.xlim(right=1.05)
    plt.xlabel(display_name)
    if title:
        plt.title(title)
    # plt.legend()
    # plt.show()
    return figure


def plot_bars(data, key, display_name, title, width, height):
    figure = plt.figure(figsize=(width, height))
    num_bars = len(data[key])
    bar_width = 0.9

    plt.grid(
        True,
        which="major",
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
        color=LIGHT_GRAY,
    )
    plt.bar(
        x=range(1, 1 + num_bars),
        height=data[key],
        width=bar_width,
        zorder=2,
        color=COLOR_MAP_DARK[key],
    )
    plt.bar(
        x=range(1, 1 + num_bars),
        height=data["retainment"],
        width=bar_width,
        zorder=3,
        color=COLOR_MAP[key],
    )

    # redraw horizontal lines that are clipped by the bars
    plt.axhline(0, color="black", linewidth=0.75, zorder=4)
    plt.axhline(1, color="black", linewidth=0.75, zorder=4)

    # plt.xlabel("updates")
    plt.xlim(left=0.5 - (1 - bar_width) / 2, right=num_bars + 0.5 + (1 - bar_width) / 2)
    plt.ylabel(display_name)
    plt.ylim((0, 1))
    if num_bars < 14:
        ticks = range(1, num_bars + 1)
    else:
        ticks = np.linspace(1, num_bars, 7, dtype=int)
    plt.xticks(ticks)
    if TITLE and title:
        plt.title(title)
    # plt.legend()
    # plt.show()
    plt.tight_layout()
    return figure


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <file.csv> <title> [<width>]")
        exit(1)

    file_path = Path(sys.argv[1])
    title = sys.argv[2]
    width = 15
    if len(sys.argv) == 4:
        width = int(sys.argv[3])

    # read csv
    df = pd.read_csv(file_path)

    for key, display_name in [
        ("retainment", "ER*"),
        # ("percentage of old", "max_keep"),
        # ("percentage of new", "max_use"),
    ]:
        if MODE == "histograms":
            fig = plot_histogram(df, key, display_name, title, width, height=3)
        elif MODE == "bars":
            fig = plot_bars(df, key, display_name, title, width, height=3)
        else:
            print(f"Unknown mode: {MODE}")
            exit(1)

        # save figure
        (OUTPUT_DIR / MODE).mkdir(exist_ok=True)
        output_path = OUTPUT_DIR / MODE / (title + "_" + display_name + ".pdf")
        print(f"Saving to {output_path}")
        fig.savefig(output_path)
