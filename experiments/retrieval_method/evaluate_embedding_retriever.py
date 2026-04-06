"""
Evaluate embedding-based retrieval with strict case+file matching.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset.retrieval.strict_retrieval_evaluator import StrictRetrievalEvaluator
from experiments.retrieval_method.evaluation_common import (
    DEFAULT_DATASET_PATH,
    DEFAULT_RESULTS_DIR,
    build_evaluation_payload,
    ensure_results_dir,
    load_project_environment,
    maybe_limit_dataset,
    parse_k_values,
    print_summary,
    save_results,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate embedding retrieval with strict case+file matching.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Strict retrieval dataset path.")
    parser.add_argument("--tutorials-dir", default=os.getenv("BLASTFOAM_TUTORIALS"), help="Tutorial root directory.")
    parser.add_argument("--embedding-level", default="file", choices=["file", "case"], help="Embedding index level.")
    parser.add_argument("--k-values", default="1,3,5,10", help="Comma-separated K values, e.g. 1,3,5,10")
    parser.add_argument("--search-k", type=int, default=40, help="Retriever candidate count before strict deduplication.")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N queries.")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR), help="Directory for result JSON files.")
    return parser.parse_args()


def main() -> None:
    load_project_environment()
    args = parse_args()

    if not args.tutorials_dir:
        raise SystemExit("Please provide --tutorials-dir or set BLASTFOAM_TUTORIALS.")

    dataset_path = Path(args.dataset).resolve()
    tutorials_dir = Path(args.tutorials_dir).resolve()
    results_dir = ensure_results_dir(Path(args.results_dir).resolve())
    k_values = parse_k_values(args.k_values)

    evaluator = StrictRetrievalEvaluator(str(dataset_path), str(tutorials_dir))
    maybe_limit_dataset(evaluator, args.limit)

    try:
        from scripts.native_embedding.embedding_retriever import EmbeddingRetriever
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Embedding evaluation dependencies are missing. "
            f"Install the packages from requirements.txt and retry. Missing module: {exc.name}"
        ) from exc

    retriever = EmbeddingRetriever(case_base_dir=str(tutorials_dir), embedding_level=args.embedding_level)
    if not retriever.vector_store:
        raise SystemExit(
            f"No FAISS index is available for embedding level '{args.embedding_level}'. "
            "Build the index first with scripts/native_embedding/build_embedding_index.py."
        )

    query_records: List[Dict[str, object]] = []

    for index, entry in enumerate(evaluator.dataset, start=1):
        print(f"[{index}/{len(evaluator.dataset)}] {entry['query']}")
        start_time = time.perf_counter()
        results_with_scores = retriever.search_with_scores(entry["query"], k=args.search_k)
        retrieval_time = time.perf_counter() - start_time

        ranked_results = []
        raw_ranked_results = []
        for document, score in results_with_scores:
            source = document.metadata.get("source")
            if not source:
                continue
            ranked_results.append(
                {
                    "path": source,
                    "score": float(score),
                }
            )
            raw_ranked_results.append(
                {
                    "source": source,
                    "score": float(score),
                }
            )

        query_records.append(
            {
                "query_id": entry["id"],
                "query": entry["query"],
                "results": ranked_results,
                "retrieval_time": retrieval_time,
                "raw_ranked_results": raw_ranked_results,
            }
        )

    results = build_evaluation_payload(
        evaluator=evaluator,
        query_records=query_records,
        k_values=k_values,
        metadata_updates={
            "dataset": str(dataset_path),
            "case_base_dir": str(tutorials_dir),
            "retriever_type": f"embedding_{args.embedding_level}",
            "embedding_level": args.embedding_level,
            "strict_mode": True,
            "search_k": args.search_k,
            "total_queries": len(evaluator.dataset),
        },
        aggregate_updates={
            "embedding_level": args.embedding_level,
            "strict_mode": True,
        },
    )

    output_name = f"embedding_retrieval_{args.embedding_level}_{results['metadata']['timestamp']}.json"
    output_path = save_results(results, results_dir / output_name)

    print(f"\nSaved results to: {output_path}")
    print_summary(
        results,
        metric_names=[
            "mrr",
            "hit@1",
            "hit@3",
            "hit@5",
            "case_hit@5",
            "precision@5",
            "recall@5",
            "avg_retrieval_time",
        ],
    )


if __name__ == "__main__":
    main()
