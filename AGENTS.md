# Repository Instructions

- This repository is now the Deep Agents implementation of PrincipiaBlastFoam.
- Use the project-local virtual environment in `.venv/` for Python commands.
- Keep `.env` local and uncommitted; do not print secrets from it.
- Prefer Deep Agents built-ins for planning, filesystem, subagents,
  permissions, and MCP integration. Add custom code only for blastFoam/OpenFOAM
  domain behavior.
- Preserve benchmark-compatible artifacts in generated case directories:
  `physics_report.md`, `execution_report.md`, `execution_status.json`,
  `workflow_evidence.md`, `artifact_contract.json`, `review_report.md`, and
  `post_processing_report.md`.
