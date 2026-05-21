# Knowledge Retrievers

本目录中的知识检索引擎目前分为两类。它们是 MCP retrieval service 的内部实现和离线评测入口，不再作为 agent-facing tool 直接暴露。

- `UserGuideKnowledgeGraphRetriever`: 面向 BlastFoam 用户手册的分层检索
- `CaseContentKnowledgeGraphRetriever`: 面向 tutorial 案例内容的全局检索

## 代码入口

- 用户手册检索: `principia_ai/retrieval/user_guide_knowledge_graph.py`
- 案例内容检索: `principia_ai/retrieval/case_content_knowledge_graph.py`
- agent-facing MCP 工具: `principia_ai/tools/mcp_retrieval_tools.py`
- retrieval LLM 配置解析: `principia_ai/tools/retrieval_llm_config.py`

## 详细文档

- 用户手册检索方法: `docs/检索方法/用户手册知识检索技术文档.md`
- 案例内容检索方法: `docs/检索方法/案例内容知识检索技术文档.md`
- 检索基线评测入口: `experiments/retrieval_method/README.md`

## Retrieval LLM 配置优先级

案例内容检索相关工具使用以下优先级解析模型配置：

1. 显式传参
2. `RETRIEVAL_LLM_*`
3. `LLM_*`

这样可以让检索方法与主工作流智能体使用不同的模型与服务地址。
