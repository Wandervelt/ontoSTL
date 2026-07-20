#!/usr/bin/env python3
import argparse
import csv
import os
import pickle
import re
import sys
from collections import Counter, defaultdict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from abstract_compare_core import MODE_PURE_TOPOLOGY, normalized_signature, req_sort_key


def list_req_pickles(directory: str):
    files = {}
    for name in os.listdir(directory):
        if re.fullmatch(r"req\d+\.pkl", name):
            files[name] = os.path.join(directory, name)
    return files


def signature_repr(sig) -> str:
    return repr(sig)


def group_status(size: int) -> str:
    return "singleton" if size == 1 else "repeated"


def load_signatures(directory: str):
    req_to_sig = {}
    groups = defaultdict(list)
    errors = []

    for name, path in list_req_pickles(directory).items():
        try:
            with open(path, "rb") as f:
                ast = pickle.load(f)
            sig = normalized_signature(ast, MODE_PURE_TOPOLOGY)
            req_to_sig[name] = sig
            groups[sig].append(name)
        except Exception as exc:
            errors.append((name, str(exc)))

    for members in groups.values():
        members.sort(key=req_sort_key)

    return req_to_sig, groups, errors


def rank_groups(groups):
    ordered = sorted(
        groups.items(),
        key=lambda kv: (-len(kv[1]), req_sort_key(kv[1][0]), signature_repr(kv[0])),
    )
    return {sig: idx for idx, (sig, _) in enumerate(ordered, start=1)}


def build_rows(non_req_to_sig, non_groups, can_req_to_sig, can_groups, shared_names, non_ranks, can_ranks):
    transition_rows = []
    edge_members = defaultdict(list)

    for name in shared_names:
        non_sig = non_req_to_sig[name]
        can_sig = can_req_to_sig[name]
        non_size = len(non_groups[non_sig])
        can_size = len(can_groups[can_sig])
        non_status = group_status(non_size)
        can_status = group_status(can_size)

        transition_rows.append(
            {
                "req": name,
                "noncanonical_group_rank": non_ranks[non_sig],
                "noncanonical_group_size": non_size,
                "noncanonical_group_status": non_status,
                "canonical_group_rank": can_ranks[can_sig],
                "canonical_group_size": can_size,
                "canonical_group_status": can_status,
                "same_signature": non_sig == can_sig,
                "same_group_rank": non_ranks[non_sig] == can_ranks[can_sig],
                "transition": f"{non_status}->{can_status}",
                "noncanonical_signature_repr": signature_repr(non_sig),
                "canonical_signature_repr": signature_repr(can_sig),
            }
        )
        edge_members[(non_sig, can_sig)].append(name)

    transition_rows.sort(key=lambda row: req_sort_key(row["req"]))
    return transition_rows, edge_members


def write_transition_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "req",
                "noncanonical_group_rank",
                "noncanonical_group_size",
                "noncanonical_group_status",
                "canonical_group_rank",
                "canonical_group_size",
                "canonical_group_status",
                "same_signature",
                "same_group_rank",
                "transition",
                "noncanonical_signature_repr",
                "canonical_signature_repr",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def write_edge_csv(path, edge_members, non_groups, can_groups, non_ranks, can_ranks):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    edges = []

    for (non_sig, can_sig), members in edge_members.items():
        members = sorted(members, key=req_sort_key)
        edges.append(
            {
                "noncanonical_group_rank": non_ranks[non_sig],
                "noncanonical_group_size": len(non_groups[non_sig]),
                "noncanonical_group_status": group_status(len(non_groups[non_sig])),
                "canonical_group_rank": can_ranks[can_sig],
                "canonical_group_size": len(can_groups[can_sig]),
                "canonical_group_status": group_status(len(can_groups[can_sig])),
                "overlap_size": len(members),
                "all_members": ";".join(members),
                "noncanonical_signature_repr": signature_repr(non_sig),
                "canonical_signature_repr": signature_repr(can_sig),
            }
        )

    edges.sort(
        key=lambda row: (
            row["noncanonical_group_rank"],
            row["canonical_group_rank"],
            -row["overlap_size"],
        )
    )

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "noncanonical_group_rank",
                "noncanonical_group_size",
                "noncanonical_group_status",
                "canonical_group_rank",
                "canonical_group_size",
                "canonical_group_status",
                "overlap_size",
                "all_members",
                "noncanonical_signature_repr",
                "canonical_signature_repr",
            ],
        )
        writer.writeheader()
        writer.writerows(edges)


def format_group_sample(groups, sig, max_members):
    members = groups[sig]
    shown = members[:max_members]
    text = ", ".join(shown)
    hidden = len(members) - len(shown)
    if hidden > 0:
        text += f", ... (+{hidden} more)"
    return text


def main():
    parser = argparse.ArgumentParser(
        description="Analyze how non-canonical pure-topology groups map into canonical pure-topology groups."
    )
    parser.add_argument(
        "--noncanonical-dir",
        default=os.path.join(CODE_DIR, "results", "forward"),
        help="Directory with non-canonical req*.pkl files (default: code/results/forward)",
    )
    parser.add_argument(
        "--canonical-dir",
        default=os.path.join(CODE_DIR, "results_canonical", "forward"),
        help="Directory with canonical req*.pkl files (default: code/results_canonical/forward)",
    )
    parser.add_argument(
        "--out-transitions-csv",
        default=os.path.join(CURRENT_DIR, "pure_topology_req_transitions.csv"),
        help="CSV path for per-requirement topology transitions.",
    )
    parser.add_argument(
        "--out-edges-csv",
        default=os.path.join(CURRENT_DIR, "pure_topology_group_edges.csv"),
        help="CSV path for non-canonical -> canonical group overlap edges.",
    )
    parser.add_argument(
        "--max-report",
        type=int,
        default=10,
        help="Maximum examples to print per summary section.",
    )
    parser.add_argument(
        "--max-members",
        type=int,
        default=8,
        help="Maximum req files to show inside one example group.",
    )
    args = parser.parse_args()

    non_dir = os.path.abspath(args.noncanonical_dir)
    can_dir = os.path.abspath(args.canonical_dir)

    if not os.path.isdir(non_dir):
        print(f"Error: Non-canonical directory not found: {non_dir}")
        sys.exit(1)
    if not os.path.isdir(can_dir):
        print(f"Error: Canonical directory not found: {can_dir}")
        sys.exit(1)

    non_req_to_sig, non_groups, non_errors = load_signatures(non_dir)
    can_req_to_sig, can_groups, can_errors = load_signatures(can_dir)

    non_names = set(non_req_to_sig)
    can_names = set(can_req_to_sig)
    shared_names = sorted(non_names & can_names, key=req_sort_key)
    missing_in_canonical = sorted(non_names - can_names, key=req_sort_key)
    missing_in_noncanonical = sorted(can_names - non_names, key=req_sort_key)

    non_ranks = rank_groups(non_groups)
    can_ranks = rank_groups(can_groups)

    transition_rows, edge_members = build_rows(
        non_req_to_sig,
        non_groups,
        can_req_to_sig,
        can_groups,
        shared_names,
        non_ranks,
        can_ranks,
    )

    write_transition_csv(os.path.abspath(args.out_transitions_csv), transition_rows)
    write_edge_csv(
        os.path.abspath(args.out_edges_csv),
        edge_members,
        non_groups,
        can_groups,
        non_ranks,
        can_ranks,
    )

    transition_counts = Counter(row["transition"] for row in transition_rows)
    changed_rows = [row for row in transition_rows if not row["same_signature"]]
    unchanged_rows = len(transition_rows) - len(changed_rows)

    non_to_can_targets = defaultdict(set)
    can_from_non_sources = defaultdict(set)
    for (non_sig, can_sig), members in edge_members.items():
        if members:
            non_to_can_targets[non_sig].add(can_sig)
            can_from_non_sources[can_sig].add(non_sig)

    disappeared_non_sigs = set(non_groups) - set(can_groups)
    new_can_sigs = set(can_groups) - set(non_groups)

    singleton_to_repeated = [
        row for row in transition_rows
        if row["noncanonical_group_status"] == "singleton"
        and row["canonical_group_status"] == "repeated"
    ]
    repeated_to_singleton = [
        row for row in transition_rows
        if row["noncanonical_group_status"] == "repeated"
        and row["canonical_group_status"] == "singleton"
    ]

    merged_non_singletons = [
        sig for sig, members in non_groups.items()
        if len(members) == 1
        and len(non_to_can_targets.get(sig, set())) == 1
        and len(can_groups[next(iter(non_to_can_targets[sig]))]) > 1
    ]
    merged_non_repeated = [
        sig for sig, members in non_groups.items()
        if len(members) > 1
        and len(non_to_can_targets.get(sig, set())) == 1
        and len(can_from_non_sources[next(iter(non_to_can_targets[sig]))]) > 1
    ]
    split_non_repeated = [
        sig for sig, members in non_groups.items()
        if len(members) > 1 and len(non_to_can_targets.get(sig, set())) > 1
    ]

    print("=== Pure Topology Transition Analysis ===")
    print(f"Non-canonical dir:             {non_dir}")
    print(f"Canonical dir:                 {can_dir}")
    print(f"Shared req*.pkl files:         {len(shared_names)}")
    print(f"Non-canonical topology groups: {len(non_groups)}")
    print(f"Canonical topology groups:     {len(can_groups)}")
    print(f"Unchanged pure-topology sigs:  {unchanged_rows}")
    print(f"Changed pure-topology sigs:    {len(changed_rows)}")
    print(f"Missing in canonical side:     {len(missing_in_canonical)}")
    print(f"Missing in non-canonical side: {len(missing_in_noncanonical)}")
    print(f"Non-canonical parse errors:    {len(non_errors)}")
    print(f"Canonical parse errors:        {len(can_errors)}")

    print("\nPer-formula status transitions:")
    for transition in ["singleton->singleton", "singleton->repeated", "repeated->singleton", "repeated->repeated"]:
        print(f"  {transition}: {transition_counts.get(transition, 0)}")

    print("\nGroup-level topology effects:")
    print(f"  Non-canonical signatures absent in canonical: {len(disappeared_non_sigs)}")
    print(f"  Canonical signatures not seen in non-canonical: {len(new_can_sigs)}")
    print(f"  Non-canonical singleton groups merged into larger canonical groups: {len(merged_non_singletons)}")
    print(f"  Non-canonical repeated groups merged into one shared canonical group: {len(merged_non_repeated)}")
    print(f"  Non-canonical repeated groups split across multiple canonical groups: {len(split_non_repeated)}")

    if singleton_to_repeated:
        print(f"\nExamples of singleton -> repeated formulas (showing up to {args.max_report}):")
        for row in singleton_to_repeated[: args.max_report]:
            print(
                f"  {row['req']}: noncanon rank {row['noncanonical_group_rank']} size {row['noncanonical_group_size']} "
                f"-> canon rank {row['canonical_group_rank']} size {row['canonical_group_size']}"
            )

    if repeated_to_singleton:
        print(f"\nExamples of repeated -> singleton formulas (showing up to {args.max_report}):")
        for row in repeated_to_singleton[: args.max_report]:
            print(
                f"  {row['req']}: noncanon rank {row['noncanonical_group_rank']} size {row['noncanonical_group_size']} "
                f"-> canon rank {row['canonical_group_rank']} size {row['canonical_group_size']}"
            )

    if merged_non_singletons:
        print(f"\nExamples of non-canonical singleton groups absorbed into repeated canonical groups:")
        for sig in merged_non_singletons[: args.max_report]:
            can_sig = next(iter(non_to_can_targets[sig]))
            print(
                f"  noncanon rank {non_ranks[sig]} ({format_group_sample(non_groups, sig, args.max_members)}) "
                f"-> canon rank {can_ranks[can_sig]} size {len(can_groups[can_sig])}"
            )

    if merged_non_repeated:
        print(f"\nExamples of non-canonical repeated groups merging into a shared canonical group:")
        for sig in merged_non_repeated[: args.max_report]:
            can_sig = next(iter(non_to_can_targets[sig]))
            print(
                f"  noncanon rank {non_ranks[sig]} size {len(non_groups[sig])} "
                f"-> canon rank {can_ranks[can_sig]} size {len(can_groups[can_sig])}"
            )

    if split_non_repeated:
        print(f"\nExamples of non-canonical repeated groups splitting across canonical groups:")
        for sig in split_non_repeated[: args.max_report]:
            targets = sorted(
                non_to_can_targets[sig],
                key=lambda target_sig: (can_ranks[target_sig], signature_repr(target_sig)),
            )
            target_text = ", ".join(
                f"canon rank {can_ranks[target_sig]} size {len(can_groups[target_sig])}"
                for target_sig in targets[: args.max_members]
            )
            extra = len(targets) - min(len(targets), args.max_members)
            if extra > 0:
                target_text += f", ... (+{extra} more)"
            print(
                f"  noncanon rank {non_ranks[sig]} size {len(non_groups[sig])} -> {target_text}"
            )

    print(f"\nWrote per-requirement transitions CSV to: {os.path.abspath(args.out_transitions_csv)}")
    print(f"Wrote group overlap CSV to:              {os.path.abspath(args.out_edges_csv)}")

    if non_errors or can_errors or missing_in_canonical or missing_in_noncanonical:
        sys.exit(1)


if __name__ == "__main__":
    main()
