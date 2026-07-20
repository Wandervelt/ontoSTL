import time
import os
import sys
import pickle
import psutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
from datetime import datetime
import json
import argparse

# Add parent directory and current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# Import core STL module (modified PyTeLo grammar and parser)
from pytelo_modified.stl import to_ast, STLFormula, Operation, RelOperation
from rdflib import Graph, Namespace, RDF

# Define the prefixes that need to be added
PREFIXES = """@prefix stl: <http://stl#> .
@prefix mtl: <http://mtl#> .
@prefix time: <http://www.w3.org/2006/time#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix req: <http://requirements#> .

"""

STL_NS = Namespace("http://stl#")
LEGACY_MTL_NS = Namespace("http://mtl#")
FORMULA_TYPE_URIS = (
    STL_NS.STLFormula,
    LEGACY_MTL_NS.MTLFormula,
    STL_NS.MTLFormula,
    LEGACY_MTL_NS.STLFormula,
)


def load_module_from_file(module_name, file_path):
    """Load a Python module from a file path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def has_formula_type(g, formula_uri):
    return any((formula_uri, RDF.type, formula_type) in g for formula_type in FORMULA_TYPE_URIS)

class ScalabilityAnalyzer:
    def __init__(self, formulas_file, output_dir, mode='canonical'):
        self.formulas_file = formulas_file
        self.output_dir = output_dir
        self.mode = mode
        self.results = []
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize process for memory monitoring
        self.process = psutil.Process()
        
        # Load conversion modules based on mode
        if mode == 'canonical':
            # Load canonical modules
            canonical_stl_to_ont = load_module_from_file("canonical_stl_to_ont", 
                                                       os.path.join(current_dir, "canonical_ast", "stl-to-ont.py"))
            canonical_ont_to_stl = load_module_from_file("canonical_ont_to_stl", 
                                                       os.path.join(current_dir, "canonical_ast", "ont-to-stl.py"))
            
            self.create_formula_ttl = canonical_stl_to_ont.create_formula_ttl
            self.to_canonical_ast = canonical_stl_to_ont.to_canonical_ast
            self.ontology_to_ast = canonical_ont_to_stl.ontology_to_ast
        else:
            # Load non-canonical modules
            non_canonical_stl_to_ont = load_module_from_file("non_canonical_stl_to_ont", 
                                                           os.path.join(current_dir, "non-canonical_ast", "stl-to-ont.py"))
            non_canonical_ont_to_stl = load_module_from_file("non_canonical_ont_to_stl", 
                                                           os.path.join(current_dir, "non-canonical_ast", "ont-to-stl.py"))
            
            self.create_formula_ttl = non_canonical_stl_to_ont.create_formula_ttl
            self.to_canonical_ast = None  # No canonicalization in non-canonical mode
            self.ontology_to_ast = non_canonical_ont_to_stl.ontology_to_ast
            
        # Store references to imported modules
        self.to_ast = to_ast
        self.Operation = Operation
        self.Graph = Graph
        self.Namespace = Namespace
        self.RDF = RDF
        
    def get_memory_usage(self):
        """Get current memory usage in MB"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def calculate_ast_depth(self, node, current_depth=0):
        """Calculate maximum depth of AST"""
        if node is None:
            return current_depth
        
        max_depth = current_depth
        
        # Check children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                child_depth = self.calculate_ast_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
        
        # Check left/right
        if hasattr(node, 'left') and node.left:
            left_depth = self.calculate_ast_depth(node.left, current_depth + 1)
            max_depth = max(max_depth, left_depth)
            
        if hasattr(node, 'right') and node.right:
            right_depth = self.calculate_ast_depth(node.right, current_depth + 1)
            max_depth = max(max_depth, right_depth)
            
        # Check child
        if hasattr(node, 'child') and node.child:
            child_depth = self.calculate_ast_depth(node.child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
            
        return max_depth
    
    def count_operators(self, node, op_count=None):
        """Count operators in AST by type"""
        if op_count is None:
            op_count = defaultdict(int)
        
        if node is None:
            return op_count
            
        # Count current node's operator
        op_count['total'] += 1
        op_name = self.Operation.getString(node.op) if hasattr(self.Operation, 'getString') else f"Op_{node.op}"
        op_count[op_name] += 1
        
        # Count temporal operators
        if node.op in [self.Operation.ALWAYS, self.Operation.EVENT, self.Operation.UNTIL]:
            op_count['temporal'] += 1
        # Count logical operators  
        elif node.op in [self.Operation.AND, self.Operation.OR, self.Operation.NOT, self.Operation.IMPLIES]:
            op_count['logical'] += 1
        # Count predicates
        elif node.op == self.Operation.PRED:
            op_count['predicate'] += 1
            
        # Recursively count in children
        if hasattr(node, 'children') and node.children:
            for child in node.children:
                self.count_operators(child, op_count)
                
        if hasattr(node, 'left') and node.left:
            self.count_operators(node.left, op_count)
            
        if hasattr(node, 'right') and node.right:
            self.count_operators(node.right, op_count)
            
        if hasattr(node, 'child') and node.child:
            self.count_operators(node.child, op_count)
            
        return op_count
    
    def categorize_formula(self, ast):
        """Categorize formula based on structure"""
        op_count = self.count_operators(ast)
        depth = self.calculate_ast_depth(ast)
        
        if op_count['temporal'] == 0:
            return "atomic_only"
        elif op_count['temporal'] == 1 and depth <= 2:
            return "simple_temporal"
        elif op_count['temporal'] > 1 and depth > 3:
            return "nested_temporal"
        elif op_count['logical'] >= 3:
            return "complex_boolean"
        else:
            return "moderate"
    
    def analyze_single_formula(self, formula, index):
        """Analyze transformation performance for a single formula"""
        result = {
            'index': index,
            'formula': formula,
            'formula_length': len(formula)
        }
        
        try:
            # Forward transformation: STL string -> AST
            start_mem = self.get_memory_usage()
            start_time = time.perf_counter()
            
            ast = self.to_ast(formula)
            
            # Apply canonicalization if in canonical mode
            if self.mode == 'canonical' and self.to_canonical_ast:
                ast = self.to_canonical_ast(ast)
            
            ast_time = time.perf_counter() - start_time
            
            # AST -> OWL/TTL
            ttl_start = time.perf_counter()
            requirement_name = f"formula_{index}"
            ttl_output = self.create_formula_ttl(ast, requirement_name)
            ttl_time = time.perf_counter() - ttl_start
            
            forward_time = time.perf_counter() - start_time
            forward_mem = self.get_memory_usage() - start_mem
            
            # Backward transformation: OWL/TTL -> AST
            back_start_time = time.perf_counter()
            back_start_mem = self.get_memory_usage()
            
            # Create complete TTL with prefixes
            complete_ttl = PREFIXES + ttl_output
            
            # Parse TTL
            g = self.Graph()
            g.parse(data=complete_ttl, format="turtle")
            
            # Find the formula in the graph
            REQ = self.Namespace("http://requirements#")
            
            formula_uri = REQ[requirement_name]
            
            # Check if the formula exists in the graph
            if not has_formula_type(g, formula_uri):
                raise Exception(f"Formula {requirement_name} not found in graph")
            
            reconstructed_ast = self.ontology_to_ast(formula_uri, g)
            
            backward_time = time.perf_counter() - back_start_time
            backward_mem = self.get_memory_usage() - back_start_mem
            
            # Total round-trip time
            total_time = forward_time + backward_time
            
            # Analyze AST structure
            ast_depth = self.calculate_ast_depth(ast)
            op_count = self.count_operators(ast)
            category = self.categorize_formula(ast)
            
            # Update result
            result.update({
                'ast_depth': ast_depth,
                'num_operators': op_count['total'],
                'num_temporal': op_count.get('temporal', 0),
                'num_logical': op_count.get('logical', 0),
                'num_predicates': op_count.get('predicate', 0),
                'category': category,
                'ast_parse_time': ast_time,
                'ttl_generation_time': ttl_time,
                'forward_time': forward_time,
                'backward_time': backward_time,
                'total_time': total_time,
                'forward_memory': forward_mem,
                'backward_memory': backward_mem,
                'ttl_size': len(complete_ttl),
                'success': True
            })
            
        except Exception as e:
            print(f"Error processing formula {index}: {str(e)}")
            result.update({
                'success': False,
                'error': str(e),
                # Add default values for failed cases
                'ast_depth': 0,
                'num_operators': 0,
                'num_temporal': 0,
                'num_logical': 0,
                'num_predicates': 0,
                'category': 'error',
                'ast_parse_time': 0,
                'ttl_generation_time': 0,
                'forward_time': 0,
                'backward_time': 0,
                'total_time': 0,
                'forward_memory': 0,
                'backward_memory': 0,
                'ttl_size': 0
            })
            
        return result
    
    def run_batch_analysis(self, formulas):
        """Analyze performance with different batch sizes"""
        print("\n=== Batch Processing Analysis ===")
        batch_sizes = [1, 10, 100, 1000]
        batch_results = []
        
        for batch_size in batch_sizes:
            if batch_size > len(formulas):
                continue
                
            print(f"\nTesting batch size: {batch_size}")
            
            # Test first 1000 formulas in batches
            test_formulas = formulas[:min(1000, len(formulas))]
            num_batches = min(10, len(test_formulas) // batch_size)  # Limit to 10 batches for speed
            
            batch_times = []
            for i in range(num_batches):
                start_idx = i * batch_size
                end_idx = start_idx + batch_size
                batch = test_formulas[start_idx:end_idx]
                
                start_time = time.perf_counter()
                start_mem = self.get_memory_usage()
                
                for j, formula in enumerate(batch):
                    try:
                        ast = self.to_ast(formula)
                        if self.mode == 'canonical' and self.to_canonical_ast:
                            ast = self.to_canonical_ast(ast)
                        ttl = self.create_formula_ttl(ast, f"temp_{i}_{j}")
                        # Add prefixes and parse to ensure it's valid
                        complete_ttl = PREFIXES + ttl
                        g = self.Graph()
                        g.parse(data=complete_ttl, format="turtle")
                    except:
                        pass  # Continue on error
                    
                batch_time = time.perf_counter() - start_time
                batch_mem = self.get_memory_usage() - start_mem
                
                batch_times.append(batch_time / batch_size)  # Average per formula
                
            if batch_times:  # Only add if we have results
                batch_results.append({
                    'batch_size': batch_size,
                    'avg_time_per_formula': np.mean(batch_times),
                    'std_time': np.std(batch_times),
                    'memory_per_formula': batch_mem / batch_size
                })
            
        return pd.DataFrame(batch_results)
    
    def run_analysis(self):
        """Run complete scalability analysis"""
        print(f"Starting scalability analysis in {self.mode} mode...")
        
        # Load formulas
        with open(self.formulas_file, 'r') as f:
            formulas = [line.strip() for line in f if line.strip()]
        
        print(f"Loaded {len(formulas)} formulas")
        
        # Analyze each formula
        for i, formula in enumerate(formulas):
            if i % 100 == 0:
                print(f"Processing formula {i}/{len(formulas)}")
                
            result = self.analyze_single_formula(formula, i)
            self.results.append(result)
        
        # Convert to DataFrame
        self.df = pd.DataFrame(self.results)
        
        # Save raw results first
        self.df.to_csv(os.path.join(self.output_dir, 'scalability_results.csv'), index=False)
        print(f"\nSaved raw results to {self.output_dir}/scalability_results.csv")
        
        # Check how many were successful
        successful = len(self.df[self.df['success'] == True])
        print(f"Successfully processed {successful}/{len(self.df)} formulas")

        # Build cumulative runtime artifacts over processing order (0..N formulas).
        self.generate_cumulative_runtime_plot()
        
        self.analyze_outliers()

        # Generate analysis and plots
        self.generate_statistics()
        self.generate_plots()
        
        # Run batch analysis separately (after main analysis is complete)
        self.batch_df = self.run_batch_analysis(formulas)
        if not self.batch_df.empty:
            self.batch_df.to_csv(os.path.join(self.output_dir, 'batch_results.csv'), index=False)
            self.plot_batch_results()

    def generate_cumulative_runtime_plot(self):
        """Plot cumulative runtime as the number of processed formulas increases."""
        if not hasattr(self, 'df') or self.df.empty:
            print("No data available for cumulative runtime plot.")
            return

        ordered = self.df.sort_values('index').copy()

        # Ensure timing columns exist and are numeric.
        for col in ['forward_time', 'backward_time', 'total_time']:
            if col not in ordered.columns:
                ordered[col] = 0.0
            ordered[col] = pd.to_numeric(ordered[col], errors='coerce').fillna(0.0)

        ordered['formula_count'] = np.arange(1, len(ordered) + 1)
        ordered['cumulative_forward_time_s'] = ordered['forward_time'].cumsum()
        ordered['cumulative_backward_time_s'] = ordered['backward_time'].cumsum()
        ordered['cumulative_total_time_s'] = ordered['total_time'].cumsum()

        # Add explicit origin point (0 formulas, 0 seconds).
        origin = pd.DataFrame(
            {
                'formula_count': [0],
                'cumulative_forward_time_s': [0.0],
                'cumulative_backward_time_s': [0.0],
                'cumulative_total_time_s': [0.0],
            }
        )
        cumulative_df = pd.concat(
            [
                origin,
                ordered[
                    [
                        'formula_count',
                        'cumulative_forward_time_s',
                        'cumulative_backward_time_s',
                        'cumulative_total_time_s',
                    ]
                ],
            ],
            ignore_index=True,
        )

        cumulative_csv_path = os.path.join(self.output_dir, 'cumulative_runtime.csv')
        cumulative_df.to_csv(cumulative_csv_path, index=False)

        plt.figure(figsize=(10, 6))
        plt.plot(
            cumulative_df['formula_count'],
            cumulative_df['cumulative_total_time_s'],
            label='Total (forward + backward)',
            linewidth=2.5,
            color='black',
        )
        plt.plot(
            cumulative_df['formula_count'],
            cumulative_df['cumulative_forward_time_s'],
            label='Forward cumulative',
            linewidth=1.8,
            color='tab:blue',
            alpha=0.9,
        )
        plt.plot(
            cumulative_df['formula_count'],
            cumulative_df['cumulative_backward_time_s'],
            label='Backward cumulative',
            linewidth=1.8,
            color='tab:green',
            alpha=0.9,
        )
        plt.xlabel('Number of Formulas Processed')
        plt.ylabel('Cumulative Time (s)')
        plt.title('Cumulative Runtime vs Number of Formulas')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        cumulative_plot_path = os.path.join(self.output_dir, 'cumulative_formulas_vs_time.png')
        plt.savefig(cumulative_plot_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Saved cumulative runtime data to {cumulative_csv_path}")
        print(f"Saved cumulative runtime plot to {cumulative_plot_path}")

    def analyze_outliers(self):
        """Analyze formulas that take significantly longer than median"""
        successful_df = self.df[self.df['success'] == True]
        
        if len(successful_df) == 0:
            return
        
        median_time = successful_df['total_time'].median()
        
        # Find formulas that take > 10x median time
        outliers = successful_df[successful_df['total_time'] > 10 * median_time]
        
        if len(outliers) > 0:
            print(f"\n=== OUTLIER ANALYSIS ===")
            print(f"Found {len(outliers)} outliers (>{10*median_time:.3f}s, which is 10x median)")
            print(f"Outlier percentage: {len(outliers)/len(successful_df)*100:.2f}%")
            
            # Analyze what makes them special
            print("\nOutlier characteristics:")
            print(f"  Average formula length: {outliers['formula_length'].mean():.1f} chars (vs {successful_df['formula_length'].mean():.1f} overall)")
            print(f"  Average AST depth: {outliers['ast_depth'].mean():.1f} (vs {successful_df['ast_depth'].mean():.1f} overall)")
            print(f"  Average operators: {outliers['num_operators'].mean():.1f} (vs {successful_df['num_operators'].mean():.1f} overall)")
            print(f"  Average temporal operators: {outliers['num_temporal'].mean():.1f} (vs {successful_df['num_temporal'].mean():.1f} overall)")
            
            # Category distribution
            print("\nOutlier categories:")
            for category, count in outliers['category'].value_counts().items():
                pct = count / len(outliers) * 100
                print(f"  {category}: {count} ({pct:.1f}%)")
            
            # Save outliers for further investigation
            outliers_with_formulas = outliers[['index', 'formula', 'total_time', 'formula_length', 
                                            'ast_depth', 'num_operators', 'category']].copy()
            outliers_with_formulas.to_csv(os.path.join(self.output_dir, 'outliers.csv'), index=False)
            print(f"\nSaved detailed outlier analysis to {self.output_dir}/outliers.csv")
            
            # Show a few example outlier formulas
            print("\nExample outlier formulas:")
            for idx, row in outliers_with_formulas.head(3).iterrows():
                print(f"  Formula {row['index']}: {row['formula'][:50]}... (time: {row['total_time']:.3f}s)")

    def generate_statistics(self):
        """Generate statistical summary"""
        successful_df = self.df[self.df['success'] == True]
        
        if len(successful_df) == 0:
            print("No successful transformations to analyze!")
            return
        
        stats = {
            'mode': self.mode,
            'total_formulas': len(self.df),
            'successful_transformations': len(successful_df),
            'failure_rate': (len(self.df) - len(successful_df)) / len(self.df) * 100,
            
            'timing_stats': {
                'forward_transformation': {
                    'mean': successful_df['forward_time'].mean(),
                    'median': successful_df['forward_time'].median(),
                    'std': successful_df['forward_time'].std(),
                    'min': successful_df['forward_time'].min(),
                    'max': successful_df['forward_time'].max(),
                    '95_percentile': successful_df['forward_time'].quantile(0.95),
                    '99_percentile': successful_df['forward_time'].quantile(0.99)
                },
                'backward_transformation': {
                    'mean': successful_df['backward_time'].mean(),
                    'median': successful_df['backward_time'].median(),
                    'std': successful_df['backward_time'].std(),
                    'min': successful_df['backward_time'].min(),
                    'max': successful_df['backward_time'].max(),
                    '95_percentile': successful_df['backward_time'].quantile(0.95),
                    '99_percentile': successful_df['backward_time'].quantile(0.99)
                },
                'total_roundtrip': {
                    'mean': successful_df['total_time'].mean(),
                    'median': successful_df['total_time'].median(),
                    'std': successful_df['total_time'].std(),
                    'min': successful_df['total_time'].min(),
                    'max': successful_df['total_time'].max(),
                    '95_percentile': successful_df['total_time'].quantile(0.95),
                    '99_percentile': successful_df['total_time'].quantile(0.99)
                }
            },
            
            'complexity_analysis': {
                'avg_formula_length': successful_df['formula_length'].mean(),
                'avg_ast_depth': successful_df['ast_depth'].mean(),
                'avg_operators': successful_df['num_operators'].mean(),
                'category_distribution': successful_df['category'].value_counts().to_dict()
            },
            
            'memory_stats': {
                'forward_memory_mean': successful_df['forward_memory'].mean(),
                'backward_memory_mean': successful_df['backward_memory'].mean()
            }
        }
        
        # Save statistics
        with open(os.path.join(self.output_dir, 'statistics.json'), 'w') as f:
            json.dump(stats, f, indent=2)
            
        # Print summary
        print(f"\n=== SCALABILITY ANALYSIS SUMMARY ({self.mode.upper()} MODE) ===")
        print(f"Total formulas analyzed: {stats['total_formulas']}")
        print(f"Success rate: {100 - stats['failure_rate']:.2f}%")
        print(f"\nTiming Statistics (seconds):")
        print(f"  Forward transformation:")
        print(f"    Mean: {stats['timing_stats']['forward_transformation']['mean']:.6f}")
        print(f"    Median: {stats['timing_stats']['forward_transformation']['median']:.6f}")
        print(f"    95th percentile: {stats['timing_stats']['forward_transformation']['95_percentile']:.6f}")
        print(f"  Backward transformation:")
        print(f"    Mean: {stats['timing_stats']['backward_transformation']['mean']:.6f}")
        print(f"    Median: {stats['timing_stats']['backward_transformation']['median']:.6f}")
        print(f"    95th percentile: {stats['timing_stats']['backward_transformation']['95_percentile']:.6f}")
        
    def generate_plots(self):
        """Generate visualization plots as separate figures"""
        successful_df = self.df[self.df['success'] == True]
        
        if len(successful_df) == 0:
            print("No successful transformations to plot!")
            return
        
        # Use clean default style
        plt.style.use('default')

        def scatter_plot(x, y, xlabel, ylabel, title, filename, log_y=False):
            plt.figure(figsize=(8, 6))
            plt.scatter(successful_df[x], successful_df[y], alpha=0.5, s=20, color='steelblue')
            plt.xlabel(xlabel)
            plt.ylabel(ylabel)
            plt.title(title)
            plt.grid(True)  # Regular grid
            if log_y:
                plt.yscale('log')
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, filename), dpi=300, bbox_inches='tight')
            plt.close()

        # Plot 1: Formula length vs time (log y)
        scatter_plot(
            x='formula_length',
            y='total_time',
            xlabel='Formula Length (characters)',
            ylabel='Total Transformation Time (s)',
            title='',
            filename='formula_length_vs_time_log.png',
            log_y=True
        )

        # Plot 2: AST depth vs time
        scatter_plot(
            x='ast_depth',
            y='total_time',
            xlabel='AST Depth',
            ylabel='Total Transformation Time (s)',
            title='',
            filename='ast_depth_vs_time.png'
        )

        # Plot 3: Number of operators vs time
        scatter_plot(
            x='num_operators',
            y='total_time',
            xlabel='Number of Operators',
            ylabel='Total Transformation Time (s)',
            title='',
            filename='num_operators_vs_time.png'
        )

        # Plot 4: Temporal operators vs time
        scatter_plot(
            x='num_temporal',
            y='total_time',
            xlabel='Number of Temporal Operators',
            ylabel='Total Transformation Time (s)',
            title='',
            filename='temporal_operators_vs_time.png'
        )

        # Plot 5: Distribution of operator counts across formulas
        operator_count_distribution = (
            successful_df['num_operators']
            .astype(int)
            .value_counts()
            .sort_index()
        )

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(
            operator_count_distribution.index,
            operator_count_distribution.values,
            width=0.9,
            color='steelblue',
            edgecolor='black',
            linewidth=0.6,
        )
        ax.set_xlabel('Number of Operators')
        ax.set_ylabel('Number of Formulas')
        ax.grid(True, axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'operator_count_histogram.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Box plots by category
        if 'category' in successful_df.columns and successful_df['category'].nunique() > 1:
            fig, ax = plt.subplots(figsize=(12, 8))
            category_order = ['atomic_only', 'simple_temporal', 'moderate', 
                             'complex_boolean', 'nested_temporal']
            existing_categories = [cat for cat in category_order if cat in successful_df['category'].unique()]
            
            successful_df.boxplot(column='total_time', by='category', ax=ax)
            ax.set_xlabel('Formula Category')
            ax.set_ylabel('Total Transformation Time (s)')
            ax.set_title('Transformation Time by Formula Category')
            plt.suptitle('')  # Remove automatic title
            plt.tight_layout()
            plt.savefig(os.path.join(self.output_dir, 'time_by_category.png'), dpi=300, bbox_inches='tight')
            plt.close()
        
        # 3. Time distribution histograms
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        axes[0].hist(successful_df['forward_time'], bins=50, alpha=0.7, color='blue')
        axes[0].set_xlabel('Forward Transformation Time (s)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Forward Transformation Time Distribution')
        axes[0].axvline(successful_df['forward_time'].median(), color='red', 
                       linestyle='--', label='Median')
        axes[0].legend()
        
        axes[1].hist(successful_df['backward_time'], bins=50, alpha=0.7, color='green')
        axes[1].set_xlabel('Backward Transformation Time (s)')
        axes[1].set_ylabel('Frequency')
        axes[1].set_title('Backward Transformation Time Distribution')
        axes[1].axvline(successful_df['backward_time'].median(), color='red', 
                       linestyle='--', label='Median')
        axes[1].legend()
        
        axes[2].hist(successful_df['total_time'], bins=50, alpha=0.7, color='purple')
        axes[2].set_xlabel('Total Round-trip Time (s)')
        axes[2].set_ylabel('Frequency')
        axes[2].set_title('Total Transformation Time Distribution')
        axes[2].axvline(successful_df['total_time'].median(), color='red', 
                       linestyle='--', label='Median')
        axes[2].legend()
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'time_distributions.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 4. Correlation heatmap
        correlation_cols = ['formula_length', 'ast_depth', 'num_operators', 
                           'num_temporal', 'num_logical', 'num_predicates',
                           'forward_time', 'backward_time', 'total_time']
        
        correlation_data = successful_df[correlation_cols].corr()
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(correlation_data, annot=True, fmt='.2f', cmap='coolwarm', 
                   center=0, square=True)
        plt.title('Correlation Matrix of Formula Complexity and Performance')
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'correlation_heatmap.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 5. CDF of transformation times
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sorted_times = np.sort(successful_df['total_time'])
        cdf = np.arange(1, len(sorted_times) + 1) / len(sorted_times)
        
        ax.plot(sorted_times, cdf, linewidth=2)
        ax.set_xlabel('Total Transformation Time (s)')
        ax.set_ylabel('Cumulative Probability')
        ax.set_title('Cumulative Distribution of Transformation Times')
        ax.grid(True, alpha=0.3)
        
        # Add percentile markers
        for percentile in [50, 90, 95, 99]:
            time_val = np.percentile(sorted_times, percentile)
            ax.axvline(time_val, color='red', alpha=0.5, linestyle='--')
            ax.text(time_val, 0.05, f'{percentile}%', rotation=90, 
                   verticalalignment='bottom')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'time_cdf.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"\nPlots saved to {self.output_dir}/")
    
    def plot_batch_results(self):
        """Plot batch processing results separately"""
        if self.batch_df.empty:
            return
            
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(self.batch_df['batch_size'], self.batch_df['avg_time_per_formula'], 
               marker='o', linewidth=2, markersize=8)
        ax.set_xlabel('Batch Size')
        ax.set_ylabel('Average Time per Formula (s)')
        ax.set_title('Batch Processing Performance')
        ax.set_xscale('log')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'batch_performance.png'), dpi=300, bbox_inches='tight')
        plt.close()


def resolve_default_formulas_file():
    """Pick the default formulas file, preferring parser-ready instantiated STL formulas."""
    dataset_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dataset'))
    stl_instantiated = os.path.join(dataset_dir, 'STL_instantiated_formulas.txt')
    stl_default = os.path.join(dataset_dir, 'STL_formulas.txt')
    mtl_legacy = os.path.join(dataset_dir, 'MTL_formulas.txt')

    if os.path.exists(stl_instantiated):
        return stl_instantiated
    if os.path.exists(stl_default):
        return stl_default
    return mtl_legacy


def load_formulas(formulas_file):
    with open(formulas_file, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def print_analysis_report(mode, output_dir):
    """Print generated artifact summary for one mode run."""
    print(f"\n=== Analysis Complete ===")
    print(f"Mode: {mode}")
    print(f"Results saved to {output_dir}/")
    print("Generated files:")
    print("  - scalability_results.csv: Raw data for all formulas")
    print("  - statistics.json: Statistical summary")
    print("  - formula_length_vs_time_log.png: Formula length vs time (log scale)")
    print("  - ast_depth_vs_time.png: AST depth vs time")
    print("  - num_operators_vs_time.png: Number of operators vs time")
    print("  - temporal_operators_vs_time.png: Temporal operators vs time")
    print("  - operator_count_histogram.png: Histogram of formulas by operator count")
    print("  - time_by_category.png: Box plots by formula category")
    print("  - time_distributions.png: Histograms of transformation times")
    print("  - correlation_heatmap.png: Correlation analysis")
    print("  - time_cdf.png: Cumulative distribution function")
    print("  - cumulative_runtime.csv: Cumulative runtime by processed-formula count")
    print("  - cumulative_formulas_vs_time.png: Number of formulas vs cumulative time")
    print("  - batch_performance.png: Batch processing analysis (if generated)")
    print("  - outliers.csv: Detailed outlier analysis (if outliers found)")


def _prepare_cumulative_total_df(csv_path, mode_label):
    """Load and normalize cumulative runtime CSV for one mode."""
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"Missing cumulative runtime CSV: {csv_path}")

    df = pd.read_csv(csv_path)
    required = {'formula_count', 'cumulative_total_time_s'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns {sorted(missing)}: {csv_path}")

    df = df[['formula_count', 'cumulative_total_time_s']].copy()
    df['formula_count'] = pd.to_numeric(df['formula_count'], errors='coerce').fillna(0).astype(int)
    df['cumulative_total_time_s'] = pd.to_numeric(df['cumulative_total_time_s'], errors='coerce').fillna(0.0)
    df = df.sort_values('formula_count').drop_duplicates(subset=['formula_count'], keep='last')

    if df.empty or int(df.iloc[0]['formula_count']) != 0:
        df = pd.concat(
            [pd.DataFrame({'formula_count': [0], 'cumulative_total_time_s': [0.0]}), df],
            ignore_index=True,
        )

    df = df.rename(columns={'cumulative_total_time_s': f'{mode_label}_cumulative_total_time_s'})
    return df


def generate_combined_total_cumulative_plot(canonical_csv, noncanonical_csv, output_dir):
    """
    Generate a shared plot with canonical vs non-canonical cumulative total runtime.

    Returns:
        Tuple of (combined_csv_path, combined_plot_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    canonical_df = _prepare_cumulative_total_df(canonical_csv, 'canonical')
    noncanonical_df = _prepare_cumulative_total_df(noncanonical_csv, 'non_canonical')

    combined = pd.merge(canonical_df, noncanonical_df, on='formula_count', how='outer').sort_values('formula_count')
    combined['canonical_cumulative_total_time_s'] = combined['canonical_cumulative_total_time_s'].ffill().fillna(0.0)
    combined['non_canonical_cumulative_total_time_s'] = (
        combined['non_canonical_cumulative_total_time_s'].ffill().fillna(0.0)
    )

    combined_csv_path = os.path.join(output_dir, 'combined_cumulative_total_runtime.csv')
    combined.to_csv(combined_csv_path, index=False)

    plt.figure(figsize=(10, 6))
    plt.plot(
        combined['formula_count'],
        combined['canonical_cumulative_total_time_s'],
        label='Canonical total cumulative time',
        linewidth=2.3,
        color='tab:blue',
    )
    plt.plot(
        combined['formula_count'],
        combined['non_canonical_cumulative_total_time_s'],
        label='Non-canonical total cumulative time',
        linewidth=2.3,
        color='tab:orange',
    )
    plt.xlabel('Number of Formulas Processed')
    plt.ylabel('Cumulative Total Time (s)')
    plt.title('Canonical vs Non-Canonical Cumulative Total Runtime')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    combined_plot_path = os.path.join(output_dir, 'canonical_vs_noncanonical_cumulative_total_time.png')
    plt.savefig(combined_plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    return combined_csv_path, combined_plot_path


def run_repeated_total_cumulative_trials(formulas, mode, runs, output_dir):
    """
    Run repeated total-runtime trials for one mode and aggregate cumulative curves.

    Returns:
        dict with aggregate dataframe and generated artifact paths.
    """
    os.makedirs(output_dir, exist_ok=True)

    run_curve_dfs = []
    run_summaries = []
    num_formulas = len(formulas)

    for run_idx in range(1, runs + 1):
        print(f"\n[{mode}] Trial {run_idx}/{runs}")
        analyzer = ScalabilityAnalyzer(
            formulas_file="",
            output_dir=output_dir,
            mode=mode,
        )

        per_formula_total_times = []
        success_count = 0
        trial_start = time.perf_counter()

        for i, formula in enumerate(formulas):
            if i % 500 == 0:
                print(f"[{mode}] Trial {run_idx}/{runs}: formula {i}/{num_formulas}")

            result = analyzer.analyze_single_formula(formula, i)
            if result.get('success'):
                success_count += 1
                per_formula_total_times.append(float(result.get('total_time', 0.0) or 0.0))
            else:
                per_formula_total_times.append(0.0)

        wall_clock_s = time.perf_counter() - trial_start
        cumulative_total = np.concatenate([[0.0], np.cumsum(np.array(per_formula_total_times, dtype=float))])
        formula_counts = np.arange(0, num_formulas + 1, dtype=int)

        curve_col = f"run_{run_idx:02d}_cumulative_total_time_s"
        run_curve_dfs.append(pd.DataFrame({"formula_count": formula_counts, curve_col: cumulative_total}))

        run_summaries.append(
            {
                "run": run_idx,
                "mode": mode,
                "num_formulas": num_formulas,
                "successful": success_count,
                "failed": num_formulas - success_count,
                "final_cumulative_total_time_s": float(cumulative_total[-1]),
                "wall_clock_time_s": float(wall_clock_s),
            }
        )

    merged_curves = run_curve_dfs[0]
    for df in run_curve_dfs[1:]:
        merged_curves = merged_curves.merge(df, on="formula_count", how="inner")

    run_cols = [c for c in merged_curves.columns if c.startswith("run_") and c.endswith("_cumulative_total_time_s")]
    merged_curves["mean_cumulative_total_time_s"] = merged_curves[run_cols].mean(axis=1)
    merged_curves["std_cumulative_total_time_s"] = merged_curves[run_cols].std(axis=1, ddof=0)
    merged_curves["min_cumulative_total_time_s"] = merged_curves[run_cols].min(axis=1)
    merged_curves["max_cumulative_total_time_s"] = merged_curves[run_cols].max(axis=1)

    per_run_curves_csv = os.path.join(output_dir, f"{mode}_per_run_cumulative_total_runtime.csv")
    aggregate_csv = os.path.join(output_dir, f"{mode}_aggregate_cumulative_total_runtime.csv")
    per_run_summary_csv = os.path.join(output_dir, f"{mode}_per_run_summary.csv")
    merged_curves.to_csv(per_run_curves_csv, index=False)
    merged_curves[
        [
            "formula_count",
            "mean_cumulative_total_time_s",
            "std_cumulative_total_time_s",
            "min_cumulative_total_time_s",
            "max_cumulative_total_time_s",
        ]
    ].to_csv(aggregate_csv, index=False)
    pd.DataFrame(run_summaries).to_csv(per_run_summary_csv, index=False)

    print(f"[{mode}] Saved per-run curves:   {per_run_curves_csv}")
    print(f"[{mode}] Saved aggregate curve:  {aggregate_csv}")
    print(f"[{mode}] Saved run summary:      {per_run_summary_csv}")

    return {
        "merged_curves_df": merged_curves,
        "aggregate_df": merged_curves[
            [
                "formula_count",
                "mean_cumulative_total_time_s",
                "std_cumulative_total_time_s",
                "min_cumulative_total_time_s",
                "max_cumulative_total_time_s",
            ]
        ].copy(),
        "per_run_curves_csv": per_run_curves_csv,
        "aggregate_csv": aggregate_csv,
        "per_run_summary_csv": per_run_summary_csv,
    }


def generate_combined_averaged_total_plot(canonical_agg_df, noncanonical_agg_df, output_dir):
    """
    Generate combined plot using averaged cumulative total runtime across repeated trials.
    """
    os.makedirs(output_dir, exist_ok=True)

    canonical = canonical_agg_df.rename(
        columns={
            "mean_cumulative_total_time_s": "canonical_mean_cumulative_total_time_s",
            "std_cumulative_total_time_s": "canonical_std_cumulative_total_time_s",
            "min_cumulative_total_time_s": "canonical_min_cumulative_total_time_s",
            "max_cumulative_total_time_s": "canonical_max_cumulative_total_time_s",
        }
    )
    noncanonical = noncanonical_agg_df.rename(
        columns={
            "mean_cumulative_total_time_s": "non_canonical_mean_cumulative_total_time_s",
            "std_cumulative_total_time_s": "non_canonical_std_cumulative_total_time_s",
            "min_cumulative_total_time_s": "non_canonical_min_cumulative_total_time_s",
            "max_cumulative_total_time_s": "non_canonical_max_cumulative_total_time_s",
        }
    )

    combined = canonical.merge(noncanonical, on="formula_count", how="outer").sort_values("formula_count")
    combined = combined.ffill().fillna(0.0)

    combined_csv = os.path.join(output_dir, "combined_average_cumulative_total_runtime.csv")
    combined.to_csv(combined_csv, index=False)

    x = combined["formula_count"].to_numpy()
    c_mean = combined["canonical_mean_cumulative_total_time_s"].to_numpy()
    c_std = combined["canonical_std_cumulative_total_time_s"].to_numpy()
    n_mean = combined["non_canonical_mean_cumulative_total_time_s"].to_numpy()
    n_std = combined["non_canonical_std_cumulative_total_time_s"].to_numpy()

    plt.figure(figsize=(10, 6))
    plt.plot(x, c_mean, label="Canonical avg cumulative total", linewidth=2.3, color="tab:blue")
    plt.plot(x, n_mean, label="Non-canonical avg cumulative total", linewidth=2.3, color="tab:orange")
    plt.fill_between(x, c_mean - c_std, c_mean + c_std, color="tab:blue", alpha=0.15, linewidth=0)
    plt.fill_between(x, n_mean - n_std, n_mean + n_std, color="tab:orange", alpha=0.15, linewidth=0)
    plt.xlabel("Number of Formulas Processed")
    plt.ylabel("Cumulative Total Time (s)")
    plt.title("Average Cumulative Total Runtime (Canonical vs Non-Canonical)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    combined_plot = os.path.join(output_dir, "canonical_vs_noncanonical_avg_cumulative_total_time.png")
    plt.savefig(combined_plot, dpi=300, bbox_inches="tight")
    plt.close()

    return combined_csv, combined_plot


def main():
    parser = argparse.ArgumentParser(description='Run scalability analysis for STL-OWL conversion')
    parser.add_argument('--canonical', action='store_true', 
                       help='Run analysis in canonical mode')
    parser.add_argument('--non-canonical', action='store_true',
                       help='Run analysis in non-canonical mode')
    parser.add_argument(
        '--total',
        action='store_true',
        help='Run repeated trials for canonical and non-canonical and plot averaged cumulative total runtime',
    )
    parser.add_argument(
        '--runs',
        type=int,
        help='Number of repeated trials for --total mode (default: 30)',
    )
    parser.add_argument(
        '--30',
        dest='use_30_runs',
        action='store_true',
        help='Shortcut for --runs 30 (only meaningful with --total)',
    )
    parser.add_argument('--formulas-file', type=str,
                       help='Path to the formulas file (optional)')
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Directory where scalability artifacts will be written (optional)',
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    selected_modes = [bool(args.canonical), bool(args.non_canonical), bool(args.total)]
    if sum(selected_modes) != 1:
        print("Error: Specify exactly one of --canonical, --non-canonical, or --total")
        sys.exit(1)

    if not args.total and (args.runs is not None or args.use_30_runs):
        print("Warning: --runs/--30 are only used with --total; ignoring them.")
    
    # Prefer instantiated STL formulas because they are parser-ready.
    formulas_file = args.formulas_file if args.formulas_file else resolve_default_formulas_file()

    default_scalability_root = os.path.join(os.path.dirname(__file__), 'results', 'scalability')

    if args.total:
        total_runs = 30
        if args.runs is not None:
            total_runs = args.runs
        if args.use_30_runs:
            total_runs = 30
        if total_runs <= 0:
            print("Error: --runs must be a positive integer")
            sys.exit(1)

        formulas = load_formulas(formulas_file)
        if not formulas:
            print(f"Error: No formulas found in {formulas_file}")
            sys.exit(1)

        # Shared root directory for total-mode outputs.
        scalability_root = os.path.abspath(args.output_dir) if args.output_dir else default_scalability_root
        total_output_dir = os.path.join(scalability_root, 'total')

        print("\n=== Total Mode (Repeated Trials) ===")
        print(f"Formulas file: {formulas_file}")
        print(f"Number of formulas: {len(formulas)}")
        print(f"Trials per mode: {total_runs}")
        print(f"Output root: {total_output_dir}")

        canonical_out = os.path.join(total_output_dir, 'canonical')
        noncanonical_out = os.path.join(total_output_dir, 'non-canonical')

        canonical_results = run_repeated_total_cumulative_trials(
            formulas=formulas,
            mode='canonical',
            runs=total_runs,
            output_dir=canonical_out,
        )
        noncanonical_results = run_repeated_total_cumulative_trials(
            formulas=formulas,
            mode='non-canonical',
            runs=total_runs,
            output_dir=noncanonical_out,
        )

        combined_csv, combined_plot = generate_combined_averaged_total_plot(
            canonical_results['aggregate_df'],
            noncanonical_results['aggregate_df'],
            total_output_dir,
        )

        print(f"\n=== Combined Averaged Cumulative Total Runtime ===")
        print(f"Shared results root: {total_output_dir}/")
        print(f"Combined CSV:        {combined_csv}")
        print(f"Combined plot:       {combined_plot}")
        return

    # Single-mode behavior remains unchanged.
    mode = 'canonical' if args.canonical else 'non-canonical'
    output_dir = (
        os.path.abspath(args.output_dir)
        if args.output_dir
        else os.path.join(default_scalability_root, mode)
    )

    analyzer = ScalabilityAnalyzer(formulas_file=formulas_file, output_dir=output_dir, mode=mode)
    analyzer.run_analysis()
    print_analysis_report(mode, analyzer.output_dir)


if __name__ == "__main__":
    main()
