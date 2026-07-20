#!/usr/bin/env python3
import argparse
import os
import re
import sys

from rdflib import Graph

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

QUERY = """
PREFIX stl: <http://stl#>
PREFIX mtl: <http://mtl#>
PREFIX req: <http://requirements#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT DISTINCT ?req
WHERE {
  ?req rdf:type ?reqType ;
       (stl:hasOperator|mtl:hasOperator) ?globallyOp ;
       (stl:hasRightOperand|mtl:hasRightOperand) ?impl .

  FILTER(?reqType IN (stl:STLFormula, mtl:MTLFormula, stl:MTLFormula, mtl:STLFormula))
  FILTER(?globallyOp IN (stl:Globally, mtl:Globally))

  FILTER(STRSTARTS(STR(?req), STR(req:)))

  ?impl rdf:type ?implType ;
        (stl:hasOperator|mtl:hasOperator) ?impliesOp ;
        (stl:hasLeftOperand|mtl:hasLeftOperand) ?leftPred ;
        (stl:hasRightOperand|mtl:hasRightOperand) ?rightPred .

  FILTER(?implType IN (stl:STLFormula, mtl:MTLFormula, stl:MTLFormula, mtl:STLFormula))
  FILTER(?impliesOp IN (stl:Implies, mtl:Implies))

  ?leftPred rdf:type ?leftType ;
            (stl:hasOperator|mtl:hasOperator) ?leftOp .

  ?rightPred rdf:type ?rightType ;
             (stl:hasOperator|mtl:hasOperator) ?rightOp .

  FILTER(?leftType IN (stl:STLFormula, mtl:MTLFormula, stl:MTLFormula, mtl:STLFormula))
  FILTER(?rightType IN (stl:STLFormula, mtl:MTLFormula, stl:MTLFormula, mtl:STLFormula))
  FILTER(?leftOp IN (stl:Equal, mtl:Equal))
  FILTER(?rightOp IN (stl:Equal, mtl:Equal))
}
ORDER BY ?req
"""


def parse_original_formulas(ttl_path: str):
    req_to_formula = {}
    with open(ttl_path, "r") as f:
        content = f.read()

    for match in re.finditer(r"# Original formula: (.+)", content):
        formula_text = match.group(1)
        pos = match.end()
        next_content = content[pos: pos + 600]
        req_match = re.search(
            r"req:(\w+)\s+a\s+(?:stl:STLFormula|mtl:MTLFormula|stl:MTLFormula|mtl:STLFormula)",
            next_content,
        )
        if req_match:
            req_to_formula[req_match.group(1)] = formula_text

    return req_to_formula


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Use SPARQL to extract requirements whose ontology shape matches "
            "('G', '_', '_', ('IMPLIES', ('PRED', '=', '_', '_'), ('PRED', '=', '_', '_')))."
        )
    )
    parser.add_argument(
        "--ttl",
        default=os.path.join(CURRENT_DIR, "results", "requirements_ontology.ttl"),
        help="Path to the input Turtle file (default: code/results/requirements_ontology.ttl)",
    )
    parser.add_argument(
        "--show-formulas",
        action="store_true",
        help="Also print the original formula comment for each matching requirement, if available.",
    )
    args = parser.parse_args()

    ttl_path = os.path.abspath(args.ttl)
    if not os.path.isfile(ttl_path):
        print(f"Error: TTL file not found: {ttl_path}")
        sys.exit(1)

    g = Graph()
    g.parse(ttl_path, format="turtle")
    rows = list(g.query(QUERY))

    req_to_formula = parse_original_formulas(ttl_path) if args.show_formulas else {}

    print("=== Matching Requirements ===")
    print(f"TTL file:   {ttl_path}")
    print(f"Matches:    {len(rows)}")
    print("Signature:  ('G', '_', '_', ('IMPLIES', ('PRED', '=', '_', '_'), ('PRED', '=', '_', '_')))")

    for row in rows:
        req_uri = str(row.req)
        req_name = req_uri.split("#")[-1]
        print(req_name)
        if args.show_formulas:
            formula_text = req_to_formula.get(req_name, "Original formula comment not found")
            print(f"  {formula_text}")


if __name__ == "__main__":
    main()
