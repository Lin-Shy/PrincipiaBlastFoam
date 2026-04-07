from dataset.retrieval.strict_retrieval_evaluator import StrictRetrievalEvaluator
import json
from pathlib import Path


CASE_CONTENT_DATASET = "dataset/retrieval/benchmarks/case_content/blastfoam_retrieval_validation_dataset_strict.json"
USER_GUIDE_DATASET = "dataset/retrieval/benchmarks/user_guide/user_guide_retrieval_validation_dataset.json"


def test_case_content_result_normalization():
    evaluator = StrictRetrievalEvaluator(CASE_CONTENT_DATASET)

    result = evaluator.normalize_result(
        "blastXiFoam/deflagrationToDetonationTransition::system/controlDict"
    )

    assert result is not None
    assert result.canonical_id == "blastXiFoam/deflagrationToDetonationTransition::system/controlDict"
    assert result.case_path == "blastXiFoam/deflagrationToDetonationTransition"
    assert result.file_path == "system/controlDict"


def test_user_guide_result_normalization_accepts_section_numbers():
    evaluator = StrictRetrievalEvaluator(USER_GUIDE_DATASET)

    result = evaluator.normalize_result("10.3.6")

    assert result is not None
    assert result.canonical_id == "method10.3.6"
    assert result.section_id == "sec10.3"
    assert result.chapter_id == "ch10"


def test_user_guide_metrics_include_section_and_chapter_hits():
    evaluator = StrictRetrievalEvaluator(USER_GUIDE_DATASET)

    def retrieval_function(query: str):
        if "RK4" in query:
            return ["method10.3.6"]
        return []

    results = evaluator.evaluate(retrieval_function, k_values=(1,))

    aggregate = results["aggregate_metrics"]
    assert "section_hit@1" in aggregate
    assert "chapter_hit@1" in aggregate
    expected_total = len(json.loads(Path(USER_GUIDE_DATASET).read_text(encoding="utf-8")))
    assert aggregate["total_queries"] == expected_total


def test_user_guide_dataset_has_broad_coverage():
    dataset = json.loads(Path(USER_GUIDE_DATASET).read_text(encoding="utf-8"))

    assert len(dataset) >= 80
    categories = {entry["category"] for entry in dataset}
    assert "equation_of_state" in categories
    assert "numerics" in categories
    assert "solvers" in categories
