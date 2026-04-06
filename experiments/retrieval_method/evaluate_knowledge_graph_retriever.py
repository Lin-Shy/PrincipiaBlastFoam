"""
Evaluate knowledge-graph retrieval with strict case+file matching.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
from pathlib import Path
from typing import Dict, List


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

def load_knowledge_graph_retriever_class():
    module_path = PROJECT_ROOT / "principia_ai" / "tools" / "case_content_knowledge_graph_tool.py"
    spec = importlib.util.spec_from_file_location("strict_kg_eval_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CaseContentKnowledgeGraphRetriever


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate knowledge-graph retrieval with strict case+file matching.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Strict retrieval dataset path.")
    parser.add_argument("--tutorials-dir", default=os.getenv("BLASTFOAM_TUTORIALS"), help="Tutorial root directory.")
    parser.add_argument("--k-values", default="1,3,5,10", help="Comma-separated K values, e.g. 1,3,5,10")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N queries.")
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR), help="Directory for result JSON files.")
    parser.add_argument("--max-iterations", type=int, default=5, help="Maximum ReAct iterations in KG retrieval.")
    parser.add_argument(
        "--include-file-content",
        action="store_true",
        help="Include file content during KG retrieval. Disabled by default for faster evaluation.",
    )
    parser.add_argument(
        "--retrieval-llm-api-key",
        default=os.getenv("RETRIEVAL_LLM_API_KEY"),
        help="LLM API key for retrieval only. Falls back to RETRIEVAL_LLM_API_KEY/LLM_API_KEY.",
    )
    parser.add_argument(
        "--retrieval-llm-base-url",
        default=os.getenv("RETRIEVAL_LLM_API_BASE_URL"),
        help="LLM base URL for retrieval only. Falls back to RETRIEVAL_LLM_API_BASE_URL/LLM_API_BASE_URL.",
    )
    parser.add_argument(
        "--retrieval-llm-model",
        default=os.getenv("RETRIEVAL_LLM_MODEL"),
        help="LLM model for retrieval only. Falls back to RETRIEVAL_LLM_MODEL/LLM_MODEL.",
    )
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

    os.environ["BLASTFOAM_TUTORIALS"] = str(tutorials_dir)

    evaluator = StrictRetrievalEvaluator(str(dataset_path), str(tutorials_dir))
    maybe_limit_dataset(evaluator, args.limit)

    try:
        CaseContentKnowledgeGraphRetriever = load_knowledge_graph_retriever_class()
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Knowledge-graph evaluation dependencies are missing. "
            f"Install the packages from requirements.txt and retry. Missing module: {exc.name}"
        ) from exc

    retriever = CaseContentKnowledgeGraphRetriever(
        llm_api_key=args.retrieval_llm_api_key,
        llm_base_url=args.retrieval_llm_base_url,
        llm_model=args.retrieval_llm_model,
    )
    query_records: List[Dict[str, object]] = []

    for index, entry in enumerate(evaluator.dataset, start=1):
        print(f"[{index}/{len(evaluator.dataset)}] {entry['query']}")
        start_time = time.perf_counter()
        detailed = retriever.search_detailed(
            entry["query"],
            top_k=max(k_values),
            include_file_content=args.include_file_content,
            max_iterations=args.max_iterations,
        )
        raw_results = detailed.get("text")
        ranked_results = list(detailed.get("structured_results", []))
        retrieval_time = time.perf_counter() - start_time

        query_records.append(
            {
                "query_id": entry["id"],
                "query": entry["query"],
                "results": ranked_results,
                "retrieval_time": retrieval_time,
                "raw_results": raw_results,
            }
        )

    results = build_evaluation_payload(
        evaluator=evaluator,
        query_records=query_records,
        k_values=k_values,
        metadata_updates={
            "dataset": str(dataset_path),
            "retriever_type": "case_content_knowledge_graph",
            "strict_mode": True,
            "max_iterations": args.max_iterations,
            "include_file_content": args.include_file_content,
            "retrieval_llm_base_url": args.retrieval_llm_base_url,
            "retrieval_llm_model": args.retrieval_llm_model,
            "structured_results": True,
            "total_queries": len(evaluator.dataset),
        },
        aggregate_updates={
            "strict_mode": True,
        },
    )

    output_name = f"knowledge_graph_retrieval_{results['metadata']['timestamp']}.json"
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
