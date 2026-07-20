#!/usr/bin/env python3
import argparse
import csv
import os
import pickle
import re
import sys
from collections import defaultdict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from abstract_compare_core import MODE_PURE_TOPOLOGY, normalized_signature, req_sort_key


def list_req_pickles(directory: str):
    files = []
    for name in os.listdir(directory):
        if re.fullmatch(r"req\d+\.pkl", name):
            files.append(name)
    return sorted(files, key=req_sort_key)


def main():
    parser = argparse.ArgumentParser(
        description="Count distinct pure-topology formulas in canonical ASTs."
    )
    parser.add_argument(
        "--input-dir",
        default=os.path.join(os.path.dirname(CURRENT_DIR), "results_canonical", "forward"),
        help="Directory with canonical req*.pkl files (default: code/results_canonical/forward)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=20,
        help="How many most-frequent topology classes to print.",
    )
    parser.add_argument(
        "--max-members",
        type=int,
        default=8,
        help="Max req files to print per displayed class.",
    )
    parser.add_argument(
        "--out-csv",
        default=os.path.join(CURRENT_DIR, "pure_topology_canonical_groups.csv"),
        help="CSV output path for all topology groups.",
    )
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    out_csv = os.path.abspath(args.out_csv)

    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found: {input_dir}")
        sys.exit(1)

    req_files = list_req_pickles(input_dir)
    if not req_files:
        print(f"No req*.pkl files found in: {input_dir}")
        sys.exit(1)

    groups = defaultdict(list)
    errors = []

    for name in req_files:
        path = os.path.join(input_dir, name)
        try:
            with open(path, "rb") as f:
                ast = pickle.load(f)
            sig = normalized_signature(ast, MODE_PURE_TOPOLOGY)
            groups[sig].append(name)
        except Exception as exc:
            errors.append((name, str(exc)))

    sorted_groups = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)
    total_files = len(req_files)
    distinct_topologies = len(sorted_groups)

    print("=== Pure Topology Distinct Count (Canonical Only) ===")
    print(f"Input dir:                    {input_dir}")
    print(f"Total req*.pkl files:         {total_files}")
    print(f"Distinct topology signatures: {distinct_topologies}")
    print(f"Errors:                       {len(errors)}")

    singleton_count = sum(1 for _, members in sorted_groups if len(members) == 1)
    repeated_count = distinct_topologies - singleton_count
    print(f"Singleton topologies:         {singleton_count}")
    print(f"Repeated topologies:          {repeated_count}")

    print(f"\nTop {min(args.top_k, len(sorted_groups))} topology classes by frequency:")
    for idx, (sig, members) in enumerate(sorted_groups[: args.top_k], start=1):
        sample = ", ".join(members[: args.max_members])
        remainder = len(members) - min(len(members), args.max_members)
        if remainder > 0:
            sample = f"{sample}, ... (+{remainder} more)"
        print(f"{idx}. count={len(members)} | sample={sample}")

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["group_rank", "group_size", "representative_req", "signature_repr", "all_members"],
        )
        writer.writeheader()
        for rank, (sig, members) in enumerate(sorted_groups, start=1):
            writer.writerow(
                {
                    "group_rank": rank,
                    "group_size": len(members),
                    "representative_req": members[0],
                    "signature_repr": repr(sig),
                    "all_members": ";".join(members),
                }
            )

    print(f"\nGroup CSV written to: {out_csv}")

    if errors:
        print("\nSample errors:")
        for name, message in errors[:10]:
            print(f" - {name}: {message}")
        if len(errors) > 10:
            print(f" ... and {len(errors) - 10} more")
        sys.exit(1)


if __name__ == "__main__":
    main()
