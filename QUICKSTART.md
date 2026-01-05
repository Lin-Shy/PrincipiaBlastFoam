# 🚀 Quick Start Guide

This guide will help you set up the **PrincipiaBlastFoam** environment and run your first automated simulation task.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

*   **Operating System**: Linux (Recommended for OpenFOAM compatibility)
*   **Python**: Version 3.10 or higher
*   **OpenFOAM**: A working installation of OpenFOAM (specifically **blastFoam** if running explosion simulations)
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

## 🏃‍♂️ Running the System

### 1. Verify Knowledge Graph Retrieval

To ensure the Knowledge Graph and retrieval tools are working correctly, run the example script:

```bash
python example_improved_retrieval.py
```

This script demonstrates the system's ability to retrieve relevant OpenFOAM case information using the improved hierarchical retrieval strategy.

### 2. Run the Main Workflow

The core of the system is the multi-agent workflow.

1.  Open `run_workflow.py`.
2.  Modify the `user_request` variable to describe your simulation task.
    *   *Example*: "Set up a 2D explosion simulation with a charge mass of 5kg located at (0 0 0)."
3.  Set the `CASE_PATH` to your target working directory.
4.  Run the workflow:

```bash
python run_workflow.py
```

### 3. Monitor Progress

The system will output logs to the console, showing the interaction between agents:
*   **Orchestrator**: Planning and delegating tasks.
*   **PhysicsAnalyst**: Analyzing requirements.
*   **CaseSetup**: Modifying files.
*   **Execution**: Running the solver.

## 🔍 Troubleshooting

*   **Neo4j Connection Error**: Ensure the Neo4j service is running and the credentials in `.env` are correct.
*   **OpenFOAM Command Not Found**: Make sure you have sourced the OpenFOAM environment variables (e.g., `source /opt/openfoam/etc/bashrc`) before running the Python scripts.
*   **LLM API Error**: Check your API key and network connection.

## 📚 Next Steps

*   Explore the [Multi-Agent Design](docs/MULTI_AGENT_DESIGN.md) to understand how the agents collaborate.
*   Check `experiments/` for more advanced usage and evaluation scripts.
