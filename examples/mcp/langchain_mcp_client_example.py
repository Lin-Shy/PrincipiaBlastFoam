"""Example: load Principia retrieval MCP tools for LangChain/LangGraph agents."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def principia_retrieval_client() -> MultiServerMCPClient:
    """Build a client that can be used as an async context manager."""
    return MultiServerMCPClient(
        {
            "principia_retrieval": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "mcp_servers.principia_retrieval.server"],
                "cwd": str(PROJECT_ROOT),
            }
        }
    )


async def load_principia_retrieval_tools():
    """Return MCP-backed LangChain tools for Principia retrieval."""
    async with principia_retrieval_client() as client:
        return client.get_tools()


async def main() -> None:
    async with principia_retrieval_client() as client:
        tools = client.get_tools()
        print(f"Loaded {len(tools)} MCP tools:")
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())
