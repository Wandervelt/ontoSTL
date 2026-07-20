import pickle as pkl  
import math
import os
import sys
from collections import Counter

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(CURRENT_DIR)
if CODE_DIR not in sys.path:
    sys.path.insert(0, CODE_DIR)

from pytelo_modified.stl import Operation, RelOperation, STLFormula

class LocalSTLFormula(STLFormula):
    def __eq__(self, other):
        """
        Recursively checks for semantic equality between two AST nodes.
        """
        if not isinstance(other, STLFormula):
            return NotImplemented

        if self.op != other.op:
            return False


        if self.op == Operation.PRED:
            return self.variable == other.variable and \
                   self.relation == other.relation and \
                   math.isclose(self.threshold, other.threshold)
                   
        elif self.op == Operation.VAR:
            return self.variable == other.variable
            
        elif self.op == Operation.BOOL:
            return self.value == other.value
            
        elif self.op in (Operation.ALWAYS, Operation.EVENT):
            # For G and F operators, compare time bounds and the child sub-formula.
            return math.isclose(self.low, other.low) and \
                   math.isclose(self.high, other.high) and \
                   self.child == other.child
                   
        elif self.op == Operation.NOT:
            # For NOT, just compare the child sub-formula.
            return self.child == other.child
            
        elif self.op == Operation.UNTIL:
            # For Until, compare time bounds and both left/right sub-formulas.
            return math.isclose(self.low, other.low) and \
                   math.isclose(self.high, other.high) and \
                   self.left == other.left and \
                   self.right == other.right
                   
        elif self.op == Operation.IMPLIES:
            return self.left == other.left and \
                   self.right == other.right
                   
        elif self.op in (Operation.AND, Operation.OR):
            if not hasattr(self, 'children') or not hasattr(other, 'children') or \
               len(self.children) != len(other.children):
                return False
            
            other_children_copy = list(other.children)
            
            for child_s in self.children:
                found_match = False
                for i, child_o in enumerate(other_children_copy):
                    if child_s == child_o:
                        other_children_copy.pop(i)
                        found_match = True
                        break
                if not found_match:
                    return False
                    
            return len(other_children_copy) == 0
            
        return False



if __name__ == "__main__":
    # Define the directories where the AST files are stored.
    original_ast_dir = "results_canonical/forward"
    reconstructed_ast_dir = "results_canonical/backward"


    # Check if the directory with original ASTs exists.
    if not os.path.isdir(original_ast_dir):
        print(f"Error: Directory '{original_ast_dir}' not found.")
        sys.exit(1)

    # Get a list of all .pkl files to be processed.
    original_files = [f for f in os.listdir(original_ast_dir) if f.endswith('.pkl')]
    if not original_files:
        print(f"No .pkl files found in '{original_ast_dir}'.")
        sys.exit(1)

    # Initialize counters 
    success_count = 0
    failure_count = 0
    failed_files = []

    # Loop through every original AST file found.
    for filename in original_files:
        print(f"\n-- Comparing {filename} --")
        original_path = os.path.join(original_ast_dir, filename)
        reconstructed_path = os.path.join(reconstructed_ast_dir, filename)

        # Check if the corresponding reconstructed file exists.
        if not os.path.exists(reconstructed_path):
            print(f"Error: Corresponding file '{reconstructed_path}' not found.")
            failure_count += 1
            failed_files.append(filename)
            continue
        
        try:
            # Load both the original and reconstructed AST objects from their files.
            with open(original_path, 'rb') as f:
                ast_original = pkl.load(f)
                ast_original.__class__ = LocalSTLFormula

            with open(reconstructed_path, 'rb') as f:
                ast_reconstructed = pkl.load(f)
                ast_reconstructed.__class__ = LocalSTLFormula
            
            # Call the __eq__ method
            if ast_original == ast_reconstructed:
                print("Equivalent")
                success_count += 1
            else:
                print("NOT Equivalent")
                failure_count += 1
                failed_files.append(filename)

        except Exception as e:
            print(f"An error occurred during comparison for {filename}: {e}")
            failure_count += 1
            failed_files.append(filename)
            
    # Print the final summary report.
    print("\n--- Comparison Summary ---")
    print(f"Total files compared: {len(original_files)}")
    print(f"Successes: {success_count}")
    print(f"Failures: {failure_count}")

    if failed_files:
        print("\nFailed requirements:")
        for f in failed_files:
            print(f" - {f.replace('.pkl', '')}")
