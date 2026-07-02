from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

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
    model_provider: str | None
    active_profile: str | None
    model_profile: str | None
    model_profile_label: str | None
    api_key_env: str | None
    recursion_limit: int
    enable_execution: bool
    require_execution: bool
    use_mcp_retrieval: bool
    model_profile_metadata: dict[str, Any] = field(default_factory=dict)


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
    model_profile: str | None = None,
    recursion_limit: int | None = None,
    use_mcp_retrieval: bool | None = None,
) -> RuntimeConfig:
    llm = resolve_main_llm_config(
        api_key=llm_api_key,
        base_url=llm_api_base_url,
        model=llm_model,
        provider=llm_provider,
        active_profile=model_profile or llm_active_profile,
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
        model_provider=llm.model_provider,
        active_profile=llm.active_profile,
        model_profile=llm.profile_id or llm.active_profile,
        model_profile_label=llm.profile_label,
        api_key_env=llm.api_key_env,
        recursion_limit=recursion_limit or int(os.getenv("DEEPAGENTS_RECURSION_LIMIT", "200")),
        enable_execution=bool_env("ENABLE_EXECUTION", False),
        require_execution=bool_env("REQUIRE_EXECUTION", False),
        use_mcp_retrieval=bool_env("USE_MCP_RETRIEVAL", True) if use_mcp_retrieval is None else use_mcp_retrieval,
        model_profile_metadata=llm.profile_metadata,
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
        "PRINCIPIA_MODEL_PROFILE": config.model_profile,
        "PRINCIPIA_MODEL_PROVIDER": config.model_provider,
        "PRINCIPIA_MODEL": config.model,
        "PRINCIPIA_MODEL_BASE_URL": config.base_url,
        "PRINCIPIA_MODEL_API_KEY_ENV": config.api_key_env,
        "LLM_ACTIVE_PROFILE": config.active_profile,
        "LLM_PROVIDER": config.provider,
        "LLM_MODEL_PROVIDER": config.model_provider,
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
        os.environ["RETRIEVAL_LLM_ACTIVE_PROFILE"] = config.model_profile or config.active_profile


def build_chat_model(config: RuntimeConfig) -> BaseChatModel:
    if not config.model:
        raise ValueError("LLM model is not configured. Set PRINCIPIA_MODEL_PROFILE or LLM_MODEL.")
    profile = resolve_llm_profile(config.base_url, config.model, config.provider)
    print(
        "Main LLM profile: "
        f"model_profile={config.model_profile or config.active_profile or 'none'}, "
        f"provider={profile.provider}, model={profile.model}, "
        f"model_provider={config.model_provider or 'auto'}, "
        f"thinking={profile.thinking}, structured_output={profile.structured_output}"
    )
    kwargs = chat_openai_kwargs(
        base_url=config.base_url,
        model=config.model,
        api_key=config.api_key,
        provider=config.provider,
        temperature=0.1,
    )
    model = kwargs.pop("model")
    return init_chat_model(
        model=model,
        model_provider=config.model_provider or "openai",
        **kwargs,
    )
