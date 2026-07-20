#!/usr/bin/env python3
import argparse
import os
import pickle
import re
import sys
from typing import Dict, List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(CURRENT_DIR)
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from pytelo_modified.stl import Operation, RelOperation, STLFormula

MODE_VARIABLE_AWARE = "variable-aware"
MODE_VARIABLE_ANONYMOUS = "variable-anonymous"
MODE_VARIABLE_ANONYMOUS_ORDER_PRESERVING = "variable-anonymous-order-preserving"
MODE_PURE_TOPOLOGY = "pure-topology"


def req_sort_key(filename: str):
    match = re.fullmatch(r"req(\d+)\.pkl", filename)
    if match:
        return (0, int(match.group(1)))
    return (1, filename)


def list_req_pickles(directory: str) -> Dict[str, str]:
    files = {}
    for name in os.listdir(directory):
        if re.fullmatch(r"req\d+\.pkl", name):
            files[name] = os.path.join(directory, name)
    return files


def stable_key(value) -> str:
    return repr(value)


def var_token_for(name: str, var_map: Dict[str, str]) -> str:
    if name not in var_map:
        var_map[name] = f"v{len(var_map)}"
    return var_map[name]


def collect_variable_names(node: STLFormula, names: set):
    if not isinstance(node, STLFormula):
        return

    if node.op in (Operation.PRED, Operation.VAR) and hasattr(node, "variable"):
        names.add(node.variable)

    if hasattr(node, "child"):
        collect_variable_names(node.child, names)
    if hasattr(node, "left"):
        collect_variable_names(node.left, names)
    if hasattr(node, "right"):
        collect_variable_names(node.right, names)
    if hasattr(node, "children"):
        for child in node.children:
            collect_variable_names(child, names)


def build_name_sorted_var_map(node: STLFormula) -> Dict[str, str]:
    names = set()
    collect_variable_names(node, names)
    ordered = sorted(names)
    return {name: f"v{i}" for i, name in enumerate(ordered)}


def signature_for_ast(node: STLFormula, mode: str, var_map: Dict[str, str]):
    if not isinstance(node, STLFormula):
        return ("UNKNOWN",)

    op = node.op
    op_name = Operation.getString(op) or f"op_{op}"

    if op == Operation.PRED:
        rel_name = RelOperation.getString(node.relation) or f"rel_{node.relation}"
        if mode == MODE_VARIABLE_AWARE:
            var_part = node.variable
        elif mode in (MODE_VARIABLE_ANONYMOUS, MODE_VARIABLE_ANONYMOUS_ORDER_PRESERVING):
            var_part = var_token_for(node.variable, var_map)
        else:
            var_part = "_"
        return ("PRED", rel_name, var_part, "_")

    if op == Operation.VAR:
        if mode == MODE_VARIABLE_AWARE:
            var_part = node.variable
        elif mode in (MODE_VARIABLE_ANONYMOUS, MODE_VARIABLE_ANONYMOUS_ORDER_PRESERVING):
            var_part = var_token_for(node.variable, var_map)
        else:
            var_part = "_"
        return ("VAR", var_part)

    if op == Operation.BOOL:
        if mode == MODE_PURE_TOPOLOGY:
            return ("BOOL", "_")
        return ("BOOL", bool(node.value))

    if op in (Operation.ALWAYS, Operation.EVENT):
        child_sig = signature_for_ast(node.child, mode, var_map)
        return (op_name, "_", "_", child_sig)

    if op == Operation.NOT:
        child_sig = signature_for_ast(node.child, mode, var_map)
        return ("NOT", child_sig)

    if op == Operation.UNTIL:
        left_sig = signature_for_ast(node.left, mode, var_map)
        right_sig = signature_for_ast(node.right, mode, var_map)
        return ("UNTIL", "_", "_", left_sig, right_sig)

    if op == Operation.IMPLIES:
        left_sig = signature_for_ast(node.left, mode, var_map)
        right_sig = signature_for_ast(node.right, mode, var_map)
        return ("IMPLIES", left_sig, right_sig)

    if op in (Operation.AND, Operation.OR):
        child_sigs = [signature_for_ast(c, mode, var_map) for c in node.children]
        # Order-insensitive for commutative operators.
        child_sigs = tuple(sorted(child_sigs, key=stable_key))
        return (op_name,) + child_sigs

    # Fallback for unexpected operator kinds.
    parts = [op_name]
    if hasattr(node, "child"):
        parts.append(signature_for_ast(node.child, mode, var_map))
    if hasattr(node, "left"):
        parts.append(signature_for_ast(node.left, mode, var_map))
    if hasattr(node, "right"):
        parts.append(signature_for_ast(node.right, mode, var_map))
    if hasattr(node, "children"):
        child_sigs = [signature_for_ast(c, mode, var_map) for c in node.children]
        child_sigs = tuple(sorted(child_sigs, key=stable_key))
        parts.append(child_sigs)
    return tuple(parts)


def normalized_signature(node: STLFormula, mode: str):
    # Mapping is per-formula.
    # MODE_VARIABLE_ANONYMOUS uses first appearance in traversal.
    # MODE_VARIABLE_ANONYMOUS_ORDER_PRESERVING uses deterministic name ordering.
    if mode == MODE_VARIABLE_ANONYMOUS_ORDER_PRESERVING:
        var_map = build_name_sorted_var_map(node)
    else:
        var_map = {}
    return signature_for_ast(node, mode, var_map)


def print_section(title: str, items: List[str], max_report: int):
    if not items:
        return
    print(f"\n{title}:")
    for name in items[:max_report]:
        print(f" - {name}")
    extra = len(items) - max_report
    if extra > 0:
        print(f" ... and {extra} more")


def run_comparison(mode: str):
    parser = argparse.ArgumentParser(
        description="Compare canonical vs non-canonical ASTs using abstraction modes."
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
        help="Maximum number of filenames to print per section.",
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

    equivalent = 0
    different = []
    errors: List[Tuple[str, str]] = []

    for name in shared:
        try:
            with open(canonical_files[name], "rb") as f:
                canonical_ast = pickle.load(f)
            with open(noncanonical_files[name], "rb") as f:
                noncanonical_ast = pickle.load(f)

            sig_c = normalized_signature(canonical_ast, mode)
            sig_n = normalized_signature(noncanonical_ast, mode)

            if sig_c == sig_n:
                equivalent += 1
            else:
                different.append(name)
        except Exception as exc:
            errors.append((name, str(exc)))

    print("=== Canonical vs Non-Canonical Comparison ===")
    print(f"Mode:              {mode}")
    print(f"Canonical dir:     {canonical_dir}")
    print(f"Non-canonical dir: {noncanonical_dir}")
    print(f"Canonical files (req*.pkl):     {len(canonical_names)}")
    print(f"Non-canonical files (req*.pkl): {len(noncanonical_names)}")
    print(f"Shared files compared:          {len(shared)}")
    print(f"Equivalent:                     {equivalent}")
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
