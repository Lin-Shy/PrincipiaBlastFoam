"""
Comparison Script for Retrieval Methods

This script compares the performance of different retrieval methods:
1. Embedding-based retrieval (case-level and file-level)
2. Knowledge graph-based retrieval

It loads evaluation results and generates comparative visualizations and statistics.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class RetrieverComparator:
    """Compare performance of different retrieval methods."""
    
    def __init__(self, results_dir: str = None):
        """
        Initialize the comparator.
        
        Args:
            results_dir: Directory containing evaluation result JSON files
        """
        if results_dir is None:
            results_dir = Path(__file__).parent / 'results'
        
        self.results_dir = Path(results_dir)
        self.results = {}
        
    def load_latest_results(self):
        """Load the most recent evaluation results for each retriever type."""
        if not self.results_dir.exists():
            print(f"Results directory not found: {self.results_dir}")
            return
        
        # Find all result files
        result_files = {
            'embedding_case': [],
            'embedding_file': [],
            'knowledge_graph': []
        }
        
        for file in self.results_dir.glob('*.json'):
            if 'embedding_retrieval_case' in file.name:
                result_files['embedding_case'].append(file)
            elif 'embedding_retrieval_file' in file.name:
                result_files['embedding_file'].append(file)
            elif 'knowledge_graph_retrieval' in file.name:
                result_files['knowledge_graph'].append(file)
        
        # Load the most recent file for each type
        for retriever_type, files in result_files.items():
            if files:
                # Sort by modification time, get the most recent
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                print(f"Loading {retriever_type}: {latest_file.name}")
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    self.results[retriever_type] = json.load(f)
            else:
                print(f"No results found for {retriever_type}")
    
    def load_specific_results(self, embedding_case_file: str = None, 
                            embedding_file_file: str = None,
                            kg_file: str = None):
        """
        Load specific result files.
        
        Args:
            embedding_case_file: Path to case-level embedding results
            embedding_file_file: Path to file-level embedding results
            kg_file: Path to knowledge graph results
        """
        if embedding_case_file:
            with open(embedding_case_file, 'r', encoding='utf-8') as f:
                self.results['embedding_case'] = json.load(f)
        
        if embedding_file_file:
            with open(embedding_file_file, 'r', encoding='utf-8') as f:
                self.results['embedding_file'] = json.load(f)
        
        if kg_file:
            with open(kg_file, 'r', encoding='utf-8') as f:
                self.results['knowledge_graph'] = json.load(f)
    
    def compare_overall_metrics(self):
        """Compare overall performance metrics across all retrievers."""
        if not self.results:
            print("No results loaded. Please load results first.")
            return
        
        print("\n" + "="*100)
        print("OVERALL PERFORMANCE COMPARISON")
        print("="*100 + "\n")
        
        # Table header
        header = f"{'Metric':<25} | "
        for retriever_type in self.results.keys():
            display_name = self._get_display_name(retriever_type)
            header += f"{display_name:>25} | "
        print(header)
        print("-" * len(header))
        
        # Metrics to compare
        metrics = ['mrr', 'hit@1', 'hit@3', 'hit@5', 'hit@10', 
                   'precision@3', 'precision@5', 'recall@3', 'recall@5']
        
        for metric in metrics:
            row = f"{metric:<25} | "
            for retriever_type in self.results.keys():
                aggregate = self.results[retriever_type].get('aggregate_metrics', {})
                value = aggregate.get(metric, 0.0)
                row += f"{value:>25.4f} | "
            print(row)
        
        # Retrieval time
        row = f"{'Avg Retrieval Time (s)':<25} | "
        for retriever_type in self.results.keys():
            aggregate = self.results[retriever_type].get('aggregate_metrics', {})
            value = aggregate.get('avg_retrieval_time', 0.0)
            row += f"{value:>25.4f} | "
        print(row)
        
        print("\n" + "="*100 + "\n")
    
    def compare_by_difficulty(self):
        """Compare performance by query difficulty."""
        if not self.results:
            print("No results loaded.")
            return
        
        print("\n" + "="*100)
        print("PERFORMANCE BY DIFFICULTY")
        print("="*100 + "\n")
        
        difficulties = ['basic', 'intermediate', 'advanced']
        
        for difficulty in difficulties:
            print(f"\n{difficulty.upper()}")
            print("-" * 50)
            
            # Table header
            header = f"{'Metric':<25} | "
            for retriever_type in self.results.keys():
                display_name = self._get_display_name(retriever_type)
                header += f"{display_name:>25} | "
            print(header)
            print("-" * len(header))
            
            # Metrics
            metrics = ['mrr', 'hit@3', 'hit@5']
            
            for metric in metrics:
                row = f"{metric:<25} | "
                for retriever_type in self.results.keys():
                    by_difficulty = self.results[retriever_type].get('aggregate_metrics', {}).get('by_difficulty', {})
                    value = by_difficulty.get(difficulty, {}).get(metric, 0.0)
                    row += f"{value:>25.4f} | "
                print(row)
    
    def compare_by_category(self, top_n: int = 10):
        """
        Compare performance by query category.
        
        Args:
            top_n: Number of top categories to display
        """
        if not self.results:
            print("No results loaded.")
            return
        
        print("\n" + "="*100)
        print(f"PERFORMANCE BY CATEGORY (Top {top_n})")
        print("="*100 + "\n")
        
        # Get all unique categories
        all_categories = set()
        for retriever_type in self.results.keys():
            by_category = self.results[retriever_type].get('aggregate_metrics', {}).get('by_category', {})
            all_categories.update(by_category.keys())
        
        # Sort categories by average hit@5 across all retrievers
        category_scores = {}
        for category in all_categories:
            scores = []
            for retriever_type in self.results.keys():
                by_category = self.results[retriever_type].get('aggregate_metrics', {}).get('by_category', {})
                score = by_category.get(category, {}).get('hit@5', 0.0)
                scores.append(score)
            category_scores[category] = np.mean(scores)
        
        # Get top N categories
        top_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        
        for category, _ in top_categories:
            print(f"\n{category.upper()}")
            print("-" * 50)
            
            # Table header
            header = f"{'Metric':<25} | "
            for retriever_type in self.results.keys():
                display_name = self._get_display_name(retriever_type)
                header += f"{display_name:>25} | "
            print(header)
            print("-" * len(header))
            
            # Metrics
            metrics = ['count', 'mrr', 'hit@3', 'hit@5']
            
            for metric in metrics:
                row = f"{metric:<25} | "
                for retriever_type in self.results.keys():
                    by_category = self.results[retriever_type].get('aggregate_metrics', {}).get('by_category', {})
                    value = by_category.get(category, {}).get(metric, 0.0)
                    
                    if metric == 'count':
                        row += f"{int(value):>25} | "
                    else:
                        row += f"{value:>25.4f} | "
                print(row)
    
    def plot_comparison(self, save_path: str = None):
        """
        Generate comparison plots.
        
        Args:
            save_path: Path to save the plot (if None, displays the plot)
        """
        if not self.results:
            print("No results loaded.")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Retrieval Methods Performance Comparison', fontsize=16, fontweight='bold')
        
        # Plot 1: Hit@K comparison
        ax1 = axes[0, 0]
        self._plot_hit_at_k(ax1)
        
        # Plot 2: MRR by difficulty
        ax2 = axes[0, 1]
        self._plot_mrr_by_difficulty(ax2)
        
        # Plot 3: Precision and Recall at K=5
        ax3 = axes[1, 0]
        self._plot_precision_recall(ax3)
        
        # Plot 4: Category performance heatmap
        ax4 = axes[1, 1]
        self._plot_category_heatmap(ax4)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")
        else:
            plt.show()
    
    def _plot_hit_at_k(self, ax):
        """Plot Hit@K comparison."""
        k_values = [1, 3, 5, 10]
        x = np.arange(len(k_values))
        width = 0.25
        
        for idx, (retriever_type, data) in enumerate(self.results.items()):
            aggregate = data.get('aggregate_metrics', {})
            hits = [aggregate.get(f'hit@{k}', 0) for k in k_values]
            
            offset = (idx - 1) * width
            ax.bar(x + offset, hits, width, label=self._get_display_name(retriever_type))
        
        ax.set_xlabel('K Value', fontweight='bold')
        ax.set_ylabel('Hit@K', fontweight='bold')
        ax.set_title('Hit@K Performance', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([f'K={k}' for k in k_values])
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
    
    def _plot_mrr_by_difficulty(self, ax):
        """Plot MRR by difficulty level."""
        difficulties = ['basic', 'intermediate', 'advanced']
        x = np.arange(len(difficulties))
        width = 0.25
        
        for idx, (retriever_type, data) in enumerate(self.results.items()):
            by_difficulty = data.get('aggregate_metrics', {}).get('by_difficulty', {})
            mrr_values = [by_difficulty.get(d, {}).get('mrr', 0) for d in difficulties]
            
            offset = (idx - 1) * width
            ax.bar(x + offset, mrr_values, width, label=self._get_display_name(retriever_type))
        
        ax.set_xlabel('Difficulty Level', fontweight='bold')
        ax.set_ylabel('MRR', fontweight='bold')
        ax.set_title('MRR by Difficulty Level', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([d.capitalize() for d in difficulties])
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
    
    def _plot_precision_recall(self, ax):
        """Plot precision and recall at K=5."""
        retrievers = list(self.results.keys())
        x = np.arange(len(retrievers))
        width = 0.35
        
        precision_values = []
        recall_values = []
        
        for retriever_type in retrievers:
            aggregate = self.results[retriever_type].get('aggregate_metrics', {})
            precision_values.append(aggregate.get('precision@5', 0))
            recall_values.append(aggregate.get('recall@5', 0))
        
        ax.bar(x - width/2, precision_values, width, label='Precision@5', color='skyblue')
        ax.bar(x + width/2, recall_values, width, label='Recall@5', color='lightcoral')
        
        ax.set_xlabel('Retriever Type', fontweight='bold')
        ax.set_ylabel('Score', fontweight='bold')
        ax.set_title('Precision and Recall at K=5', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels([self._get_display_name(r) for r in retrievers], rotation=15, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
    
    def _plot_category_heatmap(self, ax):
        """Plot category performance heatmap."""
        # Get top 10 categories by average performance
        all_categories = set()
        for retriever_type in self.results.keys():
            by_category = self.results[retriever_type].get('aggregate_metrics', {}).get('by_category', {})
            all_categories.update(by_category.keys())
        
        category_scores = {}
        for category in all_categories:
            scores = []
            for retriever_type in self.results.keys():
                by_category = self.results[retriever_type].get('aggregate_metrics', {}).get('by_category', {})
                score = by_category.get(category, {}).get('hit@5', 0.0)
                scores.append(score)
            category_scores[category] = np.mean(scores)
        
        top_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        categories = [c[0] for c in top_categories]
        
        # Build heatmap data
        data = []
        for retriever_type in self.results.keys():
            by_category = self.results[retriever_type].get('aggregate_metrics', {}).get('by_category', {})
            row = [by_category.get(cat, {}).get('hit@5', 0) for cat in categories]
            data.append(row)
        
        im = ax.imshow(data, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)
        
        # Set ticks
        ax.set_xticks(np.arange(len(categories)))
        ax.set_yticks(np.arange(len(self.results)))
        ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
        ax.set_yticklabels([self._get_display_name(r) for r in self.results.keys()])
        
        # Add colorbar
        plt.colorbar(im, ax=ax, label='Hit@5')
        
        ax.set_title('Hit@5 by Category (Top 10)', fontweight='bold')
        
        # Add values to cells
        for i in range(len(self.results)):
            for j in range(len(categories)):
                text = ax.text(j, i, f'{data[i][j]:.2f}',
                             ha="center", va="center", color="black", fontsize=7)
    
    def _get_display_name(self, retriever_type: str) -> str:
        """Get display name for retriever type."""
        names = {
            'embedding_case': 'Embedding (Case)',
            'embedding_file': 'Embedding (File)',
            'knowledge_graph': 'Knowledge Graph'
        }
        return names.get(retriever_type, retriever_type)
    
    def generate_report(self, output_file: str = None):
        """
        Generate a comprehensive comparison report.
        
        Args:
            output_file: Path to save the report (markdown format)
        """
        if not self.results:
            print("No results loaded.")
            return
        
        report_lines = []
        
        # Header
        report_lines.append("# Retrieval Methods Performance Comparison Report")
        report_lines.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Overall metrics
        report_lines.append("\n## Overall Performance\n")
        report_lines.append("| Metric | " + " | ".join([self._get_display_name(r) for r in self.results.keys()]) + " |")
        report_lines.append("|" + "---|" * (len(self.results) + 1))
        
        metrics = ['mrr', 'hit@1', 'hit@3', 'hit@5', 'hit@10', 'precision@5', 'recall@5']
        for metric in metrics:
            row = f"| {metric} | "
            for retriever_type in self.results.keys():
                aggregate = self.results[retriever_type].get('aggregate_metrics', {})
                value = aggregate.get(metric, 0.0)
                row += f"{value:.4f} | "
            report_lines.append(row)
        
        # By difficulty
        report_lines.append("\n## Performance by Difficulty\n")
        
        for difficulty in ['basic', 'intermediate', 'advanced']:
            report_lines.append(f"\n### {difficulty.capitalize()}\n")
            report_lines.append("| Metric | " + " | ".join([self._get_display_name(r) for r in self.results.keys()]) + " |")
            report_lines.append("|" + "---|" * (len(self.results) + 1))
            
            for metric in ['mrr', 'hit@3', 'hit@5']:
                row = f"| {metric} | "
                for retriever_type in self.results.keys():
                    by_difficulty = self.results[retriever_type].get('aggregate_metrics', {}).get('by_difficulty', {})
                    value = by_difficulty.get(difficulty, {}).get(metric, 0.0)
                    row += f"{value:.4f} | "
                report_lines.append(row)
        
        # Summary insights
        report_lines.append("\n## Key Insights\n")
        
        # Best overall performer
        best_mrr = max(self.results.items(), key=lambda x: x[1].get('aggregate_metrics', {}).get('mrr', 0))
        report_lines.append(f"- **Best Overall (MRR):** {self._get_display_name(best_mrr[0])} ({best_mrr[1]['aggregate_metrics']['mrr']:.4f})")
        
        best_hit5 = max(self.results.items(), key=lambda x: x[1].get('aggregate_metrics', {}).get('hit@5', 0))
        report_lines.append(f"- **Best Hit@5:** {self._get_display_name(best_hit5[0])} ({best_hit5[1]['aggregate_metrics']['hit@5']:.4f})")
        
        # Fastest
        fastest = min(self.results.items(), key=lambda x: x[1].get('aggregate_metrics', {}).get('avg_retrieval_time', float('inf')))
        report_lines.append(f"- **Fastest:** {self._get_display_name(fastest[0])} ({fastest[1]['aggregate_metrics']['avg_retrieval_time']:.4f}s)")
        
        report_text = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"Report saved to: {output_file}")
        else:
            print(report_text)
        
        return report_text


def main():
    """Main function to run the comparison."""
    
    comparator = RetrieverComparator()
    
    # Load latest results
    print("Loading latest evaluation results...")
    comparator.load_latest_results()
    
    if not comparator.results:
        print("\nNo evaluation results found.")
        print("Please run the evaluation scripts first:")
        print("  - python experiments/evaluate_embedding_retriever.py")
        print("  - python experiments/evaluate_knowledge_graph_retriever.py")
        return
    
    # Print comparisons
    comparator.compare_overall_metrics()
    comparator.compare_by_difficulty()
    comparator.compare_by_category(top_n=5)
    
    # Generate visualizations
    print("\nGenerating comparison plots...")
    plot_path = Path(__file__).parent / 'results' / f'comparison_plot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    try:
        comparator.plot_comparison(save_path=str(plot_path))
    except Exception as e:
        print(f"Could not generate plots: {e}")
        print("Note: matplotlib may not be installed or display may not be available")
    
    # Generate report
    report_path = Path(__file__).parent / 'results' / f'comparison_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    comparator.generate_report(output_file=str(report_path))


if __name__ == '__main__':
    main()
