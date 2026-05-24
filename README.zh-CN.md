# PrincipiaBlastFoam

PrincipiaBlastFoam 是一个基于 **ReAct (Reasoning + Acting) 范式** 和 **OASiS (Open Agent System for Simulation)** 架构的多智能体协作系统，专为自动化 **OpenFOAM**（特别是 **blastFoam**）仿真任务而设计。

该系统利用大语言模型（LLM）和知识图谱技术，通过协调多个专业智能体，实现从用户自然语言需求到物理仿真结果的全流程自动化。

## 🌟 核心特性

*   **基于 ReAct 范式的多智能体协作**: 深度融合 **ReAct (Reasoning + Acting)** 思想，赋予智能体“思考-行动-观察”的循环能力。由协调智能体（Orchestrator）基于当前状态动态推理并调度物理分析、算例设置、执行等专家智能体，实现复杂任务的自适应求解。
*   **知识增强检索**: 集成 User Guide 和 Case Content 知识图谱，采用层次化检索和上下文增强策略，确保智能体获取准确的物理知识和算例配置信息。
*   **MCP 检索服务**: 提供 `principia_retrieval` MCP server，可将案例内容知识图谱常驻加载为工具服务，避免每个 agent 重复初始化检索器。
*   **自动化工作流**: 支持从零开始初始化算例、修改参数、运行仿真、监控日志到结果分析的全过程。
*   **执行安全护栏**: 增加工具路径作用域、敏感输出脱敏、执行前环境检查和产物契约校验，减少误读敏感文件或错误结束 workflow 的风险。
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
*   用于运行 OpenFOAM/blastFoam 的普通 Linux 用户（不建议使用 root 直接运行求解器）
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
2.  编辑 `.env` 文件，配置 LLM API 和 Neo4j 连接信息。真实 `.env` 已被 Git 忽略，不应提交到仓库。

### 运行示例

**1. 检索评测**

检索评测入口位于 `experiments/retrieval_method/`：

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py --benchmark user_guide
```

case-content、embedding 等评测命令见 [experiments/retrieval_method/README.md](experiments/retrieval_method/README.md)。

**2. MCP 检索服务测试**

MCP server 位于 `mcp_servers/principia_retrieval/`，会在一个常驻进程中加载 Case Content 知识图谱，并向 LangChain/LangGraph 暴露工具。

```bash
python -m mcp_servers.principia_retrieval.test_client
python examples/mcp/langchain_mcp_client_example.py
```

可用工具包括 `get_case_by_intent`、`get_files_for_case`、`find_variable`、`get_file_content`、`get_modification_targets`、`search_case_content` 和 `search_user_guide`。

**3. 运行完整工作流**

通过命令行参数传入目标算例目录和自然语言任务：

```bash
python run_workflow.py \
  --case-path /data/PrincipiaBlastFoam_output/surfaceburst_scaledd3 \
  --user-request "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。"
```

> 注意：OpenFOAM 的 `#calc` / `#codeStream` 等功能会触发动态代码编译和加载。root 用户执行这类算例时可能被 OpenFOAM 安全检查拒绝，典型表现是 `blockMesh` 报 dynamicCode 安全错误。建议用普通用户运行实际 OpenFOAM/blastFoam workflow。端到端 benchmark runner 支持 `--run-as-user openfoam` 或 `OPENFOAM_RUN_AS_USER=openfoam`，并会把每轮输出目录授权给该用户。

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
├── mcp_servers/            # MCP 服务（检索工具服务化）
├── examples/               # 集成示例
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
