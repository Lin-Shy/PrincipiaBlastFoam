# Embedding-Based Retrieval

本目录包含当前 embedding 检索基线使用的索引构建与检索实现。

## 文件

- `build_embedding_index.py`: 构建并缓存 FAISS 索引
- `embedding_retriever.py`: 加载缓存索引并执行相似度搜索

## 支持的索引级别

- `case`: 仅索引 case 级 README，速度快，但无法直接支持 strict file 命中
- `file`: 索引 tutorial 中的文件内容，是当前 strict embedding 基线的默认配置

## 推荐使用流程

### 1. 在 `graph-py310` 环境中准备 `.env`

```bash
BLASTFOAM_TUTORIALS=/path/to/blastFoam_tutorials
EMBEDDING_API_KEY=...
EMBEDDING_API_BASE_URL=...
EMBEDDING_MODEL=text-embedding-v3
```

### 2. 构建索引

```bash
python scripts/native_embedding/build_embedding_index.py
```

索引会缓存到：

- `data/vector_store_cache/`

### 3. 在评测脚本中使用

```bash
python experiments/retrieval_method/evaluate_embedding_retriever.py \
  --tutorials-dir "$BLASTFOAM_TUTORIALS" \
  --embedding-level file
```

当前评测说明见：

- `experiments/retrieval_method/README.md`

## Python 调用方式

### 构建索引

```python
from scripts.native_embedding.build_embedding_index import EmbeddingIndexBuilder

builder = EmbeddingIndexBuilder(
    case_base_dir="/path/to/blastFoam_tutorials",
    embedding_level="file",
)
builder.build_and_save_index(force_rebuild=False)
```

### 执行检索

```python
from scripts.native_embedding.embedding_retriever import EmbeddingRetriever

retriever = EmbeddingRetriever(
    case_base_dir="/path/to/blastFoam_tutorials",
    embedding_level="file",
)
results = retriever.search_with_scores("Set maxCo to 0.3", k=5)
```

## 实现要点

- 使用 OpenAI-compatible embedding API
- case base dir 通过 MD5 命名缓存，避免不同教程目录互相覆盖
- file-level 模式会递归扫描 case 目录下文件，并过滤空文件/不可读文件
- 检索评测时，返回的 `source` 路径会交给 strict evaluator 做 `case + file` 归一化匹配

## 常见问题

### 没有索引文件

先运行：

```bash
python scripts/native_embedding/build_embedding_index.py
```

### file-level 太慢

这是预期现象。file-level 会扫描 tutorial 中大量文件，但它才是 strict file 命中的主基线。

### 想重建索引

```python
builder.build_and_save_index(force_rebuild=True)
```
