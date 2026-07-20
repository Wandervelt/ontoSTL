import sys
import pickle
from rdflib import Graph, Namespace, URIRef, RDF, Literal, BNode
sys.path.append('..')
from pytelo_modified.stl import Operation, RelOperation, STLFormula
import os

# --- Define Namespaces ---
STL = Namespace("http://stl#")
LEGACY_MTL = Namespace("http://mtl#")
TIME = Namespace("http://www.w3.org/2006/time#")
REQ = Namespace("http://requirements#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

FORMULA_TYPES = (
    STL.STLFormula,
    LEGACY_MTL.MTLFormula,
    STL.MTLFormula,
    LEGACY_MTL.STLFormula,
)

# --- Mappings from Ontology to AST Codes ---
ONTOLOGY_NAME_TO_OPCODE = {
    "And": Operation.AND, "Or": Operation.OR, "Not": Operation.NOT,
    "Implies": Operation.IMPLIES, "Until": Operation.UNTIL,
    "Eventually": Operation.EVENT, "Globally": Operation.ALWAYS,
    "True": Operation.BOOL, "False": Operation.BOOL,
    "GreaterThan": Operation.PRED, "LessThan": Operation.PRED,
    "GreaterThanOrEqual": Operation.PRED, "LessThanOrEqual": Operation.PRED,
    "Equal": Operation.PRED, "NotEqual": Operation.PRED,
    "Atomic": Operation.VAR, 
}
OPNAME_TO_RELCODE = {
    "GreaterThan": RelOperation.GT, "LessThan": RelOperation.LT,
    "GreaterThanOrEqual": RelOperation.GE, "LessThanOrEqual": RelOperation.LE,
    "Equal": RelOperation.EQ, "NotEqual": RelOperation.NQ,
}


def _literal_to_bound(lit, default):
    """Parse a TIME.numericPosition literal into a float bound."""
    if lit is None:
        return default

    value = lit.toPython() if hasattr(lit, "toPython") else lit

    if isinstance(value, str):
        norm = value.strip().lower()
        if norm in ("inf", "+inf"):
            return float('inf')
        if norm == "-inf":
            return float('-inf')
        try:
            return float(norm)
        except ValueError:
            return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def get_interval_bounds(interval_node, g):
    low, high = 0.0, float('inf')

    if not interval_node:
        return low, high
    
    beg_inst = g.value(interval_node, TIME.hasBeginning)
    if beg_inst:
        try:
            beg_pos_bnode = g.value(beg_inst, TIME.inTimePosition)
            low_lit = g.value(beg_pos_bnode, TIME.numericPosition)
            if low_lit is not None:
                low = _literal_to_bound(low_lit, low)
        except Exception:
            pass

    end_inst = g.value(interval_node, TIME.hasEnd)
    if end_inst:
        try:
            end_pos_bnode = g.value(end_inst, TIME.inTimePosition)
            high_lit = g.value(end_pos_bnode, TIME.numericPosition)
            if high_lit is not None:
                high = _literal_to_bound(high_lit, high)
        except Exception:
            pass
    
    else:
        high = float('inf')

    return low, high


def _value_with_compat(g, subject, property_name):
    for ns in (STL, LEGACY_MTL):
        value = g.value(subject, ns[property_name])
        if value is not None:
            return value
    return None


def _is_formula_node(node_ref, g):
    return any((node_ref, RDF.type, formula_type) in g for formula_type in FORMULA_TYPES)


def _iter_requirement_formulas(g):
    seen = set()
    for formula_type in FORMULA_TYPES:
        for subj in g.subjects(RDF.type, formula_type):
            if str(subj).startswith(str(REQ)) and subj not in seen:
                seen.add(subj)
                yield subj

def ontology_to_ast(node_ref, g):
    if not isinstance(node_ref, (URIRef, BNode)) or not _is_formula_node(node_ref, g):
        if isinstance(node_ref, Literal):
             return node_ref.toPython()
        return None

    op_uri = _value_with_compat(g, node_ref, "hasOperator")
    if not op_uri:
        return None

    op_name = op_uri.split('#')[-1] if '#' in op_uri else op_uri.split('/')[-1]
    op_code = ONTOLOGY_NAME_TO_OPCODE.get(op_name)

    if op_code is None:
        return None

    if op_code == Operation.VAR:
        variable_ref = _value_with_compat(g, node_ref, "hasOperand")
        if variable_ref is None: return None
        return STLFormula(Operation.VAR, variable=str(variable_ref.toPython()))

    if op_code == Operation.PRED:
        rel_code = OPNAME_TO_RELCODE.get(op_name)
        variable_ref = _value_with_compat(g, node_ref, "hasLeftOperand")
        threshold_ref = _value_with_compat(g, node_ref, "hasRightOperand")
        if variable_ref is None or threshold_ref is None:
            return None
        variable = variable_ref.toPython()
        threshold = threshold_ref.toPython()
        return STLFormula(Operation.PRED, relation=rel_code, variable=str(variable), threshold=float(threshold))

    elif op_code in (Operation.AND, Operation.OR):
        children = []
        
        # A small stack to process nodes iteratively instead of just one level deep
        nodes_to_process = [node_ref]
        
        while nodes_to_process:
            current_node_ref = nodes_to_process.pop(0)
            
            left_ref = _value_with_compat(g, current_node_ref, "hasLeftOperand")
            right_ref = _value_with_compat(g, current_node_ref, "hasRightOperand")

            right_op_uri = _value_with_compat(g, right_ref, "hasOperator")
            is_nested_same_op = False
            if right_op_uri:
                 right_op_name = right_op_uri.split('#')[-1]
                 right_op_code = ONTOLOGY_NAME_TO_OPCODE.get(right_op_name)
                 if right_op_code == op_code:
                     is_nested_same_op = True

            left_ast = ontology_to_ast(left_ref, g)
            if left_ast:
                 children.append(left_ast)

            if is_nested_same_op:
                nodes_to_process.append(right_ref)
            else:
                right_ast = ontology_to_ast(right_ref, g)
                if right_ast:
                    children.append(right_ast)

        return STLFormula(op_code, children=children)
    
    elif op_code == Operation.IMPLIES:
        left_ref = _value_with_compat(g, node_ref, "hasLeftOperand")
        right_ref = _value_with_compat(g, node_ref, "hasRightOperand")
        left_ast = ontology_to_ast(left_ref, g)
        right_ast = ontology_to_ast(right_ref, g)
        if not left_ast or not right_ast:
            return None
        return STLFormula(op_code, left=left_ast, right=right_ast)

    elif op_code == Operation.BOOL:
        value = (op_name == "True")
        return STLFormula(Operation.BOOL, value=value)

    elif op_code == Operation.UNTIL:
        left_ref = _value_with_compat(g, node_ref, "hasLeftOperand")
        right_ref = _value_with_compat(g, node_ref, "hasRightOperand")
        left_ast = ontology_to_ast(left_ref, g)
        right_ast = ontology_to_ast(right_ref, g)
        if not left_ast or not right_ast:
            return None
        
        low, high = get_interval_bounds(_value_with_compat(g, node_ref, "hasTimeInterval"), g)
        
        return STLFormula(op_code, left=left_ast, right=right_ast, low=low, high=high)
    
    elif op_code in (Operation.ALWAYS, Operation.EVENT, Operation.NOT):
        child_ref = _value_with_compat(g, node_ref, "hasRightOperand")
        child_ast = ontology_to_ast(child_ref, g)
        if not child_ast:
            return None
        if op_code in (Operation.ALWAYS, Operation.EVENT):
            low, high = get_interval_bounds(_value_with_compat(g, node_ref, "hasTimeInterval"), g)
            return STLFormula(op_code, child=child_ast, low=low, high=high)
        else:
            return STLFormula(op_code, child=child_ast)
    
    return None

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <path_to_formula.ttl>")
        sys.exit(1)

    ttl_file = sys.argv[1]
    output_file = "reconstructed_STL_formulas.txt"
    
    ast_dir = "asts_reconstructed"
    os.makedirs(ast_dir, exist_ok=True)
    
    g = Graph()
    g.parse(ttl_file, format="turtle")
    
    REQ = Namespace("http://requirements#")
    requirements = list(_iter_requirement_formulas(g))
    
    if not requirements:
        print("Error: No requirements found in the TTL file.")
        sys.exit(1)
    
    print(f"Found {len(requirements)} requirements to process.")
    
    reconstructed_formulas = []
    
    for req_uri in requirements:
        req_name = str(req_uri).split('#')[-1]
        print(f"\n--- Processing {req_name} ---")
        
        try:
            ast_root = ontology_to_ast(req_uri, g)
            
            if ast_root:
                print("--- Successfully Reconstructed AST Structure ---")
                
                stl_string_output = str(ast_root)
                print("--- Reconstructed STL String ---")
                print(stl_string_output)
                
                reconstructed_formulas.append(f"{stl_string_output}")

                ast_path = os.path.join(ast_dir, f"{req_name}.pkl")
                with open(ast_path, 'wb') as f:
                    pickle.dump(ast_root, f)
                print(f"Reconstructed AST for comparison saved to '{ast_path}'")

            else:
                print(f"<Error: Failed to build AST from ontology for {req_name}>")
                reconstructed_formulas.append(f"# {req_name}\n# ERROR: Failed to reconstruct")
                
        except Exception as e:
            print(f"<Error processing {req_name}: {e}>")
            reconstructed_formulas.append(f"# {req_name}\n# ERROR: {str(e)}")
    
    with open(output_file, "w") as f:
        f.write("\n".join(reconstructed_formulas))
    
    print(f"\n--- Finished processing all requirements ---")
    print(f"Reconstructed STL formulas written to '{output_file}'")

if __name__ == "__main__":
    main()
