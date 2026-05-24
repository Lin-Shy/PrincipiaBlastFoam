# 🚀 Quick Start Guide

This guide will help you set up the **PrincipiaBlastFoam** environment and run your first automated simulation task.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

*   **Operating System**: Linux (Recommended for OpenFOAM compatibility)
*   **Python**: Version 3.10 or higher
*   **OpenFOAM**: A working installation of OpenFOAM (specifically **blastFoam** if running explosion simulations)
*   **Execution User**: A normal, non-root Linux user for OpenFOAM/blastFoam runs
*   **Database**: Neo4j (Required for Knowledge Graph storage)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository_url>
cd PrincipiaBlastFoam
```

### 2. Set up Python Environment

It is recommended to use Conda or venv to manage dependencies.

```bash
# Using Conda
conda create -n principia python=3.10
conda activate principia

# OR using venv
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> Note: `requirements.txt` includes MCP support through `mcp` and
> `langchain-mcp-adapters==0.0.11`. The adapter is pinned to stay compatible
> with this project's LangChain 0.3 dependency set.

## ⚙️ Configuration

### 1. Environment Variables

The system uses a `.env` file for configuration. Start by copying the example file:

```bash
cp example.env .env
```

### 2. Edit Configuration

Open `.env` and configure the following critical settings:

*   **LLM Configuration**:
    *   `LLM_API_KEY`: Your API key (e.g., OpenAI, DashScope).
    *   `LLM_MODEL`: The model name to use (e.g., `gpt-4`, `qwen-plus`).
    *   `LLM_API_BASE_URL`: The API base URL.

*   **Neo4j Configuration**:
    *   `NEO4J_URI`: URI for your Neo4j instance (default: `bolt://localhost:7687`).
    *   `NEO4J_USERNAME`: Database username.
    *   `NEO4J_PASSWORD`: Database password.

*   **OpenFOAM Configuration**:
    *   `BLASTFOAM_TUTORIALS`: Path to your blastFoam tutorials directory (used for reference).
    *   `OPENFOAM_RUN_AS_USER`: Optional user for end-to-end benchmark runs, for example `openfoam`.

*   **Runtime Controls**:
    *   `AGENT_RUNTIME`: `langgraph` by default, with `langchain` available as a compatibility fallback.
    *   `LANGGRAPH_CHECKPOINTS`: Enables in-memory LangGraph checkpointing when set to `true`.
    *   `ORCHESTRATOR_STRUCTURED_OUTPUT`: Enables structured routing decisions.
    *   `LLM_STRUCTURED_OUTPUT` and `LLM_THINKING`: Provider capability overrides; keep `auto` unless a provider requires explicit behavior.

The real `.env` file is ignored by Git. Keep actual keys there only, not in committed files.

## 🏃‍♂️ Running the System

### 1. Verify Knowledge Graph Retrieval

To ensure the Knowledge Graph and retrieval tools are working correctly, run a small benchmark entry point:

```bash
python experiments/retrieval_method/evaluate_knowledge_graph_retriever.py --benchmark user_guide --limit 3
```

For case-content and embedding retrieval commands, see `experiments/retrieval_method/README.md`.

### 2. Verify the MCP Retrieval Server

The MCP retrieval server keeps the case-content knowledge graph loaded in one
server process and exposes retrieval as reusable tools for LangChain/LangGraph
agents.

```bash
python -m mcp_servers.principia_retrieval.test_client
python examples/mcp/langchain_mcp_client_example.py
```

The first command connects through MCP and calls representative tools. The
second command verifies that LangChain can load the MCP tools.

### 3. Run the Main Workflow

The core of the system is the multi-agent workflow.

Run `run_workflow.py` with an explicit case path and request:

```bash
python run_workflow.py \
  --case-path /data/PrincipiaBlastFoam_output/surfaceburst_scaledd3 \
  --user-request "Set up a 2D explosion simulation with a charge mass of 5kg located at (0 0 0)."
```

When running real OpenFOAM/blastFoam cases, avoid executing the solver stack as root. Some tutorials use `#calc` or `#codeStream`, which require OpenFOAM to compile and load dynamic code. OpenFOAM can reject this when the process runs as root. For benchmark runs, use:

```bash
python experiments/end2end/run_agent_benchmark.py --run-as-user openfoam
```

or:

```bash
export OPENFOAM_RUN_AS_USER=openfoam
```

### 4. Monitor Progress

The system will output logs to the console, showing the interaction between agents:
*   **Orchestrator**: Planning and delegating tasks.
*   **PhysicsAnalyst**: Analyzing requirements.
*   **CaseSetup**: Modifying files.
*   **Execution**: Running the solver.

## 🔍 Troubleshooting

*   **Neo4j Connection Error**: Ensure the Neo4j service is running and the credentials in `.env` are correct.
*   **OpenFOAM Command Not Found**: Make sure you have sourced the OpenFOAM environment variables (e.g., `source /opt/openfoam/etc/bashrc`) before running the Python scripts.
*   **OpenFOAM dynamicCode Security Error**: If `blockMesh` or another OpenFOAM utility fails with a root/dynamicCode security message, rerun through a non-root user such as `openfoam`.
*   **LLM API Error**: Check your API key and network connection.

## 📚 Next Steps

*   Explore the [Multi-Agent Design](docs/MULTI_AGENT_DESIGN.md) to understand how the agents collaborate.
*   Check `experiments/` for more advanced usage and evaluation scripts.
