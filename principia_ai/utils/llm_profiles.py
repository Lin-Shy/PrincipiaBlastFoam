"""
Provider capability profiles for OpenAI-compatible chat models.

Many providers expose an OpenAI-like API but differ on thinking controls,
structured output modes, and tool-call message contracts. This module keeps
those differences out of agent logic and makes the runtime behavior explicit.
"""

from __future__ import annotations

import copy
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


STRUCTURED_OUTPUT_MODES = {"json_schema", "json_object", "prompt_only", "disabled"}
THINKING_MODES = {"auto", "enabled", "disabled", "passthrough"}


@dataclass(frozen=True)
class LLMProfile:
    provider: str
    model: str | None = None
    base_url: str | None = None
    structured_output: str = "prompt_only"
    thinking: str = "passthrough"
    thinking_disabled_extra_body: dict[str, Any] = field(default_factory=dict)
    thinking_enabled_extra_body: dict[str, Any] = field(default_factory=dict)
    reasoning_roundtrip: bool = False

    def to_metadata(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _deep_merge(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = copy.deepcopy(dict(left))
    for key, value in right.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _env_choice(name: str, allowed: set[str], default: str) -> str:
    value = _normalize(os.getenv(name))
    if not value:
        return default
    aliases = {
        "off": "disabled",
        "false": "disabled",
        "no": "disabled",
        "on": "enabled",
        "true": "enabled",
        "yes": "enabled",
        "schema": "json_schema",
        "json_schema": "json_schema",
        "json_object": "json_object",
        "json": "json_object",
        "prompt": "prompt_only",
        "prompt_only": "prompt_only",
        "none": "disabled",
    }
    value = aliases.get(value, value)
    if value not in allowed:
        print(f"LLM profile: ignoring unsupported {name}={value!r}; using {default!r}.")
        return default
    return value


def infer_provider(base_url: str | None, model: str | None, explicit_provider: str | None = None) -> str:
    provider = _normalize(explicit_provider or os.getenv("LLM_PROVIDER"))
    if provider:
        return provider

    source = f"{base_url or ''} {model or ''}".lower()
    if "deepseek" in source:
        return "deepseek"
    if "dashscope" in source or "aliyuncs" in source or "qwen" in source:
        return "qwen"
    if "bigmodel" in source or "z.ai" in source or "zhipu" in source or "glm" in source:
        return "glm"
    if "moonshot" in source or "kimi" in source:
        return "moonshot"
    if "openai" in source or "api.openai.com" in source:
        return "openai"
    return "generic"


def _base_profile(provider: str, base_url: str | None, model: str | None) -> LLMProfile:
    if provider == "openai":
        return LLMProfile(provider=provider, model=model, base_url=base_url, structured_output="json_schema")
    if provider == "deepseek":
        return LLMProfile(
            provider=provider,
            model=model,
            base_url=base_url,
            structured_output="json_object",
            thinking="disabled",
            thinking_disabled_extra_body={"thinking": {"type": "disabled"}},
            thinking_enabled_extra_body={"thinking": {"type": "enabled"}},
        )
    if provider == "qwen":
        return LLMProfile(
            provider=provider,
            model=model,
            base_url=base_url,
            structured_output="json_object",
            thinking="disabled",
            thinking_disabled_extra_body={"enable_thinking": False},
            thinking_enabled_extra_body={"enable_thinking": True},
        )
    if provider == "glm":
        return LLMProfile(
            provider=provider,
            model=model,
            base_url=base_url,
            structured_output="json_object",
            thinking="disabled",
            thinking_disabled_extra_body={"thinking": {"type": "disabled"}},
            thinking_enabled_extra_body={"thinking": {"type": "enabled"}},
        )
    if provider == "moonshot":
        return LLMProfile(
            provider=provider,
            model=model,
            base_url=base_url,
            structured_output="json_object",
            thinking="disabled",
            thinking_disabled_extra_body={"thinking": {"type": "disabled"}},
            thinking_enabled_extra_body={"thinking": {"type": "enabled"}},
        )
    return LLMProfile(provider=provider, model=model, base_url=base_url, structured_output="prompt_only")


def resolve_llm_profile(base_url: str | None, model: str | None) -> LLMProfile:
    provider = infer_provider(base_url, model)
    profile = _base_profile(provider, base_url, model)

    thinking_override = _env_choice("LLM_THINKING", THINKING_MODES, "auto")
    structured_override = _env_choice("LLM_STRUCTURED_OUTPUT", STRUCTURED_OUTPUT_MODES | {"auto"}, "auto")

    thinking = profile.thinking if thinking_override == "auto" else thinking_override
    structured_output = profile.structured_output if structured_override == "auto" else structured_override

    roundtrip_env = _normalize(os.getenv("LLM_REASONING_ROUNDTRIP"))
    if roundtrip_env in {"1", "true", "yes", "on"}:
        reasoning_roundtrip = True
    elif roundtrip_env in {"0", "false", "no", "off"}:
        reasoning_roundtrip = False
    else:
        reasoning_roundtrip = profile.reasoning_roundtrip

    return LLMProfile(
        provider=profile.provider,
        model=model,
        base_url=base_url,
        structured_output=structured_output,
        thinking=thinking,
        thinking_disabled_extra_body=profile.thinking_disabled_extra_body,
        thinking_enabled_extra_body=profile.thinking_enabled_extra_body,
        reasoning_roundtrip=reasoning_roundtrip,
    )


def extra_body_for_profile(profile: LLMProfile) -> dict[str, Any]:
    if profile.thinking == "disabled":
        return copy.deepcopy(profile.thinking_disabled_extra_body)
    if profile.thinking == "enabled":
        return copy.deepcopy(profile.thinking_enabled_extra_body)
    return {}


def _parse_extra_body_env() -> dict[str, Any]:
    raw = os.getenv("LLM_EXTRA_BODY")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"LLM profile: ignoring invalid LLM_EXTRA_BODY JSON: {exc}")
        return {}
    if not isinstance(parsed, dict):
        print("LLM profile: ignoring LLM_EXTRA_BODY because it is not a JSON object.")
        return {}
    return parsed


def chat_openai_kwargs(
    *,
    base_url: str | None,
    model: str | None,
    api_key: str | None,
    temperature: float | None = 0.1,
) -> dict[str, Any]:
    profile = resolve_llm_profile(base_url, model)
    extra_body = _deep_merge(extra_body_for_profile(profile), _parse_extra_body_env())
    kwargs: dict[str, Any] = {
        "base_url": base_url,
        "model": model,
        "api_key": api_key,
        "temperature": temperature,
        "metadata": {"principia_llm_profile": profile.to_metadata()},
    }
    if extra_body:
        kwargs["extra_body"] = extra_body
    return kwargs


def profile_from_llm(llm: Any) -> LLMProfile:
    metadata = getattr(llm, "metadata", None)
    if isinstance(metadata, Mapping):
        raw_profile = metadata.get("principia_llm_profile")
        if isinstance(raw_profile, Mapping):
            return LLMProfile(
                provider=str(raw_profile.get("provider") or "generic"),
                model=raw_profile.get("model"),
                base_url=raw_profile.get("base_url"),
                structured_output=str(raw_profile.get("structured_output") or "prompt_only"),
                thinking=str(raw_profile.get("thinking") or "passthrough"),
                thinking_disabled_extra_body=dict(raw_profile.get("thinking_disabled_extra_body") or {}),
                thinking_enabled_extra_body=dict(raw_profile.get("thinking_enabled_extra_body") or {}),
                reasoning_roundtrip=bool(raw_profile.get("reasoning_roundtrip", False)),
            )

    model = getattr(llm, "model_name", None) or getattr(llm, "model", None)
    base_url = getattr(llm, "openai_api_base", None) or getattr(llm, "base_url", None)
    return resolve_llm_profile(str(base_url) if base_url else None, str(model) if model else None)


def structured_output_mode(llm: Any) -> str:
    mode = _env_choice("LLM_STRUCTURED_OUTPUT", STRUCTURED_OUTPUT_MODES | {"auto"}, "auto")
    if mode != "auto":
        return mode
    profile = profile_from_llm(llm)
    if profile.structured_output in STRUCTURED_OUTPUT_MODES:
        return profile.structured_output
    return "prompt_only"
