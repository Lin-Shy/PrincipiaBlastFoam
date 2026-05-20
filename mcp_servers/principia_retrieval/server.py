from __future__ import annotations

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


@mcp.tool()
def get_status() -> Dict[str, Any]:
    """Return server status and loaded knowledge graph statistics."""
    return get_service().get_status()


@mcp.tool()
def get_case_by_intent(query: str) -> Dict[str, Any]:
    """Resolve a user query or alias such as DDT to a known blastFoam tutorial case."""
    return get_service().get_case_by_intent(query)


@mcp.tool()
def get_files_for_case(case_path: str) -> Dict[str, Any]:
    """Return files known for a tutorial case path."""
    return get_service().get_files_for_case(case_path)


@mcp.tool()
def find_variable(case_path: str, variable_name: str) -> Dict[str, Any]:
    """Find files in a case that define a variable by exact variable name."""
    return get_service().find_variable(case_path, variable_name)


@mcp.tool()
def get_file_content(case_path: str, file_path: str, max_lines: int = 120) -> Dict[str, Any]:
    """Read tutorial file content from BLASTFOAM_TUTORIALS."""
    return get_service().get_file_content(case_path, file_path, max_lines=max_lines)


@mcp.tool()
def get_modification_targets(user_request: str, top_k: int = 5) -> Dict[str, Any]:
    """Return likely case files that should be modified for a user request."""
    return get_service().get_modification_targets(user_request, top_k=top_k)


@mcp.tool()
def search_case_content(
    query: str,
    top_k: int = 5,
    include_file_content: bool = False,
    max_iterations: int = 1,
) -> Dict[str, Any]:
    """Fallback LLM-driven search over the case content knowledge graph."""
    return get_service().search_case_content(
        query,
        top_k=top_k,
        include_file_content=include_file_content,
        max_iterations=max_iterations,
    )


@mcp.tool()
def search_user_guide(query: str, top_k: int = 5) -> Dict[str, Any]:
    """Search the BlastFoam user guide knowledge graph."""
    return get_service().search_user_guide(query, top_k=top_k)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

