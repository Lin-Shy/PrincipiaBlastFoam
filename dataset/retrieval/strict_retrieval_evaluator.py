"""
Retrieval evaluator for strict benchmark datasets.

Supported benchmark modes:

1. case_content:
   canonical unit is ``case_path::file_path``
2. user_guide:
   canonical unit is ``node_id`` from the user guide knowledge graph
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union


ResultLike = Union[str, Dict[str, object]]
USER_GUIDE_GRAPH_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "knowledge_graph"
    / "user_guide_knowledge_graph"
    / "user_guide_knowledge_graph.json"
)


@dataclass(frozen=True)
class NormalizedResult:
    canonical_id: str
    case_path: Optional[str] = None
    file_path: Optional[str] = None
    node_id: Optional[str] = None
    section_id: Optional[str] = None
    chapter_id: Optional[str] = None


class StrictRetrievalEvaluator:
    def __init__(self, dataset_path: str, tutorials_dir: Optional[str] = None):
        self.dataset_path = Path(dataset_path)
        self.dataset = json.loads(self.dataset_path.read_text(encoding="utf-8"))

        self.tutorials_dir = Path(tutorials_dir).resolve() if tutorials_dir else None
        self.dataset_mode = self._detect_dataset_mode()
        self.case_paths = self._collect_case_paths()
        self.user_guide_nodes: Dict[str, Dict[str, object]] = {}
        self.user_guide_number_to_ids: Dict[str, List[str]] = {}

        if self.dataset_mode == "user_guide":
            self._load_user_guide_index()

    def _detect_dataset_mode(self) -> str:
        if not self.dataset:
            raise ValueError("Dataset is empty.")

        first_entry = self.dataset[0]
        if first_entry.get("target_files"):
            return "case_content"
        if first_entry.get("target_nodes"):
            return "user_guide"
        raise ValueError(
            "Unsupported dataset schema. Expected 'target_files' or 'target_nodes' in each entry."
        )

    def _collect_case_paths(self) -> List[str]:
        if self.dataset_mode != "case_content":
            return []

        case_paths = {
            str(entry["case_path"])
            for entry in self.dataset
            if entry.get("case_path")
        }
        return sorted(case_paths, key=len, reverse=True)

    def _load_user_guide_index(self) -> None:
        if not USER_GUIDE_GRAPH_PATH.exists():
            raise FileNotFoundError(
                f"User guide knowledge graph not found: {USER_GUIDE_GRAPH_PATH}"
            )

        nodes = json.loads(USER_GUIDE_GRAPH_PATH.read_text(encoding="utf-8"))
        self.user_guide_nodes = {
            str(node["id"]): node
            for node in nodes
            if node.get("id")
        }
        self.user_guide_number_to_ids = defaultdict(list)
        for node in nodes:
            node_id = node.get("id")
            number = node.get("number")
            if not node_id or not number:
                continue
            self.user_guide_number_to_ids[str(number)].append(str(node_id))

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

    def _build_user_guide_result(self, node_id: str) -> NormalizedResult:
        chapter_id, section_id = self._resolve_user_guide_context(node_id)
        return NormalizedResult(
            canonical_id=node_id,
            node_id=node_id,
            section_id=section_id or node_id,
            chapter_id=chapter_id,
        )

    def _resolve_user_guide_context(self, node_id: str) -> Tuple[Optional[str], Optional[str]]:
        current_id = node_id
        chapter_id: Optional[str] = None
        section_id: Optional[str] = None

        while current_id:
            node = self.user_guide_nodes.get(current_id)
            if not node:
                break

            current_node_id = str(node.get("id"))
            if chapter_id is None and current_node_id.startswith("ch"):
                chapter_id = current_node_id
            if section_id is None and (current_node_id.startswith("sec") or current_node_id.startswith("ch")):
                section_id = current_node_id

            parent_id = node.get("parentId")
            current_id = str(parent_id) if parent_id else ""

        return chapter_id, section_id

    def _normalize_user_guide_reference(self, reference: object) -> Optional[str]:
        text = str(reference).strip()
        if not text:
            return None

        normalized_id = (
            text.replace("Section", "")
            .replace("section", "")
            .replace("Chapter", "")
            .replace("chapter", "")
            .strip()
        )
        if normalized_id in self.user_guide_nodes:
            return normalized_id

        number_matches = self.user_guide_number_to_ids.get(normalized_id, [])
        if len(number_matches) == 1:
            return number_matches[0]

        compact = text.replace(" ", "")
        if compact in self.user_guide_nodes:
            return compact

        return None

    def normalize_result(self, item: ResultLike) -> Optional[NormalizedResult]:
        if self.dataset_mode == "user_guide":
            return self._normalize_user_guide_result(item)
        return self._normalize_case_content_result(item)

    def _normalize_case_content_result(self, item: ResultLike) -> Optional[NormalizedResult]:
        if isinstance(item, dict):
            if item.get("canonical_id"):
                parts = str(item["canonical_id"]).split("::", 1)
                if len(parts) == 2 and all(parts):
                    return NormalizedResult(
                        canonical_id=str(item["canonical_id"]),
                        case_path=parts[0],
                        file_path=parts[1],
                    )

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
                return self._normalize_case_content_result(str(path_value))

            return None

        text = str(item).strip()
        if not text:
            return None

        if "::" in text:
            parts = text.split("::", 1)
            if len(parts) == 2 and all(parts):
                return NormalizedResult(
                    case_path=parts[0],
                    file_path=parts[1],
                    canonical_id=text,
                )

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

    def _normalize_user_guide_result(self, item: ResultLike) -> Optional[NormalizedResult]:
        if isinstance(item, dict):
            for key in ("canonical_id", "node_id", "id", "number"):
                value = item.get(key)
                if not value:
                    continue
                resolved_id = self._normalize_user_guide_reference(value)
                if resolved_id:
                    return self._build_user_guide_result(resolved_id)
            return None

        resolved_id = self._normalize_user_guide_reference(item)
        if not resolved_id:
            return None
        return self._build_user_guide_result(resolved_id)

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

    def _target_entries(self, entry: Dict[str, object]) -> Sequence[Dict[str, object]]:
        if self.dataset_mode == "case_content":
            return entry.get("target_files", [])
        return entry.get("target_nodes", [])

    def _target_ids(self, entry: Dict[str, object]) -> set[str]:
        target_ids = set()
        for target in self._target_entries(entry):
            if self.dataset_mode == "case_content":
                canonical_id = target.get("canonical_id")
                if canonical_id:
                    target_ids.add(str(canonical_id))
                    continue
                case_path = target.get("case_path")
                file_path = target.get("file_path")
                if case_path and file_path:
                    target_ids.add(f"{case_path}::{file_path}")
            else:
                canonical_id = target.get("canonical_id") or target.get("node_id")
                if canonical_id:
                    target_ids.add(str(canonical_id))
        return target_ids

    def _target_case_paths(self, entry: Dict[str, object]) -> set[str]:
        return {
            str(target["case_path"])
            for target in self._target_entries(entry)
            if target.get("case_path")
        }

    def _target_file_paths(self, entry: Dict[str, object]) -> set[str]:
        return {
            str(target["file_path"])
            for target in self._target_entries(entry)
            if target.get("file_path")
        }

    def _target_user_guide_groups(self, entry: Dict[str, object]) -> Tuple[set[str], set[str]]:
        chapter_ids: set[str] = set()
        section_ids: set[str] = set()

        for target in self._target_entries(entry):
            canonical_id = target.get("canonical_id") or target.get("node_id")
            if not canonical_id:
                continue
            resolved = self._build_user_guide_result(str(canonical_id))
            if resolved.chapter_id:
                chapter_ids.add(resolved.chapter_id)
            if resolved.section_id:
                section_ids.add(resolved.section_id)

        return chapter_ids, section_ids

    def evaluate(
        self,
        retrieval_function: Callable[[str], Sequence[ResultLike]],
        k_values: Sequence[int] = (1, 3, 5, 10),
    ) -> Dict[str, object]:
        aggregate_hits = defaultdict(list)
        aggregate_precisions = defaultdict(list)
        aggregate_recalls = defaultdict(list)
        aggregate_primary_hits = defaultdict(list)
        aggregate_secondary_hits = defaultdict(list)
        reciprocal_ranks: List[float] = []
        detailed_results: List[Dict[str, object]] = []

        by_difficulty: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        by_category: Dict[str, List[Dict[str, object]]] = defaultdict(list)

        for entry in self.dataset:
            raw_results = retrieval_function(entry["query"])
            normalized = self._normalize_ranked_results(raw_results)
            target_ids = self._target_ids(entry)

            if self.dataset_mode == "case_content":
                target_primary = self._target_case_paths(entry)
                target_secondary = self._target_file_paths(entry)
                primary_metric_prefix = "case_hit"
                secondary_metric_prefix = "file_hit"
                row = {
                    "query_id": entry["id"],
                    "query": entry["query"],
                    "case_path": entry.get("case_path"),
                    "difficulty": entry.get("difficulty"),
                    "category": entry.get("category"),
                    "target_files": list(target_ids),
                    "retrieved_files": [item.canonical_id for item in normalized],
                }
            else:
                target_secondary, target_primary = self._target_user_guide_groups(entry)
                primary_metric_prefix = "section_hit"
                secondary_metric_prefix = "chapter_hit"
                row = {
                    "query_id": entry["id"],
                    "query": entry["query"],
                    "difficulty": entry.get("difficulty"),
                    "category": entry.get("category"),
                    "target_nodes": list(target_ids),
                    "retrieved_nodes": [item.canonical_id for item in normalized],
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
                precision = len(top_ids & target_ids) / len(top_k) if top_k else 0.0
                recall = len(top_ids & target_ids) / len(target_ids) if target_ids else 0.0
                hit = bool(top_ids & target_ids)

                if self.dataset_mode == "case_content":
                    top_primary = {item.case_path for item in top_k if item.case_path}
                    top_secondary = {item.file_path for item in top_k if item.file_path}
                else:
                    top_primary = {item.section_id for item in top_k if item.section_id}
                    top_secondary = {item.chapter_id for item in top_k if item.chapter_id}

                primary_hit = bool(top_primary & target_primary)
                secondary_hit = bool(top_secondary & target_secondary)

                aggregate_hits[f"hit@{k}"].append(float(hit))
                aggregate_primary_hits[f"{primary_metric_prefix}@{k}"].append(float(primary_hit))
                aggregate_secondary_hits[f"{secondary_metric_prefix}@{k}"].append(float(secondary_hit))
                aggregate_precisions[f"precision@{k}"].append(precision)
                aggregate_recalls[f"recall@{k}"].append(recall)

                row[f"hit@{k}"] = hit
                row[f"{primary_metric_prefix}@{k}"] = primary_hit
                row[f"{secondary_metric_prefix}@{k}"] = secondary_hit
                row[f"precision@{k}"] = precision
                row[f"recall@{k}"] = recall

            detailed_results.append(row)
            if entry.get("difficulty"):
                by_difficulty[str(entry["difficulty"])].append(row)
            if entry.get("category"):
                by_category[str(entry["category"])].append(row)

        aggregate_metrics: Dict[str, object] = {
            "dataset_mode": self.dataset_mode,
            "total_queries": len(self.dataset),
            "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        }

        for metric_map in (
            aggregate_hits,
            aggregate_primary_hits,
            aggregate_secondary_hits,
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
                "dataset_mode": self.dataset_mode,
                "total_queries": len(self.dataset),
            },
            "aggregate_metrics": aggregate_metrics,
            "detailed_results": detailed_results,
        }

    def _group_metric_names(self, k: int) -> Tuple[str, ...]:
        if self.dataset_mode == "case_content":
            return (
                f"hit@{k}",
                f"case_hit@{k}",
                f"file_hit@{k}",
                f"precision@{k}",
                f"recall@{k}",
            )
        return (
            f"hit@{k}",
            f"section_hit@{k}",
            f"chapter_hit@{k}",
            f"precision@{k}",
            f"recall@{k}",
        )

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
                for metric_name in self._group_metric_names(k):
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
        str(
            Path(__file__).resolve().parent
            / "benchmarks"
            / "case_content"
            / "blastfoam_retrieval_validation_dataset_strict.json"
        ),
    )
    tutorials_dir = os.getenv("BLASTFOAM_TUTORIALS")
    evaluator = StrictRetrievalEvaluator(dataset_path=dataset_path, tutorials_dir=tutorials_dir)
    results = evaluator.evaluate(_demo_retrieval)
    print(json.dumps(results["aggregate_metrics"], indent=2))


if __name__ == "__main__":
    main()
