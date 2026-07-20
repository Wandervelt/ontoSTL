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
    if len(sys.argv) < 3:
        print("Usage: python stl-to-ont.py \"formula\" <requirement_name>")
        sys.exit(1)

    formula_string = sys.argv[1]
    requirement_name = sys.argv[2]
    output_filename = "requirements_ontology.ttl"

    ast = to_ast(formula_string)
    
    print("--- AST Structure from Input Formula ---")
    print_ast_structure(ast)
    print("--------------------------------------\n")
    
    ttl_output = create_formula_ttl(ast, requirement_name)
    
    with open(output_filename, "a") as f:
        f.write(PREFIXES)
        f.write("\n\n" + ttl_output)
    
    print(f"Successfully appended to '{output_filename}'.")
    print("--- New Generated TTL Output ---")
    print(ttl_output)



