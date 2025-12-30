# 知识图谱对齐工具

## 📦 概述

本工具实现了 User Guide 知识图谱和 Case Content 知识图谱之间的双向对齐，使得：
- **从实例到理论**：案例中的变量自动关联到 User Guide 中的物理概念
- **从理论到实例**：User Guide 概念自动关联到使用该概念的案例

## 🚀 快速开始

```bash
cd /media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam
./data/knowledge_graph/run_alignment.sh
```

**运行时间**：10-30 秒  
**输出位置**：
- `user_guide_knowledge_graph/aligned_user_guide_knowledge_graph.json`
- `case_content_knowledge_graph_aligned/*.json`

## 📊 对齐效果

成功运行后，你将获得：

**数据统计**：
- User Guide 节点：233 个
- Case Content 节点：3,989 个（28 个案例）

**对齐结果**：
- Case → Guide：283 个节点对齐（7.09% 覆盖率）
- Guide → Case：68 个节点对齐（29.18% 覆盖率）
- 平均每个 Guide 节点：5.0 个案例示例

**高频关联 Top 3**：
1. Euler (数值方法)：26 个示例
2. Solvers (概念簇)：26 个示例
3. RK2SSP (数值方法)：23 个示例

## 📁 文件说明

### 核心工具
- `align_knowledge_graphs_v1.py` - 对齐工具主程序
- `test_alignment.py` - 验证测试脚本
- `run_alignment.sh` - 一键运行脚本

### 文档
- `README.md` - 本文档（快速开始指南）
- `ALIGNMENT_GUIDE.md` - 详细使用指南和集成说明
- `BUGFIX_SUMMARY.md` - Bug 修复记录

## 🔑 对齐数据结构

### Case Content 节点新增字段
```json
{
  "label": "Variable",
  "properties": {
    "name": "JWL",
    "type": "EquationOfState",
    "concept_id": "model5.2.2.8",        // ← 新增：关联的 User Guide 节点 ID
    "concept_title": "JWL",              // ← 新增：概念标题
    "concept_type": "PhysicalModel"      // ← 新增：概念类型
  }
}
```

### User Guide 节点新增字段
```json
{
  "id": "model5.2.2.8",
  "title": "JWL",
  "semantic_type": "PhysicalModel",
  "tutorial_examples": [                 // ← 新增：使用该概念的案例
    {
      "node_id": "Variable_JWL",
      "case_name": "blastFoam_building3D",
      "source": "case_content",
      "properties": { "name": "JWL", "type": "EquationOfState" }
    }
  ],
  "tutorial_examples_count": 5           // ← 新增：示例数量
}
```

## 💻 使用示例

### 查找物理模型在哪些案例中使用
```python
import json

# 加载对齐后的 User Guide
with open('aligned_user_guide_knowledge_graph.json') as f:
    user_guide = json.load(f)

# 查找 JWL 模型
jwl_node = next((n for n in user_guide if n['title'] == 'JWL'), None)

# 获取使用该模型的案例
if jwl_node and 'tutorial_examples' in jwl_node:
    cases = {ex['case_name'] for ex in jwl_node['tutorial_examples']}
    print(f"JWL 在以下 {len(cases)} 个案例中使用:")
    for case in sorted(cases):
        print(f"  - {case}")
```

### 查找案例使用了哪些物理模型
```python
import json

# 加载对齐后的案例
with open('case_content_knowledge_graph_aligned/blastFoam_building3D.json') as f:
    case_graph = json.load(f)

# 提取所有对齐的物理模型
models = {
    n['properties']['concept_title'] 
    for n in case_graph['nodes'] 
    if 'concept_id' in n.get('properties', {})
}

print(f"building3D 案例使用了以下 {len(models)} 个模型:")
for model in sorted(models):
    print(f"  - {model}")
```

## 🔧 集成到检索系统

### 更新检索器以利用对齐数据

```python
class EnhancedRetriever:
    def search_with_theory(self, query: str):
        """检索案例时同时返回理论背景"""
        # 1. 找到相关案例节点
        case_nodes = self._find_case_nodes(query)
        
        # 2. 提取 concept_id
        concept_ids = [
            n['properties'].get('concept_id')
            for n in case_nodes
            if 'concept_id' in n.get('properties', {})
        ]
        
        # 3. 获取理论知识
        theory_nodes = self._get_user_guide_by_ids(concept_ids)
        
        return {
            'cases': case_nodes,
            'theory': theory_nodes
        }
    
    def search_with_examples(self, query: str):
        """检索理论时同时返回实例"""
        # 1. 找到相关理论节点
        theory_nodes = self._find_theory_nodes(query)
        
        # 2. 收集所有 tutorial_examples
        all_examples = []
        for node in theory_nodes:
            all_examples.extend(node.get('tutorial_examples', []))
        
        return {
            'theory': theory_nodes,
            'examples': all_examples
        }
```

## 🐛 故障排除

### 问题：对齐覆盖率偏低

**原因**：
- User Guide 包含许多理论概念，不是所有都会在案例中使用
- Case Content 中有许多配置参数，不是所有都对应理论概念
- 命名可能不完全一致（如 User Guide 用全名，案例用缩写）

**解决**：这是正常现象。当前使用简单的不区分大小写匹配，已能覆盖最常用的概念。

### 问题：运行失败

**检查清单**：
1. 确认输入文件存在：
   - `user_guide_knowledge_graph/user_guide_knowledge_graph.json`
   - `case_content_knowledge_graph/*.json`
2. 确认 Python 3.7+ 已安装
3. 查看错误日志，运行测试脚本：`python test_alignment.py`

### 问题：需要更新对齐结果

**解决**：
- 如果添加了新案例或更新了 User Guide，重新运行 `./run_alignment.sh` 即可
- 工具会覆盖之前的对齐结果

## 📚 进阶文档

- **ALIGNMENT_GUIDE.md** - 详细的技术文档、对齐逻辑说明、进阶用法
- **BUGFIX_SUMMARY.md** - 技术细节和 Bug 修复记录
- **../docs/knowledge_graph_alignment_solutions.md** - 完整的方案设计文档（4种方案）

## 📞 获取帮助

1. 查阅 `ALIGNMENT_GUIDE.md` 了解技术细节
2. 运行 `python test_alignment.py` 诊断问题
3. 查看运行日志了解错误详情

## ✅ 验证对齐结果

运行测试脚本验证对齐是否成功：

```bash
python test_alignment.py
```

预期输出：
```
✓ 通过: 5
✗ 失败: 0
🎉 所有测试通过！对齐工具运行正常。
```

---

**版本**: v1.1  
**最后更新**: 2025-10-24  
**状态**: ✅ 生产就绪
