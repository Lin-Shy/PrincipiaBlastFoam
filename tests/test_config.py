from __future__ import annotations

import os
from pathlib import Path

from principia_deepagents.config import (
    RuntimeConfig,
    bool_env,
    export_runtime_environment,
    load_project_env,
    resolve_runtime_config,
)


def test_env_file_does_not_override_existing_environment(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ENABLE_EXECUTION=true\nLLM_ACTIVE_PROFILE=from_file\n", encoding="utf-8")
    monkeypatch.setenv("ENABLE_EXECUTION", "false")
    monkeypatch.delenv("LLM_ACTIVE_PROFILE", raising=False)

    load_project_env(env_file)

    assert bool_env("ENABLE_EXECUTION") is False
    assert bool_env("MISSING_BOOL", True) is True


def _runtime_config(active_profile: str = "deepseek_v4_flash") -> RuntimeConfig:
    return RuntimeConfig(
        case_path=Path("/tmp/case"),
        user_request="test",
        tutorial_path=Path("/tmp/tutorials"),
        model="deepseek-chat",
        api_key="test-key",
        base_url="https://api.deepseek.com",
        provider="deepseek",
        model_provider="openai",
        active_profile=active_profile,
        model_profile=active_profile,
        model_profile_label="deepseek-v4-flash",
        api_key_env="DEEPSEEK_API_KEY",
        recursion_limit=20,
        enable_execution=False,
        require_execution=False,
        use_mcp_retrieval=True,
    )


def test_export_runtime_environment_defaults_retrieval_profile(monkeypatch) -> None:
    monkeypatch.delenv("RETRIEVAL_LLM_ACTIVE_PROFILE", raising=False)

    export_runtime_environment(_runtime_config())

    assert os.environ["LLM_ACTIVE_PROFILE"] == "deepseek_v4_flash"
    assert os.environ["PRINCIPIA_MODEL_PROFILE"] == "deepseek_v4_flash"
    assert os.environ["PRINCIPIA_MODEL_API_KEY_ENV"] == "DEEPSEEK_API_KEY"
    assert os.environ["RETRIEVAL_LLM_ACTIVE_PROFILE"] == "deepseek_v4_flash"
    assert os.environ["LLM_MODEL"] == "deepseek-chat"


def test_export_runtime_environment_preserves_explicit_retrieval_profile(monkeypatch) -> None:
    monkeypatch.setenv("RETRIEVAL_LLM_ACTIVE_PROFILE", "retrieval_profile")

    export_runtime_environment(_runtime_config())

    assert os.environ["RETRIEVAL_LLM_ACTIVE_PROFILE"] == "retrieval_profile"


def test_export_runtime_environment_accepts_retrieval_override(monkeypatch) -> None:
    monkeypatch.setenv("RETRIEVAL_LLM_ACTIVE_PROFILE", "from_env")

    export_runtime_environment(_runtime_config(), retrieval_active_profile="from_cli")

    assert os.environ["RETRIEVAL_LLM_ACTIVE_PROFILE"] == "from_cli"


def test_model_profile_registry_prefers_standard_api_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PRINCIPIA_MODEL_PROFILE", "deepseek_v4_flash")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "standard-key")
    monkeypatch.setenv("LLM_PROFILE_DEEPSEEK_V4_FLASH_API_KEY", "legacy-key")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_BASE_URL", raising=False)

    config = resolve_runtime_config(
        case_path=str(tmp_path / "case"),
        user_request="test",
        tutorial_path=str(tmp_path / "tutorials"),
    )

    assert config.model_profile == "deepseek_v4_flash"
    assert config.model_profile_label == "deepseek-v4-flash"
    assert config.provider == "deepseek"
    assert config.model_provider == "openai"
    assert config.model == "deepseek-v4-flash"
    assert config.api_key == "standard-key"
    assert config.api_key_env == "DEEPSEEK_API_KEY"
    assert config.model_profile_metadata["selected_api_key_env"] == "DEEPSEEK_API_KEY"


def test_model_profile_registry_accepts_legacy_profile_api_key(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PRINCIPIA_MODEL_PROFILE", "deepseek-v4-flash")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROFILE_DEEPSEEK_V4_FLASH_API_KEY", "legacy-key")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_API_BASE_URL", raising=False)

    config = resolve_runtime_config(
        case_path=str(tmp_path / "case"),
        user_request="test",
        tutorial_path=str(tmp_path / "tutorials"),
    )

    assert config.model_profile == "deepseek_v4_flash"
    assert config.api_key == "legacy-key"
    assert config.api_key_env == "LLM_PROFILE_DEEPSEEK_V4_FLASH_API_KEY"
