from __future__ import annotations

import asyncio
import atexit
import concurrent.futures
import json
import os
import sys
import threading
from contextvars import ContextVar
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_current_case_path: ContextVar[Optional[str]] = ContextVar("retrieval_case_path", default=None)
_current_user_request: ContextVar[Optional[str]] = ContextVar("retrieval_user_request", default=None)


def set_retrieval_context(case_path: Optional[str] = None, user_request: Optional[str] = None) -> None:
    """Set best-effort context used by MCP retrieval tools when LLM calls omit filters."""
    if case_path:
        _current_case_path.set(case_path)
    if user_request:
        _current_user_request.set(user_request)


class _MCPRetrievalClient:
    """Synchronous facade around a long-lived stdio MCP retrieval server."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._startup_error: Optional[BaseException] = None

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        self._ensure_started()
        if self._startup_error:
            return f"MCP retrieval unavailable: {self._startup_error}"
        if not self._loop or not self._session:
            return "MCP retrieval unavailable: client session was not initialized."

        timeout = float(os.getenv("MCP_RETRIEVAL_TIMEOUT_SECONDS", "120"))
        future = asyncio.run_coroutine_threadsafe(
            self._call_tool_async(name, arguments),
            self._loop,
        )
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            return f"MCP retrieval tool '{name}' timed out after {timeout:.0f} seconds."
        except Exception as exc:
            future.cancel()
            return f"MCP retrieval tool '{name}' failed: {exc}"

    def _ensure_started(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._ready.clear()
            self._thread = threading.Thread(target=self._run_loop, name="principia-mcp-retrieval", daemon=True)
            self._thread.start()

        self._ready.wait(timeout=float(os.getenv("MCP_RETRIEVAL_STARTUP_TIMEOUT_SECONDS", "120")))

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._connect())
        self._ready.set()
        loop.run_forever()

    async def _connect(self) -> None:
        try:
            self._exit_stack = AsyncExitStack()
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "mcp_servers.principia_retrieval.server"],
                cwd=str(PROJECT_ROOT),
                env=os.environ.copy(),
            )
            read, write = await self._exit_stack.enter_async_context(stdio_client(params))
            self._session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            await self._session.initialize()
        except BaseException as exc:  # store for sync tool output
            self._startup_error = exc

    async def _call_tool_async(self, name: str, arguments: Dict[str, Any]) -> str:
        if not self._session:
            return "MCP retrieval unavailable: session missing."
        result = await self._session.call_tool(name, arguments)
        texts = []
        for item in result.content:
            text = getattr(item, "text", None)
            if text is not None:
                texts.append(text)
            elif hasattr(item, "model_dump"):
                texts.append(json.dumps(item.model_dump(), ensure_ascii=False))
            else:
                texts.append(str(item))
        return "\n".join(texts)

    def close(self) -> None:
        if not self._loop:
            return

        async def _close() -> None:
            if self._exit_stack:
                await self._exit_stack.aclose()

        try:
            future = asyncio.run_coroutine_threadsafe(_close(), self._loop)
            future.result(timeout=5)
            self._loop.call_soon_threadsafe(self._loop.stop)
        except Exception:
            pass


_CLIENT = _MCPRetrievalClient()
atexit.register(_CLIENT.close)


def _effective_query(query: Optional[str], user_query: Optional[str]) -> str:
    return (query or user_query or _current_user_request.get() or "").strip()


def _effective_case_path(case_path: Optional[str]) -> Optional[str]:
    context_case_path = _current_case_path.get()
    if case_path and not str(case_path).startswith("/"):
        return case_path
    return context_case_path or case_path


def mcp_get_case_by_intent(query: str) -> str:
    """Resolve a user query or alias to a known blastFoam tutorial case."""
    return _CLIENT.call_tool("get_case_by_intent", {"query": query})


def mcp_get_files_for_case(case_path: Optional[str] = None) -> str:
    """Return files known for a tutorial case path. Uses current workflow case context if omitted."""
    effective_case_path = _effective_case_path(case_path)
    if not effective_case_path:
        return "No case_path provided and no retrieval context is available."
    return _CLIENT.call_tool("get_files_for_case", {"case_path": effective_case_path})


def mcp_find_variable(variable_name: str, case_path: Optional[str] = None) -> str:
    """Find files in a case that define a variable by exact variable name."""
    effective_case_path = _effective_case_path(case_path)
    if not effective_case_path:
        return "No case_path provided and no retrieval context is available."
    return _CLIENT.call_tool(
        "find_variable",
        {"case_path": effective_case_path, "variable_name": variable_name},
    )


def mcp_get_file_content(file_path: str, case_path: Optional[str] = None, max_lines: int = 120) -> str:
    """Read tutorial file content for a case and relative file path."""
    effective_case_path = _effective_case_path(case_path)
    if not effective_case_path:
        return "No case_path provided and no retrieval context is available."
    return _CLIENT.call_tool(
        "get_file_content",
        {"case_path": effective_case_path, "file_path": file_path, "max_lines": max_lines},
    )


def mcp_get_modification_targets(user_request: Optional[str] = None, top_k: int = 5) -> str:
    """Return likely case files that should be modified for a user request."""
    effective_request = user_request or _current_user_request.get()
    if not effective_request:
        return "No user_request provided and no retrieval context is available."
    return _CLIENT.call_tool(
        "get_modification_targets",
        {
            "user_request": effective_request,
            "case_path": _effective_case_path(None),
            "top_k": top_k,
        },
    )


def mcp_search_case_content(
    query: Optional[str] = None,
    user_query: Optional[str] = None,
    case_path: Optional[str] = None,
    file_path: Optional[str] = None,
    variable_name: Optional[str] = None,
    top_k: int = 5,
    include_file_content: bool = False,
    max_iterations: int = 1,
) -> str:
    """Search case knowledge with scoped filters before falling back to full-graph retrieval."""
    effective_query = _effective_query(query, user_query)
    if not effective_query and not (file_path or variable_name):
        return "No query/user_query provided and no retrieval context is available."
    return _CLIENT.call_tool(
        "search_case_content",
        {
            "query": effective_query,
            "case_path": _effective_case_path(case_path),
            "file_path": file_path,
            "variable_name": variable_name,
            "top_k": top_k,
            "include_file_content": include_file_content,
            "max_iterations": max_iterations,
        },
    )


def mcp_search_user_guide(query: Optional[str] = None, user_query: Optional[str] = None, top_k: int = 5) -> str:
    """Search the BlastFoam user guide knowledge graph through MCP."""
    effective_query = _effective_query(query, user_query)
    if not effective_query:
        return "No query/user_query provided and no retrieval context is available."
    return _CLIENT.call_tool("search_user_guide", {"query": effective_query, "top_k": top_k})


def get_mcp_retrieval_tools(
    use_knowledge_manager: bool = True,
    use_tutorial_retriever: bool = True,
) -> List[StructuredTool]:
    """Return MCP-backed retrieval tools without starting the MCP server until first use."""
    tools: List[StructuredTool] = []

    if use_tutorial_retriever:
        tools.extend(
            [
                StructuredTool.from_function(
                    mcp_get_case_by_intent,
                    name="get_case_by_intent",
                    description="Resolve a query or alias to a known blastFoam tutorial case before broad searching.",
                ),
                StructuredTool.from_function(
                    mcp_get_files_for_case,
                    name="get_files_for_case",
                    description="List known files for the current or specified tutorial case.",
                ),
                StructuredTool.from_function(
                    mcp_find_variable,
                    name="find_variable",
                    description="Find an exact variable definition within the current or specified tutorial case.",
                ),
                StructuredTool.from_function(
                    mcp_get_file_content,
                    name="get_file_content",
                    description="Read a known tutorial file by case_path and file_path. Prefer this before broad search.",
                ),
                StructuredTool.from_function(
                    mcp_get_modification_targets,
                    name="get_modification_targets",
                    description="Find likely case files to edit for a user request using deterministic intent rules.",
                ),
                StructuredTool.from_function(
                    mcp_search_case_content,
                    name="search_case_content",
                    description=(
                        "Search blastFoam tutorial case knowledge. Prefer passing case_path, file_path, or "
                        "variable_name to scope retrieval; the tool falls back to full-graph retrieval only "
                        "when scoped lookup has no hit."
                    ),
                ),
            ]
        )

    if use_knowledge_manager:
        tools.append(
            StructuredTool.from_function(
                mcp_search_user_guide,
                name="search_user_guide",
                description="Search the BlastFoam user guide through the shared MCP retrieval server.",
            )
        )

    return tools
