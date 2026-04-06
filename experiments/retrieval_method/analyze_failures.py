"""
Failure Analysis Script

This script analyzes cases where retrieval methods failed to find the target files,
helping to identify patterns in failures and opportunities for improvement.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class FailureAnalyzer:
    """Analyze retrieval failures to identify improvement opportunities."""
    
    def __init__(self, results_file: str):
        """
        Initialize the failure analyzer.
        
        Args:
            results_file: Path to the evaluation results JSON file
        """
        self.results_file = Path(results_file)
        
        with open(self.results_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        self.results = self.data.get('detailed_results', [])
        self.metadata = self.data.get('metadata', {})
        
        print(f"Loaded results from: {self.results_file.name}")
        print(f"Total queries: {len(self.results)}")
    
    def identify_failures(self, metric: str = 'hit@5', threshold: float = 0.0) -> List[Dict]:
        """
        Identify queries that failed based on a metric.
        
        Args:
            metric: Metric to use for failure detection (e.g., 'hit@5', 'mrr')
            threshold: Threshold below which a query is considered failed
            
        Returns:
            List of failed query results
        """
        failures = []
        
        for result in self.results:
            if metric in result and result[metric] <= threshold:
                failures.append(result)
        
        return failures
    
    def analyze_failure_patterns(self, failures: List[Dict]):
        """
        Analyze patterns in failures.
        
        Args:
            failures: List of failed query results
        """
        print(f"\n{'='*80}")
        print(f"FAILURE ANALYSIS - {len(failures)} failures")
        print(f"{'='*80}\n")
        
        # By difficulty
        by_difficulty = defaultdict(int)
        for f in failures:
            by_difficulty[f.get('difficulty', 'unknown')] += 1
        
        print("Failures by Difficulty:")
        for difficulty, count in sorted(by_difficulty.items()):
            percentage = (count / len(failures)) * 100 if failures else 0
            print(f"  {difficulty.capitalize()}: {count} ({percentage:.1f}%)")
        
        # By category
        by_category = defaultdict(int)
        for f in failures:
            by_category[f.get('category', 'unknown')] += 1
        
        print("\nFailures by Category (Top 10):")
        sorted_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:10]
        for category, count in sorted_categories:
            percentage = (count / len(failures)) * 100 if failures else 0
            print(f"  {category}: {count} ({percentage:.1f}%)")
        
        # Target file patterns
        target_files = defaultdict(int)
        for f in failures:
            for target in f.get('target_files', []):
                target_files[target] += 1
        
        print("\nMost Common Target Files in Failures (Top 10):")
        sorted_targets = sorted(target_files.items(), key=lambda x: x[1], reverse=True)[:10]
        for target, count in sorted_targets:
            print(f"  {target}: {count} failures")
    
    def show_failure_examples(self, failures: List[Dict], n: int = 10):
        """
        Show detailed examples of failures.
        
        Args:
            failures: List of failed query results
            n: Number of examples to show
        """
        print(f"\n{'='*80}")
        print(f"DETAILED FAILURE EXAMPLES (showing {min(n, len(failures))} of {len(failures)})")
        print(f"{'='*80}\n")
        
        for i, failure in enumerate(failures[:n], 1):
            print(f"\n--- Failure {i} ---")
            print(f"Query ID: {failure.get('query_id')}")
            print(f"Query: {failure.get('query')}")
            print(f"Difficulty: {failure.get('difficulty')}")
            print(f"Category: {failure.get('category')}")
            print(f"\nTarget Files:")
            for target in failure.get('target_files', []):
                print(f"  - {target}")
            print(f"\nRetrieved Files:")
            retrieved = failure.get('retrieved_files', [])
            if retrieved:
                for j, ret_file in enumerate(retrieved[:5], 1):
                    print(f"  {j}. {ret_file}")
            else:
                print("  (No files retrieved)")
            print(f"\nMetrics:")
            print(f"  MRR: {failure.get('mrr', 0):.4f}")
            print(f"  Hit@3: {failure.get('hit@3', False)}")
            print(f"  Hit@5: {failure.get('hit@5', False)}")
            print("-" * 80)
    
    def compare_with_other_method(self, other_results_file: str):
        """
        Compare failures with another retrieval method.
        
        Args:
            other_results_file: Path to results from another method
        """
        with open(other_results_file, 'r', encoding='utf-8') as f:
            other_data = json.load(f)
        
        other_results = {r['query_id']: r for r in other_data.get('detailed_results', [])}
        
        print(f"\n{'='*80}")
        print(f"COMPARISON WITH OTHER METHOD")
        print(f"{'='*80}\n")
        
        this_method = self.metadata.get('retriever_type', 'Method 1')
        other_method = other_data['metadata'].get('retriever_type', 'Method 2')
        
        print(f"This method: {this_method}")
        print(f"Other method: {other_method}\n")
        
        # Find queries that failed in this method but succeeded in other
        this_failed_other_succeeded = []
        both_failed = []
        
        for result in self.results:
            query_id = result['query_id']
            this_hit5 = result.get('hit@5', False)
            
            if query_id in other_results:
                other_hit5 = other_results[query_id].get('hit@5', False)
                
                if not this_hit5 and other_hit5:
                    this_failed_other_succeeded.append({
                        'query_id': query_id,
                        'query': result['query'],
                        'category': result.get('category'),
                        'difficulty': result.get('difficulty')
                    })
                elif not this_hit5 and not other_hit5:
                    both_failed.append({
                        'query_id': query_id,
                        'query': result['query'],
                        'category': result.get('category'),
                        'difficulty': result.get('difficulty')
                    })
        
        print(f"Queries failed in {this_method} but succeeded in {other_method}: {len(this_failed_other_succeeded)}")
        print(f"Queries failed in both methods: {len(both_failed)}\n")
        
        if this_failed_other_succeeded:
            print(f"\nExamples where {other_method} succeeded but {this_method} failed:")
            for i, item in enumerate(this_failed_other_succeeded[:5], 1):
                print(f"  {i}. [{item['difficulty']}] {item['query'][:70]}...")
        
        if both_failed:
            print(f"\nExamples where both methods failed (hardest queries):")
            for i, item in enumerate(both_failed[:5], 1):
                print(f"  {i}. [{item['difficulty']}] {item['query'][:70]}...")
    
    def generate_improvement_suggestions(self, failures: List[Dict]):
        """
        Generate suggestions for improving retrieval based on failure patterns.
        
        Args:
            failures: List of failed query results
        """
        print(f"\n{'='*80}")
        print(f"IMPROVEMENT SUGGESTIONS")
        print(f"{'='*80}\n")
        
        # Analyze patterns
        by_category = defaultdict(int)
        by_difficulty = defaultdict(int)
        
        for f in failures:
            by_category[f.get('category', 'unknown')] += 1
            by_difficulty[f.get('difficulty', 'unknown')] += 1
        
        # Suggestions based on categories with most failures
        problematic_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)[:3]
        
        print("1. Category-Specific Improvements:")
        for category, count in problematic_categories:
            print(f"\n   Category: {category} ({count} failures)")
            
            if category in ['file_location', 'goal_based']:
                print("   → Consider adding more contextual information to embeddings")
                print("   → Improve query expansion to include file path keywords")
            elif category in ['numerical_schemes', 'solver_control']:
                print("   → Add specialized dictionaries for technical terms")
                print("   → Include more examples of numerical parameter names")
            elif category in ['multiphase', 'physics_models']:
                print("   → Enhance knowledge graph with model relationships")
                print("   → Add cross-references between related physics models")
        
        # Suggestions based on difficulty
        print("\n2. Difficulty-Based Improvements:")
        
        if by_difficulty.get('advanced', 0) > by_difficulty.get('basic', 0):
            print("\n   Advanced queries struggling:")
            print("   → Implement multi-hop reasoning for complex queries")
            print("   → Add query decomposition for complex requirements")
            print("   → Enhance context understanding with domain knowledge")
        
        if by_difficulty.get('basic', 0) > 0:
            print("\n   Basic queries struggling:")
            print("   → Review and improve basic file path mappings")
            print("   → Add more direct keyword matches")
            print("   → Consider boosting exact matches in ranking")
        
        # General suggestions
        print("\n3. General Improvements:")
        print("   → Consider hybrid approach combining embedding + knowledge graph")
        print("   → Implement query reformulation/expansion")
        print("   → Add post-processing to re-rank results based on file types")
        print("   → Consider user feedback loop to improve over time")


def main():
    """Main function to run failure analysis."""
    
    results_dir = Path(__file__).parent / 'results'
    
    if not results_dir.exists():
        print(f"Results directory not found: {results_dir}")
        print("Please run evaluation scripts first.")
        return
    
    # List available result files
    result_files = list(results_dir.glob('*.json'))
    
    if not result_files:
        print("No evaluation results found.")
        print("Please run evaluation scripts first.")
        return
    
    print("\nAvailable result files:")
    for i, f in enumerate(result_files, 1):
        print(f"  {i}. {f.name}")
    
    # Select file to analyze
    while True:
        try:
            choice = input(f"\nSelect file to analyze (1-{len(result_files)}): ").strip()
            file_idx = int(choice) - 1
            if 0 <= file_idx < len(result_files):
                selected_file = result_files[file_idx]
                break
            else:
                print("Invalid selection. Try again.")
        except (ValueError, KeyboardInterrupt):
            print("\nExiting.")
            return
    
    # Initialize analyzer
    analyzer = FailureAnalyzer(str(selected_file))
    
    # Identify failures
    print("\nAnalyzing failures (queries with Hit@5 = 0)...")
    failures = analyzer.identify_failures(metric='hit@5', threshold=0.0)
    
    if not failures:
        print("\nNo failures found! All queries succeeded at Hit@5.")
        return
    
    # Analyze patterns
    analyzer.analyze_failure_patterns(failures)
    
    # Show examples
    analyzer.show_failure_examples(failures, n=5)
    
    # Generate suggestions
    analyzer.generate_improvement_suggestions(failures)
    
    # Optional: Compare with another method
    print("\n" + "="*80)
    response = input("\nCompare with another method's results? (yes/no): ").strip().lower()
    if response in ['yes', 'y']:
        print("\nAvailable result files:")
        for i, f in enumerate(result_files, 1):
            if f != selected_file:
                print(f"  {i}. {f.name}")
        
        try:
            choice = input(f"\nSelect file to compare with (1-{len(result_files)}): ").strip()
            file_idx = int(choice) - 1
            if 0 <= file_idx < len(result_files):
                other_file = result_files[file_idx]
                analyzer.compare_with_other_method(str(other_file))
        except (ValueError, KeyboardInterrupt):
            print("\nSkipping comparison.")


if __name__ == '__main__':
    main()
