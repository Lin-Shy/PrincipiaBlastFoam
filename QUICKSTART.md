# Quickstart

```bash
cd /data/graduation-projects/PrincipiaBlastFoam
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

Run local checks:

```bash
pytest
principia-deepagents --help
python run_workflow.py --help
python run_batch_workflow.py --help
```

Run a non-execution workflow:

```bash
python run_workflow.py \
  --case-path /tmp/principia_deepagents_surfaceburst \
  --user-request "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。" \
  --tutorial-path /data/graduation-projects/blastFoam_tutorials \
  --llm-active-profile deepseek_v4_flash \
  --retrieval-llm-active-profile deepseek_v4_flash
```

Run a solver-enabled preflight:

```bash
ENABLE_EXECUTION=true REQUIRE_EXECUTION=true \
OPENFOAM_EXECUTION_USER=openfoam OPENFOAM_CHOWN_CASE=true \
principia-deepagents preflight \
  --case-path /tmp/principia_solver_preflight_shock \
  --env-file .env
```
