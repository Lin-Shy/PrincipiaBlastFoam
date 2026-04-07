# PrincipiaBlastFoam

PrincipiaBlastFoam 是一个基于 **ReAct (Reasoning + Acting) 范式** 和 **OASiS (Open Agent System for Simulation)** 架构的多智能体协作系统，专为自动化 **OpenFOAM**（特别是 **blastFoam**）仿真任务而设计。

该系统利用大语言模型（LLM）和知识图谱技术，通过协调多个专业智能体，实现从用户自然语言需求到物理仿真结果的全流程自动化。

## 🌟 核心特性

*   **基于 ReAct 范式的多智能体协作**: 深度融合 **ReAct (Reasoning + Acting)** 思想，赋予智能体“思考-行动-观察”的循环能力。由协调智能体（Orchestrator）基于当前状态动态推理并调度物理分析、算例设置、执行等专家智能体，实现复杂任务的自适应求解。
*   **知识增强检索**: 集成 User Guide 和 Case Content 知识图谱，采用层次化检索和上下文增强策略，确保智能体获取准确的物理知识和算例配置信息。
*   **自动化工作流**: 支持从零开始初始化算例、修改参数、运行仿真、监控日志到结果分析的全过程。
*   **BlastFoam 深度支持**: 针对爆炸力学仿真（blastFoam）进行了专门的优化和知识库构建。

## 🏗️ 系统架构

系统基于 LangGraph 构建，包含以下核心智能体：

*   **OrchestratorAgent (协调者)**: 任务的总指挥，负责规划任务、调度其他智能体并处理反馈。
*   **PhysicsAnalystAgent (物理分析师)**: 分析用户需求，结合物理知识制定仿真方案。
*   **CaseSetupAgent (设置专家)**: 负责 OpenFOAM 算例文件的生成和配置（0/, constant/, system/）。
*   **ExecutionAgent (执行员)**: 编写运行脚本（Allrun），执行仿真并监控日志。
*   **PostProcessingAgent (分析师)**: 提取关键数据，生成图表和报告。
*   **ReviewerAgent (审查员)**: 负责质量保证，检查各阶段输出并诊断错误。

详细架构说明请参考 [docs/MULTI_AGENT_DESIGN.md](docs/MULTI_AGENT_DESIGN.md)。

## 🚀 快速开始

### 环境要求

*   Linux (推荐)
*   Python 3.10+
*   OpenFOAM / blastFoam 环境
*   Neo4j (用于知识图谱存储)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

1.  复制示例环境变量文件：
    ```bash
    cp example.env .env
    ```
2.  编辑 `.env` 文件，配置 LLM API 和 Neo4j 连接信息。

### 运行示例

**1. 知识图谱检索演示**

运行以下命令查看改进后的检索策略效果：

```bash
python example_improved_retrieval.py
```

**2. 运行完整工作流**

编辑 `run_workflow.py` 中的 `CASE_PATH` 和 `user_request` 变量，定义你的仿真任务，然后运行：

```bash
python run_workflow.py
```

## 📂 项目结构

```
PrincipiaBlastFoam/
├── principia_ai/           # 核心代码包
│   ├── agents/             # 智能体实现
│   ├── graph/              # 工作流图定义
│   ├── tools/              # 工具集 (检索、文件操作等)
│   └── ...
├── data/                   # 数据文件
│   ├── knowledge_graph/    # 知识图谱数据
│   └── ...
├── docs/                   # 项目文档
├── experiments/            # 实验与评估脚本
├── scripts/                # 辅助脚本
├── tests/                  # 测试用例
├── run_workflow.py         # 主运行脚本
├── QUICKSTART.md           # 快速入门指南
└── requirements.txt        # 项目依赖
```

## 📚 文档

*   [快速开始指南](QUICKSTART.md)
*   [多智能体系统设计说明 (ReAct 架构)](docs/MULTI_AGENT_DESIGN.md)
*   [量化指标实现方案](docs/量化指标实现方案.md)
*   [检索评测说明](experiments/retrieval_method/README.md)
*   [案例内容检索方法文档](docs/检索方法/案例内容知识检索技术文档.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进本项目。
