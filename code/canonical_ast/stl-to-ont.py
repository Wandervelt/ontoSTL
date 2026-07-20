import sys
import pickle
sys.path.append('..')
from pytelo_modified.stl import to_ast, Operation, RelOperation, STLFormula, stlParser
import os

PREFIXES = """@prefix stl: <http://stl#> .
@prefix mtl: <http://mtl#> .
@prefix time: <http://www.w3.org/2006/time#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix req: <http://requirements#> .
"""


def _serialize_time_bound(value):
    """Serialize numeric bounds for TIME.numericPosition."""
    if value == float('inf'):
        return '"INF"^^xsd:double'
    if value == float('-inf'):
        return '"-INF"^^xsd:double'
    return f'"{float(value)}"^^xsd:double'


def _build_interval_ttl(node, next_indent):
    """Create a time:Interval block for temporal operators."""
    interval_properties = ["a time:Interval"]

    beginning_ttl = (
        f"[ a time:Instant ; time:inTimePosition [ time:numericPosition "
        f"{_serialize_time_bound(node.low)} ; time:hasTRS time:unitSecond ] ]"
    )
    interval_properties.append(f"time:hasBeginning {beginning_ttl}")

    end_ttl = (
        f"[ a time:Instant ; time:inTimePosition [ time:numericPosition "
        f"{_serialize_time_bound(node.high)} ; time:hasTRS time:unitSecond ] ]"
    )
    interval_properties.append(f"time:hasEnd {end_ttl}")

    return (
        f"[\n{next_indent}    " +
        f" ;\n{next_indent}    ".join(interval_properties) +
        f"\n{next_indent}]"
    )

def print_ast_structure(node, indent=0):
    """Recursively prints the structure of the AST."""
    indent_str = "  " * indent
    op_name = Operation.getString(node.op) or f"Op_{node.op}"
    print(f"{indent_str}Node: {op_name}")
    if node.op == Operation.BOOL:
        print(f"{indent_str}  Value: {node.value}")
    elif node.op == Operation.VAR:
        print(f"{indent_str}  Variable: {node.variable}")
    elif node.op == Operation.PRED:
        print(f"{indent_str}  Expression: {node.variable} {RelOperation.getString(node.relation)} {node.threshold}")
    elif node.op in (Operation.ALWAYS, Operation.EVENT, Operation.UNTIL):
        print(f"{indent_str}  Interval: [{node.low}, {node.high}]")
    if hasattr(node, 'children'):
        for i, child in enumerate(node.children):
            print(f"{indent_str}Child {i}:")
            print_ast_structure(child, indent + 2)
    if hasattr(node, 'left') and node.left:
        print(f"{indent_str}Left child:")
        print_ast_structure(node.left, indent + 2)
    if hasattr(node, 'right') and node.right:
        print(f"{indent_str}Right child:")
        print_ast_structure(node.right, indent + 2)
    if hasattr(node, 'child') and node.child:
        print(f"{indent_str}Child:")
        print_ast_structure(node.child, indent + 2)

def create_formula_ttl(ast, root_name):
    """Creates the complete TTL string with prefixes."""
    prefix_declarations = [
        # "@prefix stl: <http://stl#> .",
        # "@prefix time: <http://www.w3.org/2006/time#> .",
        # "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        # "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        # "@prefix req: <http://requirements#> .",
        # ""
    ]
    formula_body = ast_to_turtle(ast, root_name, is_root=True, current_indent="")
    return "\n".join(prefix_declarations) + formula_body + " ."


def apply_nnf(node):
    """Pushes negations inwards to achieve NNF."""
    if node.op != Operation.NOT or not hasattr(node, 'child'):
        return node

    child = node.child
    
    # Double negation: NOT(NOT(A)) -> A
    if child.op == Operation.NOT:
        return child.child # Return the grandchild

    # De Morgan's for AND: NOT(A AND B) -> (NOT A) OR (NOT B)
    if child.op == Operation.AND:
        new_children = [STLFormula(Operation.NOT, child=c) for c in child.children]
        return STLFormula(Operation.OR, children=new_children)

    # De Morgan's for OR: NOT(A OR B) -> (NOT A) AND (NOT B)
    if child.op == Operation.OR:
        new_children = [STLFormula(Operation.NOT, child=c) for c in child.children]
        return STLFormula(Operation.AND, children=new_children)

    # Temporal dualities
    # NOT(F[t1,t2] A) -> G[t1,t2] (NOT A)
    if child.op == Operation.EVENT:
        return STLFormula(Operation.ALWAYS, child=STLFormula(Operation.NOT, child=child.child), low=child.low, high=child.high)
        
    # NOT(G[t1,t2] A) -> F[t1,t2] (NOT A)
    if child.op == Operation.ALWAYS:
        return STLFormula(Operation.EVENT, child=STLFormula(Operation.NOT, child=child.child), low=child.low, high=child.high)

    # Predicate negation: NOT(x > c) -> x <= c, etc.
    if child.op == Operation.PRED:
        return STLFormula(
            Operation.PRED,
            relation=RelOperation.negop[child.relation],
            variable=child.variable,
            threshold=child.threshold
        )

    return node # If no rule applies, return the original NOT node


def apply_implication_elimination(node):
    """Eliminate implication: (A -> B) becomes (!A OR B)."""
    if node.op == Operation.IMPLIES and hasattr(node, 'left') and hasattr(node, 'right'):
        return STLFormula(
            Operation.OR,
            children=[STLFormula(Operation.NOT, child=node.left), node.right]
        )
    return node


def apply_boolean_simplification(node):
    # This function relies on the main `to_canonical_ast` function for recursion.
    
    if node.op not in (Operation.AND, Operation.OR):
        return node
        
    # --- Flatten Step ---
    flat_children = []
    nodes_to_process = list(node.children)
    while nodes_to_process:
        child = nodes_to_process.pop(0)
        if child.op == node.op:
            nodes_to_process.extend(child.children)
        else:
            flat_children.append(child)
    
    # --- G-Distribution Rule (for AND nodes) ---
    if node.op == Operation.AND and len(flat_children) > 1:
        is_all_g = all(c.op == Operation.ALWAYS for c in flat_children)
        if is_all_g:
            first_child = flat_children[0]
            interval = (first_child.low, first_child.high)
            if all((c.low, c.high) == interval for c in flat_children):
                inner_children = [c.child for c in flat_children]
                inner_and_node = STLFormula(Operation.AND, children=inner_children)

                canonical_inner_node = to_canonical_ast(inner_and_node)
                
                return STLFormula(Operation.ALWAYS, child=canonical_inner_node, low=interval[0], high=interval[1])

    # --- Standard Simplification and Uniqueness ---
    simplified_children = set()
    if node.op == Operation.AND:
        if any(c.op == Operation.BOOL and not c.value for c in flat_children):
            return STLFormula(Operation.BOOL, value=False)
        for child in flat_children:
            if not (child.op == Operation.BOOL and child.value):
                simplified_children.add(child)

    elif node.op == Operation.OR:
        if any(c.op == Operation.BOOL and c.value for c in flat_children):
            return STLFormula(Operation.BOOL, value=True)
        for child in flat_children:
            if not (child.op == Operation.BOOL and not child.value):
                simplified_children.add(child)

    # --- Final Sorting and Node Creation ---
    if not simplified_children:
        if node.op == Operation.AND: return STLFormula(Operation.BOOL, value=True)
        if node.op == Operation.OR: return STLFormula(Operation.BOOL, value=False)

    if len(simplified_children) == 1:
        return list(simplified_children)[0]
    
    # The final sort guarantees canonical order for all other cases
    sorted_children = sorted(list(simplified_children))
    return STLFormula(node.op, children=sorted_children)


def apply_temporal_simplification(node):
    # For G[a,b](G[c,d](A)) -> G[a+c, b+d](A)
    if node.op == Operation.ALWAYS and hasattr(node, 'child') and node.child.op == Operation.ALWAYS:
        # Get the inner formula's child
        inner_child = node.child.child
        
        # Compose the intervals using Minkowski sum
        new_low = node.low + node.child.low
        new_high = node.high + node.child.high
        
        return STLFormula(Operation.ALWAYS, child=inner_child, low=new_low, high=new_high)

    # For F[a,b](F[c,d](A)) -> F[a+c, b+d](A)
    if node.op == Operation.EVENT and hasattr(node, 'child') and node.child.op == Operation.EVENT:
        # Get the inner formula's child
        inner_child = node.child.child
        
        # Compose the intervals using Minkowski sum
        new_low = node.low + node.child.low
        new_high = node.high + node.child.high
        
        return STLFormula(Operation.EVENT, child=inner_child, low=new_low, high=new_high)
    
    # Return the node unchanged if no simplification rule applies
    return node



def to_canonical_ast(node):
    """
    Recursively transforms an AST node into a canonical form.
    """
    if node is None:
        return None

    # 0. Eliminate implication first so recursive pass can simplify introduced NOT/OR.
    node = apply_implication_elimination(node)

    # 1. Recursively canonicalize children first (post-order traversal)
    if hasattr(node, 'left'):
        node.left = to_canonical_ast(node.left)
    if hasattr(node, 'right'):
        node.right = to_canonical_ast(node.right)
    if hasattr(node, 'child'):
        node.child = to_canonical_ast(node.child)
    if hasattr(node, 'children'):
        node.children = [to_canonical_ast(c) for c in node.children]

    # 2. Apply canonicalization rules to the current node
    node = apply_nnf(node)
    node = apply_boolean_simplification(node)
    node = apply_temporal_simplification(node)
    # The flattening, sorting, and uniqueness will be part of apply_boolean_simplification

    return node


def ast_to_turtle(node, root_name, is_root=False, current_indent=""):
    """
    Recursively transforms an AST node into a TTL string.
    """
    prop_lines = []
    next_indent = current_indent + "    "
    
    op_name_map = {
        Operation.AND: "And", Operation.OR: "Or", Operation.NOT: "Not",
        Operation.IMPLIES: "Implies", Operation.UNTIL: "Until",
        Operation.EVENT: "Eventually", Operation.ALWAYS: "Globally"
    }
    rel_op_name_map = {
        RelOperation.GT: "GreaterThan", RelOperation.LT: "LessThan",
        RelOperation.GE: "GreaterThanOrEqual", RelOperation.LE: "LessThanOrEqual",
        RelOperation.EQ: "Equal", RelOperation.NQ: "NotEqual"
    }

    if node.op == Operation.VAR:
        prop_lines.append(f"stl:hasOperator stl:Atomic")
        prop_lines.append(f"stl:hasOperand \"{node.variable}\"")

    if node.op == Operation.PRED:
        prop_lines.append(f"stl:hasOperator stl:{rel_op_name_map[node.relation]}")
        prop_lines.append(f"stl:hasLeftOperand \"{node.variable}\"")
        prop_lines.append(f"stl:hasRightOperand \"{node.threshold}\"^^xsd:double")

    elif node.op in (Operation.ALWAYS, Operation.EVENT):
        prop_lines.append(f"stl:hasOperator stl:{op_name_map[node.op]}")
        time_interval_ttl = _build_interval_ttl(node, next_indent)
        prop_lines.append(f"stl:hasTimeInterval {time_interval_ttl}")

        if hasattr(node, 'child') and node.child:
            child_ttl = ast_to_turtle(node.child, root_name, is_root=False, current_indent=next_indent)
            prop_lines.append(f"stl:hasRightOperand {child_ttl}")

    elif node.op in (Operation.AND, Operation.OR):
        prop_lines.append(f"stl:hasOperator stl:{op_name_map[node.op]}")
        if hasattr(node, 'children') and len(node.children) >= 2:
            left_child_ttl = ast_to_turtle(node.children[0], root_name, is_root=False, current_indent=next_indent)
            prop_lines.append(f"stl:hasLeftOperand {left_child_ttl}")
            if len(node.children) == 2:
                right_child_ttl = ast_to_turtle(node.children[1], root_name, is_root=False, current_indent=next_indent)
            else:
                remaining_children_node = STLFormula(node.op, children=node.children[1:])
                right_child_ttl = ast_to_turtle(remaining_children_node, root_name, is_root=False, current_indent=next_indent)
            
            prop_lines.append(f"stl:hasRightOperand {right_child_ttl}")

    elif node.op == Operation.NOT:
        prop_lines.append(f"stl:hasOperator stl:{op_name_map[node.op]}")
        if hasattr(node, 'child') and node.child:
            child_ttl = ast_to_turtle(node.child, root_name, is_root=False, current_indent=next_indent)
            prop_lines.append(f"stl:hasRightOperand {child_ttl}")

    elif node.op == Operation.IMPLIES:
        prop_lines.append(f"stl:hasOperator stl:{op_name_map[node.op]}")
        if hasattr(node, 'left') and node.left and hasattr(node, 'right') and node.right:
            left_child_ttl = ast_to_turtle(node.left, root_name, is_root=False, current_indent=next_indent)
            right_child_ttl = ast_to_turtle(node.right, root_name, is_root=False, current_indent=next_indent)
            prop_lines.append(f"stl:hasLeftOperand {left_child_ttl}")
            prop_lines.append(f"stl:hasRightOperand {right_child_ttl}")
            
    elif node.op == Operation.UNTIL:
        prop_lines.append(f"stl:hasOperator stl:{op_name_map[node.op]}")
        time_interval_ttl = _build_interval_ttl(node, next_indent)
        prop_lines.append(f"stl:hasTimeInterval {time_interval_ttl}")
        if hasattr(node, 'left') and node.left and hasattr(node, 'right') and node.right:
            left_child_ttl = ast_to_turtle(node.left, root_name, is_root=False, current_indent=next_indent)
            right_child_ttl = ast_to_turtle(node.right, root_name, is_root=False, current_indent=next_indent)
            prop_lines.append(f"stl:hasLeftOperand {left_child_ttl}")
            prop_lines.append(f"stl:hasRightOperand {right_child_ttl}")
    
    elif node.op == Operation.BOOL:
        op_name = "True" if node.value else "False"
        prop_lines.append(f"stl:hasOperator stl:{op_name}")
    
    properties_ttl = f" ;\n{next_indent}".join(prop_lines)
    
    if is_root:
        return f"req:{root_name} a stl:STLFormula ;\n{next_indent}{properties_ttl}"
    else:
        return f"[\n{next_indent}a stl:STLFormula ;\n{next_indent}{properties_ttl}\n{current_indent}]"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stl-to-ont.py <requirement_name_prefix>")
        sys.exit(1)

    requirement_name_prefix = sys.argv[1]
    output_filename = "requirements_ontology.ttl"
    input_filename = "STL_formulas.txt"
    ast_dir = "asts_original"

    os.makedirs(ast_dir, exist_ok=True)

    try:
        with open(input_filename, "r") as f:
            formulas = f.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find '{input_filename}' in the current directory.")
        sys.exit(1)
        
    all_ttl_outputs = []
    
    for i, formula_string in enumerate(formulas, 1):
        formula_string = formula_string.strip()
        if not formula_string:
            continue
            
        requirement_name = f"{requirement_name_prefix}_{i}"
        print(f"\n--- Processing Formula {i}: {requirement_name} ---")
        
        try:
            ast = to_ast(formula_string)
            canonical_ast = to_canonical_ast(ast)
            print("\n--- Canonical AST Structure ---")
            print_ast_structure(canonical_ast)
            
            ast_path = os.path.join(ast_dir, f"{requirement_name}.pkl")
            with open(ast_path, 'wb') as f:
                pickle.dump(ast, f)
            
            ttl_output = create_formula_ttl(canonical_ast, requirement_name)

            all_ttl_outputs.append(ttl_output)
            
            
            print(f"AST saved to '{ast_path}'")
            print(f"TTL generated for '{requirement_name}'")

        except Exception as e:
            print(f"Error processing formula '{formula_string}': {e}")
            continue

    with open(output_filename, "w") as f:


        f.write(PREFIXES)
        f.write("\n\n".join(all_ttl_outputs))
    print(f"\n--- Finished. All TTL content written to '{output_filename}' ---")

