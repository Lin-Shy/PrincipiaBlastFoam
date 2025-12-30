# Embedding-Based Retrieval System

本目录包含基于向量嵌入的检索系统，用于在 OpenFOAM 案例库中进行语义搜索。

## 文件说明

### 1. `build_embedding_index.py` - 索引构建工具
**用途**: 构建并保存 FAISS 向量索引

**功能**:
- 从指定目录加载文档（README 或所有文件）
- 使用阿里云 DashScope API 生成嵌入向量
- 构建 FAISS 向量索引
- 将索引保存到本地缓存

**使用方法**:
```bash
# 直接运行（会提示是否构建 file-level 索引）
python principia_ai/tools/build_embedding_index.py

# 或使用 Python 导入
from principia_ai.tools.build_embedding_index import EmbeddingIndexBuilder

builder = EmbeddingIndexBuilder(
    case_base_dir="/path/to/cases",
    embedding_level='case'  # 'case' 或 'file'
)
builder.build_and_save_index(force_rebuild=False)
```

**支持的索引级别**:
- `case`: 仅索引 README.md 文件（快速，适合案例级别搜索）
- `file`: 索引所有文件（慢，适合详细的文件级搜索）

---

### 2. `embedding_retriever.py` - 检索工具
**用途**: 加载预构建的索引并执行相似度搜索

**功能**:
- 加载已保存的 FAISS 索引
- 执行语义相似度搜索
- 返回最相关的文档
- 支持返回相似度分数

**使用方法**:
```bash
# 直接运行测试
python principia_ai/tools/embedding_retriever.py

# 或使用 Python 导入
from principia_ai.tools.embedding_retriever import EmbeddingRetriever

retriever = EmbeddingRetriever(
    case_base_dir="/path/to/cases",
    embedding_level='case'
)

# 基本搜索
results = retriever.search("PIMPLE algorithm settings", k=3)
print(results)

# 带相似度分数的搜索
results_with_scores = retriever.search_with_scores("blast simulation", k=5)
for doc, score in results_with_scores:
    print(f"Score: {score}, Source: {doc.metadata['source']}")
```

---

## 工作流程

### 第一步: 构建索引（一次性操作）

```bash
# 运行索引构建脚本
python principia_ai/tools/build_embedding_index.py
```

这将：
1. 从 `BLASTFOAM_TUTORIALS` 环境变量指定的目录加载文档
2. 为每个文档生成嵌入向量
3. 创建 FAISS 索引
4. 将索引保存到 `data/vector_store_cache/` 目录

**注意**: 
- Case-level 索引构建较快（几分钟）
- File-level 索引可能需要很长时间（数小时），因为需要处理所有文件

### 第二步: 使用检索器进行搜索

```python
from principia_ai.tools.embedding_retriever import EmbeddingRetriever

# 创建检索器（自动加载缓存的索引）
retriever = EmbeddingRetriever(
    case_base_dir="/path/to/foam/tutorials",
    embedding_level='case'
)

# 执行搜索
results = retriever.search("settings for blast simulation", k=3)
print(results)
```

---

## 配置要求

### 环境变量 (`.env` 文件)

```bash
# 嵌入 API 配置（阿里云 DashScope）
EMBEDDING_API_KEY=sk-xxxxxxxxxxxxxxxxx
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# OpenFOAM 教程目录
BLASTFOAM_TUTORIALS=/path/to/OpenFOAM/tutorials
```

### Python 依赖

```bash
pip install langchain langchain-community faiss-cpu requests python-dotenv
```

---

## 技术细节

### CustomOpenAIEmbeddings 类
- 使用标准 OpenAI API 格式调用嵌入服务
- 兼容阿里云 DashScope API
- 自动处理批量限制（每批最多 10 个文档）
- 避免了 `langchain_openai.OpenAIEmbeddings` 的兼容性问题

### 缓存机制
- 索引文件保存在 `data/vector_store_cache/` 目录
- 文件名基于案例目录路径的 MD5 哈希值
- 格式: `faiss_index_{hash}_{level}`
- 支持多个不同目录的索引共存

### 文档处理
- 自动分块处理大文件（超过 32,000 字符）
- 过滤空文档和二进制文件
- 保留文件路径等元数据

---

## 常见问题

### Q: 索引构建失败怎么办？
A: 检查：
1. `EMBEDDING_API_KEY` 是否有效
2. 网络连接是否正常
3. `BLASTFOAM_TUTORIALS` 路径是否正确
4. 是否有足够的磁盘空间

### Q: 如何重建索引？
A: 使用 `force_rebuild=True` 参数：
```python
builder.build_and_save_index(force_rebuild=True)
```

### Q: 检索速度慢怎么办？
A: 
1. 使用 case-level 索引而非 file-level
2. 减少返回结果数量 (k 参数)
3. 确保索引已缓存到本地

### Q: 如何在其他项目中使用？
A: 只需导入并指定 `case_base_dir`:
```python
from principia_ai.tools.embedding_retriever import EmbeddingRetriever

retriever = EmbeddingRetriever(
    case_base_dir="/your/custom/path",
    embedding_level='case'
)
```

---

## 性能参考

### Case-Level Index
- **文档数量**: ~100-1000 个 README 文件
- **构建时间**: 5-15 分钟
- **索引大小**: 10-50 MB
- **查询速度**: <1 秒

### File-Level Index
- **文档数量**: 数万个文件
- **构建时间**: 数小时
- **索引大小**: 100-500 MB
- **查询速度**: 1-3 秒

---

## 更新历史

- **2025-01-27**: 
  - 将原始代码分离为索引构建和检索两个独立模块
  - 添加自定义嵌入类以支持阿里云 DashScope API
  - 改进错误处理和批量处理逻辑
  - 添加向后兼容性支持
