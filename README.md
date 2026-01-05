# PrincipiaBlastFoam

PrincipiaBlastFoam is a multi-agent collaboration system based on the **ReAct (Reasoning + Acting) paradigm** and the **OASiS (Open Agent System for Simulation)** architecture, designed to automate **OpenFOAM** (specifically **blastFoam**) simulation tasks.

By leveraging Large Language Models (LLMs) and Knowledge Graph technology, the system coordinates multiple specialized agents to achieve full-process automation from user natural language requirements to physical simulation results.

## 🌟 Core Features

*   **Multi-Agent Collaboration based on ReAct Paradigm**: Deeply integrates the **ReAct (Reasoning + Acting)** philosophy, endowing agents with a "Think-Act-Observe" loop capability. An Orchestrator agent dynamically reasons based on the current state and schedules expert agents (Physics Analyst, Case Setup, Execution, etc.) to achieve adaptive problem-solving for complex tasks.
*   **Knowledge-Enhanced Retrieval**: Integrates User Guide and Case Content Knowledge Graphs, employing hierarchical retrieval and context-enhanced strategies to ensure agents obtain accurate physical knowledge and case configuration information.
*   **Automated Workflow**: Supports the entire process from scratch: case initialization, parameter modification, simulation execution, log monitoring, to result analysis.
*   **Deep BlastFoam Support**: Specifically optimized and knowledge-base constructed for explosion mechanics simulation (blastFoam).

## 🏗️ System Architecture

The system is built on LangGraph and includes the following core agents:

*   **OrchestratorAgent**: The commander of tasks, responsible for planning, scheduling other agents, and handling feedback.
*   **PhysicsAnalystAgent**: Analyzes user requirements and formulates simulation plans combining physical knowledge.
*   **CaseSetupAgent**: Responsible for generating and configuring OpenFOAM case files (0/, constant/, system/).
*   **ExecutionAgent**: Writes run scripts (Allrun), executes simulations, and monitors logs.
*   **PostProcessingAgent**: Extracts key data and generates charts and reports.
*   **ReviewerAgent**: Responsible for quality assurance, checking outputs at each stage, and diagnosing errors.

For detailed architecture description, please refer to [docs/MULTI_AGENT_DESIGN.md](docs/MULTI_AGENT_DESIGN.md).

## 🚀 Quick Start

### Requirements

*   Linux (Recommended)
*   Python 3.10+
*   OpenFOAM / blastFoam environment
*   Neo4j (for Knowledge Graph storage)

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

1.  Copy the example environment variable file:
    ```bash
    cp example.env .env
    ```
2.  Edit the `.env` file to configure LLM API and Neo4j connection information.

### Running Examples

**1. Knowledge Graph Retrieval Demo**

Run the following command to see the effect of the improved retrieval strategy:

```bash
python example_improved_retrieval.py
```

**2. Run Full Workflow**

Edit the `CASE_PATH` and `user_request` variables in `run_workflow.py` to define your simulation task, then run:

```bash
python run_workflow.py
```

## 📂 Project Structure

```
PrincipiaBlastFoam/
├── principia_ai/           # Core code package
│   ├── agents/             # Agent implementations
│   ├── graph/              # Workflow graph definition
│   ├── tools/              # Toolset (Retrieval, File operations, etc.)
│   └── ...
├── data/                   # Data files
│   ├── knowledge_graph/    # Knowledge Graph data
│   └── ...
├── docs/                   # Project documentation
├── experiments/            # Experiments and evaluation scripts
├── scripts/                # Helper scripts
├── tests/                  # Test cases
├── run_workflow.py         # Main run script
├── QUICKSTART.md           # Quick start guide
└── requirements.txt        # Project dependencies
```

## 📚 Documentation

*   [Quick Start Guide](QUICKSTART.md)
*   [Multi-Agent System Design (ReAct Architecture)](docs/MULTI_AGENT_DESIGN.md)
*   [Quantitative Metrics Implementation](docs/量化指标实现方案.md)

## 🤝 Contribution

Issues and Pull Requests are welcome to improve this project.
