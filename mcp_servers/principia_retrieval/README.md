# Principia Retrieval MCP Server

This server exposes PrincipiaBlastFoam retrieval tools over MCP. It keeps the
case-content knowledge graph loaded in one long-lived process, so agents can
reuse retrieval tools without each agent loading the graph independently.

## Run

```bash
conda run -n principia python -m mcp_servers.principia_retrieval.server
```

The server uses stdio transport for local MCP clients.

## Test

```bash
conda run -n principia python -m mcp_servers.principia_retrieval.test_client
conda run -n principia python examples/mcp/langchain_mcp_client_example.py
```

The first command calls tools through the MCP protocol. The second verifies
that LangChain can load the MCP tools through `langchain-mcp-adapters`.

## Tools

- `get_status`
- `get_case_by_intent`
- `get_files_for_case`
- `find_variable`
- `get_file_content`
- `get_modification_targets`
- `search_case_content`
- `search_user_guide`

## Two-stage retrieval

`search_case_content` and `search_user_guide` default to compact candidate mode:

```json
{
  "query": "blastFoam controlDict pressure probes",
  "case_path": "blastFoam/axisymmetricCharge",
  "detail_level": "candidates"
}
```

Candidate responses include `result_id` values and omit full file or guide
content. Retrieve detail only for the selected candidate:

```json
{
  "detail_level": "detail",
  "result_id": "case_file:..."
}
```

Use `detail_level="full"` only for rare deep dives where returning full
retrieval content in one call is worth the token cost.
