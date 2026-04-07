# User Guide Retrieval Benchmark

本目录包含 `user guide` 检索评测数据集，用于评测 `UserGuideKnowledgeGraphRetriever` 及后续同类方法。

## 文件

- `user_guide_retrieval_blueprint.json`: 数据集蓝图，维护 query / node 映射
- `user_guide_retrieval_validation_dataset.json`: 当前用户手册检索验证集
- `user_guide_retrieval_validation_audit.json`: 自动审计结果
- `USER_GUIDE_RETRIEVAL_AUDIT_SUMMARY.md`: 审计摘要

## 数据格式

每条数据包含：

- `id`: 查询编号
- `query`: 用户查询
- `difficulty`: 难度标签
- `category`: 类别标签
- `target_nodes`: 目标知识节点列表

`target_nodes` 中的字段：

- `node_id`: 用户手册知识图谱节点 ID
- `number`: 章节编号
- `title`: 节点标题
- `canonical_id`: 当前等同于 `node_id`

## 评测口径

- 检索目标单元: `node_id`
- 主指标: `mrr`, `hit@k`, `precision@k`, `recall@k`
- 辅助指标:
  - `section_hit@k`: 命中正确章节小节范围，但未必命中精确节点
  - `chapter_hit@k`: 命中正确章节范围

## 当前规模

- 查询数: `94`
- 覆盖范围:
  - governing equations
  - interfacial / granular models
  - thermodynamics / EOS / reactive models
  - burst patches / boundary conditions
  - numerics / AMR
  - function objects / utilities
  - coupling / solvers

## 自动构建与审计

```bash
python dataset/retrieval/build_user_guide_retrieval_dataset.py
```

该脚本会基于 `user_guide_retrieval_blueprint.json` 自动生成：

- 数据集 JSON
- 审计 JSON
- Markdown 审计摘要

## 运行示例

先构建 embedding 索引：

```bash
python scripts/native_embedding/build_embedding_index.py \
  --benchmark user_guide \
  --embedding-level node
```

评测 embedding baseline：

```bash
python experiments/retrieval_method/evaluate_embedding_retriever.py \
  --benchmark user_guide \
  --embedding-level node
```

评测 KG baseline：

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py \
  --benchmark user_guide
```
