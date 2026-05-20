# MCP Servers

This directory contains MCP servers that expose PrincipiaBlastFoam capabilities
as reusable tools.

## Principia Retrieval

`principia_retrieval` keeps the case-content knowledge graph loaded in one MCP
server process and exposes deterministic retrieval tools for agents.

Dependencies used with this repository's LangChain 0.3 stack:

```bash
pip install "mcp==1.27.1" "langchain-mcp-adapters==0.0.11"
```

Do not install the latest `langchain-mcp-adapters` without checking dependency
constraints: recent versions require `langchain-core>=1.0`, while this project
currently uses `langchain-core==0.3.70`.
