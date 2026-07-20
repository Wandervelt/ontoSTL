#!/usr/bin/env python3
import argparse
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd


def resolve_columns(df):
    """Return canonical/non-canonical y-columns and optional std columns."""
    # New averaged CSV format.
    if (
        "canonical_mean_cumulative_total_time_s" in df.columns
        and "non_canonical_mean_cumulative_total_time_s" in df.columns
    ):
        return (
            "canonical_mean_cumulative_total_time_s",
            "non_canonical_mean_cumulative_total_time_s",
            "canonical_std_cumulative_total_time_s",
            "non_canonical_std_cumulative_total_time_s",
        )

    # Older single-run combined CSV format.
    if (
        "canonical_cumulative_total_time_s" in df.columns
        and "non_canonical_cumulative_total_time_s" in df.columns
    ):
        return (
            "canonical_cumulative_total_time_s",
            "non_canonical_cumulative_total_time_s",
            None,
            None,
        )

    raise ValueError(
        "Could not find expected canonical/non-canonical cumulative runtime columns "
        "in the CSV."
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Replot canonical vs non-canonical cumulative total runtime "
            "from combined_average_cumulative_total_runtime.csv without rerunning analysis."
        )
    )
    parser.add_argument(
        "--input-csv",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            "scalability",
            "total",
            "combined_average_cumulative_total_runtime.csv",
        ),
        help="Path to combined cumulative runtime CSV.",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            "scalability",
            "total",
            "canonical_vs_noncanonical_avg_cumulative_total_time.png",
        ),
        help="Output PNG path.",
    )
    args = parser.parse_args()

    input_csv = os.path.abspath(args.input_csv)
    output_png = os.path.abspath(args.output)

    if not os.path.isfile(input_csv):
        print(f"Error: CSV not found: {input_csv}")
        sys.exit(1)

    df = pd.read_csv(input_csv)
    if "formula_count" not in df.columns:
        print("Error: CSV is missing required column: formula_count")
        sys.exit(1)

    try:
        c_col, n_col, c_std_col, n_std_col = resolve_columns(df)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    # Keep only numeric rows and sorted x-axis.
    plot_df = df[["formula_count", c_col, n_col] + ([c_std_col, n_std_col] if c_std_col else [])].copy()
    for col in plot_df.columns:
        plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")
    plot_df = plot_df.dropna(subset=["formula_count", c_col, n_col]).sort_values("formula_count")

    x = plot_df["formula_count"].to_numpy()
    c = plot_df[c_col].to_numpy()
    n = plot_df[n_col].to_numpy()

    plt.figure(figsize=(10, 6))
    plt.plot(x, c, label="Canonical cumulative total", linewidth=2.3, color="tab:blue")
    plt.plot(x, n, label="Non-canonical cumulative total", linewidth=2.3, color="tab:orange")

    # Draw uncertainty bands when std columns are available.
    if c_std_col and n_std_col and c_std_col in plot_df.columns and n_std_col in plot_df.columns:
        c_std = plot_df[c_std_col].fillna(0.0).to_numpy()
        n_std = plot_df[n_std_col].fillna(0.0).to_numpy()
        plt.fill_between(x, c - c_std, c + c_std, color="tab:blue", alpha=0.15, linewidth=0)
        plt.fill_between(x, n - n_std, n + n_std, color="tab:orange", alpha=0.15, linewidth=0)

    plt.xlabel("Number of Formulas Processed")
    plt.ylabel("Cumulative Total Time (s)")
    # Intentionally no title.
    plt.xlim(left=0)
    plt.ylim(bottom=0)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    os.makedirs(os.path.dirname(output_png), exist_ok=True)
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Plot written to: {output_png}")


if __name__ == "__main__":
    main()
