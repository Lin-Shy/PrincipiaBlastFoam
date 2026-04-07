# Case Content Retrieval Benchmark

本目录承载规范化后的 `case content` 检索评测数据。

当前文件：

- `blastfoam_retrieval_validation_dataset_strict.json`: 当前权威 strict 数据集
- `blastfoam_retrieval_validation_dataset_strict_audit.json`: strict 数据集审计结果

说明：

- 新评测脚本默认优先读取本目录下的数据集。
- 该 benchmark 的检索目标单元为 `case_path::file_path`。
