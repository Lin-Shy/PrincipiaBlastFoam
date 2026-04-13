from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
FIG_ROOT_DIR = OUTPUT_DIR / "figures"
TABLE_ROOT_DIR = OUTPUT_DIR / "tables"
FIG_DIR = FIG_ROOT_DIR / "en"
TABLE_DIR = TABLE_ROOT_DIR / "en"
SUMMARY_PATH = OUTPUT_DIR / "summary_stats_en.json"
CURRENT_LANGUAGE = "en"

CASE_CONTENT_EMBEDDING = (
    ROOT_DIR / "experiments/retrieval_method/results/embedding_retrieval_file_20260407_132222.json"
)
CASE_CONTENT_KG = (
    ROOT_DIR / "experiments/retrieval_method/results/knowledge_graph_retrieval_20260407_140404.json"
)
USER_GUIDE_EMBEDDING = (
    ROOT_DIR / "experiments/retrieval_method/results/user_guide/embedding_retrieval_node_20260407_151152.json"
)
USER_GUIDE_KG = (
    ROOT_DIR / "experiments/retrieval_method/results/user_guide/knowledge_graph_retrieval_20260407_154114.json"
)

EMBEDDING_COLOR = "#0F766E"
KG_COLOR = "#C2410C"
ACCENT_BLUE = "#1D4ED8"
ACCENT_RED = "#B91C1C"
LIGHT_BG = "#F8FAFC"
GRID_COLOR = "#CBD5E1"
TEXT_COLOR = "#0F172A"

FONT_FAMILIES = {
    "en": ["DejaVu Sans", "Arial", "Liberation Sans", "sans-serif"],
    "zh": ["Noto Sans CJK SC", "Source Han Sans SC", "Droid Sans Fallback", "SimHei", "sans-serif"],
}
ZH_FONT_PATHS = [
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
]

FS_SUPERTITLE = 32
FS_TITLE = 24
FS_SUBTITLE = 18
FS_BODY = 16
FS_NOTE = 15
FS_BOX = 18
FS_CARD_LABEL = 19
FS_CARD_VALUE = 40
FS_ANNOT = 14
FS_TICK = 14

TRANSLATIONS = {
    "en": {
        "system_arch_title": "PrincipiaBlastFoam System Architecture",
        "system_arch_subtitle": "Midterm-ready view of the current research system: multi-agent workflow + knowledge-enhanced retrieval + validation.",
        "user_request": "User Request",
        "orchestrator": "Orchestrator\n(ReAct planner)",
        "physics_analyst": "Physics Analyst",
        "case_setup": "Case Setup",
        "execution_agent": "Execution Agent",
        "post_processing": "Post-Processing",
        "reviewer": "Reviewer",
        "case_content_kg_box": "Case Content KG\n28 cases / 542 files / 3420 vars",
        "user_guide_kg_box": "User Guide KG\n233 structured nodes",
        "validator_box": "End-to-End Validator\nphysics validity + executability",
        "knowledge_resources_note": "Knowledge resources drive planning and retrieval.",
        "validation_note": "Validation framework is implemented and ready for larger-scale batch experiments.",
        "retrieval_title": "Two Retrieval Pipelines Used in the Midterm Evaluation",
        "retrieval_subtitle": "The evaluation compares a vector baseline with a graph-guided, reasoning-based retriever.",
        "embedding_baseline": "Embedding Baseline",
        "kg_retrieval": "Knowledge Graph Retrieval",
        "query": "Query",
        "vectorization": "Vectorization",
        "faiss_search": "FAISS Search",
        "topk_results": "Top-k Results",
        "left_pipeline_note": "Fast and simple, but weak at exact file/node disambiguation.",
        "query_task_intent": "Query + task intent",
        "react_action_selection": "ReAct action selection",
        "graph_search_inspect": "Graph search / inspect",
        "graph_reranking": "Graph-aware reranking",
        "structured_output": "Structured top-k output",
        "right_pipeline_note": "Slower, but much stronger at case/file localization and fine-grained node ranking.",
        "knowledge_graph": "Knowledge\nGraph",
        "asset_title": "Knowledge Assets and Benchmark Scale",
        "tutorial_cases": "Tutorial cases",
        "file_nodes": "File nodes",
        "variable_nodes": "Variable nodes",
        "user_guide_nodes": "User guide nodes",
        "case_benchmark_queries": "Case benchmark queries",
        "guide_benchmark_queries": "Guide benchmark queries",
        "case_content_difficulty_split": "Case Content Difficulty Split",
        "user_guide_difficulty_split": "User Guide Difficulty Split",
        "queries": "Queries",
        "basic": "basic",
        "intermediate": "intermediate",
        "advanced": "advanced",
        "case_content_overall_title": "Case Content Benchmark: KG Greatly Improves Exact File Retrieval",
        "accuracy_metrics": "Accuracy Metrics",
        "average_retrieval_time": "Average Retrieval Time",
        "score_pct": "Score (%)",
        "seconds_per_query": "Seconds / query",
        "embedding_legend": "Embedding",
        "kg_legend": "Knowledge Graph",
        "case_granularity_title": "Case Content Granularity Gap at k=5",
        "exact_file_hit5": "Exact file Hit@5",
        "case_hit5": "Case Hit@5",
        "file_family_hit5": "File family Hit@5",
        "case_granularity_note": "Embedding often finds the right case, but not the exact target file.\nKG retrieval narrows the gap between case-level and exact-file retrieval.",
        "case_difficulty_title": "Case Content Benchmark: Improvement Holds Across All Difficulty Levels",
        "mrr_by_difficulty": "MRR by Difficulty",
        "hit5_by_difficulty": "Hit@5 by Difficulty",
        "user_guide_overall_title": "User Guide Benchmark: KG Re-ranking Improves Fine-Grained Node Retrieval",
        "user_guide_granularity_title": "User Guide Benchmark: Section Localization Is Strong, Exact Node Ranking Gets Better with KG",
        "exact_node1": "Exact node@1",
        "section1": "Section@1",
        "chapter1": "Chapter@1",
        "granularity_top1": "Granularity at Top-1",
        "top1_accuracy_by_difficulty": "Top-1 Accuracy by Difficulty",
        "tradeoff_title": "Accuracy-Efficiency Trade-off of the Current Retrieval Methods",
        "tradeoff_xlabel": "Average retrieval time (seconds/query, log scale)",
        "tradeoff_ylabel": "MRR (%)",
        "tradeoff_note": "Case-content KG brings the largest accuracy gain.\nUser-guide KG improves exact node ranking with moderate latency increase.",
        "case_embedding_label": "Case Embedding",
        "case_kg_label": "Case KG",
        "guide_embedding_label": "Guide Embedding",
        "guide_kg_label": "Guide KG",
        "top_gain_title": "Where the Graph-Based Method Helps the Most",
        "case_top_gains": "Case Content: Top Category Gains",
        "guide_top_gains": "User Guide: Top Category Gains",
        "abs_gain_hit5": "Absolute gain in Hit@5 (percentage points)",
        "abs_gain_hit1": "Absolute gain in Hit@1 (percentage points)",
        "asset_case_content_kg_files": "Case content KG files",
        "asset_case_nodes": "Case nodes",
        "asset_file_nodes": "File nodes",
        "asset_variable_nodes": "Variable nodes",
        "asset_case_content_kg_edges": "Case content KG edges",
        "asset_user_guide_nodes": "User guide nodes",
        "asset_case_content_benchmark_queries": "Case content benchmark queries",
        "asset_user_guide_benchmark_queries": "User guide benchmark queries",
    },
    "zh": {
        "system_arch_title": "PrincipiaBlastFoam 系统架构",
        "system_arch_subtitle": "面向中期答辩的系统视图：多智能体工作流 + 知识增强检索 + 自动验证。",
        "user_request": "用户需求",
        "orchestrator": "协调智能体\n（ReAct 规划器）",
        "physics_analyst": "物理分析智能体",
        "case_setup": "案例配置智能体",
        "execution_agent": "执行智能体",
        "post_processing": "后处理智能体",
        "reviewer": "审查智能体",
        "case_content_kg_box": "案例内容知识图谱\n28 个案例 / 542 个文件 / 3420 个变量",
        "user_guide_kg_box": "用户手册知识图谱\n233 个结构化节点",
        "validator_box": "端到端验证器\n物理合理性 + 可执行性",
        "knowledge_resources_note": "知识资源为任务规划和检索提供支撑。",
        "validation_note": "验证框架已经实现，可继续用于后续批量实验。",
        "retrieval_title": "中期评测中的两类检索流程",
        "retrieval_subtitle": "当前实验对比了向量检索基线与图谱引导的推理式检索方法。",
        "embedding_baseline": "Embedding 基线",
        "kg_retrieval": "知识图谱检索",
        "query": "查询输入",
        "vectorization": "向量化",
        "faiss_search": "FAISS 检索",
        "topk_results": "Top-k 结果",
        "left_pipeline_note": "速度快、结构简单，但精确定位文件或节点的能力较弱。",
        "query_task_intent": "查询 + 任务意图",
        "react_action_selection": "ReAct 动作决策",
        "graph_search_inspect": "图谱搜索 / 节点检查",
        "graph_reranking": "图谱感知重排",
        "structured_output": "结构化 Top-k 输出",
        "right_pipeline_note": "速度更慢，但在案例/文件定位和细粒度节点排序上更强。",
        "knowledge_graph": "知识\n图谱",
        "asset_title": "知识资产规模与评测集规模",
        "tutorial_cases": "教程案例数",
        "file_nodes": "文件节点数",
        "variable_nodes": "变量节点数",
        "user_guide_nodes": "用户手册节点数",
        "case_benchmark_queries": "案例内容评测查询数",
        "guide_benchmark_queries": "用户手册评测查询数",
        "case_content_difficulty_split": "案例内容任务难度分布",
        "user_guide_difficulty_split": "用户手册任务难度分布",
        "queries": "查询数",
        "basic": "基础",
        "intermediate": "中等",
        "advanced": "复杂",
        "case_content_overall_title": "案例内容评测：知识图谱显著提升精确文件检索能力",
        "accuracy_metrics": "准确性指标",
        "average_retrieval_time": "平均检索时间",
        "score_pct": "分数（%）",
        "seconds_per_query": "秒 / 查询",
        "embedding_legend": "Embedding",
        "kg_legend": "知识图谱",
        "case_granularity_title": "案例内容任务在 k=5 下的定位粒度差异",
        "exact_file_hit5": "精确文件 Hit@5",
        "case_hit5": "案例命中 Hit@5",
        "file_family_hit5": "文件族命中 Hit@5",
        "case_granularity_note": "Embedding 往往能先找到相关案例，但难以进一步锁定目标文件。\n知识图谱检索显著缩小了“案例级命中”和“文件级命中”之间的差距。",
        "case_difficulty_title": "案例内容评测：不同难度下均存在明显提升",
        "mrr_by_difficulty": "不同难度下的 MRR",
        "hit5_by_difficulty": "不同难度下的 Hit@5",
        "user_guide_overall_title": "用户手册评测：知识图谱重排提升细粒度节点定位能力",
        "user_guide_granularity_title": "用户手册评测：章节定位已较强，精确节点排序继续提升",
        "exact_node1": "精确节点@1",
        "section1": "小节@1",
        "chapter1": "章节@1",
        "granularity_top1": "Top-1 粒度表现",
        "top1_accuracy_by_difficulty": "不同难度下的 Top-1 准确率",
        "tradeoff_title": "当前检索方法的精度-效率权衡",
        "tradeoff_xlabel": "平均检索时间（秒 / 查询，对数坐标）",
        "tradeoff_ylabel": "MRR（%）",
        "tradeoff_note": "案例内容任务中，知识图谱方法带来了最明显的精度提升。\n在用户手册任务中，也能在较小额外耗时下改善精确节点排序。",
        "case_embedding_label": "案例-Embedding",
        "case_kg_label": "案例-知识图谱",
        "guide_embedding_label": "手册-Embedding",
        "guide_kg_label": "手册-知识图谱",
        "top_gain_title": "知识图谱方法收益最明显的任务类别",
        "case_top_gains": "案例内容：提升最大的类别",
        "guide_top_gains": "用户手册：提升最大的类别",
        "abs_gain_hit5": "Hit@5 绝对增益（百分点）",
        "abs_gain_hit1": "Hit@1 绝对增益（百分点）",
        "asset_case_content_kg_files": "案例内容知识图谱文件数",
        "asset_case_nodes": "案例节点数",
        "asset_file_nodes": "文件节点数",
        "asset_variable_nodes": "变量节点数",
        "asset_case_content_kg_edges": "案例内容知识图谱关系数",
        "asset_user_guide_nodes": "用户手册节点数",
        "asset_case_content_benchmark_queries": "案例内容评测查询数",
        "asset_user_guide_benchmark_queries": "用户手册评测查询数",
    },
}

CATEGORY_TRANSLATIONS = {
    "zh": {
        "equation_of_state": "状态方程",
        "multiphase": "多相流",
        "structural_mechanics": "结构力学",
        "numerical_schemes": "数值格式",
        "turbulence_model": "湍流模型",
        "thermodynamics": "热力学",
        "time_control": "时间控制",
        "output_control": "输出控制",
        "initial_conditions": "初始条件",
        "boundary_conditions": "边界条件",
        "interfacial_models": "界面模型",
        "multiphase_models": "多相模型",
        "amr": "自适应网格",
        "governing_equations": "控制方程",
        "thermodynamic_models": "热力学模型",
        "diameter_models": "直径模型",
        "heat_transfer": "传热模型",
        "granular_models": "颗粒模型",
        "transport_models": "输运模型",
    }
}


def t(key: str) -> str:
    return TRANSLATIONS[CURRENT_LANGUAGE][key]


def display_label(value: str) -> str:
    if value in TRANSLATIONS[CURRENT_LANGUAGE]:
        return TRANSLATIONS[CURRENT_LANGUAGE][value]
    return CATEGORY_TRANSLATIONS.get(CURRENT_LANGUAGE, {}).get(value, value)


def configure_language(language: str):
    global CURRENT_LANGUAGE, FIG_DIR, TABLE_DIR, SUMMARY_PATH
    CURRENT_LANGUAGE = language
    FIG_DIR = FIG_ROOT_DIR / language
    TABLE_DIR = TABLE_ROOT_DIR / language
    SUMMARY_PATH = OUTPUT_DIR / f"summary_stats_{language}.json"
    font_family = FONT_FAMILIES[language]
    if language == "zh":
        for font_path in ZH_FONT_PATHS:
            if font_path.exists():
                font_manager.fontManager.addfont(str(font_path))
                font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
                font_family = [font_name]
                break
    rcParams.update(
        {
            "font.family": font_family,
            "font.sans-serif": font_family,
            "font.size": FS_BODY,
            "axes.titlesize": FS_TITLE,
            "axes.labelsize": FS_BODY,
            "xtick.labelsize": FS_TICK,
            "ytick.labelsize": FS_TICK,
            "legend.fontsize": FS_BODY,
            "axes.unicode_minus": False,
        }
    )


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: float) -> float:
    return round(value * 100.0, 2)


def configure_axis(ax):
    ax.set_facecolor("white")
    ax.grid(axis="y", color=GRID_COLOR, linestyle="--", linewidth=0.8, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=FS_TICK)


def save_figure(fig, path: Path):
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def annotate_bars(ax, bars, fmt="{:.2f}", offset=1.2, fontsize=FS_ANNOT):
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + offset,
            fmt.format(height),
            ha="center",
            va="bottom",
            fontsize=fontsize,
            color=TEXT_COLOR,
        )


def annotate_barh(ax, bars, fmt="{:.2f}", offset=1.0, fontsize=FS_ANNOT):
    for bar in bars:
        width = bar.get_width()
        ax.text(
            width + offset,
            bar.get_y() + bar.get_height() / 2,
            fmt.format(width),
            ha="left",
            va="center",
            fontsize=fontsize,
            color=TEXT_COLOR,
        )


def add_box(ax, xy, width, height, label, fc, ec="#CBD5E1", fontsize=FS_BOX):
    box = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        facecolor=fc,
        edgecolor=ec,
        linewidth=1.5,
    )
    ax.add_patch(box)
    x = xy[0] + width / 2
    y = xy[1] + height / 2
    ax.text(x, y, label, ha="center", va="center", fontsize=fontsize, color=TEXT_COLOR, weight="bold")
    return box


def connect(ax, start, end, color="#475569", style="-|>", lw=1.8):
    arrow = FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=16, linewidth=lw, color=color)
    ax.add_patch(arrow)


def collect_asset_summary() -> Dict[str, object]:
    case_kg_dir = ROOT_DIR / "data/knowledge_graph/case_content_knowledge_graph"
    case_nodes = file_nodes = variable_nodes = edges = 0
    graph_files = 0

    for path in sorted(case_kg_dir.glob("*.json")):
        data = load_json(path)
        graph_files += 1
        edges += len(data.get("relationships", []))
        for node in data.get("nodes", []):
            label = node.get("label") or node.get("type") or ""
            if label == "Case":
                case_nodes += 1
            elif label == "File":
                file_nodes += 1
            elif label == "Variable":
                variable_nodes += 1

    user_guide_nodes = load_json(
        ROOT_DIR / "data/knowledge_graph/user_guide_knowledge_graph/user_guide_knowledge_graph.json"
    )
    case_dataset = load_json(
        ROOT_DIR / "dataset/retrieval/benchmarks/case_content/blastfoam_retrieval_validation_dataset_strict.json"
    )
    guide_dataset = load_json(
        ROOT_DIR / "dataset/retrieval/benchmarks/user_guide/user_guide_retrieval_validation_dataset.json"
    )

    return {
        "case_graph_files": graph_files,
        "case_nodes": case_nodes,
        "file_nodes": file_nodes,
        "variable_nodes": variable_nodes,
        "case_graph_edges": edges,
        "user_guide_nodes": len(user_guide_nodes),
        "user_guide_semantic_types": Counter(node.get("semantic_type") or "Unknown" for node in user_guide_nodes),
        "case_dataset_size": len(case_dataset),
        "guide_dataset_size": len(guide_dataset),
        "case_difficulty": Counter(item.get("difficulty", "unknown") for item in case_dataset),
        "guide_difficulty": Counter(item.get("difficulty", "unknown") for item in guide_dataset),
    }


def load_metrics() -> Dict[str, Dict[str, object]]:
    return {
        "case_content_embedding": load_json(CASE_CONTENT_EMBEDDING)["aggregate_metrics"],
        "case_content_kg": load_json(CASE_CONTENT_KG)["aggregate_metrics"],
        "user_guide_embedding": load_json(USER_GUIDE_EMBEDDING)["aggregate_metrics"],
        "user_guide_kg": load_json(USER_GUIDE_KG)["aggregate_metrics"],
    }


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_tables(asset_summary: Dict[str, object], metrics: Dict[str, Dict[str, object]]):
    asset_rows = [
        {"item": t("asset_case_content_kg_files"), "value": asset_summary["case_graph_files"]},
        {"item": t("asset_case_nodes"), "value": asset_summary["case_nodes"]},
        {"item": t("asset_file_nodes"), "value": asset_summary["file_nodes"]},
        {"item": t("asset_variable_nodes"), "value": asset_summary["variable_nodes"]},
        {"item": t("asset_case_content_kg_edges"), "value": asset_summary["case_graph_edges"]},
        {"item": t("asset_user_guide_nodes"), "value": asset_summary["user_guide_nodes"]},
        {"item": t("asset_case_content_benchmark_queries"), "value": asset_summary["case_dataset_size"]},
        {"item": t("asset_user_guide_benchmark_queries"), "value": asset_summary["guide_dataset_size"]},
    ]
    write_csv(TABLE_DIR / "asset_summary.csv", asset_rows, ["item", "value"])

    retrieval_rows = []
    for name, payload in [
        ("case_content_embedding", metrics["case_content_embedding"]),
        ("case_content_kg", metrics["case_content_kg"]),
        ("user_guide_embedding", metrics["user_guide_embedding"]),
        ("user_guide_kg", metrics["user_guide_kg"]),
    ]:
        retrieval_rows.append(
            {
                "method": name,
                "total_queries": payload["total_queries"],
                "mrr": round(payload["mrr"], 4),
                "hit@1": round(payload["hit@1"], 4),
                "hit@3": round(payload["hit@3"], 4),
                "hit@5": round(payload["hit@5"], 4),
                "avg_retrieval_time": round(payload["avg_retrieval_time"], 4),
            }
        )
    write_csv(
        TABLE_DIR / "retrieval_overview_metrics.csv",
        retrieval_rows,
        ["method", "total_queries", "mrr", "hit@1", "hit@3", "hit@5", "avg_retrieval_time"],
    )

    case_difficulty_rows = []
    for difficulty in ["basic", "intermediate", "advanced"]:
        emb = metrics["case_content_embedding"]["by_difficulty"][difficulty]
        kg = metrics["case_content_kg"]["by_difficulty"][difficulty]
        case_difficulty_rows.append(
            {
                "difficulty": difficulty,
                "count": int(kg["count"]),
                "embedding_mrr": round(emb["mrr"], 4),
                "kg_mrr": round(kg["mrr"], 4),
                "embedding_hit@5": round(emb["hit@5"], 4),
                "kg_hit@5": round(kg["hit@5"], 4),
            }
        )
    write_csv(
        TABLE_DIR / "case_content_by_difficulty.csv",
        case_difficulty_rows,
        ["difficulty", "count", "embedding_mrr", "kg_mrr", "embedding_hit@5", "kg_hit@5"],
    )

    guide_difficulty_rows = []
    for difficulty in ["basic", "intermediate", "advanced"]:
        emb = metrics["user_guide_embedding"]["by_difficulty"][difficulty]
        kg = metrics["user_guide_kg"]["by_difficulty"][difficulty]
        guide_difficulty_rows.append(
            {
                "difficulty": difficulty,
                "count": int(kg["count"]),
                "embedding_mrr": round(emb["mrr"], 4),
                "kg_mrr": round(kg["mrr"], 4),
                "embedding_hit@1": round(emb["hit@1"], 4),
                "kg_hit@1": round(kg["hit@1"], 4),
            }
        )
    write_csv(
        TABLE_DIR / "user_guide_by_difficulty.csv",
        guide_difficulty_rows,
        ["difficulty", "count", "embedding_mrr", "kg_mrr", "embedding_hit@1", "kg_hit@1"],
    )

    case_gain_rows = []
    for category, kg_payload in metrics["case_content_kg"]["by_category"].items():
        emb_payload = metrics["case_content_embedding"]["by_category"].get(category)
        if not emb_payload:
            continue
        case_gain_rows.append(
            {
                "category": category,
                "count": int(kg_payload["count"]),
                "embedding_hit@5": round(emb_payload["hit@5"], 4),
                "kg_hit@5": round(kg_payload["hit@5"], 4),
                "gain_hit@5": round(kg_payload["hit@5"] - emb_payload["hit@5"], 4),
            }
        )
    case_gain_rows.sort(key=lambda row: row["gain_hit@5"], reverse=True)
    write_csv(
        TABLE_DIR / "case_content_top_category_improvements.csv",
        case_gain_rows[:10],
        ["category", "count", "embedding_hit@5", "kg_hit@5", "gain_hit@5"],
    )

    guide_gain_rows = []
    for category, kg_payload in metrics["user_guide_kg"]["by_category"].items():
        emb_payload = metrics["user_guide_embedding"]["by_category"].get(category)
        if not emb_payload:
            continue
        guide_gain_rows.append(
            {
                "category": category,
                "count": int(kg_payload["count"]),
                "embedding_hit@1": round(emb_payload["hit@1"], 4),
                "kg_hit@1": round(kg_payload["hit@1"], 4),
                "gain_hit@1": round(kg_payload["hit@1"] - emb_payload["hit@1"], 4),
            }
        )
    guide_gain_rows.sort(key=lambda row: row["gain_hit@1"], reverse=True)
    write_csv(
        TABLE_DIR / "user_guide_top_category_improvements.csv",
        guide_gain_rows[:10],
        ["category", "count", "embedding_hit@1", "kg_hit@1", "gain_hit@1"],
    )


def plot_system_architecture():
    fig, ax = plt.subplots(figsize=(16, 9), facecolor=LIGHT_BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.04, 0.95, t("system_arch_title"), fontsize=FS_SUPERTITLE, weight="bold", color=TEXT_COLOR)
    ax.text(
        0.04,
        0.91,
        t("system_arch_subtitle"),
        fontsize=FS_BODY,
        color="#334155",
    )

    add_box(ax, (0.05, 0.62), 0.17, 0.14, t("user_request"), "#E0F2FE")
    add_box(ax, (0.29, 0.6), 0.2, 0.18, t("orchestrator"), "#DBEAFE")

    specialists = [
        ((0.58, 0.78), t("physics_analyst"), "#DCFCE7"),
        ((0.78, 0.78), t("case_setup"), "#DCFCE7"),
        ((0.58, 0.56), t("execution_agent"), "#FEF3C7"),
        ((0.78, 0.56), t("post_processing"), "#FEF3C7"),
        ((0.68, 0.34), t("reviewer"), "#FDE68A"),
    ]
    for xy, label, color in specialists:
        add_box(ax, xy, 0.15, 0.12, label, color, fontsize=FS_SUBTITLE)

    add_box(ax, (0.09, 0.28), 0.22, 0.14, t("case_content_kg_box"), "#F1F5F9", fontsize=FS_BODY)
    add_box(ax, (0.35, 0.28), 0.22, 0.14, t("user_guide_kg_box"), "#F1F5F9", fontsize=FS_BODY)
    add_box(ax, (0.61, 0.12), 0.24, 0.14, t("validator_box"), "#F1F5F9", fontsize=FS_BODY)

    connect(ax, (0.22, 0.69), (0.29, 0.69))
    connect(ax, (0.49, 0.73), (0.58, 0.83))
    connect(ax, (0.49, 0.69), (0.58, 0.62))
    connect(ax, (0.49, 0.66), (0.78, 0.83))
    connect(ax, (0.49, 0.62), (0.78, 0.62))
    connect(ax, (0.65, 0.78), (0.73, 0.46))
    connect(ax, (0.85, 0.56), (0.79, 0.26))
    connect(ax, (0.38, 0.42), (0.38, 0.6))
    connect(ax, (0.46, 0.42), (0.46, 0.6))
    connect(ax, (0.57, 0.35), (0.68, 0.35))
    connect(ax, (0.31, 0.35), (0.58, 0.35), style="->")
    connect(ax, (0.57, 0.35), (0.61, 0.19), style="->")

    ax.text(0.09, 0.22, t("knowledge_resources_note"), fontsize=FS_NOTE, color="#475569")
    ax.text(0.62, 0.08, t("validation_note"), fontsize=FS_NOTE, color="#475569")

    save_figure(fig, FIG_DIR / "01_system_architecture.png")


def plot_retrieval_pipelines():
    fig, ax = plt.subplots(figsize=(16, 9), facecolor=LIGHT_BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.04, 0.95, t("retrieval_title"), fontsize=FS_SUPERTITLE, weight="bold", color=TEXT_COLOR)
    ax.text(0.04, 0.91, t("retrieval_subtitle"), fontsize=FS_BODY, color="#334155")

    ax.text(0.22, 0.84, t("embedding_baseline"), fontsize=FS_TITLE, weight="bold", color=EMBEDDING_COLOR, ha="center")
    ax.text(0.74, 0.84, t("kg_retrieval"), fontsize=FS_TITLE, weight="bold", color=KG_COLOR, ha="center")

    left_boxes = [
        ((0.08, 0.68), t("query"), "#E6FFFA"),
        ((0.08, 0.50), t("vectorization"), "#E6FFFA"),
        ((0.08, 0.32), t("faiss_search"), "#E6FFFA"),
        ((0.08, 0.14), t("topk_results"), "#E6FFFA"),
    ]
    for xy, label, color in left_boxes:
        add_box(ax, xy, 0.28, 0.1, label, color, fontsize=FS_SUBTITLE)

    connect(ax, (0.22, 0.68), (0.22, 0.60))
    connect(ax, (0.22, 0.50), (0.22, 0.42))
    connect(ax, (0.22, 0.32), (0.22, 0.24))
    ax.text(0.22, 0.06, t("left_pipeline_note"), ha="center", fontsize=FS_NOTE, color="#475569")

    right_boxes = [
        ((0.56, 0.72), t("query_task_intent"), "#FFF7ED"),
        ((0.56, 0.56), t("react_action_selection"), "#FFF7ED"),
        ((0.56, 0.40), t("graph_search_inspect"), "#FFF7ED"),
        ((0.56, 0.24), t("graph_reranking"), "#FFF7ED"),
        ((0.56, 0.08), t("structured_output"), "#FFF7ED"),
    ]
    for xy, label, color in right_boxes:
        add_box(ax, xy, 0.32, 0.09, label, color, fontsize=FS_SUBTITLE)

    connect(ax, (0.72, 0.72), (0.72, 0.65))
    connect(ax, (0.72, 0.56), (0.72, 0.49))
    connect(ax, (0.72, 0.40), (0.72, 0.33))
    connect(ax, (0.72, 0.24), (0.72, 0.17))
    ax.text(0.72, 0.01, t("right_pipeline_note"), ha="center", fontsize=FS_NOTE, color="#475569")

    add_box(ax, (0.42, 0.53), 0.12, 0.16, t("knowledge_graph"), "#F1F5F9", fontsize=FS_SUBTITLE)
    connect(ax, (0.54, 0.61), (0.56, 0.61), style="->")
    connect(ax, (0.54, 0.50), (0.56, 0.45), style="->")

    save_figure(fig, FIG_DIR / "02_retrieval_pipelines.png")


def plot_asset_overview(asset_summary: Dict[str, object]):
    fig = plt.figure(figsize=(16, 11), facecolor=LIGHT_BG)
    gs = fig.add_gridspec(3, 6, height_ratios=[1.0, 1.0, 1.15], hspace=0.38, wspace=0.35)

    cards = [
        (t("tutorial_cases"), asset_summary["case_nodes"], "#DBEAFE"),
        (t("file_nodes"), asset_summary["file_nodes"], "#E0F2FE"),
        (t("variable_nodes"), asset_summary["variable_nodes"], "#DCFCE7"),
        (t("user_guide_nodes"), asset_summary["user_guide_nodes"], "#FEF3C7"),
        (t("case_benchmark_queries"), asset_summary["case_dataset_size"], "#FCE7F3"),
        (t("guide_benchmark_queries"), asset_summary["guide_dataset_size"], "#EDE9FE"),
    ]

    for idx, (label, value, color) in enumerate(cards):
        row = idx // 3
        col = (idx % 3) * 2
        ax = fig.add_subplot(gs[row, col:col + 2])
        ax.set_facecolor(color)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.text(0.05, 0.72, label, fontsize=FS_CARD_LABEL, weight="bold", color=TEXT_COLOR, transform=ax.transAxes)
        ax.text(0.05, 0.30, f"{value}", fontsize=FS_CARD_VALUE, weight="bold", color=TEXT_COLOR, transform=ax.transAxes)

    ax_left = fig.add_subplot(gs[2, 0:3], facecolor="white")
    ax_right = fig.add_subplot(gs[2, 3:6], facecolor="white")

    configure_axis(ax_left)
    configure_axis(ax_right)

    order = ["basic", "intermediate", "advanced"]
    left_vals = [asset_summary["case_difficulty"][item] for item in order]
    right_vals = [asset_summary["guide_difficulty"][item] for item in order]
    left_bars = ax_left.bar(order, left_vals, color=[ACCENT_BLUE, EMBEDDING_COLOR, KG_COLOR], alpha=0.9)
    right_bars = ax_right.bar(order, right_vals, color=[ACCENT_BLUE, EMBEDDING_COLOR, KG_COLOR], alpha=0.9)
    ax_left.set_title(t("case_content_difficulty_split"), fontsize=FS_SUBTITLE, weight="bold")
    ax_right.set_title(t("user_guide_difficulty_split"), fontsize=FS_SUBTITLE, weight="bold")
    ax_left.set_ylabel(t("queries"))
    ax_right.set_ylabel(t("queries"))
    ax_left.set_xticks(range(len(order)), [display_label(item) for item in order])
    ax_right.set_xticks(range(len(order)), [display_label(item) for item in order])
    annotate_bars(ax_left, left_bars, fmt="{:.0f}", offset=2.0)
    annotate_bars(ax_right, right_bars, fmt="{:.0f}", offset=1.5)

    fig.suptitle(t("asset_title"), fontsize=FS_SUPERTITLE, weight="bold", color=TEXT_COLOR, y=0.98)
    save_figure(fig, FIG_DIR / "03_asset_and_benchmark_overview.png")


def plot_case_content_overall(metrics: Dict[str, Dict[str, object]]):
    emb = metrics["case_content_embedding"]
    kg = metrics["case_content_kg"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 9.6), facecolor=LIGHT_BG, gridspec_kw={"width_ratios": [2.2, 1]})
    fig.subplots_adjust(top=0.76, wspace=0.18)

    metric_names = ["MRR", "Hit@1", "Hit@3", "Hit@5"]
    emb_vals = [pct(emb["mrr"]), pct(emb["hit@1"]), pct(emb["hit@3"]), pct(emb["hit@5"])]
    kg_vals = [pct(kg["mrr"]), pct(kg["hit@1"]), pct(kg["hit@3"]), pct(kg["hit@5"])]
    x = range(len(metric_names))
    width = 0.36

    ax = axes[0]
    configure_axis(ax)
    bars1 = ax.bar([i - width / 2 for i in x], emb_vals, width=width, color=EMBEDDING_COLOR, label=t("embedding_legend"))
    bars2 = ax.bar([i + width / 2 for i in x], kg_vals, width=width, color=KG_COLOR, label=t("kg_legend"))
    ax.set_xticks(list(x), metric_names)
    ax.set_ylim(0, 100)
    ax.set_ylabel(t("score_pct"))
    ax.set_title(t("accuracy_metrics"), fontsize=FS_TITLE, weight="bold")
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.03), ncol=2, borderaxespad=0.0)
    annotate_bars(ax, bars1)
    annotate_bars(ax, bars2)

    ax2 = axes[1]
    configure_axis(ax2)
    times = [emb["avg_retrieval_time"], kg["avg_retrieval_time"]]
    bars3 = ax2.bar([t("embedding_legend"), t("kg_legend")], times, color=[EMBEDDING_COLOR, KG_COLOR])
    ax2.set_ylabel(t("seconds_per_query"))
    ax2.set_title(t("average_retrieval_time"), fontsize=FS_TITLE, weight="bold")
    annotate_bars(ax2, bars3, fmt="{:.2f}", offset=0.15)

    fig.suptitle(t("case_content_overall_title"), fontsize=FS_SUPERTITLE, weight="bold", color=TEXT_COLOR)
    save_figure(fig, FIG_DIR / "04_case_content_overall_metrics.png")


def plot_case_content_granularity(metrics: Dict[str, Dict[str, object]]):
    emb = metrics["case_content_embedding"]
    kg = metrics["case_content_kg"]
    fig, ax = plt.subplots(figsize=(14.5, 9.0), facecolor=LIGHT_BG)
    fig.subplots_adjust(top=0.80)
    configure_axis(ax)

    metric_names = [t("exact_file_hit5"), t("case_hit5"), t("file_family_hit5")]
    emb_vals = [pct(emb["hit@5"]), pct(emb["case_hit@5"]), pct(emb["file_hit@5"])]
    kg_vals = [pct(kg["hit@5"]), pct(kg["case_hit@5"]), pct(kg["file_hit@5"])]
    x = range(len(metric_names))
    width = 0.34
    bars1 = ax.bar([i - width / 2 for i in x], emb_vals, width=width, color=EMBEDDING_COLOR, label=t("embedding_legend"))
    bars2 = ax.bar([i + width / 2 for i in x], kg_vals, width=width, color=KG_COLOR, label=t("kg_legend"))
    ax.set_xticks(list(x), metric_names)
    ax.set_ylim(0, 100)
    ax.set_ylabel(t("score_pct"))
    ax.set_title(t("case_granularity_title"), fontsize=FS_TITLE, weight="bold", color=TEXT_COLOR)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.03), ncol=2, borderaxespad=0.0)
    annotate_bars(ax, bars1)
    annotate_bars(ax, bars2)
    ax.text(
        0.02,
        0.93,
        t("case_granularity_note"),
        transform=ax.transAxes,
        fontsize=FS_NOTE,
        color="#475569",
        va="top",
    )

    save_figure(fig, FIG_DIR / "05_case_content_granularity_gap.png")


def plot_case_content_difficulty(metrics: Dict[str, Dict[str, object]]):
    emb = metrics["case_content_embedding"]["by_difficulty"]
    kg = metrics["case_content_kg"]["by_difficulty"]
    difficulties = ["basic", "intermediate", "advanced"]

    fig, axes = plt.subplots(1, 2, figsize=(16, 9.6), facecolor=LIGHT_BG)
    fig.subplots_adjust(top=0.76, wspace=0.20)
    for ax in axes:
        configure_axis(ax)

    width = 0.34
    x = range(len(difficulties))

    bars1 = axes[0].bar([i - width / 2 for i in x], [pct(emb[item]["mrr"]) for item in difficulties], width=width, color=EMBEDDING_COLOR, label=t("embedding_legend"))
    bars2 = axes[0].bar([i + width / 2 for i in x], [pct(kg[item]["mrr"]) for item in difficulties], width=width, color=KG_COLOR, label=t("kg_legend"))
    axes[0].set_xticks(list(x), [display_label(item) for item in difficulties])
    axes[0].set_ylim(0, 100)
    axes[0].set_ylabel(t("tradeoff_ylabel"))
    axes[0].set_title(t("mrr_by_difficulty"), fontsize=FS_TITLE, weight="bold")
    axes[0].legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.05), ncol=2, borderaxespad=0.0)
    annotate_bars(axes[0], bars1)
    annotate_bars(axes[0], bars2)

    bars3 = axes[1].bar([i - width / 2 for i in x], [pct(emb[item]["hit@5"]) for item in difficulties], width=width, color=EMBEDDING_COLOR)
    bars4 = axes[1].bar([i + width / 2 for i in x], [pct(kg[item]["hit@5"]) for item in difficulties], width=width, color=KG_COLOR)
    axes[1].set_xticks(list(x), [display_label(item) for item in difficulties])
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("Hit@5 (%)")
    axes[1].set_title(t("hit5_by_difficulty"), fontsize=FS_TITLE, weight="bold")
    annotate_bars(axes[1], bars3)
    annotate_bars(axes[1], bars4)

    fig.suptitle(t("case_difficulty_title"), fontsize=FS_SUPERTITLE, weight="bold", color=TEXT_COLOR)
    save_figure(fig, FIG_DIR / "06_case_content_difficulty_breakdown.png")


def plot_user_guide_overall(metrics: Dict[str, Dict[str, object]]):
    emb = metrics["user_guide_embedding"]
    kg = metrics["user_guide_kg"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 9.6), facecolor=LIGHT_BG, gridspec_kw={"width_ratios": [2.2, 1]})
    fig.subplots_adjust(top=0.76, wspace=0.18)

    metric_names = ["MRR", "Hit@1", "Hit@3", "Hit@5"]
    emb_vals = [pct(emb["mrr"]), pct(emb["hit@1"]), pct(emb["hit@3"]), pct(emb["hit@5"])]
    kg_vals = [pct(kg["mrr"]), pct(kg["hit@1"]), pct(kg["hit@3"]), pct(kg["hit@5"])]
    x = range(len(metric_names))
    width = 0.36

    ax = axes[0]
    configure_axis(ax)
    bars1 = ax.bar([i - width / 2 for i in x], emb_vals, width=width, color=EMBEDDING_COLOR, label=t("embedding_legend"))
    bars2 = ax.bar([i + width / 2 for i in x], kg_vals, width=width, color=KG_COLOR, label=t("kg_legend"))
    ax.set_xticks(list(x), metric_names)
    ax.set_ylim(0, 105)
    ax.set_ylabel(t("score_pct"))
    ax.set_title(t("accuracy_metrics"), fontsize=FS_TITLE, weight="bold")
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.03), ncol=2, borderaxespad=0.0)
    annotate_bars(ax, bars1)
    annotate_bars(ax, bars2)

    ax2 = axes[1]
    configure_axis(ax2)
    times = [emb["avg_retrieval_time"], kg["avg_retrieval_time"]]
    bars3 = ax2.bar([t("embedding_legend"), t("kg_legend")], times, color=[EMBEDDING_COLOR, KG_COLOR])
    ax2.set_ylabel(t("seconds_per_query"))
    ax2.set_title(t("average_retrieval_time"), fontsize=FS_TITLE, weight="bold")
    annotate_bars(ax2, bars3, fmt="{:.2f}", offset=0.08)

    fig.suptitle(t("user_guide_overall_title"), fontsize=FS_SUPERTITLE, weight="bold", color=TEXT_COLOR)
    save_figure(fig, FIG_DIR / "07_user_guide_overall_metrics.png")


def plot_user_guide_granularity(metrics: Dict[str, Dict[str, object]]):
    emb = metrics["user_guide_embedding"]
    kg = metrics["user_guide_kg"]
    emb_diff = metrics["user_guide_embedding"]["by_difficulty"]
    kg_diff = metrics["user_guide_kg"]["by_difficulty"]

    fig, axes = plt.subplots(1, 2, figsize=(16, 9.6), facecolor=LIGHT_BG)
    fig.subplots_adjust(top=0.76, wspace=0.20)
    for ax in axes:
        configure_axis(ax)

    metric_names = [t("exact_node1"), t("section1"), t("chapter1")]
    emb_vals = [pct(emb["hit@1"]), pct(emb["section_hit@1"]), pct(emb["chapter_hit@1"])]
    kg_vals = [pct(kg["hit@1"]), pct(kg["section_hit@1"]), pct(kg["chapter_hit@1"])]
    x = range(len(metric_names))
    width = 0.34
    bars1 = axes[0].bar([i - width / 2 for i in x], emb_vals, width=width, color=EMBEDDING_COLOR, label=t("embedding_legend"))
    bars2 = axes[0].bar([i + width / 2 for i in x], kg_vals, width=width, color=KG_COLOR, label=t("kg_legend"))
    axes[0].set_xticks(list(x), metric_names)
    axes[0].set_ylim(0, 105)
    axes[0].set_ylabel(t("score_pct"))
    axes[0].set_title(t("granularity_top1"), fontsize=FS_TITLE, weight="bold")
    axes[0].legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.05), ncol=2, borderaxespad=0.0)
    annotate_bars(axes[0], bars1)
    annotate_bars(axes[0], bars2)

    difficulties = ["basic", "intermediate", "advanced"]
    bars3 = axes[1].bar([i - width / 2 for i in range(len(difficulties))], [pct(emb_diff[item]["hit@1"]) for item in difficulties], width=width, color=EMBEDDING_COLOR)
    bars4 = axes[1].bar([i + width / 2 for i in range(len(difficulties))], [pct(kg_diff[item]["hit@1"]) for item in difficulties], width=width, color=KG_COLOR)
    axes[1].set_xticks(list(range(len(difficulties))), [display_label(item) for item in difficulties])
    axes[1].set_ylim(0, 105)
    axes[1].set_ylabel("Hit@1 (%)")
    axes[1].set_title(t("top1_accuracy_by_difficulty"), fontsize=FS_TITLE, weight="bold")
    annotate_bars(axes[1], bars3)
    annotate_bars(axes[1], bars4)

    fig.suptitle(t("user_guide_granularity_title"), fontsize=FS_SUPERTITLE, weight="bold", color=TEXT_COLOR)
    save_figure(fig, FIG_DIR / "08_user_guide_granularity_and_difficulty.png")


def plot_tradeoff(metrics: Dict[str, Dict[str, object]]):
    fig, ax = plt.subplots(figsize=(13.5, 9.2), facecolor=LIGHT_BG)
    fig.subplots_adjust(top=0.86)
    configure_axis(ax)

    points = [
        (t("case_embedding_label"), metrics["case_content_embedding"]["avg_retrieval_time"], pct(metrics["case_content_embedding"]["mrr"]), EMBEDDING_COLOR),
        (t("case_kg_label"), metrics["case_content_kg"]["avg_retrieval_time"], pct(metrics["case_content_kg"]["mrr"]), KG_COLOR),
        (t("guide_embedding_label"), metrics["user_guide_embedding"]["avg_retrieval_time"], pct(metrics["user_guide_embedding"]["mrr"]), ACCENT_BLUE),
        (t("guide_kg_label"), metrics["user_guide_kg"]["avg_retrieval_time"], pct(metrics["user_guide_kg"]["mrr"]), ACCENT_RED),
    ]

    for label, x, y, color in points:
        ax.scatter(x, y, s=180, color=color, edgecolor="white", linewidth=1.5)
        ax.text(x * 1.03, y + 1.0, label, fontsize=FS_NOTE, color=TEXT_COLOR)

    ax.set_xscale("log")
    ax.set_xlabel(t("tradeoff_xlabel"))
    ax.set_ylabel(t("tradeoff_ylabel"))
    ax.set_title(t("tradeoff_title"), fontsize=FS_TITLE, weight="bold", color=TEXT_COLOR)
    ax.text(
        0.03,
        0.07,
        t("tradeoff_note"),
        transform=ax.transAxes,
        fontsize=FS_NOTE,
        color="#475569",
    )

    save_figure(fig, FIG_DIR / "09_accuracy_efficiency_tradeoff.png")


def plot_top_category_gains(metrics: Dict[str, Dict[str, object]]):
    case_rows: List[Tuple[str, float]] = []
    for category, kg_payload in metrics["case_content_kg"]["by_category"].items():
        emb_payload = metrics["case_content_embedding"]["by_category"].get(category)
        if emb_payload:
            case_rows.append((display_label(category), pct(kg_payload["hit@5"] - emb_payload["hit@5"])))
    case_rows.sort(key=lambda item: item[1], reverse=True)
    case_rows = case_rows[:10]

    guide_rows: List[Tuple[str, float]] = []
    for category, kg_payload in metrics["user_guide_kg"]["by_category"].items():
        emb_payload = metrics["user_guide_embedding"]["by_category"].get(category)
        if emb_payload:
            guide_rows.append((display_label(category), pct(kg_payload["hit@1"] - emb_payload["hit@1"])))
    guide_rows.sort(key=lambda item: item[1], reverse=True)
    guide_rows = guide_rows[:10]

    fig, axes = plt.subplots(1, 2, figsize=(16, 10), facecolor=LIGHT_BG)
    fig.subplots_adjust(top=0.82, wspace=0.20)
    for ax in axes:
        configure_axis(ax)

    case_labels = [item[0] for item in reversed(case_rows)]
    case_vals = [item[1] for item in reversed(case_rows)]
    bars1 = axes[0].barh(case_labels, case_vals, color=KG_COLOR)
    axes[0].set_xlabel(t("abs_gain_hit5"))
    axes[0].set_title(t("case_top_gains"), fontsize=FS_TITLE, weight="bold")
    annotate_barh(axes[0], bars1, fmt="{:.2f}", offset=1.0)

    guide_labels = [item[0] for item in reversed(guide_rows)]
    guide_vals = [item[1] for item in reversed(guide_rows)]
    bars2 = axes[1].barh(guide_labels, guide_vals, color=ACCENT_RED)
    axes[1].set_xlabel(t("abs_gain_hit1"))
    axes[1].set_title(t("guide_top_gains"), fontsize=FS_TITLE, weight="bold")
    annotate_barh(axes[1], bars2, fmt="{:.2f}", offset=1.0)

    fig.suptitle(t("top_gain_title"), fontsize=FS_SUPERTITLE, weight="bold", color=TEXT_COLOR)
    save_figure(fig, FIG_DIR / "10_top_category_improvements.png")


def export_summary_json(asset_summary: Dict[str, object], metrics: Dict[str, Dict[str, object]]):
    summary = {
        "asset_summary": {
            "case_graph_files": asset_summary["case_graph_files"],
            "case_nodes": asset_summary["case_nodes"],
            "file_nodes": asset_summary["file_nodes"],
            "variable_nodes": asset_summary["variable_nodes"],
            "case_graph_edges": asset_summary["case_graph_edges"],
            "user_guide_nodes": asset_summary["user_guide_nodes"],
            "case_dataset_size": asset_summary["case_dataset_size"],
            "guide_dataset_size": asset_summary["guide_dataset_size"],
        },
        "headline_results": {
            "case_content": {
                "embedding_mrr": round(metrics["case_content_embedding"]["mrr"], 4),
                "kg_mrr": round(metrics["case_content_kg"]["mrr"], 4),
                "embedding_hit@5": round(metrics["case_content_embedding"]["hit@5"], 4),
                "kg_hit@5": round(metrics["case_content_kg"]["hit@5"], 4),
                "embedding_avg_time": round(metrics["case_content_embedding"]["avg_retrieval_time"], 4),
                "kg_avg_time": round(metrics["case_content_kg"]["avg_retrieval_time"], 4),
            },
            "user_guide": {
                "embedding_mrr": round(metrics["user_guide_embedding"]["mrr"], 4),
                "kg_mrr": round(metrics["user_guide_kg"]["mrr"], 4),
                "embedding_hit@1": round(metrics["user_guide_embedding"]["hit@1"], 4),
                "kg_hit@1": round(metrics["user_guide_kg"]["hit@1"], 4),
                "embedding_avg_time": round(metrics["user_guide_embedding"]["avg_retrieval_time"], 4),
                "kg_avg_time": round(metrics["user_guide_kg"]["avg_retrieval_time"], 4),
            },
        },
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def main(language: str = "en"):
    configure_language(language)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    asset_summary = collect_asset_summary()
    metrics = load_metrics()

    export_tables(asset_summary, metrics)
    export_summary_json(asset_summary, metrics)

    plot_system_architecture()
    plot_retrieval_pipelines()
    plot_asset_overview(asset_summary)
    plot_case_content_overall(metrics)
    plot_case_content_granularity(metrics)
    plot_case_content_difficulty(metrics)
    plot_user_guide_overall(metrics)
    plot_user_guide_granularity(metrics)
    plot_tradeoff(metrics)
    plot_top_category_gains(metrics)

    print(f"Generated figures in: {FIG_DIR}")
    print(f"Generated tables in: {TABLE_DIR}")
    print(f"Generated summary in: {SUMMARY_PATH}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate midterm figures, tables and summary files.")
    parser.add_argument("--language", choices=["en", "zh"], default="en", help="Output language for figure text.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(language=args.language)
