# PrincipiaBlastFoam

PrincipiaBlastFoam is now implemented on the LangChain team Deep Agents
framework. The previous LangGraph/ReAct runtime has been removed from the
active code path.

## Architecture

- Deep Agents provides the main agent harness, planning, virtual filesystem,
  subagents, permissions, and MCP tool integration.
- This repository keeps domain-specific code for blastFoam tutorial selection,
  MCP retrieval, OpenFOAM preflight/execution, deterministic post-processing
  summaries, artifact contracts, and benchmark-compatible workflow output.
- Legacy-compatible `run_workflow.py` and `run_batch_workflow.py` entrypoints
  are preserved, but they now call the Deep Agents implementation.

## Environment

```bash
cd /data/graduation-projects/PrincipiaBlastFoam
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

The existing `.env` file is used directly and remains git-ignored.
Model/provider/base URL metadata is tracked in
`config/model_profiles.json`; `.env` should only carry the selected
`PRINCIPIA_MODEL_PROFILE`, provider API keys, and local runtime switches. The
older `LLM_ACTIVE_PROFILE` and `LLM_PROFILE_*` variables are still accepted for
compatibility, but new experiments should use `--model-profile` so local result
archives record a stable profile id without duplicating model metadata in
`.env`.

## Smoke Commands

```bash
pytest
principia-deepagents --help
python run_workflow.py --help
python run_batch_workflow.py --help
principia-deepagents mcp-smoke
```

Current parity evidence is recorded in
[`docs/MIGRATION_STATUS.md`](docs/MIGRATION_STATUS.md). The latest full
solver-enabled 12-case matrix passed with `--recursion-limit 80`, successful
`execution_status.json`, valid `post_processing_report.md`, and passing
artifact contracts for every case.

## Workflow Run

```bash
python run_workflow.py \
  --case-path /data/PrincipiaBlastFoam_output/deepagents_surfaceburst \
  --user-request "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。" \
  --tutorial-path /data/graduation-projects/blastFoam_tutorials \
  --model-profile deepseek_v4_flash \
  --retrieval-llm-active-profile deepseek_v4_flash
```

The direct CLI is also available:

```bash
principia-deepagents run \
  --case-path /data/PrincipiaBlastFoam_output/deepagents_surfaceburst \
  --user-request "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。" \
  --tutorial-path /data/graduation-projects/blastFoam_tutorials \
  --model-profile deepseek_v4_flash \
  --retrieval-llm-active-profile deepseek_v4_flash
```

## Solver Smoke

```bash
ENABLE_EXECUTION=true REQUIRE_EXECUTION=true \
OPENFOAM_EXECUTION_USER=openfoam OPENFOAM_CHOWN_CASE=true \
principia-deepagents preflight \
  --case-path /tmp/principia_solver_execute_shock \
  --env-file .env

ENABLE_EXECUTION=true REQUIRE_EXECUTION=true \
OPENFOAM_EXECUTION_USER=openfoam OPENFOAM_CHOWN_CASE=true \
principia-deepagents execute \
  --case-path /tmp/principia_solver_execute_shock \
  --env-file .env \
  --timeout-seconds 180
```
