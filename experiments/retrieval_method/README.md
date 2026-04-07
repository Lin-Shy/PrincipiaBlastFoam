# Retrieval Method Evaluation

本目录是当前检索基线评测的唯一入口说明。

所有在用的评测脚本都基于全 tutorial 范围的 strict 检索基准，按精确的 `case_path::file_path` 进行打分，不再使用旧的“只看相对文件路径”的 case 内局部评测口径。

## 当前口径

- 权威数据集: `dataset/retrieval/blastfoam_retrieval_validation_dataset_strict.json`
- 评测单元: `case_path::file_path`
- 当前数据规模: `210` 条查询
- 结果目录: `experiments/retrieval_method/results/`
- 推荐运行环境: `graph-py310`

## 目录结构

- `evaluate_embedding_retriever.py`: strict embedding 基线评测
- `evaluate_knowledge_graph_retriever.py`: strict KG 基线评测
- `compare_retrievers.py`: 对比多个结果文件的聚合指标
- `analyze_failures.py`: 对单个结果文件做失败案例分析
- `evaluation_common.py`: 评测公共逻辑

## 前置条件

### 1. 运行环境

请在 `graph-py310` 环境中运行，并保证项目根目录下 `.env` 至少包含以下配置：

```bash
BLASTFOAM_TUTORIALS=/path/to/blastFoam_tutorials

EMBEDDING_API_KEY=...
EMBEDDING_API_BASE_URL=...
EMBEDDING_MODEL=text-embedding-v3

LLM_API_KEY=...
LLM_API_BASE_URL=...
LLM_MODEL=...

RETRIEVAL_LLM_API_KEY=...
RETRIEVAL_LLM_API_BASE_URL=...
RETRIEVAL_LLM_MODEL=...

# KG 检索 ReAct 最大迭代轮数（默认 3）
KG_RETRIEVAL_MAX_ITERATIONS=3
```

说明：

- embedding 基线读取 `EMBEDDING_*`
- KG 检索优先读取 `RETRIEVAL_LLM_*`
- 如果未提供 `RETRIEVAL_LLM_*`，KG 检索会回退到 `LLM_*`

### 2. 数据与索引

- strict 数据集已位于 `dataset/retrieval/`
- case content knowledge graph 位于 `data/knowledge_graph/case_content_knowledge_graph/`
- embedding 基线需要先构建 FAISS 索引

构建 embedding 索引：

```bash
python scripts/native_embedding/build_embedding_index.py
```

## 运行方式

### 1. Embedding 基线

默认评测 file-level embedding 检索：

```bash
python experiments/retrieval_method/evaluate_embedding_retriever.py \
  --tutorials-dir "$BLASTFOAM_TUTORIALS"
```

常用参数：

- `--embedding-level file|case`: 选择文件级或案例级索引，默认 `file`
- `--search-k 40`: strict 去重前的候选数
- `--k-values 1,3,5,10`: 评测的 K 值
- `--limit N`: 只跑前 N 条，便于快速冒烟
- `--results-dir ...`: 自定义结果输出目录

### 2. Knowledge Graph 基线

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py \
  --tutorials-dir "$BLASTFOAM_TUTORIALS"
```

如果希望检索方法使用与主工作流不同的 LLM，可以显式传 retrieval LLM 参数：

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py \
  --tutorials-dir "$BLASTFOAM_TUTORIALS" \
  --retrieval-llm-base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --retrieval-llm-model qwen-plus
```

常用参数：

- `--max-iterations N`: ReAct 搜索最大轮数（默认读取 `.env` 的 `KG_RETRIEVAL_MAX_ITERATIONS`，默认值为 `3`）
- `--include-file-content`: 检索时连同原始文件内容一起读入，精度更高但更慢
- `--limit N`: 快速抽样评测

retrieval LLM 配置优先级：

1. 命令行显式传参
2. `.env` 中的 `RETRIEVAL_LLM_*`
3. `.env` 中的 `LLM_*`

KG 最大迭代轮数配置优先级：

1. 命令行 `--max-iterations`
2. `.env` 中的 `KG_RETRIEVAL_MAX_ITERATIONS`
3. 默认值 `3`

### 3. 对比不同基线结果与可视化

```bash
python experiments/retrieval_method/compare_retrievers.py
```

该脚本会优先加载 `results/` 中每种方法最新的结果文件，并输出对比表；如果安装了 `matplotlib`，会自动生成 embedding 与 KG 的可视化对比图。

当前可视化方法代码位于 `compare_retrievers.py`：

- `plot_comparison`: 统一生成 2x2 对比图
- `_plot_hit_at_k`: 比较 Hit@K（Embedding/KG）
- `_plot_mrr_by_difficulty`: 按难度比较 MRR
- `_plot_precision_recall`: 比较 Precision@5 / Recall@5
- `_plot_category_heatmap`: 按类别比较 Hit@5 热力图

输出文件示例：

- `results/comparison_plot_YYYYMMDD_HHMMSS.png`
- `results/comparison_report_YYYYMMDD_HHMMSS.md`

### 4. 分析失败案例

```bash
python experiments/retrieval_method/analyze_failures.py
```

该脚本会列出可用结果文件，随后按 `hit@5` 等指标筛出失败查询并给出模式分析。

## 结果指标

当前 strict 结果至少关注以下指标：

- `mrr`
- `hit@1`, `hit@3`, `hit@5`
- `case_hit@k`: case 对但 file 错的情况也能反映出来
- `file_hit@k`: file 对但 case 错的情况
- `precision@k`
- `recall@k`
- `avg_retrieval_time`

其中最重要的是：

- strict `hit@k`: case 和 file 必须同时命中
- `case_hit@k`: 用来区分“先找对案例、但文件没排上来”的问题

## 输出文件

结果默认写入 `experiments/retrieval_method/results/`：

- `embedding_retrieval_file_YYYYMMDD_HHMMSS.json`
- `embedding_retrieval_case_YYYYMMDD_HHMMSS.json`
- `knowledge_graph_retrieval_YYYYMMDD_HHMMSS.json`

每个结果文件都包含：

- `metadata`: 数据集路径、模型配置、时间戳等
- `aggregate_metrics`: 聚合指标
- `detailed_results`: 每条查询的目标、命中情况、检索耗时和原始结果

## 建议工作流

1. 先确认 `.env` 与 `BLASTFOAM_TUTORIALS` 正确。
2. 如果要跑 embedding，先构建索引。
3. 分别运行 embedding 与 KG 基线。
4. 用 `compare_retrievers.py` 看整体差异。
5. 用 `analyze_failures.py` 追踪失败类别、案例族和目标文件族。

## 相关文档

- strict 数据集说明: `dataset/retrieval/STRICT_RETRIEVAL_VALIDATION_README.md`
- strict 审计摘要: `dataset/retrieval/STRICT_RETRIEVAL_AUDIT_SUMMARY.md`
- strict 数据集问题复核: `dataset/retrieval/STRICT_RETRIEVAL_DATASET_ISSUE_REVIEW.md`
- 案例内容 KG 检索方法: `docs/检索方法/案例内容知识检索技术文档.md`
- 用户手册 KG 检索方法: `docs/检索方法/用户手册知识检索技术文档.md`
- embedding 检索实现说明: `scripts/native_embedding/EMBEDDING_README.md`

本 README 已覆盖旧的 `SCRIPTS_SUMMARY.md` 和 `WORKFLOW_GUIDE.md`，后续以这里为准。
