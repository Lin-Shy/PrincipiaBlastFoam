#!/usr/bin/env python3
"""
Analyzer and visualization tool for the strict retrieval dataset.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Dict, List

import numpy as np

try:
    from retrieval_analysis_common import (
        DEFAULT_DATASET_PATH,
        ResultNormalizer,
        dataset_mode,
        entry_target_case_paths,
        entry_target_file_paths,
        entry_target_identifiers,
        example_retrieval_function,
    )
except ModuleNotFoundError:
    from dataset.retrieval.retrieval_analysis_common import (
        DEFAULT_DATASET_PATH,
        ResultNormalizer,
        dataset_mode,
        entry_target_case_paths,
        entry_target_file_paths,
        entry_target_identifiers,
        example_retrieval_function,
    )


class RetrievalDatasetAnalyzer:
    """Analyzer for retrieval validation datasets."""

    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        with self.dataset_path.open("r", encoding="utf-8") as f:
            self.dataset = json.load(f)
        self.n_entries = len(self.dataset)
        self.mode = dataset_mode(self.dataset)

    def get_statistics(self) -> Dict:
        stats = {
            "dataset_mode": self.mode,
            "total_entries": self.n_entries,
            "difficulty_distribution": Counter(e["difficulty"] for e in self.dataset),
            "category_distribution": Counter(e["category"] for e in self.dataset),
            "target_identifier_distribution": Counter(
                identifier for entry in self.dataset for identifier in entry_target_identifiers(entry)
            ),
            "target_file_distribution": Counter(
                file_path for entry in self.dataset for file_path in entry_target_file_paths(entry)
            ),
            "multi_file_queries": sum(1 for e in self.dataset if len(e["target_files"]) > 1),
            "single_file_queries": sum(1 for e in self.dataset if len(e["target_files"]) == 1),
            "avg_files_per_query": np.mean([len(e["target_files"]) for e in self.dataset]),
            "max_files_per_query": max(len(e["target_files"]) for e in self.dataset),
        }

        if self.mode == "strict":
            stats["target_case_distribution"] = Counter(
                case_path for entry in self.dataset for case_path in entry_target_case_paths(entry)
            )

        query_lengths = [len(e["query"].split()) for e in self.dataset]
        stats["avg_query_length"] = np.mean(query_lengths)
        stats["min_query_length"] = min(query_lengths)
        stats["max_query_length"] = max(query_lengths)
        return stats

    def print_statistics(self):
        stats = self.get_statistics()

        print("=" * 70)
        print("RETRIEVAL VALIDATION DATASET STATISTICS")
        print("=" * 70)
        print(f"\nDataset: {self.dataset_path}")
        print(f"Mode: {stats['dataset_mode']}")
        print(f"Total Entries: {stats['total_entries']}")

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

        identifier_title = 'Top 10 Strict Targets:'
        print(f"\n{identifier_title:<30}")
        for identifier, count in stats['target_identifier_distribution'].most_common(10):
            print(f"  {identifier:<60} {count:>3}")

        print(f"\n{'Top 10 File Families:':<30}")
        for file_path, count in stats['target_file_distribution'].most_common(10):
            print(f"  {file_path:<40} {count:>3}")

        if self.mode == 'strict':
            print(f"\n{'Target Case Distribution:':<30}")
            for case_path, count in stats['target_case_distribution'].most_common(10):
                print(f"  {case_path:<50} {count:>3}")

        print(f"\n{'Top 10 Categories:':<30}")
        for cat, count in sorted(stats['category_distribution'].items(), key=lambda item: item[1], reverse=True)[:10]:
            pct = 100 * count / stats['total_entries']
            print(f"  {cat:<30} {count:>3} ({pct:>5.1f}%)")

        print("=" * 70)

    def get_by_category(self, category: str) -> List[Dict]:
        return [e for e in self.dataset if e['category'] == category]

    def get_by_difficulty(self, difficulty: str) -> List[Dict]:
        return [e for e in self.dataset if e['difficulty'] == difficulty]

    def get_by_file(self, filepath: str) -> List[Dict]:
        matched: List[Dict] = []
        for entry in self.dataset:
            identifiers = set(entry_target_identifiers(entry))
            file_paths = set(entry_target_file_paths(entry))
            if filepath in identifiers or filepath in file_paths:
                matched.append(entry)
        return matched

    def export_summary(self, output_path: str):
        stats = self.get_statistics()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"Summary exported to {output_path}")


class RetrievalEvaluator:
    """Evaluate retrieval system performance for the strict dataset."""

    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        with self.dataset_path.open('r', encoding='utf-8') as f:
            self.dataset = json.load(f)
        self.mode = dataset_mode(self.dataset)
        self.result_normalizer = ResultNormalizer(str(self.dataset_path), self.dataset)

    def evaluate(self, retrieval_function: Callable[[str], List[str]], verbose: bool = False) -> Dict:
        results = {
            'exact_matches': 0,
            'precisions': [],
            'recalls': [],
            'f1_scores': [],
            'reciprocal_ranks': [],
            'case_hits': [],
            'file_hits': [],
            'per_difficulty': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'per_category': defaultdict(lambda: {'correct': 0, 'total': 0}),
            'false_positives': [],
            'false_negatives': [],
            'errors': [],
        }

        for entry in self.dataset:
            try:
                raw_results = list(retrieval_function(entry['query']))
                retrieved_list = self.result_normalizer.normalize(raw_results)
                retrieved = set(retrieved_list)
                target_list = entry_target_identifiers(entry)
                target = set(target_list)

                tp = len(retrieved & target)
                fp = len(retrieved - target)
                fn = len(target - retrieved)

                exact_match = retrieved == target
                precision = tp / len(retrieved) if retrieved else 0.0
                recall = tp / len(target) if target else 0.0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

                rr = 0.0
                for index, item in enumerate(retrieved_list, start=1):
                    if item in target:
                        rr = 1.0 / index
                        break

                target_case_paths = set(entry_target_case_paths(entry))
                target_file_paths = set(entry_target_file_paths(entry))
                retrieved_case_paths = {item.split('::', 1)[0] for item in retrieved_list if '::' in item}
                retrieved_file_paths = {item.split('::', 1)[1] for item in retrieved_list if '::' in item}
                case_hit = float(bool(retrieved_case_paths & target_case_paths))
                file_hit = float(bool(retrieved_file_paths & target_file_paths))
                results['case_hits'].append(case_hit)
                results['file_hits'].append(file_hit)

                if exact_match:
                    results['exact_matches'] += 1
                results['precisions'].append(precision)
                results['recalls'].append(recall)
                results['f1_scores'].append(f1)
                results['reciprocal_ranks'].append(rr)
                results['false_positives'].append(fp)
                results['false_negatives'].append(fn)

                results['per_difficulty'][entry['difficulty']]['total'] += 1
                if exact_match:
                    results['per_difficulty'][entry['difficulty']]['correct'] += 1

                results['per_category'][entry['category']]['total'] += 1
                if exact_match:
                    results['per_category'][entry['category']]['correct'] += 1

                if verbose:
                    print(f"\nQuery {entry['id']}: {entry['query'][:80]}...")
                    print(f"  Target: {target_list}")
                    print(f"  Retrieved: {retrieved_list}")
                    print(f"  Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {f1:.3f}")
                    print(f"  CaseHit: {case_hit:.0f}, FileHit: {file_hit:.0f}")
                    if not exact_match:
                        print("  ✗ Not exact match")

            except Exception as exc:
                results['errors'].append({
                    'entry_id': entry['id'],
                    'query': entry['query'],
                    'error': str(exc),
                })
                if verbose:
                    print(f"\nError on query {entry['id']}: {exc}")

        metrics = {
            'dataset_mode': self.mode,
            'exact_match_accuracy': results['exact_matches'] / (len(self.dataset) - len(results['errors'])) if (len(self.dataset) - len(results['errors'])) > 0 else 0.0,
            'mean_precision': np.mean(results['precisions']) if results['precisions'] else 0.0,
            'mean_recall': np.mean(results['recalls']) if results['recalls'] else 0.0,
            'mean_f1': np.mean(results['f1_scores']) if results['f1_scores'] else 0.0,
            'mean_reciprocal_rank': np.mean(results['reciprocal_ranks']) if results['reciprocal_ranks'] else 0.0,
            'avg_false_positives': np.mean(results['false_positives']) if results['false_positives'] else 0.0,
            'avg_false_negatives': np.mean(results['false_negatives']) if results['false_negatives'] else 0.0,
            'total_errors': len(results['errors']),
            'difficulty_breakdown': {},
            'category_breakdown': {},
            'mean_case_hit': np.mean(results['case_hits']) if results['case_hits'] else 0.0,
            'mean_file_hit': np.mean(results['file_hits']) if results['file_hits'] else 0.0,
        }

        for diff, stats in results['per_difficulty'].items():
            metrics['difficulty_breakdown'][diff] = {
                'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0,
                'total': stats['total'],
            }

        for cat, stats in results['per_category'].items():
            metrics['category_breakdown'][cat] = {
                'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0,
                'total': stats['total'],
            }

        return metrics

    def print_evaluation_results(self, metrics: Dict):
        print("\n" + "=" * 70)
        print("RETRIEVAL SYSTEM EVALUATION RESULTS")
        print("=" * 70)
        print(f"\nMode: {metrics['dataset_mode']}")

        print(f"\n{'Overall Metrics:':<30}")
        print(f"  {'Exact Match Accuracy':<25} {metrics['exact_match_accuracy']:>6.2%}")
        print(f"  {'Mean Precision':<25} {metrics['mean_precision']:>6.2%}")
        print(f"  {'Mean Recall':<25} {metrics['mean_recall']:>6.2%}")
        print(f"  {'Mean F1 Score':<25} {metrics['mean_f1']:>6.2%}")
        print(f"  {'Mean Reciprocal Rank':<25} {metrics['mean_reciprocal_rank']:>6.3f}")
        print(f"  {'Mean Case Hit':<25} {metrics['mean_case_hit']:>6.2%}")
        print(f"  {'Mean File Hit':<25} {metrics['mean_file_hit']:>6.2%}")
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
        sorted_cats = sorted(metrics['category_breakdown'].items(), key=lambda item: (item[1]['accuracy'], item[1]['total']), reverse=True)[:10]
        for cat, stats in sorted_cats:
            print(f"  {cat:<30} {stats['accuracy']:>6.2%}  ({stats['total']} queries)")

        print("\n" + "=" * 70)

    def visualize_results(self, metrics: Dict, output_path: str = None):
        try:
            import matplotlib.pyplot as plt
        except ModuleNotFoundError as exc:
            raise SystemExit(
                "Visualization requires matplotlib. Install it first or run without --visualize."
            ) from exc

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f"Retrieval Dataset Analysis ({metrics['dataset_mode']})", fontsize=16, fontweight='bold')

        ax = axes[0, 0]
        metric_names = ['Exact Match\nAccuracy', 'Mean\nPrecision', 'Mean\nRecall', 'Mean\nF1 Score']
        metric_values = [
            metrics['exact_match_accuracy'],
            metrics['mean_precision'],
            metrics['mean_recall'],
            metrics['mean_f1'],
        ]
        bars = ax.bar(metric_names, metric_values, color=['#2ecc71', '#3498db', '#e74c3c', '#f39c12'])
        ax.set_ylabel('Score')
        ax.set_title('Overall Performance Metrics')
        ax.set_ylim(0, 1)
        ax.grid(axis='y', alpha=0.3)
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, height, f'{height:.2%}', ha='center', va='bottom', fontweight='bold')

        ax = axes[0, 1]
        difficulties = ['basic', 'intermediate', 'advanced']
        accuracies = [metrics['difficulty_breakdown'].get(diff, {}).get('accuracy', 0.0) for diff in difficulties]
        bars = ax.bar(difficulties, accuracies, color=['#27ae60', '#f39c12', '#c0392b'])
        ax.set_ylabel('Accuracy')
        ax.set_title('Accuracy by Difficulty Level')
        ax.set_ylim(0, 1)
        ax.grid(axis='y', alpha=0.3)
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, height, f'{height:.2%}', ha='center', va='bottom', fontweight='bold')

        ax = axes[1, 0]
        sorted_cats = sorted(metrics['category_breakdown'].items(), key=lambda item: item[1]['accuracy'], reverse=True)[:8]
        cat_names = [item[0] for item in sorted_cats]
        cat_accs = [item[1]['accuracy'] for item in sorted_cats]
        bars = ax.barh(cat_names, cat_accs, color='#3498db')
        ax.set_xlabel('Accuracy')
        ax.set_title('Top 8 Categories by Accuracy')
        ax.set_xlim(0, 1)
        ax.grid(axis='x', alpha=0.3)
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height() / 2.0, f' {width:.2%}', ha='left', va='center', fontsize=9)

        ax = axes[1, 1]
        error_metrics = ['Avg False\nPositives', 'Avg False\nNegatives', 'Total\nErrors']
        error_values = [
            metrics['avg_false_positives'],
            metrics['avg_false_negatives'],
            metrics['total_errors'],
        ]
        bars = ax.bar(error_metrics, error_values, color=['#e67e22', '#e74c3c', '#95a5a6'])
        ax.set_ylabel('Count')
        ax.set_title('Error Analysis')
        ax.grid(axis='y', alpha=0.3)
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2.0, height, f'{height:.2f}', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to {output_path}")
        else:
            plt.show()


def main():
    parser = argparse.ArgumentParser(description='Analyze and evaluate retrieval datasets')
    parser.add_argument('--dataset', '-d', default=str(DEFAULT_DATASET_PATH), help='Path to dataset JSON file. Defaults to the strict dataset.')
    parser.add_argument('--analyze', '-a', action='store_true', help='Print dataset statistics')
    parser.add_argument('--evaluate', '-e', action='store_true', help='Evaluate built-in example retrieval function')
    parser.add_argument('--visualize', '-v', action='store_true', help='Create visualization of results')
    parser.add_argument('--output', '-o', default=None, help='Output path for visualization')
    parser.add_argument('--verbose', action='store_true', help='Verbose output during evaluation')
    args = parser.parse_args()

    if args.analyze:
        analyzer = RetrievalDatasetAnalyzer(args.dataset)
        analyzer.print_statistics()

    if args.evaluate:
        evaluator = RetrievalEvaluator(args.dataset)
        print("\nEvaluating built-in example retrieval function...")
        metrics = evaluator.evaluate(
            example_retrieval_function,
            verbose=args.verbose,
        )
        evaluator.print_evaluation_results(metrics)

        if args.visualize:
            output = args.output or 'retrieval_evaluation_results.png'
            evaluator.visualize_results(metrics, output)

    if not args.analyze and not args.evaluate:
        parser.print_help()


if __name__ == '__main__':
    main()
