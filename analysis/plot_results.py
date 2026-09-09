import csv
import matplotlib.pyplot as plt


RESULTS_FILE = "analysis/liquidity_results.csv"
OUTPUT_FILE = "analysis/slippage_by_liquidity.png"


def load_results():
    data = {}

    with open(RESULTS_FILE, newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            scenario = row["scenario"]
            size = row["size"]

            # Remove tiny floating-point values such as -1e-15
            slippage = max(
                0.0,
                float(row["average_slippage"])
            )

            data[(scenario, size)] = slippage

    return data


def create_chart(data):
    sizes = ["SMALL", "MEDIUM", "LARGE"]

    deep = [
        data[("DEEP", size)]
        for size in sizes
    ]

    thin = [
        data[("THIN", size)]
        for size in sizes
    ]

    x = range(len(sizes))
    width = 0.36

    fig, ax = plt.subplots(figsize=(8, 5))

    deep_bars = ax.bar(
        [position - width / 2 for position in x],
        deep,
        width,
        label="Deep liquidity"
    )

    thin_bars = ax.bar(
        [position + width / 2 for position in x],
        thin,
        width,
        label="Thin liquidity"
    )

    ax.set_xlabel("Market order size")
    ax.set_ylabel("Average slippage (price units)")
    ax.set_title(
        "Market Order Slippage Under Deep vs Thin Liquidity"
    )

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        ["Small", "Medium", "Large"]
    )

    ax.legend()

    ax.bar_label(
        deep_bars,
        fmt="%.4f",
        padding=3,
        fontsize=8
    )

    ax.bar_label(
        thin_bars,
        fmt="%.4f",
        padding=3,
        fontsize=8
    )

    fig.tight_layout()
    fig.savefig(
        OUTPUT_FILE,
        dpi=300,
        bbox_inches="tight"
    )

    print("Chart saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    results = load_results()
    create_chart(results)
