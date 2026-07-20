#!/usr/bin/env python3
"""
STL Command Line Tool

A CLI tool for working with Signal Temporal Logic (STL) formulas with Boolean-valued predicates.
Supports conversion between STL formulas, ASTs, and ontologies with optional canonicalization.
"""

import argparse
import sys
import json
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import os
import math
from rdflib import Graph, Namespace, URIRef, RDF

# Add parent directory and current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# Import core STL module (modified PyTeLo grammar and parser)
from pytelo_modified.stl import to_ast, STLFormula, Operation, RelOperation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

STL_NS = Namespace("http://stl#")
LEGACY_MTL_NS = Namespace("http://mtl#")
REQ_NS = Namespace("http://requirements#")
FORMULA_TYPE_URIS = (
    STL_NS.STLFormula,
    LEGACY_MTL_NS.MTLFormula,
    STL_NS.MTLFormula,
    LEGACY_MTL_NS.STLFormula,
)
ONTOLOGY_PREFIXES = """@prefix stl: <http://stl#> .
@prefix mtl: <http://mtl#> .
@prefix time: <http://www.w3.org/2006/time#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix req: <http://requirements#> .
"""


def resolve_batch_artifact_dir(path: str) -> Path:
    """Resolve the directory that should hold batch-level artifacts.

    For the conventional layouts `.../forward` and `.../backward`, this returns
    the parent directory so shared files land next to those folders:

    - `code/results/forward` -> `code/results`
    - `code/results/backward` -> `code/results`
    """
    artifact_dir = Path(path)
    if artifact_dir.name in {"forward", "backward"}:
        return artifact_dir.parent
    return artifact_dir


def load_module_from_file(module_name, file_path):
    "Load a Python module from a file path."
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load conversion modules
# For non-canonical operations
stl_to_ont = load_module_from_file("stl_to_ont", os.path.join(current_dir, "non-canonical_ast", "stl-to-ont.py"))
ont_to_stl = load_module_from_file("ont_to_stl", os.path.join(current_dir, "non-canonical_ast", "ont-to-stl.py"))
# For canonical operations
canonical_stl = load_module_from_file("canonical_stl", os.path.join(current_dir, "canonical_ast", "stl-to-ont.py"))


def iter_requirement_formulas(g: Graph):
    seen = set()
    for formula_type in FORMULA_TYPE_URIS:
        for subj in g.subjects(RDF.type, formula_type):
            if str(subj).startswith(str(REQ_NS)) and subj not in seen:
                seen.add(subj)
                yield subj


def check_asts_equal(ast1: STLFormula, ast2: STLFormula) -> bool:
    """
    Recursively checks for semantic equality between two AST nodes.
    From LocalSTLFormula.__eq__ method from ast_comparator.py - part of extensions to PyTeLo.
    """
    if not isinstance(ast1, STLFormula) or not isinstance(ast2, STLFormula):
        return False
    
    if ast1.op != ast2.op:
        return False
    
    if ast1.op == Operation.PRED:
        return (ast1.variable == ast2.variable and
                ast1.relation == ast2.relation and
                math.isclose(ast1.threshold, ast2.threshold))
    
    elif ast1.op == Operation.VAR:
        return ast1.variable == ast2.variable
    
    elif ast1.op == Operation.BOOL:
        return ast1.value == ast2.value
    
    elif ast1.op in (Operation.ALWAYS, Operation.EVENT):
        return (math.isclose(ast1.low, ast2.low) and
                math.isclose(ast1.high, ast2.high) and
                check_asts_equal(ast1.child, ast2.child))
    
    elif ast1.op == Operation.NOT:
        return check_asts_equal(ast1.child, ast2.child)
    
    elif ast1.op == Operation.UNTIL:
        return (math.isclose(ast1.low, ast2.low) and
                math.isclose(ast1.high, ast2.high) and
                check_asts_equal(ast1.left, ast2.left) and
                check_asts_equal(ast1.right, ast2.right))
    
    elif ast1.op == Operation.IMPLIES:
        return (check_asts_equal(ast1.left, ast2.left) and
                check_asts_equal(ast1.right, ast2.right))
    
    elif ast1.op in (Operation.AND, Operation.OR):
        if not hasattr(ast1, 'children') or not hasattr(ast2, 'children'):
            return False
        if len(ast1.children) != len(ast2.children):
            return False
        
        # For AND/OR
        ast2_children_copy = list(ast2.children)
        
        for child1 in ast1.children:
            found_match = False
            for i, child2 in enumerate(ast2_children_copy):
                if check_asts_equal(child1, child2):
                    ast2_children_copy.pop(i)
                    found_match = True
                    break
            if not found_match:
                return False
        
        return len(ast2_children_copy) == 0
    
    return False


class STLTool:
    """Main class for STL command line tool operations."""
    
    def __init__(self, canonical: bool = False):
        """Initialize the STL tool.
        
        Args:
            canonical: Whether to use canonical form for ASTs
        """
        self.canonical = canonical
    
    def parse_formula(self, formula: str, output_format: str = 'text') -> Dict[str, Any]:
        """Parse an STL formula into an AST.
        
        Args:
            formula: The STL formula string
            output_format: Output format ('text', 'pickle')
            
        Returns:
            Dictionary containing the AST and string representation
        """
        try:
            # Parse the formula
            ast = to_ast(formula)
            
            # Apply canonicalization if requested
            if self.canonical:
                ast = canonical_stl.to_canonical_ast(ast)
            
            result = {
                'formula': formula,
                'canonical': self.canonical,
                'ast_str': str(ast),
                'ast_obj': ast
            }
            
            return result
        except Exception as e:
            raise Exception(f"Failed to parse formula: {str(e)}")
    
    def formula_to_ontology(self, formula: str, req_name: str = "requirement") -> str:
        """Convert an STL formula to ontology (TTL format).
        
        Args:
            formula: The STL formula string
            req_name: Name for the requirement in the ontology
            
        Returns:
            TTL string representation
        """
        try:
            # Parse the formula
            ast = to_ast(formula)
            
            # Apply canonicalization if requested
            if self.canonical:
                ast = canonical_stl.to_canonical_ast(ast)
            
            # Convert to TTL
            ttl_body = stl_to_ont.create_formula_ttl(ast, req_name)
            
            # Store original formula as a comment
            ttl_content = ONTOLOGY_PREFIXES + f"\n# Original formula: {formula}\n\n" + ttl_body
            return ttl_content
        except Exception as e:
            raise Exception(f"Failed to convert formula to ontology: {str(e)}")
    
    def ontology_to_formula(self, ttl_file: str) -> Dict[str, Any]:
        """Convert an ontology file back to STL formula.
        
        Args:
            ttl_file: Path to the TTL file
            
        Returns:
            Dictionary containing the reconstructed AST and formula
        """
        try:
            
            # Parse the TTL file
            g = Graph()
            g.parse(ttl_file, format="turtle")
            
            # Find all requirements
            requirements = list(iter_requirement_formulas(g))
            
            if not requirements:
                raise Exception("No requirements found in the TTL file")
            
            results = []
            
            # Process each requirement
            for req_uri in requirements:
                req_name = str(req_uri).split('#')[-1]
                
                # Reconstruct AST
                ast_root = ont_to_stl.ontology_to_ast(req_uri, g)
                
                if ast_root:
                    # Try to extract original formula from comments - to compare reconstruction with original
                    original_formula = None
                    with open(ttl_file, 'r') as f:
                        content = f.read()
                        import re
                        match = re.search(r'# Original formula: (.+)', content)
                        if match:
                            original_formula = match.group(1)
                    
                    results.append({
                        'requirement': req_name,
                        'original_formula': original_formula or "Not found in file",
                        'reconstructed_ast': str(ast_root),
                        'ast_obj': ast_root
                    })
                else:
                    results.append({
                        'requirement': req_name,
                        'original_formula': "Error",
                        'reconstructed_ast': "Failed to reconstruct",
                        'ast_obj': None
                    })
            
            return {'results': results}
        except Exception as e:
            raise Exception(f"Failed to convert ontology to formula: {str(e)}")
    
    def compare_asts(self, ast1: STLFormula, ast2: STLFormula) -> Dict[str, Any]:
        """Compare two ASTs for semantic equivalence.
        
        Args:
            ast1: First AST
            ast2: Second AST
            
        Returns:
            Dictionary with comparison results
        """
        try:
            equal = check_asts_equal(ast1, ast2)
            return {
                'equal': equal,
                'ast1_str': str(ast1),
                'ast2_str': str(ast2)
            }
        except Exception as e:
            raise Exception(f"Failed to compare ASTs: {str(e)}")
    
    def batch_process(self, input_file: str, req_prefix: str = "req", output_dir: str = "results/forward") -> Dict[str, Any]:
        """Process multiple STL formulas from a file.
        
        Args:
            input_file: Path to file containing STL formulas (one per line)
            req_prefix: Prefix for requirement names (default: req)
            output_dir: Directory to save outputs (default: results/forward)
            
        Returns:
            Dictionary with processing results
        """
        import os
        from pathlib import Path
        
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        results = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'formulas': []
        }
        
        all_ttl_content = [ONTOLOGY_PREFIXES]
        
        try:
            with open(input_file, 'r') as f:
                formulas = [line.strip() for line in f if line.strip()]
            
            results['total'] = len(formulas)
            
            for i, formula in enumerate(formulas, 1):
                req_name = f"{req_prefix}{i}"
                
                try:
                    # Parse the formula
                    ast = to_ast(formula)
                    
                    # Apply canonicalization if requested
                    if self.canonical:
                        ast = canonical_stl.to_canonical_ast(ast)
                    
                    # Save AST as pickle
                    pkl_file = os.path.join(output_dir, f"{req_name}.pkl")
                    with open(pkl_file, 'wb') as f:
                        pickle.dump(ast, f)
                    
                    # Convert to TTL
                    ttl_body = stl_to_ont.create_formula_ttl(ast, req_name)
                    
                    # Add to combined TTL content
                    all_ttl_content.append(f"\n# Original formula: {formula}")
                    all_ttl_content.append(ttl_body)
                    
                    results['successful'] += 1
                    results['formulas'].append({
                        'index': i,
                        'formula': formula,
                        'req_name': req_name,
                        'status': 'success',
                        'pkl_file': pkl_file
                    })
                    
                    logger.info(f"Processed {req_name}: {formula}")
                    
                except Exception as e:
                    results['failed'] += 1
                    results['formulas'].append({
                        'index': i,
                        'formula': formula,
                        'req_name': req_name,
                        'status': 'failed',
                        'error': str(e)
                    })
                    logger.error(f"Failed to process {req_name}: {formula} - {str(e)}")
            
            # Save the combined ontology next to the chosen output directory.
            ttl_output_dir = resolve_batch_artifact_dir(output_dir)
            ttl_output_dir.mkdir(parents=True, exist_ok=True)
            ttl_file = ttl_output_dir / "requirements_ontology.ttl"
            with open(ttl_file, 'w') as f:
                f.write('\n'.join(all_ttl_content))
            
            logger.info(f"\nBatch processing complete:")
            logger.info(f"Total formulas: {results['total']}")
            logger.info(f"Successful: {results['successful']}")
            logger.info(f"Failed: {results['failed']}")
            logger.info(f"Combined TTL saved to: {ttl_file}")
            logger.info(f"Individual AST pickle files saved to: {output_dir}/")
            
            return results
            
        except Exception as e:
            raise Exception(f"Failed to process batch file: {str(e)}")
    
    def batch_reconstruct(self, ttl_file: str, output_dir: str = "results/backward") -> Dict[str, Any]:
        """Process a TTL file to reconstruct ASTs and save them as pickle files.
        
        Args:
            ttl_file: Path to the TTL file containing ontologies
            output_dir: Directory to save reconstructed AST pickle files (default: results/backward)
            
        Returns:
            Dictionary with reconstruction results
        """
        import os
        from pathlib import Path
        
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Determine whether this reconstruction should use canonical result paths.
        # This supports both explicit canonical mode (-c) and explicit canonical directories.
        def is_canonical_results_path(path: str) -> bool:
            return "results_canonical" in Path(path).parts

        is_canonical_context = (
            self.canonical
            or is_canonical_results_path(ttl_file)
            or is_canonical_results_path(output_dir)
        )

        # Save reconstructed formula text next to the chosen output directory.
        results_dir = resolve_batch_artifact_dir(output_dir)
        results_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'reconstructions': []
        }
        
        # Dictionary to store reconstructed formulas with their order
        reconstructed_formulas_dict = {}
        
        try:
            # Parse the TTL file
            g = Graph()
            g.parse(ttl_file, format="turtle")
            
            # Find all requirements
            requirements = list(iter_requirement_formulas(g))
            
            results['total'] = len(requirements)
            
            if not requirements:
                logger.warning("No requirements found in the TTL file")
                return results
            
            # Extract original formulas from comments if available
            original_formulas = {}
            with open(ttl_file, 'r') as f:
                content = f.read()
                import re
                for match in re.finditer(r'# Original formula: (.+)', content):
                    # Try to extract requirement name from the next few lines
                    formula_text = match.group(1)
                    # Look for requirement name pattern in the following content
                    pos = match.end()
                    next_content = content[pos:pos+500]  # Look ahead
                    req_match = re.search(
                        r'req:(\w+)\s+a\s+(?:stl:STLFormula|mtl:MTLFormula|stl:MTLFormula|mtl:STLFormula)',
                        next_content,
                    )
                    if req_match:
                        req_name = req_match.group(1)
                        original_formulas[req_name] = formula_text
            
            # Process each requirement
            for req_uri in requirements:
                req_name = str(req_uri).split('#')[-1]
                
                try:
                    # Reconstruct AST
                    ast_root = ont_to_stl.ontology_to_ast(req_uri, g)
                    
                    if ast_root:
                        # Save AST as pickle
                        pkl_file = os.path.join(output_dir, f"{req_name}.pkl")
                        with open(pkl_file, 'wb') as f:
                            pickle.dump(ast_root, f)
                        
                        results['successful'] += 1
                        results['reconstructions'].append({
                            'requirement': req_name,
                            'original_formula': original_formulas.get(req_name, "Not found in file"),
                            'reconstructed_ast': str(ast_root),
                            'status': 'success',
                            'pkl_file': pkl_file
                        })
                        
                        logger.info(f"Reconstructed {req_name}: {str(ast_root)}")
                        
                        # Store with requirement name to maintain order
                        reconstructed_formulas_dict[req_name] = str(ast_root)
                    else:
                        results['failed'] += 1
                        results['reconstructions'].append({
                            'requirement': req_name,
                            'original_formula': original_formulas.get(req_name, "Not found in file"),
                            'status': 'failed',
                            'error': "Failed to reconstruct AST"
                        })
                        logger.error(f"Failed to reconstruct {req_name}")
                        
                except Exception as e:
                    results['failed'] += 1
                    results['reconstructions'].append({
                        'requirement': req_name,
                        'original_formula': original_formulas.get(req_name, "Not found in file"),
                        'status': 'failed',
                        'error': str(e)
                    })
                    logger.error(f"Error reconstructing {req_name}: {str(e)}")
            
            logger.info(f"\nBatch reconstruction complete:")
            logger.info(f"Total requirements: {results['total']}")
            logger.info(f"Successful: {results['successful']}")
            logger.info(f"Failed: {results['failed']}")
            logger.info(f"Reconstructed AST pickle files saved to: {output_dir}/")
            
            # Save reconstructed formulas to text file
            if reconstructed_formulas_dict:
                formulas_filename = (
                    "reconstructed_formulas_canonical.txt"
                    if is_canonical_context
                    else "reconstructed_formulas.txt"
                )
                formulas_file = results_dir / formulas_filename
                with open(formulas_file, 'w') as f:
                    # Write formulas in the order of requirements (req1, req2, req3, ...)
                    # Extract requirement numbers and sort numerically
                    sorted_reqs = sorted(reconstructed_formulas_dict.keys(), 
                                       key=lambda x: int(x.replace('req', '')) if x.startswith('req') and x[3:].isdigit() else x)
                    
                    formulas_in_order = []
                    for req_name in sorted_reqs:
                        formulas_in_order.append(reconstructed_formulas_dict[req_name])
                    
                    f.write('\n'.join(formulas_in_order))
                logger.info(f"Reconstructed formulas saved to: {formulas_file}")
                results['formulas_file'] = formulas_file
            
            return results
            
        except Exception as e:
            raise Exception(f"Failed to process TTL file: {str(e)}")
    
    def batch_compare(self, forward_dir: str = "results/forward", backward_dir: str = "results/backward") -> Dict[str, Any]:
        """Compare AST pickle files between forward and backward directories.
        
        Args:
            forward_dir: Directory containing forward conversion pickle files
            backward_dir: Directory containing backward conversion pickle files
            
        Returns:
            Dictionary with comparison results
        """
        import os
        from pathlib import Path
        
        results = {
            'total': 0,
            'successes': 0,
            'failures': 0,
            'missing': 0,
            'comparisons': []
        }
        
        try:
            # Check if directories exist
            if not os.path.isdir(forward_dir):
                raise Exception(f"Forward directory '{forward_dir}' not found")
            if not os.path.isdir(backward_dir):
                raise Exception(f"Backward directory '{backward_dir}' not found")
            
            # Get list of pkl files in forward directory
            forward_files = [f for f in os.listdir(forward_dir) if f.endswith('.pkl')]
            
            if not forward_files:
                logger.warning(f"No .pkl files found in '{forward_dir}'")
                return results
            
            results['total'] = len(forward_files)
            logger.info(f"Found {len(forward_files)} pickle files to compare")
            
            # Compare each file
            for filename in sorted(forward_files):
                req_name = filename.replace('.pkl', '')
                forward_path = os.path.join(forward_dir, filename)
                backward_path = os.path.join(backward_dir, filename)
                
                comparison = {
                    'requirement': req_name,
                    'forward_file': forward_path,
                    'backward_file': backward_path
                }
                
                # Check if corresponding backward file exists
                if not os.path.exists(backward_path):
                    results['missing'] += 1
                    comparison['status'] = 'missing'
                    comparison['error'] = f"Backward file not found: {backward_path}"
                    results['comparisons'].append(comparison)
                    logger.warning(f"{req_name}: Backward file not found")
                    continue
                
                try:
                    # Load both ASTs
                    with open(forward_path, 'rb') as f:
                        forward_ast = pickle.load(f)
                    
                    with open(backward_path, 'rb') as f:
                        backward_ast = pickle.load(f)
                    
                    # Compare ASTs
                    equal = check_asts_equal(forward_ast, backward_ast)
                    
                    if equal:
                        results['successes'] += 1
                        comparison['status'] = 'equal'
                        comparison['equal'] = True
                        logger.info(f"{req_name}: ✓ Equivalent")
                    else:
                        results['failures'] += 1
                        comparison['status'] = 'not_equal'
                        comparison['equal'] = False
                        comparison['forward_ast'] = str(forward_ast)
                        comparison['backward_ast'] = str(backward_ast)
                        logger.warning(f"{req_name}: ✗ NOT Equivalent")
                        logger.debug(f"  Forward:  {str(forward_ast)}")
                        logger.debug(f"  Backward: {str(backward_ast)}")
                    
                    results['comparisons'].append(comparison)
                    
                except Exception as e:
                    results['failures'] += 1
                    comparison['status'] = 'error'
                    comparison['error'] = str(e)
                    results['comparisons'].append(comparison)
                    logger.error(f"{req_name}: Error during comparison - {str(e)}")
            
            # Print summary
            logger.info(f"\n--- Batch Comparison Summary ---")
            logger.info(f"Total files compared: {results['total']}")
            logger.info(f"Successes (equivalent): {results['successes']}")
            logger.info(f"Failures (not equivalent): {results['failures']}")
            logger.info(f"Missing backward files: {results['missing']}")
            
            if results['failures'] > 0 or results['missing'] > 0:
                logger.info("\nFailed/Missing requirements:")
                for comp in results['comparisons']:
                    if comp['status'] in ['not_equal', 'missing', 'error']:
                        logger.info(f" - {comp['requirement']} ({comp['status']})")
            
            return results
            
        except Exception as e:
            raise Exception(f"Failed to perform batch comparison: {str(e)}")
    
    def roundtrip_test(self, formula: str, req_name: str = "requirement") -> Dict[str, Any]:
        """Test full roundtrip conversion: STL -> Ontology -> STL.
        
        Args:
            formula: The STL formula string
            req_name: Name for the requirement
            
        Returns:
            Dictionary with roundtrip test results
        """
        import tempfile
        import os
        
        try:
            # Step 1: Parse original formula
            original_ast = to_ast(formula)
            
            # Apply canonicalization if requested
            if self.canonical:
                original_ast = canonical_stl.to_canonical_ast(original_ast)
            
            # Step 2: Convert to ontology
            ttl_body = stl_to_ont.create_formula_ttl(original_ast, req_name)
            
            # Add prefixes and original formula comment
            ttl_content = ONTOLOGY_PREFIXES + f"\n# Original formula: {formula}\n\n" + ttl_body
            
            # Step 3: Save to temporary file and read back
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
                f.write(ttl_content)
                temp_file = f.name
            
            try:
                # Step 4: Convert back from ontology
                result = self.ontology_to_formula(temp_file)
                if not result['results']:
                    raise Exception("No requirements found in generated TTL")
                reconstructed_ast = result['results'][0]['ast_obj']
                
                # Step 5: Compare ASTs
                equal = check_asts_equal(original_ast, reconstructed_ast)
                
                return {
                    'success': True,
                    'original_formula': formula,
                    'original_ast': str(original_ast),
                    'reconstructed_ast': str(reconstructed_ast),
                    'asts_equal': equal,
                    'canonical': self.canonical,
                    'ttl_content': ttl_content
                }
            finally:
                os.unlink(temp_file)
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'original_formula': formula
            }


# Backward-compatible import alias
MTLTool = STLTool


def format_output(data: Dict[str, Any], format_type: str = 'text') -> str:
    """Format output based on the requested format type.
    
    Args:
        data: Data to format
        format_type: Output format ('text', 'json')
        
    Returns:
        Formatted string
    """
    if format_type == 'json':
        # Remove non-serializable objects for JSON output
        clean_data = {}
        for k, v in data.items():
            if k != 'ast_obj' and not isinstance(v, STLFormula):
                clean_data[k] = v
        return json.dumps(clean_data, indent=2)
    else:
        # Text format
        output = []
        for k, v in data.items():
            if k != 'ast_obj':
                output.append(f"{k}: {v}")
        return '\n'.join(output)


def remap_results_path_for_canonical(path: str) -> str:
    """Map default results paths to results_canonical in canonical mode."""
    if not path:
        return path
    if path == "results" or path.startswith("results/"):
        return path.replace("results", "results_canonical", 1)
    if path == "./results" or path.startswith("./results/"):
        return path.replace("./results", "results_canonical", 1)
    return path


def main():
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description='STL Command Line Tool - Convert between STL formulas, ASTs, and ontologies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse an STL formula to AST
  %(prog)s parse "x > 10 && F[0,5] y > 20"
  
  # Parse an STL formula to AST and save to pickle file
  %(prog)s parse "x > 10 && F[0,5] y > 20" -o myFormula
  # Note: Will save to code/results/plkFiles/myFormula.pkl
  
  # Convert STL formula to ontology
  %(prog)s to-ontology "G[0,10] (speed < 50)" -o traffic_rule.ttl
  
  # Convert ontology back to STL
  %(prog)s from-ontology traffic_rule.ttl
  
  # Convert ontology back to STL and save AST to pickle file
  %(prog)s from-ontology traffic_rule.ttl -o reconstructed
  # Note: Will save to code/results/plkFiles/reconstructed.pkl
  
  # Compare two formulas
  %(prog)s compare "x > 10 && y > 20" "y > 20 && x > 10"
  
  # Test roundtrip conversion
  %(prog)s roundtrip "!(x < 5 && y > 3)"
  
  # Use canonical form
  %(prog)s -c parse "!(x < 5 && y > 3)"
  
  # Process multiple formulas from a file (forward conversion)
  %(prog)s batch ../dataset/STL_formulas.txt -p req -o results/forward
  
  # Reconstruct ASTs from a TTL file (backward conversion)
  %(prog)s batch-reconstruct results/requirements_ontology.ttl -o results/backward
  
  # Compare pickle files between forward and backward directories
  %(prog)s compare-batch -f results/forward -b results/backward 
        """
    )
    
    # Global options
    parser.add_argument('-c', '--canonical', action='store_true',
                        help='Use canonical form for AST operations')
    parser.add_argument('-f', '--format', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Parse command
    parse_parser = subparsers.add_parser('parse', help='Parse STL formula to AST')
    parse_parser.add_argument('formula', help='STL formula to parse')
    parse_parser.add_argument('-o', '--output', help='Output file for AST (pickle format). If no path provided, saves to results/plkFiles/')
    
    # To-ontology command
    to_ont_parser = subparsers.add_parser('to-ontology', help='Convert STL formula to ontology')
    to_ont_parser.add_argument('formula', help='STL formula to convert')
    to_ont_parser.add_argument('-n', '--name', default='requirement',
                               help='Requirement name (default: requirement)')
    to_ont_parser.add_argument('-o', '--output', help='Output TTL file')
    
    # From-ontology command
    from_ont_parser = subparsers.add_parser('from-ontology', help='Convert ontology to STL formula')
    from_ont_parser.add_argument('ttl_file', help='TTL file to convert')
    from_ont_parser.add_argument('-o', '--output', help='Output file for reconstructed ASTs (pickle format). If no path provided, saves to results/plkFiles/')
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare two STL formulas/ASTs')
    compare_parser.add_argument('formula1', help='First STL formula or pickle file')
    compare_parser.add_argument('formula2', help='Second STL formula or pickle file')
    
    # Roundtrip command
    roundtrip_parser = subparsers.add_parser('roundtrip', help='Test roundtrip conversion')
    roundtrip_parser.add_argument('formula', help='STL formula to test')
    roundtrip_parser.add_argument('-n', '--name', default='requirement',
                                  help='Requirement name (default: requirement)')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple STL formulas from a file')
    batch_parser.add_argument('input_file', help='Input file containing STL formulas (one per line)')
    batch_parser.add_argument('-p', '--prefix', default='req',
                              help='Prefix for requirement names (default: req)')
    batch_parser.add_argument('-o', '--output-dir', default='results/forward',
                              help='Output directory for results (default: results/forward)')
    
    # Batch reconstruct command
    batch_recon_parser = subparsers.add_parser('batch-reconstruct', help='Reconstruct ASTs from a TTL file')
    batch_recon_parser.add_argument('ttl_file', help='TTL file containing ontologies')
    batch_recon_parser.add_argument('-o', '--output-dir', default='results/backward',
                                    help='Output directory for reconstructed ASTs (default: results/backward)')
    
    # Batch compare command
    batch_compare_parser = subparsers.add_parser('compare-batch', help='Compare pickle files between forward and backward directories')
    batch_compare_parser.add_argument('-f', '--forward', default='results/forward',
                                      help='Directory with forward conversion pickle files (default: results/forward)')
    batch_compare_parser.add_argument('-b', '--backward', default='results/backward',
                                      help='Directory with backward conversion pickle files (default: results/backward)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Set up logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Keep canonical outputs isolated under results_canonical when default results paths are used.
    if args.canonical:
        if args.command in ('batch', 'batch-reconstruct') and hasattr(args, 'output_dir'):
            remapped_output_dir = remap_results_path_for_canonical(args.output_dir)
            if remapped_output_dir != args.output_dir:
                logger.info(f"Canonical mode: remapping output directory to {remapped_output_dir}")
                args.output_dir = remapped_output_dir

        if args.command == 'batch-reconstruct' and hasattr(args, 'ttl_file'):
            remapped_ttl_file = remap_results_path_for_canonical(args.ttl_file)
            if remapped_ttl_file != args.ttl_file:
                logger.info(f"Canonical mode: remapping TTL file path to {remapped_ttl_file}")
                args.ttl_file = remapped_ttl_file
    
    # Create tool instance
    tool = STLTool(canonical=args.canonical)
    
    try:
        if args.command == 'parse':
            result = tool.parse_formula(args.formula)
            
            # Output AST
            if args.output:
                # If output doesn't have a path, save to results/plkFiles directory
                if not os.path.dirname(args.output):
                    output_path = os.path.join(current_dir, 'results', 'plkFiles', args.output)
                else:
                    output_path = args.output
                
                # Ensure .pkl extension
                if not output_path.endswith('.pkl'):
                    output_path += '.pkl'
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    pickle.dump(result['ast_obj'], f)
                logger.info(f"AST saved to {output_path}")
            else:
                print(format_output(result, args.format))
        
        elif args.command == 'to-ontology':
            ttl_content = tool.formula_to_ontology(args.formula, args.name)
            
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(ttl_content)
                logger.info(f"Ontology saved to {args.output}")
            else:
                print(ttl_content)
        
        elif args.command == 'from-ontology':
            result = tool.ontology_to_formula(args.ttl_file)
            
            if args.output:
                # If output doesn't have a path, save to results/plkFiles directory
                if not os.path.dirname(args.output):
                    output_path = os.path.join(current_dir, 'results', 'plkFiles', args.output)
                else:
                    output_path = args.output
                
                # Ensure .pkl extension
                if not output_path.endswith('.pkl'):
                    output_path += '.pkl'
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Save reconstructed ASTs
                asts = {r['requirement']: r['ast_obj'] for r in result['results']}
                with open(output_path, 'wb') as f:
                    pickle.dump(asts, f)
                logger.info(f"Reconstructed ASTs saved to {output_path}")
            
            print(format_output(result, args.format))
        
        elif args.command == 'compare':
            # Load ASTs (either from formula strings or pickle files)
            def load_ast(input_str):
                if input_str.endswith('.pkl') or input_str.endswith('.pickle'):
                    with open(input_str, 'rb') as f:
                        return pickle.load(f)
                else:
                    ast = to_ast(input_str)
                    if args.canonical:
                        ast = canonical_stl.to_canonical_ast(ast)
                    return ast
            
            ast1 = load_ast(args.formula1)
            ast2 = load_ast(args.formula2)
            
            result = tool.compare_asts(ast1, ast2)
            print(format_output(result, args.format))
            
            # Exit with code 0 if equal, 1 if not equal
            sys.exit(0 if result['equal'] else 1)
        
        elif args.command == 'roundtrip':
            result = tool.roundtrip_test(args.formula, args.name)
            print(format_output(result, args.format))
            
            # Exit with code 0 if successful and ASTs equal, 1 otherwise
            sys.exit(0 if result.get('success') and result.get('asts_equal') else 1)
        
        elif args.command == 'batch':
            result = tool.batch_process(args.input_file, args.prefix, args.output_dir)
            
            # Print summary
            if args.format == 'json':
                # For JSON, only include serializable data
                json_result = {
                    'total': result['total'],
                    'successful': result['successful'],
                    'failed': result['failed'],
                    'formulas': [{k: v for k, v in f.items() if k != 'ast_obj'} 
                                 for f in result['formulas']]
                }
                print(json.dumps(json_result, indent=2))
            else:
                # Already printed by batch_process method
                pass
            
            # Exit with code 0 if all successful, 1 if any failed
            sys.exit(0 if result['failed'] == 0 else 1)
        
        elif args.command == 'batch-reconstruct':
            result = tool.batch_reconstruct(args.ttl_file, args.output_dir)
            
            # Print summary
            if args.format == 'json':
                # For JSON, only include serializable data
                json_result = {
                    'total': result['total'],
                    'successful': result['successful'],
                    'failed': result['failed'],
                    'reconstructions': [{k: v for k, v in r.items() if k != 'ast_obj'} 
                                        for r in result['reconstructions']]
                }
                print(json.dumps(json_result, indent=2))
            else:
                # Already printed by batch_reconstruct method
                pass
            
            # Exit with code 0 if all successful, 1 if any failed
            sys.exit(0 if result['failed'] == 0 else 1)
        
        elif args.command == 'compare-batch':
            result = tool.batch_compare(args.forward, args.backward)
            
            # Print summary
            if args.format == 'json':
                # For JSON, only include serializable data
                json_result = {
                    'total': result['total'],
                    'successes': result['successes'],
                    'failures': result['failures'],
                    'missing': result['missing'],
                    'comparisons': result['comparisons']
                }
                print(json.dumps(json_result, indent=2))
            else:
                # Already printed by batch_compare method
                pass
            
            # Exit with code 0 if all successful, 1 if any failed or missing
            sys.exit(0 if result['failures'] == 0 and result['missing'] == 0 else 1)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
