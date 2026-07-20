import argparse
import os
import random
import re
from typing import Dict, Tuple


class StlTemplateInstantiator:
    """Instantiate STL template placeholders while preserving STL-level predicates."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def _get_random_numeric_value(self) -> float:
        return round(self.rng.uniform(-50.0, 1000.0), 2)

    def _get_random_temporal_value(self) -> int:
        return self.rng.randint(1, 500)

    def _contains_forbidden_operators(self, formula: str) -> bool:
        return re.search(r"\b(historically|since)\b", formula, flags=re.IGNORECASE) is not None

    def instantiate_template(self, template: str) -> str:
        """
        Instantiate numeric/temporal placeholders while leaving id1/id2/... untouched.
        """
        formula = template

        numeric_ranges: Dict[str, Tuple[float, float]] = {}
        numeric_values: Dict[str, float] = {}

        def numeric_replacer(match: re.Match) -> str:
            placeholder = match.group(0)
            if "valuea" in placeholder or "valueb" in placeholder:
                base_name = placeholder.split("value")[0] + "value"
                if base_name not in numeric_ranges:
                    numeric_ranges[base_name] = tuple(
                        sorted((self._get_random_numeric_value(), self._get_random_numeric_value()))
                    )
                low, high = numeric_ranges[base_name]
                return str(low if "valuea" in placeholder else high)

            if placeholder not in numeric_values:
                numeric_values[placeholder] = self._get_random_numeric_value()
            return str(numeric_values[placeholder])

        formula = re.sub(r"num\d+value[ab]?#", numeric_replacer, formula)

        temporal_ranges: Dict[str, Tuple[int, int]] = {}
        temporal_values: Dict[str, int] = {}

        def temporal_replacer(match: re.Match) -> str:
            placeholder = match.group(0)
            if "temporala" in placeholder or "temporalb" in placeholder:
                base_name = placeholder.split("temporal")[0] + "temporal"
                if base_name not in temporal_ranges:
                    temporal_ranges[base_name] = tuple(
                        sorted((self._get_random_temporal_value(), self._get_random_temporal_value()))
                    )
                low, high = temporal_ranges[base_name]
                return str(low if "temporala" in placeholder else high)

            if placeholder not in temporal_values:
                temporal_values[placeholder] = self._get_random_temporal_value()
            return str(temporal_values[placeholder])

        formula = re.sub(r"num\d+temporal[ab]?#", temporal_replacer, formula)

        # Normalize interval notation from [a:b] to [a, b].
        formula = re.sub(r"\[(\d+\.?\d*):(\d+\.?\d*)\]", r"[\1, \2]", formula)

        return formula

    def coerce_rhs_identifiers_to_numeric(self, formula: str) -> str:
        """
        Ensure comparison right-hand sides are numeric literals, as required by downstream parser.
        """
        rhs_numeric_map: Dict[str, float] = {}
        comparison_pattern = re.compile(
            r"(?P<lhs>\b[a-zA-Z_]\w*\b)\s*(?P<op>==|!=|>=|<=|>|<)\s*(?P<rhs>\b[a-zA-Z_]\w*\b)"
        )

        def replacer(match: re.Match) -> str:
            lhs = match.group("lhs")
            op = match.group("op")
            rhs = match.group("rhs")
            if rhs not in rhs_numeric_map:
                rhs_numeric_map[rhs] = self._get_random_numeric_value()
            return f"{lhs} {op} {rhs_numeric_map[rhs]}"

        return comparison_pattern.sub(replacer, formula)

    def normalize_stl_syntax(self, formula: str) -> str:
        replacements = {
            r"\balways\b": "G",
            r"\beventually\b": "F",
            r"\buntil\b": "U",
            r"\bnot\b": "!",
            r"\band\b": "&&",
            r"\bor\b": "||",
        }

        normalized = formula
        for pattern, replacement in replacements.items():
            normalized = re.sub(pattern, replacement, normalized)

        # Equality normalization for parsers that use '=' rather than '=='.
        normalized = normalized.replace("==", "=")
        # Implication normalization is token-based, not word-based.
        normalized = normalized.replace("->", "=>")

        return normalized


def process_and_write_formulas(input_filename: str, output_filename: str, seed: int = 42) -> None:
    if not os.path.exists(input_filename):
        print("--- ERROR ---")
        print(f"Input file '{input_filename}' not found.")
        print("Please ensure your STL template file is present and correctly named.")
        print("---------------")
        return

    with open(input_filename, "r", encoding="utf-8") as f:
        templates = [line.strip() for line in f if line.strip()]

    if not templates:
        print(f"Error: No templates found in '{input_filename}'.")
        return

    converter = StlTemplateInstantiator(seed=seed)

    kept = 0
    skipped = 0
    with open(output_filename, "w", encoding="utf-8") as out_f:
        for template in templates:
            if converter._contains_forbidden_operators(template):
                skipped += 1
                continue

            stl_formula = converter.instantiate_template(template)
            stl_formula = converter.coerce_rhs_identifiers_to_numeric(stl_formula)
            stl_formula = converter.normalize_stl_syntax(stl_formula)
            out_f.write(stl_formula + "\n")
            kept += 1

    print(
        f"Success! Generated {kept} STL formulas (skipped {skipped} containing 'historically' or 'since') "
        f"to '{output_filename}' with seed={seed}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Instantiate STL templates into STL formulas with deterministic randomization."
    )
    parser.add_argument("-i", "--input", default="STL_formulas.txt", help="Input STL template file")
    parser.add_argument(
        "-o",
        "--output",
        default="STL_instantiated_formulas.txt",
        help="Output file for instantiated STL formulas",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generation")

    args = parser.parse_args()
    process_and_write_formulas(args.input, args.output, seed=args.seed)


if __name__ == "__main__":
    main()
