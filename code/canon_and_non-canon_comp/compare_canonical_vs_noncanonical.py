#!/usr/bin/env python3
import argparse
import math
import os
import pickle
import re
import sys
from pathlib import Path

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(CURRENT_DIR)
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from pytelo_modified.stl import Operation, STLFormula


def check_asts_equal(ast1: STLFormula, ast2: STLFormula) -> bool:
    """Recursively compare ASTs for semantic equality."""
    if not isinstance(ast1, STLFormula) or not isinstance(ast2, STLFormula):
        return False

    if ast1.op != ast2.op:
        return False

    if ast1.op == Operation.PRED:
        return (
            ast1.variable == ast2.variable
            and ast1.relation == ast2.relation
            and math.isclose(ast1.threshold, ast2.threshold)
        )
    if ast1.op == Operation.VAR:
        return ast1.variable == ast2.variable
    if ast1.op == Operation.BOOL:
        return ast1.value == ast2.value
    if ast1.op in (Operation.ALWAYS, Operation.EVENT):
        return (
            math.isclose(ast1.low, ast2.low)
            and math.isclose(ast1.high, ast2.high)
            and check_asts_equal(ast1.child, ast2.child)
        )
    if ast1.op == Operation.NOT:
        return check_asts_equal(ast1.child, ast2.child)
    if ast1.op == Operation.UNTIL:
        return (
            math.isclose(ast1.low, ast2.low)
            and math.isclose(ast1.high, ast2.high)
            and check_asts_equal(ast1.left, ast2.left)
            and check_asts_equal(ast1.right, ast2.right)
        )
    if ast1.op == Operation.IMPLIES:
        return check_asts_equal(ast1.left, ast2.left) and check_asts_equal(ast1.right, ast2.right)
    if ast1.op in (Operation.AND, Operation.OR):
        if not hasattr(ast1, "children") or not hasattr(ast2, "children"):
            return False
        if len(ast1.children) != len(ast2.children):
            return False

        remaining = list(ast2.children)
        for child1 in ast1.children:
            found = False
            for i, child2 in enumerate(remaining):
                if check_asts_equal(child1, child2):
                    remaining.pop(i)
                    found = True
                    break
            if not found:
                return False
        return len(remaining) == 0

    return False


def req_sort_key(filename: str):
    match = re.fullmatch(r"req(\d+)\.pkl", filename)
    if match:
        return (0, int(match.group(1)))
    return (1, filename)


def list_req_pickles(directory: str) -> dict:
    files = {}
    for name in os.listdir(directory):
        if re.fullmatch(r"req\d+\.pkl", name):
            files[name] = os.path.join(directory, name)
    return files


def print_section(title: str, items: list, max_report: int):
    if not items:
        return
    print(f"\n{title}:")
    for name in items[:max_report]:
        print(f" - {name}")
    extra = len(items) - max_report
    if extra > 0:
        print(f" ... and {extra} more")


def main():
    parser = argparse.ArgumentParser(
        description="Compare canonical vs non-canonical forward AST pickles by req number."
    )
    parser.add_argument(
        "--canonical-dir",
        default=os.path.join(CODE_DIR, "results_canonical", "forward"),
        help="Canonical forward directory (default: code/results_canonical/forward)",
    )
    parser.add_argument(
        "--noncanonical-dir",
        default=os.path.join(CODE_DIR, "results", "forward"),
        help="Non-canonical forward directory (default: code/results/forward)",
    )
    parser.add_argument(
        "--max-report",
        type=int,
        default=40,
        help="Maximum number of filenames to print per mismatch/missing section.",
    )
    args = parser.parse_args()

    canonical_dir = os.path.abspath(args.canonical_dir)
    noncanonical_dir = os.path.abspath(args.noncanonical_dir)

    if not os.path.isdir(canonical_dir):
        print(f"Error: Canonical directory not found: {canonical_dir}")
        sys.exit(1)
    if not os.path.isdir(noncanonical_dir):
        print(f"Error: Non-canonical directory not found: {noncanonical_dir}")
        sys.exit(1)

    canonical_files = list_req_pickles(canonical_dir)
    noncanonical_files = list_req_pickles(noncanonical_dir)

    canonical_names = set(canonical_files.keys())
    noncanonical_names = set(noncanonical_files.keys())

    shared = sorted(canonical_names & noncanonical_names, key=req_sort_key)
    missing_in_noncanonical = sorted(canonical_names - noncanonical_names, key=req_sort_key)
    missing_in_canonical = sorted(noncanonical_names - canonical_names, key=req_sort_key)

    equal = 0
    different = []
    errors = []

    for name in shared:
        try:
            with open(canonical_files[name], "rb") as f:
                canonical_ast = pickle.load(f)
            with open(noncanonical_files[name], "rb") as f:
                noncanonical_ast = pickle.load(f)
        except Exception as exc:
            errors.append((name, f"load error: {exc}"))
            continue

        try:
            if check_asts_equal(canonical_ast, noncanonical_ast):
                equal += 1
            else:
                different.append(name)
        except Exception as exc:
            errors.append((name, f"compare error: {exc}"))

    print("=== Canonical vs Non-Canonical Forward AST Comparison ===")
    print(f"Canonical dir:     {canonical_dir}")
    print(f"Non-canonical dir: {noncanonical_dir}")
    print(f"Canonical files (req*.pkl):     {len(canonical_names)}")
    print(f"Non-canonical files (req*.pkl): {len(noncanonical_names)}")
    print(f"Shared files compared:          {len(shared)}")
    print(f"Equivalent:                     {equal}")
    print(f"Different:                      {len(different)}")
    print(f"Missing in non-canonical side:  {len(missing_in_noncanonical)}")
    print(f"Missing in canonical side:      {len(missing_in_canonical)}")
    print(f"Load/compare errors:            {len(errors)}")

    print_section("Different ASTs", different, args.max_report)
    print_section("Missing in non-canonical side", missing_in_noncanonical, args.max_report)
    print_section("Missing in canonical side", missing_in_canonical, args.max_report)
    if errors:
        print("\nErrors:")
        for name, message in errors[: args.max_report]:
            print(f" - {name}: {message}")
        extra = len(errors) - args.max_report
        if extra > 0:
            print(f" ... and {extra} more")

    has_issues = bool(different or missing_in_noncanonical or missing_in_canonical or errors)
    sys.exit(1 if has_issues else 0)


if __name__ == "__main__":
    main()
