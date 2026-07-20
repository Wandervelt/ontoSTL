# STL-to-Ontology Replication Repository

## Overview

This repository contains the code and checked-in artifacts used to study bidirectional conversion between **Signal Temporal Logic (STL)** formulas and **OWL/Turtle ontologies**.

The workflow implemented here is:

1. Parse STL formulas into abstract syntax trees (ASTs).
2. Convert ASTs to Turtle/OWL ontologies.
3. Reconstruct ASTs from those ontologies.
4. Compare the original and reconstructed ASTs.
5. Analyze structural reductions under canonicalization.
6. Measure scalability and query the resulting knowledge graphs with SPARQL.

The repository includes both:

- a **non-canonical** pipeline, and
- a **canonical** pipeline that normalizes ASTs before ontology generation.

The code was developed and tested on Linux.

## Repository Layout

```text
.
├── README.MD
├── dataset/
│   ├── STL_formulas.txt
│   ├── STL_instantiated_formulas.txt
│   ├── stl-template-to-stl.py
│   └── ...
└── code/
    ├── stl-owl-tool.py
    ├── mtl-owl-tool.py
    ├── scalability.py
    ├── visualize.py
    ├── query_requirements_g_implies_equal_equal.py
    ├── query_requirements_g_or_notequal_equal.py
    ├── canonical_ast/
    ├── non-canonical_ast/
    ├── pytelo_modified/
    ├── canon_and_non-canon_comp/
    ├── results/
    └── results_canonical/
```

## Main Entry Points

- `python code/stl-owl-tool.py ...`
  Preferred CLI for parsing, ontology generation, reconstruction, and comparison.
- `python code/mtl-owl-tool.py ...`
  Legacy-compatible entry point for MTL. It runs the same tool.
- `python code/scalability.py ...`
  Scalability analysis and repeated-trial timing.

## Setup

Commands below assume you are running from the **repository root**.

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Optional but recommended for visualization:

- Install Graphviz so the `dot` executable is available on your system.

To confirm the CLI is available:

```bash
python code/stl-owl-tool.py --help
```

## Dataset Used for the Paper Workflow

The parser-ready dataset is:

```text
dataset/STL_instantiated_formulas.txt
```

It contains **8,888 non-empty STL formulas**. Note that `wc -l` may report `8887` because the file does not end with a trailing newline.

If you want to regenerate that file from the templates:

```bash
python dataset/stl-template-to-stl.py \
  -i dataset/STL_formulas.txt \
  -o dataset/STL_instantiated_formulas.txt \
  --seed 42
```

Expected outcome:

- `dataset/STL_instantiated_formulas.txt` is regenerated with 8838 instantiated formulas, the remaining 50 are inside the file dataset/50_mtl_set.txt. This sums up to 8888 total formulas.

## Recommended Replication Order

To reproduce the full workflow used in the paper, run the steps in this order:

1. Parse and convert all formulas without canonicalization.
2. Reconstruct all formulas without canonicalization.
3. Compare the original and reconstructed ASTs without canonicalization.
4. Parse and convert all formulas with canonicalization.
5. Reconstruct all formulas with canonicalization.
6. Compare the original and reconstructed ASTs with canonicalization.
7. Count distinct pure-topology signatures in both settings.
8. Run scalability analysis.
9. Run the SPARQL demonstration queries.

## Step 1: Parse All Formulas

Parsing happens as the first stage of the batch pipeline. Each formula string is converted into an AST object before ontology generation.

For example, the formula:

```text
G[0,5](!p3) && p2 && p1
```

corresponds conceptually to an AST such as:

```text
AND
├── GLOBALLY [0, 5]
│   └── NOT
│       └── VAR(p3)
├── VAR(p2)
└── VAR(p1)
```

Run the non-canonical forward pass:

```bash
python code/stl-owl-tool.py batch \
  dataset/STL_instantiated_formulas.txt \
  -p req \
  -o code/results/forward
```

Run the canonical forward pass:

```bash
python code/stl-owl-tool.py -c batch \
  dataset/STL_instantiated_formulas.txt \
  -p req \
  -o code/results_canonical/forward
```

Expected output:

- `8,888` AST pickle files in `code/results/forward/`
- `8,888` AST pickle files in `code/results_canonical/forward/`
- `code/results/requirements_ontology.ttl`
- `code/results_canonical/requirements_ontology.ttl`

## Step 2: RQ1 Round-Trip Without Canonicalization

Reconstruct the non-canonical ontology back into ASTs:

```bash
python code/stl-owl-tool.py batch-reconstruct \
  code/results/requirements_ontology.ttl \
  -o code/results/backward
```

Compare forward and backward ASTs:

```bash
python code/stl-owl-tool.py compare-batch \
  -f code/results/forward \
  -b code/results/backward
```

Find the reconstructed formulas in:

- `code/results/reconstructed_formulas.txt`

Illustrative per-formula behavior:

```text
Formula 1: G[0,5](!p3) && p2 && p1
  Forward:  AST -> OWL  ✓
  Backward: OWL -> AST  ✓
  Equivalence check: PASS

Formula 2: (p1 && p2) && !(F[0,5]p3)
  Forward:  AST -> OWL  ✓
  Backward: OWL -> AST  ✓
  Equivalence check: PASS
```

Observed result in the checked-in artifacts:

```text
--- Batch Comparison Summary ---
Total files compared: 8888
Successes (equivalent): 8888
Failures (not equivalent): 0
Missing backward files: 0
```

That is:

- `8,888 / 8,888 PASS`
- `100%` round-trip agreement

## Step 3: RQ1 Round-Trip With Canonicalization

Reconstruct the canonical ontology back into ASTs:

```bash
python code/stl-owl-tool.py -c batch-reconstruct \
  code/results_canonical/requirements_ontology.ttl \
  -o code/results_canonical/backward
```

Compare canonical forward and backward ASTs:

```bash
python code/stl-owl-tool.py -c compare-batch \
  -f code/results_canonical/forward \
  -b code/results_canonical/backward
```

Find the reconstructed canonical formulas in:

- `code/results_canonical/reconstructed_formulas_canonical.txt`

Canonicalization may normalize syntactically different formulas to the same AST. For example:

```text
Formula 1: G[0,5](!p3) && p2 && p1
  Canonical AST: p1 ∧ p2 ∧ G[0,5](¬p3)
  Forward:  AST -> OWL  ✓
  Backward: OWL -> AST  ✓
  Equivalence check: PASS

Formula 2: (p1 && p2) && !(F[0,5]p3)
  Canonical AST: p1 ∧ p2 ∧ G[0,5](¬p3)
  Forward:  AST -> OWL  ✓
  Backward: OWL -> AST  ✓
  Equivalence check: PASS
```

Observed result in the checked-in artifacts:

```text
--- Batch Comparison Summary ---
Total files compared: 8888
Successes (equivalent): 8888
Failures (not equivalent): 0
Missing backward files: 0
```

That is:

- `8,888 / 8,888 PASS`
- `100%` round-trip agreement

## Step 4: RQ2 Topology Analysis

The pure-topology analysis removes concrete names and values and keeps only the structural skeleton of a formula.

Example:

```text
G[0,5](x > 5 ∧ y < 3)      -> topology: G(PRED(>) ∧ PRED(<))
G[20,40](a > 99 ∧ b < -1)  -> topology: G(PRED(>) ∧ PRED(<))
```

These two formulas belong to the same topology group.

Count pure topologies in the non-canonical ASTs:

```bash
python code/canon_and_non-canon_comp/count_distinct_pure_topology_noncanonical.py
```

Count pure topologies in the canonical ASTs:

```bash
python code/canon_and_non-canon_comp/count_distinct_pure_topology_canonical.py
```

Observed output:

```text
Non-canonical:
  Total formulas:      8,888
  Distinct topologies: 2,439
  Singleton:           1,771
  Repeated:              668

Canonical:
  Total formulas:      8,888
  Distinct topologies: 2,032
  Singleton:           1,411
  Repeated:              621

Reduction: 407 topologies eliminated
```

Additional artifacts written by these scripts:

- `code/canon_and_non-canon_comp/pure_topology_noncanonical_groups.csv`
- `code/canon_and_non-canon_comp/pure_topology_canonical_groups.csv`

## Step 5: RQ3 Scalability Analysis

Run a single non-canonical scalability pass:

```bash
python code/scalability.py --non-canonical
```

Run a single canonical scalability pass:

```bash
python code/scalability.py --canonical
```

Run repeated-trial cumulative timing for both modes over 30 runs:

```bash
python code/scalability.py --total --30
```

Single-run statistics from the checked-in artifacts:

### Non-canonical

```text
              Forward    Backward   Total
Mean:         1.594 ms   3.560 ms   5.154 ms
Median:       1.445 ms   3.159 ms   4.654 ms
Std Dev:      0.756 ms   2.642 ms   3.007 ms
95th pct:     2.947 ms   6.253 ms   8.990 ms
99th pct:     4.015 ms   7.955 ms  11.118 ms
```

### Canonical

```text
              Forward    Backward   Total
Mean:         1.585 ms   3.374 ms   4.959 ms
Median:       1.427 ms   2.956 ms   4.432 ms
Std Dev:      0.796 ms   2.346 ms   2.787 ms
95th pct:     3.021 ms   6.093 ms   8.852 ms
99th pct:     4.061 ms   8.063 ms  11.664 ms
```

Repeated-trial cumulative totals over 30 runs:

```text
Canonical cumulative total:     42.3245 s
Non-canonical cumulative total: 41.0140 s
```

Main output locations:

- `code/results/scalability/non-canonical/`
- `code/results/scalability/canonical/`
- `code/results/scalability/total/`

Important generated files include:

- `scalability_results.csv`
- `statistics.json`
- `cumulative_runtime.csv`
- `cumulative_formulas_vs_time.png`
- `canonical_vs_noncanonical_avg_cumulative_total_time.png`

## Step 6: SPARQL Demonstration

The repository includes two query scripts used to demonstrate how the generated knowledge graphs can be searched structurally.

Run the non-canonical query:

```bash
python code/query_requirements_g_implies_equal_equal.py
```

Observed result in the checked-in artifacts:

```text
--- Non-canonical graph ---
Query: G(p1 = c1 -> p2 = c2)
Results: 69 formulas matched
```

Run the canonical query:

```bash
python code/query_requirements_g_or_notequal_equal.py
```

Observed result in the checked-in artifacts:

```text
--- Canonical graph ---
Query: G(¬p1 ≠ c1 ∨ p2 = c2)
Results: 90 formulas matched
  (69 former implications + 21 existing disjunctions)
```

These scripts operate on:

- `code/results/requirements_ontology.ttl`
- `code/results_canonical/requirements_ontology.ttl`

## Optional Utilities

### Parse a Single Formula

```bash
python code/stl-owl-tool.py parse "x > 10 && F[0,5] y > 20"
```

### Convert a Single Formula to Ontology

```bash
python code/stl-owl-tool.py to-ontology "G[0,10] (speed < 50)" -o traffic_rule.ttl
```

### Reconstruct a Formula from an Ontology

```bash
python code/stl-owl-tool.py from-ontology traffic_rule.ttl
```

### Visualize ASTs

```bash
python code/visualize.py code/results/forward/req1.pkl
python code/visualize.py code/results/forward/req1.pkl code/results/backward/req1.pkl
```

Visualizations are written to `code/results/visualize/`.

## Notes

- The `-c` flag enables canonicalization.
- The tool writes `stl:` / `http://stl#` by default but can still read legacy `mtl:` / `http://mtl#` ontologies.
- `code/stl-owl-tool.py` is the preferred entry point; `code/mtl-owl-tool.py` is kept for compatibility with older names.
- The parser implementation is based on a modified version of PyTeLo in `code/pytelo_modified/`.

## License

Except for `code/pytelo_modified/`, the original code in this repository is
licensed under the MIT License. See [`LICENSE`](LICENSE).

`code/pytelo_modified/` contains modified code derived from
[PyTeLo](https://github.com/erl-lehigh/PyTeLo), originally developed by the
Explainable Robotics Lab (ERL).

That directory is distributed under the BSD 3-Clause License. See
[`code/pytelo_modified/LICENSE`](code/pytelo_modified/LICENSE) and
[`code/pytelo_modified/README.MD`](code/pytelo_modified/README.MD) for the
original attribution and a summary of the modifications.

## Troubleshooting

If something does not reproduce as expected:

1. Confirm you are running commands from the repository root.
2. Confirm dependencies are installed from `requirements.txt`.
3. Confirm `dataset/STL_instantiated_formulas.txt` exists and contains 8,888 formulas.
4. If rerunning experiments, clear or move old results before starting.
5. Use `--help` on the relevant script to inspect available options.
