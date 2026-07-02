# Migration Status

Date: 2026-07-02

## Status

PrincipiaBlastFoam has been migrated to the LangChain team Deep Agents
framework. The old LangGraph/ReAct runtime is no longer the active system.

## Active Implementation

- Main package: `src/principia_deepagents/`
- CLI: `principia-deepagents`
- Legacy-compatible entrypoints:
  - `run_workflow.py`
  - `run_batch_workflow.py`
- MCP retrieval server: `mcp_servers/principia_retrieval/`
- End-to-end benchmark adapter:
  - `experiments/end2end/run_deepagents_benchmark.py`

The root entrypoints preserve the old command shape but dispatch to the Deep
Agents workflow. They also re-exec through the project-local `.venv/bin/python`
when that virtual environment exists.

## Removed From Active Code Path

- `principia_ai/` LangGraph/ReAct package
- Old `BaseAgent` custom ReAct loop
- Old LangGraph `StateGraph` workflow wrapper
- Old orchestrator JSON route machinery
- Old generic file/search/edit/shell tool wrappers
- Old end-to-end runner that imported `principia_ai`

## Reused Content

- Existing `.env` is used directly and remains git-ignored.
- Knowledge graph data, case descriptions, tutorial metadata, and MCP retrieval
  service logic were migrated/reused where still useful.
- The old `run_workflow.py` and `run_batch_workflow.py` user-facing interfaces
  are retained as compatibility wrappers.

## Verification

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"

.venv/bin/python -m pytest -q
# 47 passed

.venv/bin/python -m compileall -q src tests experiments scripts run_workflow.py run_batch_workflow.py

.venv/bin/python run_workflow.py --help
.venv/bin/python run_batch_workflow.py --help
.venv/bin/principia-deepagents --help
```

Latest full solver-enabled parity matrix from the DeepAgents development line:

```text
/tmp/principia_deepagents_solver_full_r80_process_timeout/deepagents_run_20260702_053130/deepagents_benchmark_results.json
total=12, passed=12, failed=0
execution_status completed/success: 12/12
artifact_contract ok=true: 12/12
post_processing_report_valid=true: 12/12
```

## Notes

- A project-local `.venv/` is required for normal use.
- Solver execution should use a non-root user such as `openfoam`:
  `OPENFOAM_EXECUTION_USER=openfoam OPENFOAM_CHOWN_CASE=true`.
- Deterministic fallback remains part of the design. In the latest r80 matrix,
  5 cases completed with no agent warning and 7 cases used deterministic
  execution fallback, including one process-timeout recovery.
