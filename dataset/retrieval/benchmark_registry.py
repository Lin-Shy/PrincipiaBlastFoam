"""
Benchmark registry for retrieval evaluation datasets and outputs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_DIR = PROJECT_ROOT / "dataset" / "retrieval"
BENCHMARKS_DIR = RETRIEVAL_DIR / "benchmarks"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "retrieval_method" / "results"


BENCHMARK_CONFIGS: Dict[str, Dict[str, object]] = {
    "case_content": {
        "label": "Case Content",
        "default_dataset": BENCHMARKS_DIR / "case_content" / "blastfoam_retrieval_validation_dataset_strict.json",
        "default_results_dir": RESULTS_DIR / "case_content",
        "knowledge_graph_module": PROJECT_ROOT / "principia_ai" / "tools" / "case_content_knowledge_graph_tool.py",
        "knowledge_graph_class": "CaseContentKnowledgeGraphRetriever",
        "summary_metrics": (
            "mrr",
            "hit@1",
            "hit@3",
            "hit@5",
            "case_hit@5",
            "precision@5",
            "recall@5",
            "avg_retrieval_time",
        ),
        "supports_embedding": True,
    },
    "user_guide": {
        "label": "User Guide",
        "default_dataset": BENCHMARKS_DIR / "user_guide" / "user_guide_retrieval_validation_dataset.json",
        "default_results_dir": RESULTS_DIR / "user_guide",
        "knowledge_graph_module": PROJECT_ROOT / "principia_ai" / "tools" / "user_guide_knowledge_graph_tool.py",
        "knowledge_graph_class": "UserGuideKnowledgeGraphRetriever",
        "summary_metrics": (
            "mrr",
            "hit@1",
            "hit@3",
            "hit@5",
            "section_hit@5",
            "chapter_hit@5",
            "precision@5",
            "recall@5",
            "avg_retrieval_time",
        ),
        "supports_embedding": True,
        "default_embedding_level": "node",
    },
}


def list_benchmarks() -> tuple[str, ...]:
    return tuple(BENCHMARK_CONFIGS.keys())


def get_benchmark_config(benchmark: str) -> Dict[str, object]:
    try:
        config = BENCHMARK_CONFIGS[benchmark]
    except KeyError as exc:
        supported = ", ".join(list_benchmarks())
        raise ValueError(f"Unsupported benchmark '{benchmark}'. Supported: {supported}") from exc

    return config
