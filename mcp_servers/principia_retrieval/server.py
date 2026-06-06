from __future__ import annotations

import sys
from contextlib import redirect_stdout
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from mcp_servers.principia_retrieval.retrieval_service import get_service


mcp = FastMCP(
    "principia-retrieval",
    instructions=(
        "Retrieval tools for PrincipiaBlastFoam. The server keeps knowledge "
        "graphs loaded and provides deterministic case/file lookup plus "
        "fallback LLM-based retrieval."
    ),
)


def _call_service(method_name: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
    # stdio MCP uses stdout for JSON-RPC. Keep legacy retriever print output on stderr.
    with redirect_stdout(sys.stderr):
        method = getattr(get_service(), method_name)
        return method(*args, **kwargs)


@mcp.tool()
def get_status() -> Dict[str, Any]:
    """Return server status and loaded knowledge graph statistics."""
    return _call_service("get_status")


@mcp.tool()
def get_case_by_intent(query: str) -> Dict[str, Any]:
    """Resolve a user query or alias such as DDT to a known blastFoam tutorial case."""
    return _call_service("get_case_by_intent", query)


@mcp.tool()
def get_files_for_case(case_path: str) -> Dict[str, Any]:
    """Return files known for a tutorial case path."""
    return _call_service("get_files_for_case", case_path)


@mcp.tool()
def find_variable(case_path: str, variable_name: str) -> Dict[str, Any]:
    """Find files in a case that define a variable by exact variable name."""
    return _call_service("find_variable", case_path, variable_name)


@mcp.tool()
def get_file_content(case_path: str, file_path: str, max_lines: int = 120) -> Dict[str, Any]:
    """Read tutorial file content from BLASTFOAM_TUTORIALS."""
    return _call_service("get_file_content", case_path, file_path, max_lines=max_lines)


@mcp.tool()
def get_modification_targets(user_request: str, case_path: str | None = None, top_k: int = 5) -> Dict[str, Any]:
    """Return likely case files that should be modified for a user request."""
    return _call_service("get_modification_targets", user_request, case_path=case_path, top_k=top_k)


@mcp.tool()
def search_case_content(
    query: str = "",
    case_path: str | None = None,
    file_path: str | None = None,
    variable_name: str | None = None,
    top_k: int = 5,
    include_file_content: bool = False,
    max_iterations: int = 1,
    detail_level: str = "candidates",
    result_id: str | None = None,
    max_detail_lines: int = 120,
) -> Dict[str, Any]:
    """Search case content in two stages. Defaults to candidates; use detail_level='detail' with result_id for content."""
    return _call_service(
        "search_case_content",
        query,
        case_path=case_path,
        file_path=file_path,
        variable_name=variable_name,
        top_k=top_k,
        include_file_content=include_file_content,
        max_iterations=max_iterations,
        detail_level=detail_level,
        result_id=result_id,
        max_detail_lines=max_detail_lines,
    )


@mcp.tool()
def search_user_guide(
    query: str = "",
    top_k: int = 5,
    detail_level: str = "candidates",
    result_id: str | None = None,
) -> Dict[str, Any]:
    """Search the BlastFoam user guide in two stages. Defaults to candidates; use detail_level='detail' with result_id for content."""
    return _call_service(
        "search_user_guide",
        query,
        top_k=top_k,
        detail_level=detail_level,
        result_id=result_id,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
