#!/usr/bin/env python3
import argparse
import csv
import os
import sys


def parse_args():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(
        description="Show the most repeated topology groups from a pure-topology groups CSV."
    )
    parser.add_argument(
        "--input-csv",
        default=os.path.join(current_dir, "pure_topology_canonical_groups.csv"),
        help=(
            "Input groups CSV path "
            "(default: code/canon_and_non-canon_comp/pure_topology_canonical_groups.csv)"
        ),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of most repeated groups to print (default: 10).",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=2,
        help="Minimum group size to count as repeated (default: 2).",
    )
    parser.add_argument(
        "--max-members",
        type=int,
        default=12,
        help="Max member req files to print for each group (default: 12).",
    )
    return parser.parse_args()


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def main():
    args = parse_args()
    input_csv = os.path.abspath(args.input_csv)

    if not os.path.isfile(input_csv):
        print(f"Error: CSV not found: {input_csv}")
        print("Tip: run count_distinct_pure_topology_canonical.py or *_noncanonical.py first.")
        sys.exit(1)

    with open(input_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"No rows found in CSV: {input_csv}")
        sys.exit(1)

    repeated = [r for r in rows if to_int(r.get("group_size")) >= args.min_size]
    repeated.sort(
        key=lambda r: (-to_int(r.get("group_size")), to_int(r.get("group_rank"), 10**9))
    )

    top_rows = repeated[: args.top_k]

    print("=== Top Repeated Pure Topologies ===")
    print(f"Input CSV:          {input_csv}")
    print(f"Total groups:       {len(rows)}")
    print(f"Repeated groups:    {len(repeated)} (min-size={args.min_size})")
    print(f"Top groups shown:   {len(top_rows)}")

    if not top_rows:
        print("\nNo repeated groups matched the filter.")
        return

    print("")
    for i, row in enumerate(top_rows, start=1):
        group_rank = row.get("group_rank", "?")
        group_size = to_int(row.get("group_size"))
        signature = row.get("signature_repr", "").strip()
        all_members = row.get("all_members", "")
        members = [m for m in all_members.split(";") if m]

        shown_members = members[: args.max_members]
        hidden_count = max(0, len(members) - len(shown_members))
        members_text = ", ".join(shown_members) if shown_members else "(none)"
        if hidden_count > 0:
            members_text += f", ... (+{hidden_count} more)"

        print(f"{i}. group_rank={group_rank} | size={group_size}")
        print(f"   signature: {signature}")
        print(f"   members:   {members_text}")


if __name__ == "__main__":
    main()
