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
    DEFAULT_BENCHMARK,
    build_evaluation_payload,
    load_project_environment,
    maybe_limit_dataset,
    parse_k_values,
    print_summary,
    resolve_dataset_path,
    resolve_results_dir,
    save_results,
)


KG_RETRIEVAL_MAX_ITERATIONS_ENV = "KG_RETRIEVAL_MAX_ITERATIONS"


def default_kg_max_iterations() -> int:
    raw_value = os.getenv(KG_RETRIEVAL_MAX_ITERATIONS_ENV, "3")
    try:
        return max(1, int(raw_value))
    except ValueError:
        return 3

def load_knowledge_graph_retriever_class(module_path: Path, class_name: str):
    spec = importlib.util.spec_from_file_location("strict_kg_eval_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec from {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate knowledge-graph retrieval for the configured benchmark.")
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK, help="Benchmark name, e.g. case_content or user_guide.")
    parser.add_argument("--dataset", default=None, help="Retrieval dataset path. Defaults to the selected benchmark dataset.")
    parser.add_argument("--tutorials-dir", default=os.getenv("BLASTFOAM_TUTORIALS"), help="Tutorial root directory.")
    parser.add_argument("--k-values", default="1,3,5,10", help="Comma-separated K values, e.g. 1,3,5,10")
    parser.add_argument("--limit", type=int, default=None, help="Evaluate only the first N queries.")
    parser.add_argument("--results-dir", default=None, help="Directory for result JSON files. Defaults to the selected benchmark results directory.")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=default_kg_max_iterations(),
        help="Maximum ReAct iterations in KG retrieval (env: KG_RETRIEVAL_MAX_ITERATIONS, default: 3).",
    )
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

    if args.benchmark == "case_content" and not args.tutorials_dir:
        raise SystemExit("Please provide --tutorials-dir or set BLASTFOAM_TUTORIALS.")

    from dataset.retrieval.benchmark_registry import get_benchmark_config

    benchmark_config = get_benchmark_config(args.benchmark)
    dataset_path = resolve_dataset_path(args.benchmark, args.dataset)
    tutorials_dir = Path(args.tutorials_dir).resolve() if args.tutorials_dir else None
    results_dir = resolve_results_dir(args.benchmark, args.results_dir)
    k_values = parse_k_values(args.k_values)

    if tutorials_dir:
        os.environ["BLASTFOAM_TUTORIALS"] = str(tutorials_dir)

    evaluator = StrictRetrievalEvaluator(str(dataset_path), str(tutorials_dir) if tutorials_dir else None)
    maybe_limit_dataset(evaluator, args.limit)

    try:
        retriever_class = load_knowledge_graph_retriever_class(
            module_path=Path(benchmark_config["knowledge_graph_module"]),
            class_name=str(benchmark_config["knowledge_graph_class"]),
        )
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Knowledge-graph evaluation dependencies are missing. "
            f"Install the packages from requirements.txt and retry. Missing module: {exc.name}"
        ) from exc

    retriever = retriever_class(
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
            "benchmark": args.benchmark,
            "retriever_type": f"{args.benchmark}_knowledge_graph",
            "strict_mode": True,
            "max_iterations": args.max_iterations,
            "include_file_content": args.include_file_content,
            "retrieval_llm_base_url": args.retrieval_llm_base_url,
            "retrieval_llm_model": args.retrieval_llm_model,
            "structured_results": True,
            "total_queries": len(evaluator.dataset),
        },
        aggregate_updates={
            "benchmark": args.benchmark,
            "strict_mode": True,
        },
    )

    output_name = f"knowledge_graph_retrieval_{results['metadata']['timestamp']}.json"
    output_path = save_results(results, results_dir / output_name)

    print(f"\nSaved results to: {output_path}")
    print_summary(
        results,
        metric_names=benchmark_config["summary_metrics"],
    )


if __name__ == "__main__":
    main()
