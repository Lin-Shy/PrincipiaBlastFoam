from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import os
import sys
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _clean_mcp_env() -> dict[str, str]:
    env = {}
    for key, value in os.environ.items():
        if key.startswith("BASH_FUNC_"):
            continue
        env[key] = value
    return env


def mcp_server_config() -> dict[str, dict[str, Any]]:
    return {
        "principia_retrieval": {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", "mcp_servers.principia_retrieval.server"],
            "cwd": str(PROJECT_ROOT),
            "env": _clean_mcp_env(),
        }
    }


def _run_async_in_sync(coro_factory):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro_factory())).result()


def _syncify_mcp_tool(tool: Any) -> Any:
    if getattr(tool, "func", None) is not None:
        return tool
    if getattr(tool, "coroutine", None) is None:
        return tool

    def call_tool_sync(**kwargs):
        return _run_async_in_sync(lambda: tool.ainvoke(kwargs))

    call_tool_sync.__name__ = f"{getattr(tool, 'name', 'mcp_tool')}_sync"
    return StructuredTool.from_function(
        func=call_tool_sync,
        name=getattr(tool, "name", None),
        description=getattr(tool, "description", None) or getattr(tool, "name", "MCP tool"),
        return_direct=getattr(tool, "return_direct", False),
        args_schema=getattr(tool, "args_schema", None),
        response_format="content",
    )


async def load_mcp_retrieval_tools_async() -> list[Any]:
    client = MultiServerMCPClient(mcp_server_config())
    tools = client.get_tools()
    if inspect.isawaitable(tools):
        tools = await tools
    return [_syncify_mcp_tool(tool) for tool in tools]


def load_mcp_retrieval_tools() -> list[Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(load_mcp_retrieval_tools_async())
    raise RuntimeError("load_mcp_retrieval_tools() cannot run inside an active event loop")
