本目录包含从 `dataset/retrieval/blastfoam_retrieval_validation_dataset.json` 自动生成的统计文件：

文件列表：
- retrieval_dataset_summary.csv — 汇总统计（总查询数、平均目标文件数、top target files 与难度统计）
- retrieval_target_file_counts.csv — 每个目标文件的出现次数（频次表）
- retrieval_category_counts.csv — 每个类别的查询数量
- retrieval_difficulty_counts.csv — 难度分布
- retrieval_dataset_queries.csv — 原始查询的 CSV 导出（id, query, difficulty, category, num_target_files, target_files）

如果需要生成 Excel（.xlsx），请在虚拟环境中安装 pandas 与 openpyxl：

```bash
pip install pandas openpyxl
python docs/检索方法/retrieval_dataset_describtion/make_excel_from_csv.py
```

说明：我已把这些 CSV 放在本目录，便于直接打开或插入到 PPT。若你希望我代为在仓库中生成 Excel，我可以尝试安装依赖或在你允许的情况下执行生成（需要 Python 包）。