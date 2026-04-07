"""
Build and audit the user-guide retrieval benchmark.

The build process is driven by a compact blueprint so the dataset can be
regenerated deterministically after edits.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_DIR = PROJECT_ROOT / "dataset" / "retrieval"
BENCHMARK_DIR = RETRIEVAL_DIR / "benchmarks" / "user_guide"
GRAPH_PATH = PROJECT_ROOT / "data" / "knowledge_graph" / "user_guide_knowledge_graph" / "user_guide_knowledge_graph.json"
BLUEPRINT_PATH = BENCHMARK_DIR / "user_guide_retrieval_blueprint.json"
DATASET_PATH = BENCHMARK_DIR / "user_guide_retrieval_validation_dataset.json"
AUDIT_PATH = BENCHMARK_DIR / "user_guide_retrieval_validation_audit.json"
SUMMARY_PATH = BENCHMARK_DIR / "USER_GUIDE_RETRIEVAL_AUDIT_SUMMARY.md"
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "into", "is",
    "it", "its", "of", "on", "or", "section", "the", "to", "used", "user", "where",
    "which", "with",
}


def load_graph() -> List[Dict[str, object]]:
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))


def load_blueprint() -> List[Dict[str, object]]:
    return json.loads(BLUEPRINT_PATH.read_text(encoding="utf-8"))


def normalize_query(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def significant_tokens(text: str) -> List[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def resolve_context(node_id: str, id_to_node: Dict[str, Dict[str, object]]) -> Tuple[Optional[str], Optional[str]]:
    current_id = node_id
    chapter_id: Optional[str] = None
    section_id: Optional[str] = None

    while current_id:
        node = id_to_node.get(current_id)
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


def query_has_disambiguating_context(
    query: str,
    node_id: str,
    id_to_node: Dict[str, Dict[str, object]],
) -> bool:
    query_lower = query.lower()
    current_id = node_id
    context_tokens = set()

    while current_id:
        node = id_to_node.get(current_id)
        if not node:
            break

        title = str(node.get("title") or "")
        number = str(node.get("number") or "")
        if number and number in query_lower:
            return True
        context_tokens.update(significant_tokens(title))

        parent_id = node.get("parentId")
        current_id = str(parent_id) if parent_id else ""

    return any(token in query_lower for token in context_tokens)


def build_dataset(
    blueprint: List[Dict[str, object]],
    nodes: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    id_to_node = {
        str(node["id"]): node
        for node in nodes
        if node.get("id")
    }
    title_to_node_ids: Dict[str, List[str]] = defaultdict(list)
    for node_id, node in id_to_node.items():
        title = str(node.get("title") or "").strip()
        if title:
            title_to_node_ids[title].append(node_id)

    dataset: List[Dict[str, object]] = []
    per_entry_audit: List[Dict[str, object]] = []
    normalized_queries_seen: Dict[str, int] = {}
    node_ids_seen: Dict[str, int] = {}

    for index, spec in enumerate(blueprint, start=1):
        node_id = str(spec["node_id"])
        query = str(spec["query"]).strip()
        difficulty = str(spec["difficulty"])
        category = str(spec["category"])
        node = id_to_node.get(node_id)

        if not node:
            per_entry_audit.append(
                {
                    "id": index,
                    "node_id": node_id,
                    "status": "fail",
                    "issues": ["missing_node"],
                }
            )
            continue

        chapter_id, section_id = resolve_context(node_id, id_to_node)
        normalized_query = normalize_query(query)
        issues: List[str] = []
        status = "pass"

        if normalized_query in normalized_queries_seen:
            issues.append(f"duplicate_query_with_entry_{normalized_queries_seen[normalized_query]}")
            status = "warn"
        else:
            normalized_queries_seen[normalized_query] = index

        if node_id in node_ids_seen:
            issues.append(f"duplicate_node_with_entry_{node_ids_seen[node_id]}")
            status = "warn"
        else:
            node_ids_seen[node_id] = index

        title = str(node.get("title") or "")
        number = str(node.get("number") or "")
        if title and len(title_to_node_ids.get(title, [])) > 1 and not query_has_disambiguating_context(query, node_id, id_to_node):
            issues.append("ambiguous_title")
            status = "warn"

        if not str(node.get("content_summary") or "").strip():
            issues.append("missing_content_summary")
            status = "warn"

        if not str(node.get("content") or "").strip() and not node.get("table"):
            issues.append("missing_content_and_table")
            status = "warn"

        dataset.append(
            {
                "id": index,
                "query": query,
                "description": str(spec.get("description") or query),
                "difficulty": difficulty,
                "category": category,
                "benchmark": "user_guide",
                "source_blueprint": str(BLUEPRINT_PATH.relative_to(PROJECT_ROOT)),
                "target_nodes": [
                    {
                        "node_id": node_id,
                        "number": number,
                        "title": title,
                        "canonical_id": node_id,
                        "section_id": section_id,
                        "chapter_id": chapter_id,
                    }
                ],
            }
        )
        per_entry_audit.append(
            {
                "id": index,
                "node_id": node_id,
                "number": number,
                "title": title,
                "status": status,
                "issues": issues,
            }
        )

    return dataset, per_entry_audit


def build_audit_payload(
    dataset: List[Dict[str, object]],
    per_entry_audit: List[Dict[str, object]],
) -> Dict[str, object]:
    status_counter = Counter(row["status"] for row in per_entry_audit)
    difficulty_distribution = Counter(entry["difficulty"] for entry in dataset)
    category_distribution = Counter(entry["category"] for entry in dataset)
    chapter_distribution = Counter(
        target.get("chapter_id")
        for entry in dataset
        for target in entry.get("target_nodes", [])
        if target.get("chapter_id")
    )
    section_distribution = Counter(
        target.get("section_id")
        for entry in dataset
        for target in entry.get("target_nodes", [])
        if target.get("section_id")
    )
    query_lengths = [len(str(entry["query"]).split()) for entry in dataset]

    duplicate_queries = [
        row for row in per_entry_audit
        if any(issue.startswith("duplicate_query_with_entry_") for issue in row["issues"])
    ]
    duplicate_nodes = [
        row for row in per_entry_audit
        if any(issue.startswith("duplicate_node_with_entry_") for issue in row["issues"])
    ]
    ambiguous_titles = [
        row for row in per_entry_audit
        if "ambiguous_title" in row["issues"]
    ]

    return {
        "metadata": {
            "blueprint_path": str(BLUEPRINT_PATH),
            "graph_path": str(GRAPH_PATH),
            "dataset_path": str(DATASET_PATH),
            "total_entries": len(dataset),
        },
        "summary": {
            "pass": status_counter.get("pass", 0),
            "warn": status_counter.get("warn", 0),
            "fail": status_counter.get("fail", 0),
            "difficulty_distribution": dict(sorted(difficulty_distribution.items())),
            "category_distribution": dict(sorted(category_distribution.items())),
            "chapter_distribution": dict(sorted(chapter_distribution.items())),
            "section_count": len(section_distribution),
            "avg_query_length": mean(query_lengths) if query_lengths else 0.0,
            "min_query_length": min(query_lengths) if query_lengths else 0,
            "max_query_length": max(query_lengths) if query_lengths else 0,
            "duplicate_query_count": len(duplicate_queries),
            "duplicate_node_count": len(duplicate_nodes),
            "ambiguous_title_count": len(ambiguous_titles),
        },
        "checks": {
            "duplicate_queries": duplicate_queries,
            "duplicate_nodes": duplicate_nodes,
            "ambiguous_titles": ambiguous_titles,
        },
        "per_entry_audit": per_entry_audit,
    }


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_summary(path: Path, dataset: List[Dict[str, object]], audit: Dict[str, object]) -> None:
    summary = audit["summary"]
    lines = [
        "# User Guide Retrieval Audit Summary",
        "",
        f"- Graph path: `{GRAPH_PATH}`",
        f"- Blueprint path: `{BLUEPRINT_PATH}`",
        f"- Dataset size: `{len(dataset)}`",
        f"- Audit status: `{summary['pass']} pass / {summary['warn']} warn / {summary['fail']} fail`",
        "",
        "## Coverage",
        "",
        f"- Unique target sections: `{summary['section_count']}`",
        f"- Average query length: `{summary['avg_query_length']:.1f}` words",
        f"- Query length range: `{summary['min_query_length']} - {summary['max_query_length']}` words",
        "",
        "## Difficulty Distribution",
        "",
    ]

    for difficulty, count in summary["difficulty_distribution"].items():
        lines.append(f"- `{difficulty}`: `{count}`")

    lines.extend([
        "",
        "## Category Distribution",
        "",
    ])
    for category, count in summary["category_distribution"].items():
        lines.append(f"- `{category}`: `{count}`")

    lines.extend([
        "",
        "## Chapter Coverage",
        "",
    ])
    for chapter_id, count in summary["chapter_distribution"].items():
        lines.append(f"- `{chapter_id}`: `{count}`")

    lines.extend([
        "",
        "## Audit Notes",
        "",
        f"- Duplicate queries: `{summary['duplicate_query_count']}`",
        f"- Duplicate target nodes: `{summary['duplicate_node_count']}`",
        f"- Ambiguous titles: `{summary['ambiguous_title_count']}`",
    ])

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and audit the user-guide retrieval dataset.")
    parser.add_argument("--dataset-output", default=str(DATASET_PATH), help="Path to the generated dataset JSON.")
    parser.add_argument("--audit-output", default=str(AUDIT_PATH), help="Path to the generated audit JSON.")
    parser.add_argument("--summary-output", default=str(SUMMARY_PATH), help="Path to the generated markdown summary.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    nodes = load_graph()
    blueprint = load_blueprint()
    dataset, per_entry_audit = build_dataset(blueprint, nodes)
    audit_payload = build_audit_payload(dataset, per_entry_audit)

    dataset_output = Path(args.dataset_output).resolve()
    audit_output = Path(args.audit_output).resolve()
    summary_output = Path(args.summary_output).resolve()

    write_json(dataset_output, dataset)
    write_json(audit_output, audit_payload)
    write_summary(summary_output, dataset, audit_payload)

    print(f"Generated dataset: {dataset_output}")
    print(f"Generated audit: {audit_output}")
    print(f"Generated summary: {summary_output}")
    print(
        "Audit status: "
        f"{audit_payload['summary']['pass']} pass / "
        f"{audit_payload['summary']['warn']} warn / "
        f"{audit_payload['summary']['fail']} fail"
    )


if __name__ == "__main__":
    main()
