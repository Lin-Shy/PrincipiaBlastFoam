"""
Shared helpers for strict retrieval evaluation scripts.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Deque, Dict, Iterable, List, MutableMapping, Optional, Sequence

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args, **_kwargs):  # type: ignore[no-redef]
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset.retrieval.benchmark_registry import get_benchmark_config
from dataset.retrieval.strict_retrieval_evaluator import StrictRetrievalEvaluator


DEFAULT_BENCHMARK = "case_content"
DEFAULT_DATASET_PATH = Path(get_benchmark_config(DEFAULT_BENCHMARK)["default_dataset"])
DEFAULT_RESULTS_DIR = Path(get_benchmark_config(DEFAULT_BENCHMARK)["default_results_dir"])


def load_project_environment() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def parse_k_values(raw_value: Optional[str]) -> List[int]:
    if not raw_value:
        return [1, 3, 5, 10]
    values = [int(item.strip()) for item in raw_value.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one K value is required.")
    return values


def ensure_results_dir(results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def resolve_dataset_path(benchmark: str, dataset_override: Optional[str]) -> Path:
    if dataset_override:
        return Path(dataset_override).resolve()
    return Path(get_benchmark_config(benchmark)["default_dataset"]).resolve()


def resolve_results_dir(benchmark: str, results_override: Optional[str]) -> Path:
    if results_override:
        return ensure_results_dir(Path(results_override).resolve())
    return ensure_results_dir(Path(get_benchmark_config(benchmark)["default_results_dir"]).resolve())


def now_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def save_results(payload: Dict[str, object], output_path: Path) -> Path:
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def build_evaluation_payload(
    evaluator: StrictRetrievalEvaluator,
    query_records: Sequence[Dict[str, object]],
    k_values: Sequence[int],
    metadata_updates: Optional[Dict[str, object]] = None,
    aggregate_updates: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    records_by_query: MutableMapping[str, Deque[Dict[str, object]]] = defaultdict(deque)
    records_by_id: Dict[int, Dict[str, object]] = {}

    for record in query_records:
        records_by_query[str(record["query"])].append(record)
        records_by_id[int(record["query_id"])] = record

    results = evaluator.evaluate(
        lambda query: records_by_query[str(query)].popleft()["results"],
        k_values=k_values,
    )

    aggregate_metrics = results["aggregate_metrics"]
    aggregate_metrics["avg_retrieval_time"] = mean(
        float(record["retrieval_time"]) for record in query_records
    ) if query_records else 0.0

    if aggregate_updates:
        aggregate_metrics.update(aggregate_updates)

    for row in results["detailed_results"]:
        record = records_by_id[int(row["query_id"])]
        row["retrieval_time"] = record["retrieval_time"]
        if "raw_results" in record:
            row["raw_results"] = record["raw_results"]
        if "raw_ranked_results" in record:
            row["raw_ranked_results"] = record["raw_ranked_results"]

    metadata = results["metadata"]
    metadata["timestamp"] = now_timestamp()
    if metadata_updates:
        metadata.update(metadata_updates)

    return results


def maybe_limit_dataset(evaluator: StrictRetrievalEvaluator, limit: Optional[int]) -> None:
    if limit is not None and limit > 0:
        evaluator.dataset = evaluator.dataset[:limit]


def print_summary(results: Dict[str, object], metric_names: Iterable[str]) -> None:
    aggregate = results.get("aggregate_metrics", {})
    print("\nEvaluation summary:")
    for metric_name in metric_names:
        if metric_name in aggregate:
            value = aggregate[metric_name]
            if isinstance(value, float):
                print(f"  {metric_name}: {value:.4f}")
            else:
                print(f"  {metric_name}: {value}")
