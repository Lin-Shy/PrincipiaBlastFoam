# PrincipiaBlastFoam

PrincipiaBlastFoam is a multi-agent collaboration system based on the **ReAct (Reasoning + Acting) paradigm** and the **OASiS (Open Agent System for Simulation)** architecture, designed to automate **OpenFOAM** (specifically **blastFoam**) simulation tasks.

By leveraging Large Language Models (LLMs) and Knowledge Graph technology, the system coordinates multiple specialized agents to achieve full-process automation from user natural language requirements to physical simulation results.

## 🌟 Core Features

*   **Multi-Agent Collaboration based on ReAct Paradigm**: Deeply integrates the **ReAct (Reasoning + Acting)** philosophy, endowing agents with a "Think-Act-Observe" loop capability. An Orchestrator agent dynamically reasons based on the current state and schedules expert agents (Physics Analyst, Case Setup, Execution, etc.) to achieve adaptive problem-solving for complex tasks.
*   **Knowledge-Enhanced Retrieval**: Integrates User Guide and Case Content Knowledge Graphs, employing hierarchical retrieval and context-enhanced strategies to ensure agents obtain accurate physical knowledge and case configuration information.
*   **MCP Retrieval Service**: Provides the `principia_retrieval` MCP server so retrieval tools can be loaded once and reused by LangChain/LangGraph agents.
*   **Automated Workflow**: Supports the entire process from scratch: case initialization, parameter modification, simulation execution, log monitoring, to result analysis.
*   **Execution Guardrails**: Adds scoped file tools, sensitive-output redaction, environment preflight checks, and artifact validation to reduce unsafe or incomplete workflow runs.
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
*   A non-root Linux user for running OpenFOAM/blastFoam solvers
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
2.  Edit the `.env` file to configure LLM API and Neo4j connection information. The real `.env` file is ignored by Git and must not be committed.

### Running Examples

**1. Retrieval Evaluation**

The retrieval benchmark entry points live under `experiments/retrieval_method/`:

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py --benchmark user_guide
```

See [experiments/retrieval_method/README.md](experiments/retrieval_method/README.md) for case-content and embedding benchmark commands.

**2. MCP Retrieval Server Smoke Test**

```bash
python -m mcp_servers.principia_retrieval.test_client
python examples/mcp/langchain_mcp_client_example.py
```

**3. Run Full Workflow**

Pass the target case directory and natural-language request to `run_workflow.py`:

```bash
python run_workflow.py \
  --case-path /data/PrincipiaBlastFoam_output/surfaceburst_scaledd3 \
  --user-request "Simulate a surface-burst case and keep the farthest scaled distance close to 3."
```

> Note: OpenFOAM features such as `#calc` and `#codeStream` compile and load dynamic code. Running those cases as root can be rejected by OpenFOAM's security checks, often during utilities such as `blockMesh`. Use a normal Linux user for actual OpenFOAM/blastFoam execution. The end-to-end benchmark runner supports `--run-as-user openfoam` or `OPENFOAM_RUN_AS_USER=openfoam` and will hand off each workflow subprocess to that user.

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
*   [Retrieval Evaluation Guide](experiments/retrieval_method/README.md)
*   [Case Content Retrieval Method](docs/检索方法/案例内容知识检索技术文档.md)

## 🤝 Contribution

Issues and Pull Requests are welcome to improve this project.
