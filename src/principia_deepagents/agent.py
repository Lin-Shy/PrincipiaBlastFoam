from __future__ import annotations

from pathlib import Path
from typing import Any

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend

from principia_deepagents.config import RuntimeConfig, build_chat_model
from principia_deepagents.prompts import (
    CASE_SETUP_PROMPT,
    EXECUTION_PROMPT,
    MAIN_SYSTEM_PROMPT,
    PHYSICS_ANALYST_PROMPT,
    POSTPROCESS_PROMPT,
    REVIEWER_PROMPT,
)
from principia_deepagents.tools.mcp import load_mcp_retrieval_tools
from principia_deepagents.tools.openfoam import make_openfoam_tools


def base_permissions() -> list[FilesystemPermission]:
    return [
        FilesystemPermission(operations=["read", "write"], paths=["/.env", "/.env.*"], mode="deny"),
        FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="allow"),
    ]


def reviewer_permissions() -> list[FilesystemPermission]:
    return [
        FilesystemPermission(operations=["read"], paths=["/.env", "/.env.*"], mode="deny"),
        FilesystemPermission(operations=["write"], paths=["/review_report.md"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/artifact_contract.json"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/workflow_evidence.md"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/workflow_evidence.json"], mode="allow"),
        FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
        FilesystemPermission(operations=["read"], paths=["/**"], mode="allow"),
    ]


def build_tools(config: RuntimeConfig) -> list[Any]:
    tools = make_openfoam_tools(
        case_path=config.case_path,
        user_request=config.user_request,
        tutorial_path=config.tutorial_path,
        default_require_execution=config.require_execution or config.enable_execution,
        default_require_review=config.require_execution or config.enable_execution,
    )
    if config.use_mcp_retrieval:
        try:
            tools.extend(load_mcp_retrieval_tools())
            print(f"Loaded {len(tools)} total tools including MCP retrieval.")
        except Exception as exc:
            print(f"Warning: MCP retrieval tools unavailable; continuing with local tools only: {exc}")
    return tools


def build_subagents(config: RuntimeConfig) -> list[dict[str, Any]]:
    return [
        {
            "name": "physics-analyst",
            "description": "Analyze blastFoam/OpenFOAM physics, retrieve domain knowledge, and write physics_report.md.",
            "system_prompt": PHYSICS_ANALYST_PROMPT,
        },
        {
            "name": "case-setup",
            "description": "Modify OpenFOAM case dictionaries and scripts according to physics_report.md and the user request.",
            "system_prompt": CASE_SETUP_PROMPT,
        },
        {
            "name": "execution-specialist",
            "description": "Run preflight, controlled solver execution, execution evidence, and execution reports.",
            "system_prompt": EXECUTION_PROMPT,
        },
        {
            "name": "post-processing",
            "description": "Inspect solver outputs and produce post_processing_report.md for every completed workflow.",
            "system_prompt": POSTPROCESS_PROMPT,
        },
        {
            "name": "reviewer",
            "description": "Perform final deterministic QA and write review_report.md.",
            "system_prompt": REVIEWER_PROMPT,
            "permissions": reviewer_permissions(),
        },
    ]


def create_principia_agent(config: RuntimeConfig):
    config.case_path.mkdir(parents=True, exist_ok=True)
    backend = FilesystemBackend(root_dir=Path(config.case_path), virtual_mode=True)
    model = build_chat_model(config)
    return create_deep_agent(
        model=model,
        tools=build_tools(config),
        system_prompt=MAIN_SYSTEM_PROMPT,
        subagents=build_subagents(config),
        backend=backend,
        permissions=base_permissions(),
        name="principia-blastfoam-deepagents",
    )
