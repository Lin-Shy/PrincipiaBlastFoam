#!/usr/bin/env python3
"""
Retrieval Validation Dataset Analyzer and Evaluation Tool

This script provides utilities for working with the BlastFOAM retrieval validation dataset.
It includes functions for:
- Dataset statistics and analysis
- Retrieval system evaluation
- Performance metrics calculation
- Visualization of results
"""

import json
import numpy as np
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple, Callable
import matplotlib.pyplot as plt
from pathlib import Path


class RetrievalDatasetAnalyzer:
    """Analyzer for retrieval validation dataset."""
    
    def __init__(self, dataset_path: str):
        """Load and initialize the dataset."""
        with open(dataset_path, 'r', encoding='utf-8') as f:
            self.dataset = json.load(f)
        self.n_entries = len(self.dataset)
    
    def get_statistics(self) -> Dict:
        """Calculate comprehensive dataset statistics."""
        stats = {
            'total_entries': self.n_entries,
            'difficulty_distribution': Counter(e['difficulty'] for e in self.dataset),
            'category_distribution': Counter(e['category'] for e in self.dataset),
            'target_files_distribution': Counter(
                file for e in self.dataset for file in e['target_files']
            ),
            'multi_file_queries': sum(1 for e in self.dataset if len(e['target_files']) > 1),
            'single_file_queries': sum(1 for e in self.dataset if len(e['target_files']) == 1),
            'avg_files_per_query': np.mean([len(e['target_files']) for e in self.dataset]),
            'max_files_per_query': max(len(e['target_files']) for e in self.dataset),
        }
        
        # Query type analysis
        query_lengths = [len(e['query'].split()) for e in self.dataset]
        stats['avg_query_length'] = np.mean(query_lengths)
        stats['min_query_length'] = min(query_lengths)
        stats['max_query_length'] = max(query_lengths)
        
        return stats
    
    def print_statistics(self):
        """Print formatted statistics."""
        stats = self.get_statistics()
        
        print("=" * 70)
        print("RETRIEVAL VALIDATION DATASET STATISTICS")
        print("=" * 70)
        print(f"\nTotal Entries: {stats['total_entries']}")
        
        print(f"\n{'Difficulty Distribution:':<30}")
        for diff, count in sorted(stats['difficulty_distribution'].items()):
            pct = 100 * count / stats['total_entries']
            print(f"  {diff:<20} {count:>4} ({pct:>5.1f}%)")
        
        print(f"\n{'Query Types:':<30}")
        print(f"  {'Single-file queries':<20} {stats['single_file_queries']:>4}")
        print(f"  {'Multi-file queries':<20} {stats['multi_file_queries']:>4}")
        print(f"  {'Avg files per query':<20} {stats['avg_files_per_query']:>4.2f}")
        print(f"  {'Max files per query':<20} {stats['max_files_per_query']:>4}")
        
        print(f"\n{'Query Length Statistics:':<30}")
        print(f"  {'Average words':<20} {stats['avg_query_length']:>4.1f}")
        print(f"  {'Min words':<20} {stats['min_query_length']:>4}")
        print(f"  {'Max words':<20} {stats['max_query_length']:>4}")
        
        print(f"\n{'Top 10 Most Targeted Files:':<30}")
        for file, count in stats['target_files_distribution'].most_common(10):
            print(f"  {file:<40} {count:>3}")
        
        print(f"\n{'Top 10 Categories:':<30}")
        for cat, count in sorted(stats['category_distribution'].items(), 
                                 key=lambda x: x[1], reverse=True)[:10]:
            pct = 100 * count / stats['total_entries']
            print(f"  {cat:<30} {count:>3} ({pct:>5.1f}%)")
        
        print("=" * 70)
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Get all entries for a specific category."""
        return [e for e in self.dataset if e['category'] == category]
    
    def get_by_difficulty(self, difficulty: str) -> List[Dict]:
        """Get all entries for a specific difficulty level."""
        return [e for e in self.dataset if e['difficulty'] == difficulty]
    
    def get_by_file(self, filepath: str) -> List[Dict]:
        """Get all entries that target a specific file."""
        return [e for e in self.dataset if filepath in e['target_files']]
    
    def export_summary(self, output_path: str):
        """Export dataset summary to JSON."""
        stats = self.get_statistics()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"Summary exported to {output_path}")


class RetrievalEvaluator:
    """Evaluate retrieval system performance."""
    
    def __init__(self, dataset_path: str):
        """Initialize with dataset."""
        with open(dataset_path, 'r', encoding='utf-8') as f:
            self.dataset = json.load(f)
    
    def evaluate(
        self, 
        retrieval_function: Callable[[str], List[str]],
        verbose: bool = False
    ) -> Dict:
        """
        Evaluate a retrieval function against the dataset.
        
        Args:
            retrieval_function: Function that takes query string and returns list of file paths
            verbose: If True, print detailed results for each query
            
        Returns:
            Dictionary containing evaluation metrics
        """
        results = {
            'exact_matches': 0,
            'precisions': [],
            'recalls': [],
            'f1_scores': [],
            'reciprocal_ranks': [],
            'per_difficulty': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'per_category': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'false_positives': [],
            'false_negatives': [],
            'errors': []
        }
        
        for entry in self.dataset:
            try:
                retrieved = set(retrieval_function(entry['query']))
                target = set(entry['target_files'])
                
                # Calculate metrics
                tp = len(retrieved & target)
                fp = len(retrieved - target)
                fn = len(target - retrieved)
                
                exact_match = (retrieved == target)
                precision = tp / len(retrieved) if len(retrieved) > 0 else 0
                recall = tp / len(target) if len(target) > 0 else 0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                
                # Reciprocal rank (assume retrieved files are ordered)
                retrieved_list = list(retrieval_function(entry['query']))
                rr = 0
                for i, file in enumerate(retrieved_list, 1):
                    if file in target:
                        rr = 1 / i
                        break
                
                # Store results
                if exact_match:
                    results['exact_matches'] += 1
                results['precisions'].append(precision)
                results['recalls'].append(recall)
                results['f1_scores'].append(f1)
                results['reciprocal_ranks'].append(rr)
                results['false_positives'].append(fp)
                results['false_negatives'].append(fn)
                
                # Per-difficulty and per-category tracking
                results['per_difficulty'][entry['difficulty']]['total'] += 1
                if exact_match:
                    results['per_difficulty'][entry['difficulty']]['correct'] += 1
                
                results['per_category'][entry['category']]['total'] += 1
                if exact_match:
                    results['per_category'][entry['category']]['correct'] += 1
                
                if verbose:
                    print(f"\nQuery {entry['id']}: {entry['query'][:60]}...")
                    print(f"  Target: {target}")
                    print(f"  Retrieved: {retrieved}")
                    print(f"  Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {f1:.3f}")
                    if not exact_match:
                        print(f"  ✗ Not exact match")
                    
            except Exception as e:
                results['errors'].append({
                    'entry_id': entry['id'],
                    'query': entry['query'],
                    'error': str(e)
                })
                if verbose:
                    print(f"\nError on query {entry['id']}: {e}")
        
        # Calculate aggregate metrics
        n_total = len(self.dataset) - len(results['errors'])
        metrics = {
            'exact_match_accuracy': results['exact_matches'] / n_total if n_total > 0 else 0,
            'mean_precision': np.mean(results['precisions']) if results['precisions'] else 0,
            'mean_recall': np.mean(results['recalls']) if results['recalls'] else 0,
            'mean_f1': np.mean(results['f1_scores']) if results['f1_scores'] else 0,
            'mean_reciprocal_rank': np.mean(results['reciprocal_ranks']) if results['reciprocal_ranks'] else 0,
            'avg_false_positives': np.mean(results['false_positives']) if results['false_positives'] else 0,
            'avg_false_negatives': np.mean(results['false_negatives']) if results['false_negatives'] else 0,
            'total_errors': len(results['errors']),
            'difficulty_breakdown': {},
            'category_breakdown': {}
        }
        
        # Per-difficulty accuracy
        for diff, stats in results['per_difficulty'].items():
            metrics['difficulty_breakdown'][diff] = {
                'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0,
                'total': stats['total']
            }
        
        # Per-category accuracy
        for cat, stats in results['per_category'].items():
            metrics['category_breakdown'][cat] = {
                'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0,
                'total': stats['total']
            }
        
        return metrics
    
    def print_evaluation_results(self, metrics: Dict):
        """Print formatted evaluation results."""
        print("\n" + "=" * 70)
        print("RETRIEVAL SYSTEM EVALUATION RESULTS")
        print("=" * 70)
        
        print(f"\n{'Overall Metrics:':<30}")
        print(f"  {'Exact Match Accuracy':<25} {metrics['exact_match_accuracy']:>6.2%}")
        print(f"  {'Mean Precision':<25} {metrics['mean_precision']:>6.2%}")
        print(f"  {'Mean Recall':<25} {metrics['mean_recall']:>6.2%}")
        print(f"  {'Mean F1 Score':<25} {metrics['mean_f1']:>6.2%}")
        print(f"  {'Mean Reciprocal Rank':<25} {metrics['mean_reciprocal_rank']:>6.3f}")
        print(f"  {'Avg False Positives':<25} {metrics['avg_false_positives']:>6.2f}")
        print(f"  {'Avg False Negatives':<25} {metrics['avg_false_negatives']:>6.2f}")
        print(f"  {'Total Errors':<25} {metrics['total_errors']:>6}")
        
        print(f"\n{'Accuracy by Difficulty:':<30}")
        for diff in ['basic', 'intermediate', 'advanced']:
            if diff in metrics['difficulty_breakdown']:
                acc = metrics['difficulty_breakdown'][diff]['accuracy']
                total = metrics['difficulty_breakdown'][diff]['total']
                print(f"  {diff.capitalize():<20} {acc:>6.2%}  ({total} queries)")
        
        print(f"\n{'Top 10 Categories by Accuracy:':<30}")
        sorted_cats = sorted(
            metrics['category_breakdown'].items(),
            key=lambda x: (x[1]['accuracy'], x[1]['total']),
            reverse=True
        )[:10]
        for cat, stats in sorted_cats:
            print(f"  {cat:<30} {stats['accuracy']:>6.2%}  ({stats['total']} queries)")
        
        print("\n" + "=" * 70)
    
    def visualize_results(self, metrics: Dict, output_path: str = None):
        """Create visualization of evaluation results."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Retrieval System Performance Analysis', fontsize=16, fontweight='bold')
        
        # 1. Overall metrics bar chart
        ax = axes[0, 0]
        metric_names = ['Exact Match\nAccuracy', 'Mean\nPrecision', 'Mean\nRecall', 'Mean\nF1 Score']
        metric_values = [
            metrics['exact_match_accuracy'],
            metrics['mean_precision'],
            metrics['mean_recall'],
            metrics['mean_f1']
        ]
        bars = ax.bar(metric_names, metric_values, color=['#2ecc71', '#3498db', '#e74c3c', '#f39c12'])
        ax.set_ylabel('Score')
        ax.set_title('Overall Performance Metrics')
        ax.set_ylim(0, 1)
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2%}', ha='center', va='bottom', fontweight='bold')
        
        # 2. Difficulty breakdown
        ax = axes[0, 1]
        difficulties = ['basic', 'intermediate', 'advanced']
        accuracies = [metrics['difficulty_breakdown'].get(d, {}).get('accuracy', 0) 
                     for d in difficulties]
        bars = ax.bar(difficulties, accuracies, color=['#27ae60', '#f39c12', '#c0392b'])
        ax.set_ylabel('Accuracy')
        ax.set_title('Accuracy by Difficulty Level')
        ax.set_ylim(0, 1)
        ax.grid(axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2%}', ha='center', va='bottom', fontweight='bold')
        
        # 3. Top categories
        ax = axes[1, 0]
        sorted_cats = sorted(
            metrics['category_breakdown'].items(),
            key=lambda x: x[1]['accuracy'],
            reverse=True
        )[:8]
        cat_names = [c[0] for c in sorted_cats]
        cat_accs = [c[1]['accuracy'] for c in sorted_cats]
        bars = ax.barh(cat_names, cat_accs, color='#3498db')
        ax.set_xlabel('Accuracy')
        ax.set_title('Top 8 Categories by Accuracy')
        ax.set_xlim(0, 1)
        ax.grid(axis='x', alpha=0.3)
        
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                   f' {width:.2%}', ha='left', va='center', fontsize=9)
        
        # 4. Error analysis
        ax = axes[1, 1]
        error_metrics = ['Avg False\nPositives', 'Avg False\nNegatives', 'Total\nErrors']
        error_values = [
            metrics['avg_false_positives'],
            metrics['avg_false_negatives'],
            metrics['total_errors']
        ]
        bars = ax.bar(error_metrics, error_values, color=['#e67e22', '#e74c3c', '#95a5a6'])
        ax.set_ylabel('Count')
        ax.set_title('Error Analysis')
        ax.grid(axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to {output_path}")
        else:
            plt.show()


# Example usage functions
def example_simple_retrieval_function(query: str) -> List[str]:
    """
    Example retrieval function using simple keyword matching.
    Replace this with your actual retrieval implementation.
    """
    query_lower = query.lower()
    
    # Simple keyword-based routing
    files = []
    
    if any(word in query_lower for word in ['turbulence', 'ras', 'laminar', 'komega', 'kepsilon', 'spalart']):
        files.append('constant/turbulenceProperties')
    
    if any(word in query_lower for word in ['endtime', 'maxco', 'deltat', 'time step', 'duration', 'courant']):
        files.append('system/controlDict')
    
    if any(word in query_lower for word in ['mesh', 'cells', 'blockmesh', 'resolution']):
        files.append('system/blockMeshDict')
    
    if any(word in query_lower for word in ['refinement', 'amr', 'adaptive']):
        files.append('constant/dynamicMeshDict')
    
    if any(word in query_lower for word in ['density', 'eos', 'equation of state', 'material', 'phase']):
        files.append('constant/phaseProperties')
    
    if any(word in query_lower for word in ['combustion', 'flame', 'reaction', 'arrhenius', 'equivalence']):
        files.append('constant/combustionProperties')
    
    if any(word in query_lower for word in ['initial', 'charge', 'explosive', 'setfields']):
        files.append('system/setFieldsDict')
    
    if any(word in query_lower for word in ['scheme', 'discretization', 'muscl', 'limiter', 'vanleer']):
        files.append('system/fvSchemes')
    
    if any(word in query_lower for word in ['velocity', 'boundary']):
        files.append('0/U')
    
    if any(word in query_lower for word in ['write', 'output', 'format', 'interval']):
        files.append('system/controlDict')
    
    return list(set(files))  # Remove duplicates


def main():
    """Main function demonstrating usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze and evaluate retrieval validation dataset')
    parser.add_argument('--dataset', '-d', 
                       default='dataset/retrieval/blastfoam_retrieval_validation_dataset.json',
                       help='Path to dataset JSON file')
    parser.add_argument('--analyze', '-a', action='store_true',
                       help='Print dataset statistics')
    parser.add_argument('--evaluate', '-e', action='store_true',
                       help='Evaluate example retrieval function')
    parser.add_argument('--visualize', '-v', action='store_true',
                       help='Create visualization of results')
    parser.add_argument('--output', '-o', default=None,
                       help='Output path for visualization')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output during evaluation')
    
    args = parser.parse_args()
    
    if args.analyze:
        analyzer = RetrievalDatasetAnalyzer(args.dataset)
        analyzer.print_statistics()
    
    if args.evaluate:
        evaluator = RetrievalEvaluator(args.dataset)
        print("\nEvaluating example retrieval function...")
        metrics = evaluator.evaluate(example_simple_retrieval_function, verbose=args.verbose)
        evaluator.print_evaluation_results(metrics)
        
        if args.visualize:
            output = args.output or 'retrieval_evaluation_results.png'
            evaluator.visualize_results(metrics, output)


if __name__ == '__main__':
    main()
