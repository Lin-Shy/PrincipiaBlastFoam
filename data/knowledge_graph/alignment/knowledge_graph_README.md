# blastFoam 知识图谱（Knowledge Graph）

该目录存放了用于 blastFoam 案例自动生成的知识图谱及相关工具。整个知识系统由两个核心知识图谱和一个对齐过程组成，旨在将具体的实例知识与抽象的概念知识相关联。

## 📚 快速导航

- **[README.md](./README.md)** - 快速开始指南和基本用法
- **[ALIGNMENT_GUIDE.md](./ALIGNMENT_GUIDE.md)** - 详细的技术文档和进阶用法
- **[BUGFIX_SUMMARY.md](./BUGFIX_SUMMARY.md)** - Bug 修复记录

## 知识图谱体系

我们的知识体系包含两个图谱：

1. **Case Content 知识图谱（实例知识）**: 从 blastFoam 教程案例中提取，代表具体的、可直接使用的配置实例。
2. **User Guide 知识图谱（概念知识）**: 从 blastFoam 用户指南中构建，代表通用的、抽象的物理和软件概念。

通过将两者对齐，我们可以为具体的实例（例如，`phaseProperties` 文件中的 `JWL` 状态方程）找到其在用户指南中的理论解释，从而增强知识的深度和可用性。

### 1. Case Content 知识图谱（实例知识）

- **来源**: blastFoam 教程案例 (`reference_cases/`)
- **输出**: `case_content_knowledge_graph/*.json`（每个案例一个文件）
- **描述**: 该图谱包含了从教程案例中解析出的实体，如案例 (`Case`)、文件 (`File`)、变量 (`Variable`) 等。节点代表了在特定案例中使用的具体设置。

### 2. User Guide 知识图谱（概念知识）

- **来源**: blastFoam 用户指南
- **构建方法**: 使用大型语言模型（LLM）从文档中提取概念、定义和层次关系
- **输出**: `user_guide_knowledge_graph/user_guide_knowledge_graph.json`
- **描述**: 该图谱以树状结构组织了 blastFoam 的核心概念，包含 233 个节点，涵盖物理模型 (`PhysicalModel`)、数值方法 (`NumericalMethod`)、控制方程 (`GoverningEquation`) 等。

### 3. 知识图谱对齐

- **目的**: 将 Case Content 中的具体节点链接到 User Guide 中的抽象定义
- **对齐工具**: `align_knowledge_graphs_v1.py`
- **核心逻辑**:
  1. 为 Case 节点添加 `concept_id` 字段，指向 User Guide 中的概念
  2. 为 User Guide 节点添加 `tutorial_examples` 字段，列出使用该概念的案例
- **对齐方式**: 基于不区分大小写的名称匹配
- **输出**:
  - `user_guide_knowledge_graph/aligned_user_guide_knowledge_graph.json`
  - `case_content_knowledge_graph_aligned/*.json`

## 目录结构

-   `/data/knowledge_graph/`: 知识图谱根目录
    -   `/tutorial_knowledge_graph/`: 存放实例知识图谱及其构建和对齐工具。
    -   `/user_guide_knowledge_graph/`: 存放从用户指南中提取的概念知识图谱。

## 🚀 快速开始

```bash
# 运行对齐工具
cd /media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam
./data/knowledge_graph/run_alignment.sh
```

详细使用说明请参考 [README.md](./README.md)。

## 在智能体工作流中的应用

对齐后的知识图谱为智能体（Agent）提供了更强大的能力：

1. **检索增强**: 检索案例时自动关联理论背景，检索理论时自动提供实例参考
2. **智能推荐**: 基于已有案例的使用模式推荐合适的物理模型
3. **错误诊断**: 从实例追溯到概念，帮助定位配置问题的根本原因
4. **知识问答**: 结合理论和实践，提供更全面的回答

## 目录结构

```
data/knowledge_graph/
├── README.md                           # 快速开始指南
├── ALIGNMENT_GUIDE.md                  # 详细技术文档
├── BUGFIX_SUMMARY.md                   # Bug 修复记录
├── align_knowledge_graphs_v1.py        # 对齐工具
├── test_alignment.py                   # 测试脚本
├── run_alignment.sh                    # 一键运行脚本
├── user_guide_knowledge_graph/         # User Guide 知识图谱
│   ├── user_guide_knowledge_graph.json
│   └── aligned_user_guide_knowledge_graph.json  # 对齐后
├── case_content_knowledge_graph/       # Case Content 知识图谱
│   ├── blastFoam_building3D.json
│   ├── blastEulerFoam_reactingParticles.json
│   └── ...
└── case_content_knowledge_graph_aligned/  # 对齐后的 Case 图谱
    ├── blastFoam_building3D.json
    └── ...
```

## 相关文档

- [完整方案设计](../../docs/knowledge_graph_alignment_solutions.md) - 4 种对齐方案的详细设计
-   开发知识图谱的可视化工具。
-   建立一个用户界面，方便手动管理和扩充知识图谱。
