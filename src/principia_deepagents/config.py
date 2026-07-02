from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from principia_deepagents.utils.llm_profiles import (
    chat_openai_kwargs,
    resolve_llm_profile,
    resolve_main_llm_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RuntimeConfig:
    case_path: Path
    user_request: str
    tutorial_path: Path
    model: str | None
    api_key: str | None
    base_url: str | None
    provider: str | None
    active_profile: str | None
    recursion_limit: int
    enable_execution: bool
    require_execution: bool
    use_mcp_retrieval: bool


def bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def load_project_env(env_file: str | os.PathLike[str] | None = None) -> None:
    if env_file:
        load_dotenv(env_file, override=False)
        return
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def resolve_runtime_config(
    *,
    case_path: str,
    user_request: str,
    tutorial_path: str | None = None,
    llm_active_profile: str | None = None,
    llm_provider: str | None = None,
    llm_api_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    recursion_limit: int | None = None,
    use_mcp_retrieval: bool | None = None,
) -> RuntimeConfig:
    llm = resolve_main_llm_config(
        api_key=llm_api_key,
        base_url=llm_api_base_url,
        model=llm_model,
        provider=llm_provider,
        active_profile=llm_active_profile,
    )
    resolved_tutorial_path = tutorial_path or os.getenv(
        "BLASTFOAM_TUTORIALS",
        "/data/graduation-projects/blastFoam_tutorials",
    )
    return RuntimeConfig(
        case_path=Path(case_path).expanduser().resolve(),
        user_request=user_request,
        tutorial_path=Path(resolved_tutorial_path).expanduser().resolve(),
        model=llm.model,
        api_key=llm.api_key,
        base_url=llm.base_url,
        provider=llm.provider,
        active_profile=llm.active_profile,
        recursion_limit=recursion_limit or int(os.getenv("DEEPAGENTS_RECURSION_LIMIT", "200")),
        enable_execution=bool_env("ENABLE_EXECUTION", False),
        require_execution=bool_env("REQUIRE_EXECUTION", False),
        use_mcp_retrieval=bool_env("USE_MCP_RETRIEVAL", True) if use_mcp_retrieval is None else use_mcp_retrieval,
    )


def export_runtime_environment(
    config: RuntimeConfig,
    *,
    retrieval_active_profile: str | None = None,
) -> None:
    """
    Mirror resolved runtime settings into os.environ for child processes.

    MCP retrieval runs in a separate Python process, so CLI-only overrides must
    be visible through environment variables before MCP tools are loaded.
    """
    values = {
        "LLM_ACTIVE_PROFILE": config.active_profile,
        "LLM_PROVIDER": config.provider,
        "LLM_API_BASE_URL": config.base_url,
        "LLM_API_KEY": config.api_key,
        "LLM_MODEL": config.model,
    }
    for key, value in values.items():
        if value:
            os.environ[key] = str(value)

    if retrieval_active_profile:
        os.environ["RETRIEVAL_LLM_ACTIVE_PROFILE"] = retrieval_active_profile
    elif config.active_profile and not os.getenv("RETRIEVAL_LLM_ACTIVE_PROFILE"):
        os.environ["RETRIEVAL_LLM_ACTIVE_PROFILE"] = config.active_profile


def build_chat_model(config: RuntimeConfig) -> ChatOpenAI:
    if not config.model:
        raise ValueError("LLM model is not configured. Set LLM_ACTIVE_PROFILE or LLM_MODEL.")
    profile = resolve_llm_profile(config.base_url, config.model, config.provider)
    print(
        "Main LLM profile: "
        f"active_profile={config.active_profile or 'none'}, "
        f"provider={profile.provider}, model={profile.model}, "
        f"thinking={profile.thinking}, structured_output={profile.structured_output}"
    )
    return ChatOpenAI(
        **chat_openai_kwargs(
            base_url=config.base_url,
            model=config.model,
            api_key=config.api_key,
            provider=config.provider,
            temperature=0.1,
        )
    )
