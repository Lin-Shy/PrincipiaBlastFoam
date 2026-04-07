# Retrieval Method Evaluation

本目录是当前检索基线评测的统一入口。

目前支持两个 benchmark：

- `case_content`: 全 tutorial 范围的 strict 检索评测，目标单元为 `case_path::file_path`
- `user_guide`: BlastFoam 用户手册知识图谱检索评测，目标单元为 `node_id`

## Benchmark 概览

### `case_content`

- 数据集: `dataset/retrieval/benchmarks/case_content/blastfoam_retrieval_validation_dataset_strict.json`
- 数据规模: `210` 条查询
- 结果目录: `experiments/retrieval_method/results/case_content/`
- 当前方法:
  - embedding retrieval
  - knowledge-graph retrieval

### `user_guide`

- 数据集: `dataset/retrieval/benchmarks/user_guide/user_guide_retrieval_validation_dataset.json`
- 数据规模: `94` 条查询
- 结果目录: `experiments/retrieval_method/results/user_guide/`
- 当前方法:
  - embedding retrieval
  - knowledge-graph retrieval
  - 自动构建 / 审计脚本: `dataset/retrieval/build_user_guide_retrieval_dataset.py`

## 目录结构

- `evaluate_embedding_retriever.py`: embedding 基线评测
- `evaluate_knowledge_graph_retriever.py`: KG 基线评测
- `compare_retrievers.py`: 对比多个结果文件的聚合指标
- `analyze_failures.py`: 对单个结果文件做失败案例分析
- `evaluation_common.py`: 评测公共逻辑

## 前置条件

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

KG_RETRIEVAL_MAX_ITERATIONS=3
```

说明：

- embedding 基线读取 `EMBEDDING_*`
- KG 检索优先读取 `RETRIEVAL_LLM_*`
- 如果未提供 `RETRIEVAL_LLM_*`，KG 检索会回退到 `LLM_*`
- `user_guide` benchmark 不依赖 `BLASTFOAM_TUTORIALS`

## 数据与索引

- benchmark 数据集位于 `dataset/retrieval/benchmarks/`
- case content knowledge graph 位于 `data/knowledge_graph/case_content_knowledge_graph/`
- user guide knowledge graph 位于 `data/knowledge_graph/user_guide_knowledge_graph/`
- `case_content` embedding 基线需要先构建 FAISS 索引

构建 embedding 索引：

```bash
python scripts/native_embedding/build_embedding_index.py
```

## 运行方式

### 1. `case_content` Embedding 基线

```bash
python experiments/retrieval_method/evaluate_embedding_retriever.py \
  --benchmark case_content \
  --tutorials-dir "$BLASTFOAM_TUTORIALS"
```

常用参数：

- `--embedding-level file|case`: 选择文件级或案例级索引，默认 `file`
- `--search-k 40`: strict 去重前的候选数
- `--k-values 1,3,5,10`: 评测的 K 值
- `--limit N`: 只跑前 N 条，便于快速冒烟
- `--results-dir ...`: 自定义结果输出目录

说明：

- `case_content` 支持 `file` / `case`
- `user_guide` 支持 `node`

评测 `user_guide` embedding：

```bash
python experiments/retrieval_method/evaluate_embedding_retriever.py \
  --benchmark user_guide \
  --embedding-level node
```

### 2. Knowledge Graph 基线

评测 `case_content`：

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py \
  --benchmark case_content \
  --tutorials-dir "$BLASTFOAM_TUTORIALS"
```

评测 `user_guide`：

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py \
  --benchmark user_guide
```

如果希望检索方法使用与主工作流不同的 LLM，可以显式传 retrieval LLM 参数：

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py \
  --benchmark case_content \
  --tutorials-dir "$BLASTFOAM_TUTORIALS" \
  --retrieval-llm-base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
  --retrieval-llm-model qwen-plus
```

常用参数：

- `--benchmark case_content|user_guide`: 选择 benchmark
- `--max-iterations N`: case-content ReAct 搜索最大轮数
- `--include-file-content`: case-content 检索时连同原始文件内容一起读入
- `--limit N`: 快速抽样评测

说明：

- `case_content` 会使用 `CaseContentKnowledgeGraphRetriever`
- `user_guide` 会使用 `UserGuideKnowledgeGraphRetriever`
- `user_guide` 当前忽略 `--max-iterations` 与 `--include-file-content`

### 3. 对比不同基线结果与可视化

```bash
python experiments/retrieval_method/compare_retrievers.py
```

该脚本默认读取 `case_content` 结果目录中最新的 embedding / KG 结果，并输出对比表；如果安装了 `matplotlib`，会自动生成可视化对比图。

输出文件示例：

- `experiments/retrieval_method/results/case_content/comparison_plot_YYYYMMDD_HHMMSS.png`
- `experiments/retrieval_method/results/case_content/comparison_report_YYYYMMDD_HHMMSS.md`

### 4. 分析失败案例

```bash
python experiments/retrieval_method/analyze_failures.py
```

该脚本默认扫描 `case_content` 结果目录中的可用结果文件。它也兼容 `user_guide` 结果文件的目标节点展示格式。

## 结果指标

所有 benchmark 共同关注：

- `mrr`
- `hit@1`, `hit@3`, `hit@5`
- `precision@k`
- `recall@k`
- `avg_retrieval_time`

`case_content` 额外关注：

- `case_hit@k`: 先找对案例、但文件没排上来
- `file_hit@k`: 文件家族是否命中

`user_guide` 额外关注：

- `section_hit@k`: 命中正确小节范围
- `chapter_hit@k`: 命中正确章节范围

## 输出文件

结果默认写入 `experiments/retrieval_method/results/<benchmark>/`：

- `case_content/embedding_retrieval_file_YYYYMMDD_HHMMSS.json`
- `case_content/embedding_retrieval_case_YYYYMMDD_HHMMSS.json`
- `case_content/knowledge_graph_retrieval_YYYYMMDD_HHMMSS.json`
- `user_guide/embedding_retrieval_node_YYYYMMDD_HHMMSS.json`
- `user_guide/knowledge_graph_retrieval_YYYYMMDD_HHMMSS.json`

每个结果文件都包含：

- `metadata`: 数据集路径、benchmark、模型配置、时间戳等
- `aggregate_metrics`: 聚合指标
- `detailed_results`: 每条查询的目标、命中情况、检索耗时和原始结果

## 建议工作流

1. 先确认所选 benchmark 的数据与依赖就绪。
2. 如果要跑 `case_content` embedding，先构建索引。
3. 运行对应 benchmark 的评测脚本。
4. 对 `case_content` 用 `compare_retrievers.py` 看整体差异。
5. 用 `analyze_failures.py` 追踪失败类别和目标项模式。

## 相关文档

- strict 数据集说明: `dataset/retrieval/STRICT_RETRIEVAL_VALIDATION_README.md`
- case-content benchmark 目录: `dataset/retrieval/benchmarks/case_content/`
- user-guide benchmark 目录: `dataset/retrieval/benchmarks/user_guide/`
- 案例内容 KG 检索方法: `docs/检索方法/案例内容知识检索技术文档.md`
- 用户手册 KG 检索方法: `docs/检索方法/用户手册知识检索技术文档.md`
- embedding 检索实现说明: `scripts/native_embedding/EMBEDDING_README.md`
