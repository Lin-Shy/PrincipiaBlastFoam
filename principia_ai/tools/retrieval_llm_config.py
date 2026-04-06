"""
Helpers for configuring retrieval-specific LLM clients.
"""

from __future__ import annotations

import os
from typing import Dict, Optional


def resolve_retrieval_llm_config(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """
    Resolve LLM settings for retrieval tools.

    Retrieval tools first use explicit arguments, then retrieval-specific
    environment variables, and finally fall back to the agent-wide LLM config.
    """
    resolved_api_key = api_key or os.getenv("RETRIEVAL_LLM_API_KEY") or os.getenv("LLM_API_KEY")
    resolved_base_url = (
        base_url
        or os.getenv("RETRIEVAL_LLM_API_BASE_URL")
        or os.getenv("LLM_API_BASE_URL")
    )
    resolved_model = model or os.getenv("RETRIEVAL_LLM_MODEL") or os.getenv("LLM_MODEL") or "gpt-4"

    return {
        "api_key": resolved_api_key,
        "base_url": resolved_base_url,
        "model": resolved_model,
    }
