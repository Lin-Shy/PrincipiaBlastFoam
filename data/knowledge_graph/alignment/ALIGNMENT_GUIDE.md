# 知识图谱对齐工具 - 详细指南

## 目录
- [工作原理](#工作原理)
- [对齐逻辑](#对齐逻辑)
- [输出文件详解](#输出文件详解)
- [集成指南](#集成指南)
- [进阶用法](#进阶用法)
- [性能优化](#性能优化)

## 工作原理

本工具实现了**轻量级标签对齐**方案，核心思路：

```
输入                           对齐工具                        输出
┌────────────┐              ┌──────────┐                  ┌────────────┐
│ User Guide │              │          │                  │  Aligned   │
│ 233 nodes  │─── title ───>│  Index   │                  │ User Guide │
└────────────┘   索引       │  Build   │                  │ + examples │
                             │          │                  └────────────┘
┌────────────┐              │  Match   │                  ┌────────────┐
│    Case    │              │  Engine  │                  │  Aligned   │
│ 3989 nodes │─── name ────>│          │                  │   Cases    │
│ (28 files) │   索引       │  Align   │                  │+concept_id │
└────────────┘              └──────────┘                  └────────────┘
                                  │
                         匹配逻辑：不区分大小写
                    case.name.lower() == guide.title.lower()
```

### 对齐流程

1. **加载数据**
   - 加载 User Guide 知识图谱（233 个节点）
   - 加载所有 Case Content 知识图谱（28 个文件）

2. **构建索引**
   - 为 User Guide 的 `title` 字段建立小写索引
   - 为 Case Content 的 `name` 字段建立小写索引

3. **双向对齐**
   - **Case → Guide**：为 Case 节点添加 `concept_id` 等字段
   - **Guide → Case**：为 Guide 节点添加 `tutorial_examples` 字段

4. **生成报告**
   - 统计对齐数量和覆盖率
   - 分析高频匹配
   - 识别未匹配节点

5. **保存结果**
   - 保存对齐后的 User Guide
   - 保存对齐后的所有 Case 文件

## 对齐逻辑

### 匹配规则

#### 1. Case → User Guide 匹配

```python
# 伪代码
for case_node in case_nodes:
    if case_node.label != 'Variable':
        continue  # 只对齐 Variable 节点
    
    name = case_node.properties.name.lower()
    
    if name in user_guide_title_index:
        matched_nodes = user_guide_title_index[name]
        
        # 优先选择 PhysicalModel 类型
        best_match = select_best_match(matched_nodes)
        
        # 添加对齐字段
        case_node.properties.concept_id = best_match.id
        case_node.properties.concept_title = best_match.title
        case_node.properties.concept_type = best_match.semantic_type
```

**关键点**：
- 只对齐 `Variable` 类型的节点
- 不区分大小写：`"JWL"` 匹配 `"jwl"`、`"Jwl"` 等
- 多个匹配时优先选择 `PhysicalModel` 类型

#### 2. User Guide → Case 匹配

```python
# 伪代码
for guide_node in user_guide_nodes:
    title = guide_node.title.lower()
    
    if title in case_name_index:
        matched_cases = case_name_index[title]
        
        # 收集所有匹配的案例信息
        examples = []
        for case_info in matched_cases:
            examples.append({
                'case_name': case_info.case_name,
                'variable_name': case_info.node.properties.name,
                'variable_type': case_info.node.properties.type,
                'file_path': case_info.node.properties.path
            })
        
        # 添加到 Guide 节点
        guide_node.tutorial_examples = examples
        guide_node.tutorial_examples_count = len(examples)
```

**关键点**：
- 所有类型的 Guide 节点都参与匹配
- 可能匹配到多个案例（一对多关系）
- 保留完整的案例上下文信息

### 匹配示例

**示例 1：JWL 状态方程**

User Guide 节点：
```json
{
  "id": "model5.2.2.8",
  "title": "JWL",
  "semantic_type": "PhysicalModel"
}
```

Case Content 节点：
```json
{
  "id": "Variable_123",
  "label": "Variable",
  "properties": {
    "name": "JWL",
    "type": "EquationOfState",
    "path": "constant/phaseProperties"
  }
}
```

匹配过程：
```
"JWL".lower() == "jwl".lower()  ✓ 匹配成功

对齐后 Case 节点：
{
  "properties": {
    "name": "JWL",
    "concept_id": "model5.2.2.8",      ← 新增
    "concept_title": "JWL",            ← 新增
    "concept_type": "PhysicalModel"    ← 新增
  }
}

对齐后 Guide 节点：
{
  "id": "model5.2.2.8",
  "title": "JWL",
  "tutorial_examples": [              ← 新增
    {
      "case_name": "blastFoam_building3D",
      "variable_name": "JWL",
      ...
    }
  ]
}
```

**示例 2：大小写不敏感**

| User Guide | Case Content | 结果 |
|-----------|-------------|------|
| `SchillerNaumann` | `schillernaumann` | ✓ 匹配 |
| `Gauss` | `gauss` | ✓ 匹配 |
| `RK2SSP` | `rk2ssp` | ✓ 匹配 |

## 输出文件详解

### 对齐后的 User Guide

**路径**: `user_guide_knowledge_graph/aligned_user_guide_knowledge_graph.json`

**结构变化**：
```json
{
  "id": "model5.2.2.8",
  "parentId": "sec5.2.2",
  "semantic_type": "PhysicalModel",
  "title": "JWL",
  "number": "5.2.2.8",
  "content_summary": "Jones-Wilkins-Lee equation of state...",
  "content": "...",
  
  // ========== 新增字段 ==========
  "tutorial_examples": [
    {
      "node_id": "Variable_JWL",
      "node_label": "Variable",
      "source": "case_content",
      "case_name": "blastFoam_building3D",
      "case_path": "constant/phaseProperties",
      "properties": {
        "name": "JWL",
        "type": "EquationOfState",
        "path": "..."
      }
    },
    // ... 更多示例
  ],
  "tutorial_examples_count": 5
}
```

**字段说明**：
- `tutorial_examples`: 数组，包含所有使用该概念的案例
  - `node_id`: Case 中的节点 ID
  - `case_name`: 案例名称
  - `source`: 固定为 `"case_content"`
  - `properties`: 变量的详细信息
- `tutorial_examples_count`: 示例数量

### 对齐后的 Case Content

**路径**: `case_content_knowledge_graph_aligned/*.json`（每个案例一个文件）

**结构变化**：
```json
{
  "nodes": [
    {
      "id": "Variable_JWL",
      "label": "Variable",
      "properties": {
        "name": "JWL",
        "type": "EquationOfState",
        "path": "constant/phaseProperties",
        
        // ========== 新增字段 ==========
        "concept_id": "model5.2.2.8",
        "concept_title": "JWL",
        "concept_type": "PhysicalModel"
      }
    },
    // ... 更多节点
  ],
  "edges": [...]
}
```

**字段说明**：
- `concept_id`: 对应的 User Guide 节点 ID
- `concept_title`: 概念标题
- `concept_type`: 概念类型（PhysicalModel、NumericalMethod 等）

## 集成指南

### 方案 1：增强现有检索器

```python
class EnhancedCaseRetriever:
    """增强的案例检索器，支持理论关联"""
    
    def __init__(self):
        # 加载对齐后的图谱
        self.case_graphs = self._load_aligned_cases()
        self.user_guide = self._load_aligned_user_guide()
    
    def search_with_theory(self, query: str) -> dict:
        """检索案例，同时返回相关理论"""
        # 1. 搜索相关案例节点
        case_nodes = self._semantic_search(query)
        
        # 2. 提取 concept_id
        concept_ids = set()
        for node in case_nodes:
            concept_id = node.get('properties', {}).get('concept_id')
            if concept_id:
                concept_ids.add(concept_id)
        
        # 3. 获取理论知识
        theory_nodes = [
            n for n in self.user_guide 
            if n['id'] in concept_ids
        ]
        
        return {
            'case_examples': case_nodes,
            'theory_background': theory_nodes,
            'alignment_count': len(concept_ids)
        }
```

### 方案 2：创建统一检索接口

```python
class UnifiedKnowledgeRetriever:
    """统一的知识检索接口"""
    
    def __init__(self):
        self.case_retriever = EnhancedCaseRetriever()
        self.guide_retriever = EnhancedGuideRetriever()
    
    def search(self, query: str, mode='both'):
        """
        统一检索接口
        
        Args:
            query: 检索查询
            mode: 'theory' | 'practice' | 'both'
        """
        results = {}
        
        if mode in ['practice', 'both']:
            # 搜索案例并关联理论
            case_results = self.case_retriever.search_with_theory(query)
            results['practice'] = case_results
        
        if mode in ['theory', 'both']:
            # 搜索理论并关联案例
            guide_results = self.guide_retriever.search_with_examples(query)
            results['theory'] = guide_results
        
        # 计算对齐统计
        results['stats'] = self._calculate_alignment_stats(results)
        
        return results
```

### 方案 3：RAG 增强

```python
def generate_response_with_alignment(query: str, llm):
    """使用对齐数据增强 RAG"""
    
    # 1. 检索相关知识
    retriever = UnifiedKnowledgeRetriever()
    results = retriever.search(query, mode='both')
    
    # 2. 构建上下文
    context_parts = []
    
    # 理论部分
    for theory in results.get('theory', {}).get('theory', []):
        context_parts.append(f"理论：{theory['title']}")
        context_parts.append(theory['content_summary'])
    
    # 实践部分
    for example in results.get('theory', {}).get('examples', []):
        case_name = example.get('case_name', 'Unknown')
        var_name = example.get('properties', {}).get('name', '')
        context_parts.append(f"实例：{case_name} 使用了 {var_name}")
    
    context = "\n\n".join(context_parts)
    
    # 3. 生成回答
    prompt = f"""基于以下理论和实践知识回答问题：

{context}

问题：{query}

请结合理论和实践给出全面的回答。
"""
    
    response = llm.generate(prompt)
    return response
```

## 进阶用法

### 自定义匹配逻辑

如果需要更复杂的匹配，可以继承并重写：

```python
from align_knowledge_graphs_v1 import KnowledgeGraphAligner

class FuzzyAligner(KnowledgeGraphAligner):
    """支持模糊匹配的对齐器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加同义词映射
        self.synonyms = {
            'jwl': ['jones-wilkins-lee', 'jwl'],
            'eos': ['equation of state', 'eos'],
        }
    
    def _find_matching_concept(self, var_name: str):
        """增强的匹配方法，支持同义词"""
        var_name_lower = var_name.lower()
        
        # 1. 精确匹配
        if var_name_lower in self.title_to_user_guide_nodes:
            return super()._find_matching_concept(var_name)
        
        # 2. 同义词匹配
        for key, synonyms in self.synonyms.items():
            if var_name_lower in synonyms:
                if key in self.title_to_user_guide_nodes:
                    return self.title_to_user_guide_nodes[key][0]
        
        # 3. 模糊匹配（编辑距离）
        from difflib import get_close_matches
        matches = get_close_matches(
            var_name_lower, 
            self.title_to_user_guide_nodes.keys(),
            n=1,
            cutoff=0.8
        )
        if matches:
            return self.title_to_user_guide_nodes[matches[0]][0]
        
        return None
```

### 批量验证对齐质量

```python
import random

def validate_alignment_quality(aligned_graph_path: str, sample_size: int = 50):
    """随机抽样验证对齐质量"""
    
    with open(aligned_graph_path) as f:
        graph = json.load(f)
    
    # 找出所有对齐的节点
    aligned_nodes = [
        node for node in graph['nodes']
        if 'concept_id' in node.get('properties', {})
    ]
    
    # 随机抽样
    samples = random.sample(aligned_nodes, min(sample_size, len(aligned_nodes)))
    
    correct = 0
    wrong = 0
    
    for node in samples:
        props = node['properties']
        print(f"\n变量名: {props['name']}")
        print(f"概念标题: {props['concept_title']}")
        print(f"概念类型: {props['concept_type']}")
        
        answer = input("是否正确匹配？(y/n/s=skip): ").lower()
        if answer == 'y':
            correct += 1
        elif answer == 'n':
            wrong += 1
    
    total = correct + wrong
    if total > 0:
        accuracy = correct / total * 100
        print(f"\n准确率: {accuracy:.1f}% ({correct}/{total})")
    
    return correct, wrong
```

## 性能优化

### 1. 增量对齐

如果只添加了少量新案例，可以只对齐新案例：

```python
def incremental_align(new_case_files: list):
    """增量对齐新添加的案例"""
    aligner = KnowledgeGraphAligner()
    
    # 只加载 User Guide
    aligner.load_user_guide()
    
    # 只加载新案例
    for case_file in new_case_files:
        aligner._load_single_case(case_file)
    
    # 执行对齐
    aligner.align_case_content_to_user_guide()
    
    # 保存结果
    aligner.save_aligned_graphs()
```

### 2. 并行处理

对于大量案例，可以并行处理：

```python
from multiprocessing import Pool

def align_single_case(case_file: str, user_guide: dict):
    """对齐单个案例"""
    # 实现单个案例的对齐逻辑
    pass

def parallel_align(case_files: list, num_workers: int = 4):
    """并行对齐多个案例"""
    with Pool(num_workers) as pool:
        results = pool.starmap(
            align_single_case,
            [(f, user_guide) for f in case_files]
        )
    return results
```

### 3. 缓存索引

对于频繁运行，可以缓存索引：

```python
import pickle

class CachedAligner(KnowledgeGraphAligner):
    """支持索引缓存的对齐器"""
    
    def load_user_guide(self):
        cache_file = self.cache_dir / 'user_guide_index.pkl'
        
        if cache_file.exists():
            # 加载缓存
            with open(cache_file, 'rb') as f:
                self.title_to_user_guide_nodes = pickle.load(f)
        else:
            # 构建索引
            super().load_user_guide()
            # 保存缓存
            with open(cache_file, 'wb') as f:
                pickle.dump(self.title_to_user_guide_nodes, f)
```

## 常见问题

### Q: 为什么覆盖率只有 7-30%？

**A**: 这是正常现象，原因：
1. User Guide 包含许多理论概念，不是所有都会在案例中使用
2. Case Content 中有很多配置参数，不是所有都对应理论概念
3. 当前使用简单匹配，已能覆盖最常用的核心概念

### Q: 如何提高对齐准确率？

**A**: 
1. **添加同义词映射**：处理命名差异
2. **引入类型过滤**：只匹配相同类型的节点
3. **考虑上下文**：利用父节点信息
4. **人工审核**：定期验证高频匹配
5. **建立负例**：排除已知的误匹配

### Q: 对齐结果如何更新？

**A**: 
- 添加新案例或更新 User Guide 后，重新运行 `./run_alignment.sh`
- 工具会完全重新对齐，覆盖旧结果
- 如果只更新少量案例，可以使用增量对齐（见性能优化部分）

### Q: 如何验证对齐质量？

**A**:
1. 运行 `python test_alignment.py` 进行自动测试
2. 使用本文档的"批量验证"脚本进行人工抽样
3. 查看对齐报告中的高频匹配，判断是否合理
4. 在实际使用中收集反馈

---

**版本**: v1.1  
**最后更新**: 2025-10-24
