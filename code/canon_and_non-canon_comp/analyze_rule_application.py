#!/usr/bin/env python3
import argparse
import csv
import json
import math
import os
import pickle
import re
import sys
from collections import Counter

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(CURRENT_DIR)
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from pytelo_modified.stl import Operation, RelOperation, STLFormula


def check_asts_equal(ast1: STLFormula, ast2: STLFormula) -> bool:
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


def clone_ast(node):
    return pickle.loads(pickle.dumps(node))


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


def record_if_changed(rule_hits: Counter, rule_name: str, before_node, after_node):
    if not check_asts_equal(before_node, after_node):
        rule_hits[rule_name] += 1


def apply_implication_elimination_traced(node, rule_hits: Counter):
    if node.op == Operation.IMPLIES and hasattr(node, "left") and hasattr(node, "right"):
        out = STLFormula(Operation.OR, children=[STLFormula(Operation.NOT, child=node.left), node.right])
        record_if_changed(rule_hits, "implication.to_or_not", node, out)
        return out
    return node


def apply_nnf_traced(node, rule_hits: Counter):
    if node.op != Operation.NOT or not hasattr(node, "child"):
        return node

    child = node.child
    if child.op == Operation.NOT:
        out = child.child
        record_if_changed(rule_hits, "nnf.double_negation", node, out)
        return out

    if child.op == Operation.AND:
        out = STLFormula(Operation.OR, children=[STLFormula(Operation.NOT, child=c) for c in child.children])
        record_if_changed(rule_hits, "nnf.demorgan_and_to_or", node, out)
        return out

    if child.op == Operation.OR:
        out = STLFormula(Operation.AND, children=[STLFormula(Operation.NOT, child=c) for c in child.children])
        record_if_changed(rule_hits, "nnf.demorgan_or_to_and", node, out)
        return out

    if child.op == Operation.EVENT:
        out = STLFormula(
            Operation.ALWAYS,
            child=STLFormula(Operation.NOT, child=child.child),
            low=child.low,
            high=child.high,
        )
        record_if_changed(rule_hits, "nnf.not_event_to_always_not", node, out)
        return out

    if child.op == Operation.ALWAYS:
        out = STLFormula(
            Operation.EVENT,
            child=STLFormula(Operation.NOT, child=child.child),
            low=child.low,
            high=child.high,
        )
        record_if_changed(rule_hits, "nnf.not_always_to_event_not", node, out)
        return out

    if child.op == Operation.PRED:
        out = STLFormula(
            Operation.PRED,
            relation=RelOperation.negop[child.relation],
            variable=child.variable,
            threshold=child.threshold,
        )
        record_if_changed(rule_hits, "nnf.negate_predicate_relation", node, out)
        return out

    return node


def apply_boolean_simplification_traced(node, rule_hits: Counter):
    if node.op not in (Operation.AND, Operation.OR):
        return node

    # Flatten nested same-op nodes.
    flat_children = []
    nodes_to_process = list(node.children)
    flattened = False
    while nodes_to_process:
        child = nodes_to_process.pop(0)
        if child.op == node.op:
            flattened = True
            nodes_to_process.extend(child.children)
        else:
            flat_children.append(child)

    if flattened:
        flattened_node = STLFormula(node.op, children=flat_children)
        record_if_changed(rule_hits, "boolean.flatten", node, flattened_node)

    # G-distribution for AND with same interval.
    if node.op == Operation.AND and len(flat_children) > 1:
        if all(c.op == Operation.ALWAYS for c in flat_children):
            interval = (flat_children[0].low, flat_children[0].high)
            if all((c.low, c.high) == interval for c in flat_children):
                inner_and = STLFormula(Operation.AND, children=[c.child for c in flat_children])
                canonical_inner = to_canonical_ast_traced(inner_and, rule_hits)
                distributed = STLFormula(Operation.ALWAYS, child=canonical_inner, low=interval[0], high=interval[1])
                record_if_changed(rule_hits, "boolean.distribute_always_over_and", node, distributed)
                return distributed

    if node.op == Operation.AND:
        if any(c.op == Operation.BOOL and not c.value for c in flat_children):
            out = STLFormula(Operation.BOOL, value=False)
            record_if_changed(rule_hits, "boolean.and_false_dominates", node, out)
            return out
        filtered = [c for c in flat_children if not (c.op == Operation.BOOL and c.value)]
        if len(filtered) != len(flat_children):
            filtered_node = STLFormula(Operation.AND, children=filtered) if filtered else STLFormula(Operation.BOOL, value=True)
            record_if_changed(rule_hits, "boolean.remove_and_true_identity", node, filtered_node)
    else:
        if any(c.op == Operation.BOOL and c.value for c in flat_children):
            out = STLFormula(Operation.BOOL, value=True)
            record_if_changed(rule_hits, "boolean.or_true_dominates", node, out)
            return out
        filtered = [c for c in flat_children if not (c.op == Operation.BOOL and not c.value)]
        if len(filtered) != len(flat_children):
            filtered_node = STLFormula(Operation.OR, children=filtered) if filtered else STLFormula(Operation.BOOL, value=False)
            record_if_changed(rule_hits, "boolean.remove_or_false_identity", node, filtered_node)

    unique_children = set(filtered)
    if len(unique_children) < len(filtered):
        dedup_node = STLFormula(node.op, children=sorted(list(unique_children))) if unique_children else (
            STLFormula(Operation.BOOL, value=True) if node.op == Operation.AND else STLFormula(Operation.BOOL, value=False)
        )
        record_if_changed(rule_hits, "boolean.deduplicate_children", node, dedup_node)

    if not unique_children:
        out = STLFormula(Operation.BOOL, value=True) if node.op == Operation.AND else STLFormula(Operation.BOOL, value=False)
        record_if_changed(rule_hits, "boolean.empty_children_to_constant", node, out)
        return out

    if len(unique_children) == 1:
        out = list(unique_children)[0]
        record_if_changed(rule_hits, "boolean.single_child_collapse", node, out)
        return out

    out = STLFormula(node.op, children=sorted(list(unique_children)))
    record_if_changed(rule_hits, "boolean.normalize_order", node, out)
    return out


def apply_temporal_simplification_traced(node, rule_hits: Counter):
    if node.op == Operation.ALWAYS and hasattr(node, "child") and node.child.op == Operation.ALWAYS:
        out = STLFormula(
            Operation.ALWAYS,
            child=node.child.child,
            low=node.low + node.child.low,
            high=node.high + node.child.high,
        )
        record_if_changed(rule_hits, "temporal.merge_nested_always", node, out)
        return out

    if node.op == Operation.EVENT and hasattr(node, "child") and node.child.op == Operation.EVENT:
        out = STLFormula(
            Operation.EVENT,
            child=node.child.child,
            low=node.low + node.child.low,
            high=node.high + node.child.high,
        )
        record_if_changed(rule_hits, "temporal.merge_nested_eventually", node, out)
        return out

    return node


def to_canonical_ast_traced(node, rule_hits: Counter):
    if node is None:
        return None

    node = apply_implication_elimination_traced(node, rule_hits)

    if hasattr(node, "left"):
        node.left = to_canonical_ast_traced(node.left, rule_hits)
    if hasattr(node, "right"):
        node.right = to_canonical_ast_traced(node.right, rule_hits)
    if hasattr(node, "child"):
        node.child = to_canonical_ast_traced(node.child, rule_hits)
    if hasattr(node, "children"):
        node.children = [to_canonical_ast_traced(c, rule_hits) for c in node.children]

    node = apply_nnf_traced(node, rule_hits)
    node = apply_boolean_simplification_traced(node, rule_hits)
    node = apply_temporal_simplification_traced(node, rule_hits)
    return node


def main():
    parser = argparse.ArgumentParser(
        description="Analyze which canonicalization rules changed ASTs between non-canonical and canonical outputs."
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
        "--out-prefix",
        default=os.path.join(CURRENT_DIR, "rule_analysis"),
        help="Output prefix for summary JSON and CSV reports.",
    )
    args = parser.parse_args()

    canonical_dir = os.path.abspath(args.canonical_dir)
    noncanonical_dir = os.path.abspath(args.noncanonical_dir)
    out_prefix = os.path.abspath(args.out_prefix)

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

    totals = Counter()
    totals["canonical_files"] = len(canonical_names)
    totals["noncanonical_files"] = len(noncanonical_names)
    totals["shared"] = len(shared)
    totals["missing_in_noncanonical"] = len(missing_in_noncanonical)
    totals["missing_in_canonical"] = len(missing_in_canonical)

    rule_totals_all = Counter()
    rule_totals_different = Counter()
    rule_totals_equivalent = Counter()

    per_req_rows = []
    load_or_compare_errors = []

    for name in shared:
        try:
            with open(canonical_files[name], "rb") as f:
                canonical_ast = pickle.load(f)
            with open(noncanonical_files[name], "rb") as f:
                noncanonical_ast = pickle.load(f)
        except Exception as exc:
            load_or_compare_errors.append((name, f"load error: {exc}"))
            continue

        pair_equivalent = check_asts_equal(canonical_ast, noncanonical_ast)
        rule_hits = Counter()

        try:
            transformed = to_canonical_ast_traced(clone_ast(noncanonical_ast), rule_hits)
        except Exception as exc:
            load_or_compare_errors.append((name, f"trace error: {exc}"))
            continue

        transformed_changed_input = not check_asts_equal(transformed, noncanonical_ast)
        transformed_matches_canonical = check_asts_equal(transformed, canonical_ast)
        any_rules_changed_ast = bool(rule_hits)

        totals["pair_equivalent" if pair_equivalent else "pair_different"] += 1
        if transformed_changed_input:
            totals["canonicalization_changed_input"] += 1
        else:
            totals["canonicalization_left_input_unchanged"] += 1

        if pair_equivalent:
            if transformed_changed_input:
                totals["equivalent_but_canonicalization_changed_input"] += 1
            else:
                totals["equivalent_and_no_change_from_canonicalization"] += 1
        else:
            if transformed_changed_input:
                totals["different_and_canonicalization_changed_input"] += 1
            else:
                totals["different_but_no_change_from_canonicalization"] += 1

        if transformed_matches_canonical:
            totals["traced_transform_matches_canonical_ast"] += 1
        else:
            totals["traced_transform_mismatch_with_canonical_ast"] += 1

        if any_rules_changed_ast:
            rule_totals_all.update(rule_hits)
            if pair_equivalent:
                rule_totals_equivalent.update(rule_hits)
            else:
                rule_totals_different.update(rule_hits)

        per_req_rows.append(
            {
                "req_file": name,
                "pair_equivalent": pair_equivalent,
                "transformed_changed_input": transformed_changed_input,
                "transformed_matches_canonical": transformed_matches_canonical,
                "rules_applied_count": sum(rule_hits.values()),
                "rules_applied": ";".join(f"{k}:{v}" for k, v in sorted(rule_hits.items())),
            }
        )

    totals["load_or_compare_errors"] = len(load_or_compare_errors)

    summary = {
        "dirs": {
            "canonical": canonical_dir,
            "noncanonical": noncanonical_dir,
        },
        "totals": dict(totals),
        "top_rules_all": rule_totals_all.most_common(),
        "top_rules_for_different_pairs": rule_totals_different.most_common(),
        "top_rules_for_equivalent_pairs": rule_totals_equivalent.most_common(),
        "missing_in_noncanonical": missing_in_noncanonical,
        "missing_in_canonical": missing_in_canonical,
        "errors": load_or_compare_errors,
    }

    os.makedirs(os.path.dirname(out_prefix), exist_ok=True)
    summary_path = f"{out_prefix}_summary.json"
    csv_path = f"{out_prefix}_per_requirement.csv"

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "req_file",
                "pair_equivalent",
                "transformed_changed_input",
                "transformed_matches_canonical",
                "rules_applied_count",
                "rules_applied",
            ],
        )
        writer.writeheader()
        writer.writerows(per_req_rows)

    print("=== Rule Application Analysis ===")
    print(f"Canonical dir:     {canonical_dir}")
    print(f"Non-canonical dir: {noncanonical_dir}")
    print(f"Shared compared:   {totals['shared']}")
    print(f"Equivalent pairs:  {totals['pair_equivalent']}")
    print(f"Different pairs:   {totals['pair_different']}")
    print(f"Changed by canonicalization: {totals['canonicalization_changed_input']}")
    print(f"Unchanged by canonicalization: {totals['canonicalization_left_input_unchanged']}")
    print(f"Equivalent + unchanged: {totals['equivalent_and_no_change_from_canonicalization']}")
    print(f"Equivalent + changed:   {totals['equivalent_but_canonicalization_changed_input']}")
    print(f"Different + changed:    {totals['different_and_canonicalization_changed_input']}")
    print(f"Different + unchanged:  {totals['different_but_no_change_from_canonicalization']}")
    print(f"Trace matches canonical AST: {totals['traced_transform_matches_canonical_ast']}")
    print(f"Trace mismatch canonical AST: {totals['traced_transform_mismatch_with_canonical_ast']}")
    print(f"Errors: {totals['load_or_compare_errors']}")
    print(f"\nSummary JSON: {summary_path}")
    print(f"Per-requirement CSV: {csv_path}")

    if rule_totals_different:
        print("\nTop rules among different pairs:")
        for rule_name, count in rule_totals_different.most_common(12):
            print(f" - {rule_name}: {count}")


if __name__ == "__main__":
    main()
