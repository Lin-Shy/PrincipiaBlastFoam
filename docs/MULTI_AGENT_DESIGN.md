# 多智能体系统设计说明文档

## 1. 系统概述

本项目采用基于 ReAct (Reasoning and Acting) 范式的多智能体（Multi-Agent）架构，旨在自动化处理 OpenFOAM 仿真流程。系统由一个核心协调者（Orchestrator）和多个专注于特定领域的专家智能体（Specialist Agents）组成。

该架构的设计目标是将复杂的仿真任务分解为可管理的子任务，通过智能体之间的协作，实现从案例分析、参数设置、仿真运行到后处理分析的全流程自动化。

## 2. 智能体角色定义

系统包含以下核心智能体，每个智能体承担特定的职责：

### 2.1 核心协调者
*   **Orchestrator Agent (协调者智能体)**
    *   **角色**: 项目经理 / 大脑。
    *   **职责**: 负责整体任务的规划、协调和委派。它不直接执行具体的仿真操作，而是根据用户目标和当前状态，制定执行计划，并将任务分发给合适的专家智能体。
    *   **能力**: 具备全局视野，能够评估项目状态，制定分步计划，并监控任务进度。

### 2.2 专家智能体 (The "Hands")
*   **Physics Analyst Agent (物理分析师智能体)**
    *   **角色**: 领域专家 / 顾问。
    *   **职责**: 负责分析仿真案例的物理背景，生成符合求解器（如 blastFoam）要求的修改计划。它不直接修改文件，而是提供专业的修改建议和参数配置方案。
    *   **能力**: 理解物理模型、边界条件和求解器约束。

*   **Case Setup Agent (案例设置智能体)**
    *   **角色**: 执行工程师 / 操作员。
    *   **职责**: 根据物理分析师的计划或协调者的指令，直接修改 OpenFOAM 的配置文件（如 `0/`, `constant/`, `system/` 目录下的文件）。
    *   **能力**: 精确操作文件系统，修改字典文件，确保语法正确。

*   **Execution Agent (执行智能体)**
    *   **角色**: 仿真工程师。
    *   **职责**: 负责运行仿真求解器，监控运行日志，处理运行时的错误或发散问题。
    *   **能力**: 执行 Shell 命令，解析日志文件，判断仿真状态。

*   **Post Processing Agent (后处理智能体)**
    *   **角色**: 数据分析师。
    *   **职责**: 负责仿真结果的数据提取、处理和可视化。
    *   **能力**: 使用后处理工具（如 ParaView 脚本、Python 库）生成图表和报告。

*   **Reviewer (审查者智能体)**
    *   **角色**: 质量保证 / 审核员。
    *   **职责**: 检查各阶段的输出结果是否符合预期，验证仿真结果的合理性。
    *   **能力**: 逻辑校验，结果验证。

## 3. ReAct 范式设计

本系统的智能体设计深度融合了 ReAct (Reasoning + Acting) 思想，使智能体具备“思考-行动-观察”的循环能力。

### 3.1 认知过程 (Cognitive Process)
每个智能体（特别是 Orchestrator）在执行任务前，都会遵循以下认知流程：

1.  **理解目标 (Understand Goal)**: 明确当前任务的“完成定义”是什么。
2.  **评估状态 (Assess State)**: 利用工具（Observation）获取当前环境的真实状态，而不是基于假设。
3.  **制定计划 (Formulate Plan)**: 基于目标和状态，进行推理（Reasoning），将剩余工作分解为离散的步骤。
4.  **执行/委派 (Act/Delegate)**: 
    *   对于 Orchestrator：选择一个合适的专家智能体，并提供清晰的指令。
    *   对于专家智能体：调用具体的工具（如文件读写、命令执行）来完成任务。
5.  **完成 (Finish)**: 确认任务完成后，报告结果。

### 3.2 思考与行动的循环
*   **Reasoning (推理)**: 智能体在采取行动前，会在“思维链”中进行推理，分析当前情况，决定下一步该做什么。例如，Orchestrator 会思考：“用户想要修改边界条件，但我不知道当前边界条件是什么，所以我需要先让 Physics Analyst 去分析。”
*   **Acting (行动)**: 基于推理结果，智能体调用工具（Tools）。
*   **Observation (观察)**: 工具执行后返回结果（如文件内容、命令输出），智能体根据这些反馈进行新一轮的推理。

## 4. 协作工作流

1.  **用户输入**: 用户提供一个仿真目标（例如：“将入口速度改为 100m/s 并运行仿真”）。
2.  **Orchestrator 规划**: Orchestrator 接收请求，分析当前案例状态，生成高层计划。
3.  **任务分发**:
    *   Orchestrator -> Physics Analyst: “分析当前 `0/U` 文件，制定修改速度为 100m/s 的方案。”
    *   Physics Analyst -> Orchestrator: 返回具体的修改参数和建议。
    *   Orchestrator -> Case Setup Agent: “根据上述建议，修改 `0/U` 文件。”
    *   Case Setup Agent -> Orchestrator: “文件修改完成。”
    *   Orchestrator -> Execution Agent: “运行求解器。”
4.  **闭环反馈**: 每个步骤完成后，Orchestrator 都会重新评估状态，确保任务按计划推进，直到最终目标达成。

## 5. 当前运行时保护机制

近期代码在原有 ReAct 流程上增加了几类防护，避免 workflow 在不完整或不安全的状态下继续推进：

1.  **结构化路由**: Orchestrator 优先使用结构化输出解析 `next_agent` 和 `task_instructions`，并对 agent 名称做别名归一化。若模型或 provider 不支持结构化输出，可通过 `ORCHESTRATOR_LEGACY_FALLBACK` 回退到旧的文本解析路径。
2.  **工具路径作用域**: 文件读取、搜索、编辑和终端执行工具会在当前 case 目录上下文中解析相对路径，降低 agent 误操作仓库根目录或读取无关文件的概率。
3.  **敏感信息脱敏**: 工具输出、agent 日志、benchmark 日志和 Git diff 会过滤 `.env` 等敏感文件，并对常见 API key、token、password 字段做脱敏。
4.  **执行前检查**: ExecutionAgent 在启动求解器前检查 case 目录、`Allrun`、并行运行依赖、root + dynamicCode 风险以及 OpenFOAM 命令可用性。阻塞项会写入 `execution_report.md` 和 `execution_status.json`。
5.  **产物契约校验**: Physics report、post-processing report 和执行状态都有最低可用性校验。若报告为空、过短或包含明显 agent/tool 错误，workflow 会标记失败而不是误报完成。

相关环境变量包括 `AGENT_RUNTIME`、`LANGGRAPH_CHECKPOINTS`、`ORCHESTRATOR_STRUCTURED_OUTPUT`、`LLM_STRUCTURED_OUTPUT`、`LLM_THINKING` 和 `ALLOW_ROOT_OPENFOAM`。
