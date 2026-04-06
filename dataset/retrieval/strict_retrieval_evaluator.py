"""
Strict retrieval evaluator for full-tutorial retrieval.

This evaluator treats the canonical retrieval unit as:

    case_path::file_path

It is designed for the strict dataset produced by
``build_strict_retrieval_dataset.py`` and accepts structured retrieval results
or path-like strings that can be normalized back to a tutorial case and file.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union


ResultLike = Union[str, Dict[str, object]]


@dataclass(frozen=True)
class NormalizedResult:
    case_path: str
    file_path: str
    canonical_id: str


class StrictRetrievalEvaluator:
    def __init__(self, dataset_path: str, tutorials_dir: Optional[str] = None):
        self.dataset_path = Path(dataset_path)
        self.dataset = json.loads(self.dataset_path.read_text(encoding="utf-8"))

        self.tutorials_dir = Path(tutorials_dir).resolve() if tutorials_dir else None
        self.case_paths = self._collect_case_paths()

    def _collect_case_paths(self) -> List[str]:
        case_paths = {
            entry["case_path"]
            for entry in self.dataset
            if entry.get("case_path")
        }
        return sorted(case_paths, key=len, reverse=True)

    def _split_full_relative_path(self, relative_path: str) -> Optional[Tuple[str, str]]:
        cleaned = relative_path.strip().lstrip("*").strip()
        cleaned = cleaned.replace("\\", "/")

        for case_path in self.case_paths:
            prefix = f"{case_path}/"
            if cleaned.startswith(prefix):
                return case_path, cleaned[len(prefix):]

        marker_positions = []
        for marker in ("0/", "0.orig/", "constant/", "system/"):
            index = cleaned.find(marker)
            if index > 0:
                marker_positions.append((index, marker))

        if not marker_positions:
            return None

        index, _marker = min(marker_positions, key=lambda item: item[0])
        case_path = cleaned[:index].rstrip("/")
        file_path = cleaned[index:]
        if not case_path or not file_path:
            return None
        return case_path, file_path

    def normalize_result(self, item: ResultLike) -> Optional[NormalizedResult]:
        if isinstance(item, dict):
            if item.get("canonical_id"):
                parts = str(item["canonical_id"]).split("::", 1)
                if len(parts) == 2 and all(parts):
                    return NormalizedResult(parts[0], parts[1], str(item["canonical_id"]))

            case_path = item.get("case_path")
            file_path = item.get("file_path")
            if case_path and file_path:
                case_path_str = str(case_path)
                file_path_str = str(file_path)
                return NormalizedResult(
                    case_path=case_path_str,
                    file_path=file_path_str,
                    canonical_id=f"{case_path_str}::{file_path_str}",
                )

            path_value = item.get("path") or item.get("source")
            if path_value:
                return self.normalize_result(str(path_value))

            return None

        text = str(item).strip()
        if not text:
            return None

        if "::" in text:
            parts = text.split("::", 1)
            if len(parts) == 2 and all(parts):
                return NormalizedResult(parts[0], parts[1], text)

        cleaned = text.lstrip("*").strip().replace("\\", "/")
        if self.tutorials_dir:
            try:
                path_obj = Path(cleaned)
                if path_obj.is_absolute():
                    relative_path = str(path_obj.resolve().relative_to(self.tutorials_dir))
                else:
                    relative_path = cleaned
            except Exception:
                relative_path = cleaned
        else:
            relative_path = cleaned

        split = self._split_full_relative_path(relative_path)
        if not split:
            return None

        case_path, file_path = split
        return NormalizedResult(
            case_path=case_path,
            file_path=file_path,
            canonical_id=f"{case_path}::{file_path}",
        )

    def _normalize_ranked_results(self, results: Sequence[ResultLike]) -> List[NormalizedResult]:
        normalized: List[NormalizedResult] = []
        seen = set()

        for item in results:
            candidate = self.normalize_result(item)
            if not candidate or candidate.canonical_id in seen:
                continue
            seen.add(candidate.canonical_id)
            normalized.append(candidate)

        return normalized

    def evaluate(
        self,
        retrieval_function: Callable[[str], Sequence[ResultLike]],
        k_values: Sequence[int] = (1, 3, 5, 10),
    ) -> Dict[str, object]:
        aggregate_hits = defaultdict(list)
        aggregate_precisions = defaultdict(list)
        aggregate_recalls = defaultdict(list)
        aggregate_case_hits = defaultdict(list)
        aggregate_file_hits = defaultdict(list)
        reciprocal_ranks: List[float] = []
        detailed_results: List[Dict[str, object]] = []

        by_difficulty: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        by_category: Dict[str, List[Dict[str, object]]] = defaultdict(list)

        for entry in self.dataset:
            raw_results = retrieval_function(entry["query"])
            normalized = self._normalize_ranked_results(raw_results)

            target_ids = {target["canonical_id"] for target in entry["target_files"]}
            target_cases = {target["case_path"] for target in entry["target_files"]}
            target_files = {target["file_path"] for target in entry["target_files"]}

            row = {
                "query_id": entry["id"],
                "query": entry["query"],
                "case_path": entry.get("case_path"),
                "difficulty": entry.get("difficulty"),
                "category": entry.get("category"),
                "target_files": list(target_ids),
                "retrieved_files": [item.canonical_id for item in normalized],
            }

            reciprocal_rank = 0.0
            for index, item in enumerate(normalized, start=1):
                if item.canonical_id in target_ids:
                    reciprocal_rank = 1.0 / index
                    break
            reciprocal_ranks.append(reciprocal_rank)
            row["mrr"] = reciprocal_rank

            for k in k_values:
                top_k = normalized[:k]
                top_ids = {item.canonical_id for item in top_k}
                top_cases = {item.case_path for item in top_k}
                top_files = {item.file_path for item in top_k}

                hit = bool(top_ids & target_ids)
                case_hit = bool(top_cases & target_cases)
                file_hit = bool(top_files & target_files)
                precision = len(top_ids & target_ids) / len(top_k) if top_k else 0.0
                recall = len(top_ids & target_ids) / len(target_ids) if target_ids else 0.0

                aggregate_hits[f"hit@{k}"].append(float(hit))
                aggregate_case_hits[f"case_hit@{k}"].append(float(case_hit))
                aggregate_file_hits[f"file_hit@{k}"].append(float(file_hit))
                aggregate_precisions[f"precision@{k}"].append(precision)
                aggregate_recalls[f"recall@{k}"].append(recall)

                row[f"hit@{k}"] = hit
                row[f"case_hit@{k}"] = case_hit
                row[f"file_hit@{k}"] = file_hit
                row[f"precision@{k}"] = precision
                row[f"recall@{k}"] = recall

            detailed_results.append(row)
            if entry.get("difficulty"):
                by_difficulty[str(entry["difficulty"])].append(row)
            if entry.get("category"):
                by_category[str(entry["category"])].append(row)

        aggregate_metrics: Dict[str, object] = {
            "total_queries": len(self.dataset),
            "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        }

        for metric_map in (
            aggregate_hits,
            aggregate_case_hits,
            aggregate_file_hits,
            aggregate_precisions,
            aggregate_recalls,
        ):
            for key, values in metric_map.items():
                aggregate_metrics[key] = sum(values) / len(values) if values else 0.0

        aggregate_metrics["by_difficulty"] = self._summarize_groups(by_difficulty, k_values)
        aggregate_metrics["by_category"] = self._summarize_groups(by_category, k_values)

        return {
            "metadata": {
                "dataset": str(self.dataset_path),
                "tutorials_dir": str(self.tutorials_dir) if self.tutorials_dir else None,
                "total_queries": len(self.dataset),
            },
            "aggregate_metrics": aggregate_metrics,
            "detailed_results": detailed_results,
        }

    def _summarize_groups(
        self,
        groups: Dict[str, List[Dict[str, object]]],
        k_values: Sequence[int],
    ) -> Dict[str, Dict[str, float]]:
        summary: Dict[str, Dict[str, float]] = {}

        for group_name, rows in groups.items():
            if not rows:
                continue

            group_summary: Dict[str, float] = {
                "count": float(len(rows)),
                "mrr": sum(float(row["mrr"]) for row in rows) / len(rows),
            }
            for k in k_values:
                for metric_name in (
                    f"hit@{k}",
                    f"case_hit@{k}",
                    f"file_hit@{k}",
                    f"precision@{k}",
                    f"recall@{k}",
                ):
                    group_summary[metric_name] = (
                        sum(float(row[metric_name]) for row in rows) / len(rows)
                    )

            summary[group_name] = group_summary

        return summary


def _demo_retrieval(query: str) -> Sequence[ResultLike]:
    del query
    return []


def main() -> None:
    dataset_path = os.getenv(
        "STRICT_RETRIEVAL_DATASET",
        str(Path(__file__).resolve().with_name("blastfoam_retrieval_validation_dataset_strict.json")),
    )
    tutorials_dir = os.getenv("BLASTFOAM_TUTORIALS")
    evaluator = StrictRetrievalEvaluator(dataset_path=dataset_path, tutorials_dir=tutorials_dir)
    results = evaluator.evaluate(_demo_retrieval)
    print(json.dumps(results["aggregate_metrics"], indent=2))


if __name__ == "__main__":
    main()
