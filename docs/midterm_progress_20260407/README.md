# 中期进展汇报材料目录

本目录用于集中整理毕业设计《中期进展》答辩阶段可直接复用的图表、表格和说明文档，方便后续制作 PPT 与撰写论文。

## 目录内容

- `generate_midterm_assets.py`
  从现有实验结果与知识图谱数据中自动生成图表、CSV 表格与汇总 JSON。
- `figures/`
  存放答辩与论文可直接使用的 PNG 图。
- `tables/`
  存放便于复制到论文或 PPT 的 CSV 表格。
- `summary_stats.json`
  汇总后的关键数字，便于后续脚本或人工引用。
- `中期进展汇报说明.md`
  适合作为中期答辩讲稿和论文阶段性总结的文字底稿。
- `PPT提纲建议.md`
  给出一版可直接套用的 PPT 章节组织建议。

## 生成方式

按项目要求，使用 `graph-py310` 环境运行。

生成英文版：

```bash
conda run -n graph-py310 python docs/midterm_progress_20260407/generate_midterm_assets.py
```

生成中文版：

```bash
conda run -n graph-py310 python docs/midterm_progress_20260407/generate_midterm_assets_zh.py
```

也可以用统一脚本手动指定语言：

```bash
conda run -n graph-py310 python docs/midterm_progress_20260407/generate_midterm_assets.py --language zh
```

## 输出路径

- 英文图表：`docs/midterm_progress_20260407/figures/en/`
- 中文图表：`docs/midterm_progress_20260407/figures/zh/`
- 英文表格：`docs/midterm_progress_20260407/tables/en/`
- 中文表格：`docs/midterm_progress_20260407/tables/zh/`
- 英文汇总：`docs/midterm_progress_20260407/summary_stats_en.json`
- 中文汇总：`docs/midterm_progress_20260407/summary_stats_zh.json`

## 当前使用的数据来源

- `experiments/retrieval_method/results/embedding_retrieval_file_20260407_132222.json`
- `experiments/retrieval_method/results/knowledge_graph_retrieval_20260407_140404.json`
- `experiments/retrieval_method/results/user_guide/embedding_retrieval_node_20260407_151152.json`
- `experiments/retrieval_method/results/user_guide/knowledge_graph_retrieval_20260407_154114.json`
- `data/knowledge_graph/case_content_knowledge_graph/`
- `data/knowledge_graph/user_guide_knowledge_graph/user_guide_knowledge_graph.json`
- `dataset/retrieval/benchmarks/case_content/blastfoam_retrieval_validation_dataset_strict.json`
- `dataset/retrieval/benchmarks/user_guide/user_guide_retrieval_validation_dataset.json`

## 使用建议

- 优先把 `figures/04` 到 `figures/09` 用在“实验结果”部分。
- 把 `figures/01` 和 `figures/02` 用在“系统设计 / 方法设计”部分。
- 把 `figures/03` 用在“数据基础与实验设置”部分。
- 如果答辩时间紧，建议保留 6 张核心图：
  `01_system_architecture.png`
  `03_asset_and_benchmark_overview.png`
  `04_case_content_overall_metrics.png`
  `05_case_content_granularity_gap.png`
  `07_user_guide_overall_metrics.png`
  `09_accuracy_efficiency_tradeoff.png`
