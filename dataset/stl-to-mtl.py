import random
import re
import os

IDENTIFIERS = [
    'speed', 'acceleration', 'pressure', 'temperature', 'voltage', 'current',
    'error_rate', 'response_time', 'fuel_level', 'altitude', 'request', 'grant',
    'signal_A', 'signal_B', 'mode', 'status', 'is_active', 'error_code', 'x', 'y', 'z'
]


class StlFormulaConverter:
    """
    A class to handle the instantiation of STL templates and their abstraction into STL formulas,
    with syntax tailored to the user's specific requirements.
    """

    def __init__(self):
        self.predicate_to_prop_map = {}
        self.prop_counter = 1

    def _get_random_identifier(self):
        return random.choice(IDENTIFIERS)

    def _get_random_numeric_value(self):
        return round(random.uniform(-50.0, 1000.0), 2)

    def _get_random_temporal_value(self):
        return random.randint(1, 500)

    def instantiate_template(self, template: str) -> str:
        """
        Replaces all placeholders in an STL template string with concrete, random values.
        """
        formula = template

        id_map = {}
        for id_placeholder in re.findall(r'id\d+', formula):
            if id_placeholder not in id_map:
                id_map[id_placeholder] = self._get_random_identifier() if random.random() > 0.2 else str(random.randint(0, 5))
        for placeholder, value in id_map.items():
            formula = formula.replace(placeholder, str(value))

        range_values = {}
        for num_placeholder in re.findall(r'num\d+value[ab]?#', formula):
            base_name = num_placeholder.split('value')[0] + 'value'
            if 'valuea' in num_placeholder:
                if base_name not in range_values:
                    range_values[base_name] = (self._get_random_numeric_value(), self._get_random_numeric_value())
                val_a, val_b = sorted(range_values[base_name])
                formula = formula.replace(num_placeholder, str(val_a))
            elif 'valueb' in num_placeholder:
                if base_name not in range_values:
                   range_values[base_name] = (self._get_random_numeric_value(), self._get_random_numeric_value())
                val_a, val_b = sorted(range_values[base_name])
                formula = formula.replace(num_placeholder, str(val_b))
            else:
                 formula = formula.replace(num_placeholder, str(self._get_random_numeric_value()))

        temporal_ranges = {}
        for time_placeholder in re.findall(r'num\d+temporal[ab]?#', formula):
            base_name = time_placeholder.split('temporal')[0] + 'temporal'
            if 'temporala' in time_placeholder:
                if base_name not in temporal_ranges:
                    temporal_ranges[base_name] = (self._get_random_temporal_value(), self._get_random_temporal_value())
                time_a, time_b = sorted(temporal_ranges[base_name])
                formula = formula.replace(time_placeholder, str(time_a))
            elif 'temporalb' in time_placeholder:
                if base_name not in temporal_ranges:
                    temporal_ranges[base_name] = (self._get_random_temporal_value(), self._get_random_temporal_value())
                time_a, time_b = sorted(temporal_ranges[base_name])
                formula = formula.replace(time_placeholder, str(time_b))
            else:
                formula = formula.replace(time_placeholder, str(self._get_random_temporal_value()))
        
        formula = re.sub(r'\[(\d+\.?\d*):(\d+\.?\d*)\]', r'[\1, \2]', formula)

        return formula

    def _get_proposition_for_predicate(self, predicate: str) -> str:
        """Gets or creates an abstract proposition for a given predicate string."""
        predicate = predicate.strip()
        if predicate not in self.predicate_to_prop_map:
            prop_name = f"p{self.prop_counter}"
            self.predicate_to_prop_map[predicate] = prop_name
            self.prop_counter += 1
        return self.predicate_to_prop_map[predicate]

    def _finalize_stl_syntax(self, formula: str) -> str:
        """Converts common logic words to the user's specified STL symbols."""
        replacements = {
            r'\b->\b': '=>',
            r'\band\b': '&&',
            r'\bor\b': '||',
            r'\bnot\b': '!',
            # Handle temporal operators
            r'\balways\b': 'G',
            r'\beventually\b': 'F',
            r'\buntil\b': 'U',
            r'\bsince\b': 'S' # Assuming Since might be present
        }
        for word, symbol in replacements.items():
            formula = re.sub(word, symbol, formula)
        return formula

    def abstract_to_stl(self, stl_formula: str) -> str:
        self.predicate_to_prop_map = {}
        self.prop_counter = 1
        output_formula = stl_formula

        predicate_patterns = [
            re.compile(r'\b(rise|fall)\s*\([^)]+\)'),
            re.compile(r'\(([^()]*?)\)'),
            re.compile(r'\b([a-zA-Z_]\w*\s*(?:==|!=|>=|<=|>|<)\s*[\d.-]+)\b')
        ]
        
        # This simplified logic finds and replaces predicates.
        # It's a heuristic that works well for the given template structures.
        temp_formula = output_formula
        all_predicates = []
        for pattern in predicate_patterns:
            all_predicates.extend(re.findall(pattern, temp_formula))

        # Sort predicates by length, longest first, to handle nested cases correctly.
        all_predicates = sorted(list(set(all_predicates)), key=len, reverse=True)
        
        for predicate in all_predicates:
            # Clean up predicate string if it's a tuple from regex groups
            pred_str = predicate[0] if isinstance(predicate, tuple) else predicate
            
            # Heuristic to avoid replacing already processed parts or temporal logic
            temporal_ops = ['G', 'F', 'U', 'S', 'always', 'eventually', 'until', 'since']
            if 'p' not in pred_str and not any(op in pred_str for op in temporal_ops):
                prop = self._get_proposition_for_predicate(pred_str)
                # Use a function for replacement to avoid regex interpretation issues
                output_formula = output_formula.replace(pred_str, prop)

        output_formula = self._finalize_stl_syntax(output_formula)
        return output_formula

    # Backward-compatible aliases
    def _finalize_mtl_syntax(self, formula: str) -> str:
        return self._finalize_stl_syntax(formula)

    def abstract_to_mtl(self, stl_formula: str) -> str:
        return self.abstract_to_stl(stl_formula)


# Backward-compatible class alias
StlToMtlConverter = StlFormulaConverter

def process_and_write_formulas(input_filename: str, output_filename: str):
    """
    Reads STL templates, generates STL formulas, and writes them to an output file.
    """
    if not os.path.exists(input_filename):
        print(f"--- ERROR ---")
        print(f"Input file '{input_filename}' not found.")
        print("Please ensure your file with STL templates is present and correctly named.")
        print("---------------")
        return

    with open(input_filename, 'r') as f:
        templates = [line.strip() for line in f if line.strip()]

    if not templates:
        print(f"Error: No templates found in '{input_filename}'.")
        return

    converter = StlFormulaConverter()
    
    # Open the output file to write the results
    with open(output_filename, 'w') as out_f:
        # Process each template once
        for template in templates:
            stl_formula = converter.instantiate_template(template)
            output_formula = converter.abstract_to_stl(stl_formula)
            out_f.write(output_formula + '\n')

    print(f"Success! {len(templates)} STL formulas have been generated and saved to '{output_filename}'.")


# --- Main Execution ---
if __name__ == "__main__":
    INPUT_FILE = "STL_formulas.txt"
    OUTPUT_FILE = "STL_formulas_output.txt"

    process_and_write_formulas(INPUT_FILE, OUTPUT_FILE)
