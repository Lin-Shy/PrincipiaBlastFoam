# Strict Retrieval Validation

本文件描述当前在用的 strict 检索验证基准。它面向“在所有 tutorial 中检索目标文件”的场景，评测单位是精确的 `case_path::file_path`。

## 为什么需要 strict 数据集

旧版数据集 `blastfoam_retrieval_validation_dataset.json` 只标注相对文件路径，例如 `system/controlDict`。

这种标注在“单个 case 内检索”时勉强可用，但一旦检索范围扩大到所有 tutorial，就会出现大量歧义，因为很多案例都包含同名文件。

由 `build_strict_retrieval_dataset.py` 生成的审计结果表明：

- 旧数据集共 `120` 条
- 仅 `6` 条可以唯一解析到某个 case
- `108` 条在多个 case 之间歧义
- `6` 条指向当前 tutorial 语料中不存在的文件

因此，旧数据集不能再作为全 tutorial strict 评测基准。

## 当前权威基准

### 数据文件

- strict 数据集: `dataset/retrieval/blastfoam_retrieval_validation_dataset_strict.json`
- strict 审计: `dataset/retrieval/blastfoam_retrieval_validation_dataset_strict_audit.json`
- tutorial 清单: `dataset/retrieval/tutorial_case_manifest.json`
- 审计摘要: `dataset/retrieval/STRICT_RETRIEVAL_AUDIT_SUMMARY.md`
- 问题复核: `dataset/retrieval/STRICT_RETRIEVAL_DATASET_ISSUE_REVIEW.md`

### 标注格式

每个目标文件都使用规范 ID：

```text
case_path::file_path
```

例如：

```text
blastFoam/freeField::system/controlDict
```

### 当前状态

- 数据集大小: `210`
- 覆盖 tutorial case 数: `25`
- 单目标记录: `161`，多目标记录: `49`
- 新增扩充记录: `80`
  - 第 1 轮: `44`（`source_dataset = manual_strict_expansion_20260407.json`）
  - 第 2 轮: `36`（`source_dataset = manual_strict_expansion_round2_20260407.json`，全部为 advanced 多目标）
- 全量路径有效性校验: `210/210` 通过（基于 `tutorial_case_manifest.json` 的 case+file 严格匹配）
- 构建脚本审计状态（核心 130 条）: `122 pass / 8 warn / 0 fail`

上述 `8` 条 warning 主要是“隐式目标文件”类型，属于语义上合理但词面不显式的检索样本，并不表示标签损坏。

## 评测器

严格评测逻辑位于：

- `dataset/retrieval/strict_retrieval_evaluator.py`

它支持把下列检索结果归一化为 strict target：

- `case_path::file_path`
- `{ "case_path": "...", "file_path": "..." }`
- tutorial 下的绝对路径
- `blastFoam/freeField/system/controlDict` 这类全相对路径

## 当前评测入口

- embedding 基线: `experiments/retrieval_method/evaluate_embedding_retriever.py`
- KG 基线: `experiments/retrieval_method/evaluate_knowledge_graph_retriever.py`
- 数据集分析脚本: `dataset/retrieval/analyze_retrieval_dataset.py`
- 轻量分析脚本: `dataset/retrieval/analyze_retrieval_dataset_simple.py`

当前结果建议至少报告：

- strict `hit@k`
- `case_hit@k`
- `file_hit@k`
- `mrr`
- `precision@k`
- `recall@k`

## 快速查看 strict 数据集

只查看统计信息：

```bash
python dataset/retrieval/analyze_retrieval_dataset_simple.py --analyze
```

运行脚本内置的示例启发式检索并打分：

```bash
python dataset/retrieval/analyze_retrieval_dataset_simple.py --evaluate
```

这两个分析脚本现在都按 strict 数据集口径运行。

## 重建数据集

```bash
python dataset/retrieval/build_strict_retrieval_dataset.py \
  --tutorials-dir /path/to/blastFoam_tutorials
```

说明：该脚本当前重建的是基于 modification 数据源的核心 strict 集（130 条）。
本次新增的 44 条扩充样本属于人工增强样本，需要在此基础上继续维护。

## 旧数据集状态

旧版 `blastfoam_retrieval_validation_dataset.json` 已下线并从仓库移除，不再作为评测或构建输入。

如果要进行当前有效的全 tutorial 检索评测，请始终使用 strict 数据集。
