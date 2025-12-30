#!/usr/bin/env python3
"""
Simple Retrieval Validation Dataset Analyzer

This script provides basic utilities for working with the BlastFOAM retrieval 
validation dataset without external dependencies.
"""

import json
from collections import Counter, defaultdict
from typing import Dict, List, Set, Callable


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
        }
        
        # Calculate averages
        files_per_query = [len(e['target_files']) for e in self.dataset]
        stats['avg_files_per_query'] = sum(files_per_query) / len(files_per_query)
        stats['max_files_per_query'] = max(files_per_query)
        
        # Query type analysis
        query_lengths = [len(e['query'].split()) for e in self.dataset]
        stats['avg_query_length'] = sum(query_lengths) / len(query_lengths)
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
        
        print(f"\n{'Top 15 Most Targeted Files:':<30}")
        for file, count in stats['target_files_distribution'].most_common(15):
            print(f"  {file:<40} {count:>3}")
        
        print(f"\n{'Category Distribution:':<30}")
        for cat, count in sorted(stats['category_distribution'].items(), 
                                 key=lambda x: x[1], reverse=True):
            pct = 100 * count / stats['total_entries']
            print(f"  {cat:<35} {count:>3} ({pct:>5.1f}%)")
        
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
                
                # Reciprocal rank
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
                    print(f"  P={precision:.2f} R={recall:.2f} F1={f1:.2f} {'✓' if exact_match else '✗'}")
                    
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
        
        def safe_mean(lst):
            return sum(lst) / len(lst) if lst else 0
        
        metrics = {
            'exact_match_accuracy': results['exact_matches'] / n_total if n_total > 0 else 0,
            'mean_precision': safe_mean(results['precisions']),
            'mean_recall': safe_mean(results['recalls']),
            'mean_f1': safe_mean(results['f1_scores']),
            'mean_reciprocal_rank': safe_mean(results['reciprocal_ranks']),
            'avg_false_positives': safe_mean(results['false_positives']),
            'avg_false_negatives': safe_mean(results['false_negatives']),
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
        print(f"  {'Exact Match Accuracy':<25} {metrics['exact_match_accuracy']*100:>6.2f}%")
        print(f"  {'Mean Precision':<25} {metrics['mean_precision']*100:>6.2f}%")
        print(f"  {'Mean Recall':<25} {metrics['mean_recall']*100:>6.2f}%")
        print(f"  {'Mean F1 Score':<25} {metrics['mean_f1']*100:>6.2f}%")
        print(f"  {'Mean Reciprocal Rank':<25} {metrics['mean_reciprocal_rank']:>6.3f}")
        print(f"  {'Avg False Positives':<25} {metrics['avg_false_positives']:>6.2f}")
        print(f"  {'Avg False Negatives':<25} {metrics['avg_false_negatives']:>6.2f}")
        print(f"  {'Total Errors':<25} {metrics['total_errors']:>6}")
        
        print(f"\n{'Accuracy by Difficulty:':<30}")
        for diff in ['basic', 'intermediate', 'advanced']:
            if diff in metrics['difficulty_breakdown']:
                acc = metrics['difficulty_breakdown'][diff]['accuracy']
                total = metrics['difficulty_breakdown'][diff]['total']
                print(f"  {diff.capitalize():<20} {acc*100:>6.2f}%  ({total} queries)")
        
        print(f"\n{'Top 10 Categories by Accuracy:':<30}")
        sorted_cats = sorted(
            metrics['category_breakdown'].items(),
            key=lambda x: (x[1]['accuracy'], x[1]['total']),
            reverse=True
        )[:10]
        for cat, stats in sorted_cats:
            print(f"  {cat:<35} {stats['accuracy']*100:>5.1f}%  (n={stats['total']})")
        
        print("\n" + "=" * 70)


def example_simple_retrieval_function(query: str) -> List[str]:
    """
    Example retrieval function using simple keyword matching.
    Replace this with your actual retrieval implementation.
    """
    query_lower = query.lower()
    files = []
    
    # Simple keyword-based routing
    if any(word in query_lower for word in ['turbulence', 'ras', 'laminar', 'komega', 'kepsilon', 'spalart']):
        files.append('constant/turbulenceProperties')
    
    if any(word in query_lower for word in ['endtime', 'maxco', 'deltat', 'time step', 'duration', 'courant', 'time', 'longer', 'stable']):
        files.append('system/controlDict')
    
    if any(word in query_lower for word in ['mesh', 'cells', 'blockmesh', 'resolution', 'finer', 'x-direction', 'y-direction', 'z-direction']):
        files.append('system/blockMeshDict')
    
    if any(word in query_lower for word in ['refinement', 'amr', 'adaptive', 'maxrefinement', 'dynamic']):
        files.append('constant/dynamicMeshDict')
    
    if any(word in query_lower for word in ['density', 'eos', 'equation of state', 'material', 'phase', 'explosive', 'rho0', 'jwl', 'bkw', 'window', 'particle']):
        files.append('constant/phaseProperties')
    
    if any(word in query_lower for word in ['combustion', 'flame', 'reaction', 'arrhenius', 'equivalence', 'su', 'flame speed', 'deflagration', 'detonation']):
        files.append('constant/combustionProperties')
    
    if any(word in query_lower for word in ['initial', 'charge', 'location', 'setfield', 'explosive charge', 'sphere', 'box']):
        files.append('system/setFieldsDict')
    
    if any(word in query_lower for word in ['scheme', 'discretization', 'muscl', 'limiter', 'vanleer', 'vanalbada', 'numerical', 'flux']):
        files.append('system/fvSchemes')
    
    if any(word in query_lower for word in ['velocity', 'moving', 'cone', 'm/s']):
        files.append('0/U')
    
    if any(word in query_lower for word in ['write', 'output', 'format', 'interval', 'binary', 'ascii']):
        if 'system/controlDict' not in files:
            files.append('system/controlDict')
    
    if 'particle' in query_lower and 'turbulence' in query_lower:
        files.append('constant/turbulenceProperties.particles')
    
    return list(set(files))


def main():
    """Main function demonstrating usage."""
    import sys
    
    dataset_path = 'dataset/retrieval/blastfoam_retrieval_validation_dataset.json'
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--analyze' or command == '-a':
            analyzer = RetrievalDatasetAnalyzer(dataset_path)
            analyzer.print_statistics()
        
        elif command == '--evaluate' or command == '-e':
            evaluator = RetrievalEvaluator(dataset_path)
            print("\nEvaluating example retrieval function...")
            verbose = '--verbose' in sys.argv or '-v' in sys.argv
            metrics = evaluator.evaluate(example_simple_retrieval_function, verbose=verbose)
            evaluator.print_evaluation_results(metrics)
        
        elif command == '--help' or command == '-h':
            print("Usage: python analyze_retrieval_dataset.py [OPTION]")
            print("\nOptions:")
            print("  -a, --analyze    Print dataset statistics")
            print("  -e, --evaluate   Evaluate example retrieval function")
            print("  -v, --verbose    Verbose output during evaluation")
            print("  -h, --help       Show this help message")
        
        else:
            print(f"Unknown option: {command}")
            print("Use --help for usage information")
    else:
        print("BlastFOAM Retrieval Validation Dataset Tool")
        print("\nUsage: python analyze_retrieval_dataset.py [OPTION]")
        print("Use --help for more information")


if __name__ == '__main__':
    main()
