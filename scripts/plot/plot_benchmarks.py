from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

OUTPUT_DIR = Path("output") / "plots"


def plot_rectangles(data):
    # Iterate over each unique directory
    for directory in data["directory"].unique():
        name = Path(directory).name
        # Get the data for this directory
        directory_df = data[data["directory"] == directory]

        # Create a figure
        fig, ax = plt.subplots(figsize=(8, 6))

        # Plot the data for this directory
        for method in directory_df["method"].unique():
            method_group = directory_df[directory_df["method"] == method]
            x = list(method_group["unique_samples"])
            y = list(method_group["time"])
            ax.plot(x, y, "+", label=method)
            ax.fill_between([0] + x, [0, 0], y + y, alpha=0.2, label=method)

        # Set the title and labels
        ax.set_title(name)
        ax.set_xlabel("Unique Samples")
        ax.set_ylabel("Time")
        ax.legend()
        ax.grid(True)

        # plt.show()
        # break
        # Save the plot as a PDF
        plt.savefig(OUTPUT_DIR / f"benchmark_{name}.pdf")

        # Close the figure to free up resources
        plt.close()


def plot_sweetspot(data):
    # Iterate over each unique directory
    sweet_spots = []
    for directory in data["directory"].unique():
        name = Path(directory).name
        # Get the data for this directory
        directory_df = data[data["directory"] == directory]
        # print(name)
        # print(directory_df)
        method_none = directory_df[directory_df["method"] == "none"]
        method_rejection = directory_df[directory_df["method"] == "rejection"]
        method_tseitin = directory_df[directory_df["method"] == "tseitin"]
        t_gen_none = float(method_none["time"].iloc[0])
        t_gen_reject = float(method_rejection["time"].iloc[0])
        t_gen_tseitin = float(method_tseitin["time"].iloc[0])
        samples_none = int(method_none["unique_samples"].iloc[0])
        samples_rejection = int(method_rejection["unique_samples"].iloc[0])
        samples_tseitin = int(method_tseitin["unique_samples"].iloc[0])

        sweetspot_rejection = (t_gen_reject - t_gen_none) / (
            samples_none - samples_rejection
        )
        sweetspot_tseitin = (t_gen_tseitin - t_gen_none) / (
            samples_none - samples_tseitin
        )
        sweet_spots.append(
            {
                "history": directory,
                "sweetspot tseitin": sweetspot_tseitin,
                "sweet spot rejection": sweetspot_rejection,
            }
        )
        """
        samples_none * x + t_gen_none > samples_reject * x + t_gen_reject
        samples_none * x - samples_reject * x  >  t_gen_reject - t_gen_none
        x  >  (t_gen_reject - t_gen_none) / (samples_none - samples_reject)
        """

        # Create a figure
        fig, ax = plt.subplots(figsize=(5, 3))
        g = 2 * sweetspot_tseitin
        plt.plot(
            [0, g],
            [t_gen_none, t_gen_none + g * samples_none],
            linestyle="dashed",
            label="baseline",
        )
        plt.plot(
            [0, g],
            [
                t_gen_reject,
                t_gen_reject + g * samples_rejection,
            ],
            label="rejection",
        )
        plt.plot(
            [0, g],
            [
                t_gen_tseitin,
                t_gen_tseitin + g * samples_tseitin,
            ],
            label="tseitin",
        )

        # Set the title and labels
        ax.set_ylim(bottom=0)
        ax.set_xlim(left=0, right=g)
        ax.set_title(name)
        ax.set_xlabel("Average test duration per sample in seconds")
        ax.set_ylabel("Overall runtime in seconds")
        ax.legend()
        ax.grid(True)
        plt.tight_layout()
        # plt.show()

        # break
        # Save the plot as a PDF
        output_path = OUTPUT_DIR / f"benchmark_sweetspot_{name}.pdf"
        plt.savefig(output_path)
        print("saved", output_path)

        # Close the figure to free up resources
        plt.close()

    df = pd.DataFrame(sweet_spots)
    output_path = OUTPUT_DIR / "sweet_spots.csv"
    df.to_csv(output_path)
    print("wrote to", output_path)


def main():
    import sys

    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <benchmarks.csv>")
        exit(1)

    file_path = Path(sys.argv[1])
    data = pd.read_csv(file_path)

    # Group by 'directory', 'method', 'sampler', and 'total_samples',
    # and then aggregate 'unique_samples' and 'time' by taking the mean
    averaged_df = (
        data.groupby(["directory", "method", "sampler", "total_samples"])[
            ["unique_samples", "time"]
        ]
        .mean()
        .reset_index()
    )

    # Print the resulting DataFrame
    print(averaged_df)
    plot_sweetspot(averaged_df)
    # plot_rectangles(averaged_df)


if __name__ == "__main__":
    main()
