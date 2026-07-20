import pickle as pkl
import sys
import os
from graphviz import Digraph
sys.path.append('..')
from stl import Operation, RelOperation, STLFormula

class ASTVisualizer:
    def __init__(self):
        self.node_counter = 0
        self.graph = None
        
    def get_node_label(self, node):
        """Generate a human-readable label for each node type."""
        if node.op == Operation.PRED:
            rel_symbol = {
                RelOperation.GT: ">",
                RelOperation.LT: "<",
                RelOperation.GE: "≥",
                RelOperation.LE: "≤",
                RelOperation.EQ: "=",
                RelOperation.NQ: "≠"
            }.get(node.relation, "?")
            return f"{node.variable} {rel_symbol} {node.threshold}"
            
        elif node.op == Operation.VAR:
            return f"Var: {node.variable}"
            
        elif node.op == Operation.BOOL:
            return "True" if node.value else "False"
            
        elif node.op == Operation.ALWAYS:
            return f"G[{node.low}, {node.high}]"
            
        elif node.op == Operation.EVENT:
            return f"F[{node.low}, {node.high}]"
            
        elif node.op == Operation.UNTIL:
            return f"U[{node.low}, {node.high}]"
            
        elif node.op == Operation.NOT:
            return "¬ (NOT)"
            
        elif node.op == Operation.AND:
            return "∧ (AND)"
            
        elif node.op == Operation.OR:
            return "∨ (OR)"
            
        elif node.op == Operation.IMPLIES:
            return "→ (IMPLIES)"
            
        else:
            return f"Op: {node.op}"
    
    def get_node_shape(self, node):
        """Return appropriate shape for different node types."""
        if node.op in (Operation.PRED, Operation.VAR, Operation.BOOL):
            return "box"
        elif node.op in (Operation.ALWAYS, Operation.EVENT, Operation.UNTIL):
            return "diamond"
        else:
            return "ellipse"
    
    def get_node_color(self, node):
        """Return color scheme for different node types."""
        color_map = {
            Operation.PRED: "lightblue",
            Operation.VAR: "lightgreen",
            Operation.BOOL: "lightyellow",
            Operation.AND: "lightcoral",
            Operation.OR: "lightpink",
            Operation.NOT: "lightgray",
            Operation.IMPLIES: "plum",
            Operation.ALWAYS: "lightsteelblue",
            Operation.EVENT: "palegreen",
            Operation.UNTIL: "peachpuff"
        }
        return color_map.get(node.op, "white")
    
    def visualize_node(self, node, parent_id=None):
        """Recursively visualize nodes and their connections."""
        if node is None:
            return
            
        # Create unique node ID
        node_id = f"node_{self.node_counter}"
        self.node_counter += 1
        
        # Add node to graph
        label = self.get_node_label(node)
        shape = self.get_node_shape(node)
        color = self.get_node_color(node)
        
        self.graph.node(node_id, label=label, shape=shape, 
                       style="filled", fillcolor=color, fontsize="10")
        
        # Connect to parent if exists
        if parent_id:
            self.graph.edge(parent_id, node_id)
        
        # Handle different node types
        if hasattr(node, 'child') and node.child:
            self.visualize_node(node.child, node_id)
            
        if hasattr(node, 'left') and node.left:
            self.visualize_node(node.left, node_id)
            
        if hasattr(node, 'right') and node.right:
            self.visualize_node(node.right, node_id)
            
        if hasattr(node, 'children') and node.children:
            for i, child in enumerate(node.children):
                self.visualize_node(child, node_id)
    
    def visualize_ast(self, ast_root, output_name="ast_tree"):
        """Create and render the visualization."""
        self.node_counter = 0
        self.graph = Digraph(comment='AST Visualization')
        self.graph.attr(rankdir='TB')  # Top to Bottom layout
        self.graph.attr('node', fontname='Arial')
        self.graph.attr('edge', fontname='Arial')
        
        # Start visualization from root
        self.visualize_node(ast_root)
        
        # Render to file
        self.graph.render(output_name, format='png', cleanup=True)
        self.graph.render(output_name, format='pdf', cleanup=True)
        
        return self.graph

def load_and_visualize_pkl(pkl_path, output_name=None):
    """Load a PKL file and visualize the AST."""
    try:
        # Load the AST from pickle file
        with open(pkl_path, 'rb') as f:
            ast = pkl.load(f)
        
        print(f"Successfully loaded AST from {pkl_path}")
        
        # Generate output name if not provided
        if output_name is None:
            base_name = os.path.splitext(os.path.basename(pkl_path))[0]
            output_name = f"ast_viz_{base_name}"
        
        # Create visualizer and generate visualization
        visualizer = ASTVisualizer()
        graph = visualizer.visualize_ast(ast, output_name)
        
        print(f"Visualization saved as {output_name}.png and {output_name}.pdf")
        
        # Also print text representation
        print("\n--- AST Text Structure ---")
        print_ast_text(ast)
        
        return graph
        
    except Exception as e:
        print(f"Error loading or visualizing {pkl_path}: {e}")
        return None

def print_ast_text(node, indent=0):
    """Print text representation of AST (similar to your print_ast_structure)."""
    indent_str = "  " * indent
    
    if node.op == Operation.PRED:
        rel_str = RelOperation.getString(node.relation)
        print(f"{indent_str}PREDICATE: {node.variable} {rel_str} {node.threshold}")
    elif node.op == Operation.VAR:
        print(f"{indent_str}VARIABLE: {node.variable}")
    elif node.op == Operation.BOOL:
        print(f"{indent_str}BOOLEAN: {node.value}")
    elif node.op == Operation.ALWAYS:
        print(f"{indent_str}GLOBALLY [{node.low}, {node.high}]:")
        if node.child:
            print_ast_text(node.child, indent + 1)
    elif node.op == Operation.EVENT:
        print(f"{indent_str}EVENTUALLY [{node.low}, {node.high}]:")
        if node.child:
            print_ast_text(node.child, indent + 1)
    elif node.op == Operation.UNTIL:
        print(f"{indent_str}UNTIL [{node.low}, {node.high}]:")
        print(f"{indent_str}  Left:")
        if node.left:
            print_ast_text(node.left, indent + 2)
        print(f"{indent_str}  Right:")
        if node.right:
            print_ast_text(node.right, indent + 2)
    elif node.op == Operation.NOT:
        print(f"{indent_str}NOT:")
        if node.child:
            print_ast_text(node.child, indent + 1)
    elif node.op == Operation.AND:
        print(f"{indent_str}AND:")
        if hasattr(node, 'children'):
            for i, child in enumerate(node.children):
                print(f"{indent_str}  Child {i+1}:")
                print_ast_text(child, indent + 2)
    elif node.op == Operation.OR:
        print(f"{indent_str}OR:")
        if hasattr(node, 'children'):
            for i, child in enumerate(node.children):
                print(f"{indent_str}  Child {i+1}:")
                print_ast_text(child, indent + 2)
    elif node.op == Operation.IMPLIES:
        print(f"{indent_str}IMPLIES:")
        print(f"{indent_str}  Left:")
        if node.left:
            print_ast_text(node.left, indent + 2)
        print(f"{indent_str}  Right:")
        if node.right:
            print_ast_text(node.right, indent + 2)

def compare_and_visualize(pkl1_path, pkl2_path):
    """Load two PKL files and create side-by-side visualization."""
    try:
        # Load both ASTs
        with open(pkl1_path, 'rb') as f:
            ast1 = pkl.load(f)
        with open(pkl2_path, 'rb') as f:
            ast2 = pkl.load(f)
        
        # Create combined graph
        graph = Digraph(comment='AST Comparison')
        graph.attr(rankdir='TB')
        graph.attr('graph', compound='true')
        
        # Create subgraphs for each AST
        with graph.subgraph(name='cluster_0') as sg1:
            sg1.attr(label=f'AST 1: {os.path.basename(pkl1_path)}')
            sg1.attr(style='filled', color='lightgrey')
            visualizer1 = ASTVisualizer()
            visualizer1.graph = sg1
            visualizer1.visualize_node(ast1)
        
        with graph.subgraph(name='cluster_1') as sg2:
            sg2.attr(label=f'AST 2: {os.path.basename(pkl2_path)}')
            sg2.attr(style='filled', color='lightblue')
            visualizer2 = ASTVisualizer()
            visualizer2.graph = sg2
            visualizer2.node_counter = 1000  # Offset to avoid ID conflicts
            visualizer2.visualize_node(ast2)
        
        output_name = "ast_comparison"
        graph.render(output_name, format='png', cleanup=True)
        graph.render(output_name, format='pdf', cleanup=True)
        
        print(f"Comparison visualization saved as {output_name}.png and {output_name}.pdf")
        
    except Exception as e:
        print(f"Error comparing ASTs: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python visualize.py <pkl_file>                    # Visualize single AST")
        print("  python visualize.py <pkl_file1> <pkl_file2>       # Compare two ASTs")
        print("  python visualize.py --dir <directory>              # Visualize all PKL files in directory")
        sys.exit(1)
    
    if sys.argv[1] == "--dir" and len(sys.argv) >= 3:
        # Visualize all PKL files in directory
        directory = sys.argv[2]
        pkl_files = [f for f in os.listdir(directory) if f.endswith('.pkl')]
        
        if not pkl_files:
            print(f"No .pkl files found in {directory}")
            sys.exit(1)
        
        print(f"Found {len(pkl_files)} PKL files to visualize")
        
        for pkl_file in pkl_files:
            pkl_path = os.path.join(directory, pkl_file)
            print(f"\n--- Processing {pkl_file} ---")
            load_and_visualize_pkl(pkl_path)
            
    elif len(sys.argv) == 2:
        # Single file visualization
        load_and_visualize_pkl(sys.argv[1])
        
    elif len(sys.argv) == 3:
        # Compare two files
        compare_and_visualize(sys.argv[1], sys.argv[2])
    
    else:
        print("Invalid arguments")
        sys.exit(1)