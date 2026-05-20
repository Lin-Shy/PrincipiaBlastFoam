from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _to_jsonable(value):
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_servers.principia_retrieval.server"],
        cwd=str(PROJECT_ROOT),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS", [tool.name for tool in tools.tools])

            for name, arguments in [
                ("get_status", {}),
                ("get_case_by_intent", {"query": "DDT laminar flame speed Su"}),
                (
                    "get_modification_targets",
                    {
                        "user_request": (
                            "Simulate DDT and change Su from 0.434 to 0.35."
                        ),
                        "top_k": 4,
                    },
                ),
                (
                    "find_variable",
                    {
                        "case_path": "blastXiFoam/deflagrationToDetonationTransition",
                        "variable_name": "Su",
                    },
                ),
                (
                    "get_file_content",
                    {
                        "case_path": "blastXiFoam/deflagrationToDetonationTransition",
                        "file_path": "constant/combustionProperties",
                        "max_lines": 40,
                    },
                ),
            ]:
                result = await session.call_tool(name, arguments)
                print(f"\nCALL {name}")
                print(json.dumps(_to_jsonable(result.content), ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    asyncio.run(main())
