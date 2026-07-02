# PrincipiaBlastFoam

PrincipiaBlastFoam 已迁移为基于 LangChain 团队 Deep Agents 框架的实现。
旧的 LangGraph/ReAct 运行时不再作为 active code path 使用。

## 当前架构

- Deep Agents 负责主智能体、规划、虚拟文件系统、子智能体、权限和 MCP
  工具集成。
- 本项目只保留 blastFoam/OpenFOAM 领域相关代码：tutorial 选择、MCP
  检索、执行前检查、求解执行、后处理摘要、产物契约和 benchmark 兼容输出。
- `run_workflow.py` 和 `run_batch_workflow.py` 仍保留旧入口形式，但内部已
  调用 Deep Agents 实现。

## 环境

```bash
cd /data/graduation-projects/PrincipiaBlastFoam
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

项目直接使用当前目录下已有的 `.env`，该文件保持 git 忽略，不要提交或打印。

## 快速检查

```bash
pytest
principia-deepagents --help
python run_workflow.py --help
python run_batch_workflow.py --help
principia-deepagents mcp-smoke
```

功能复现和 benchmark 证据见
[`docs/MIGRATION_STATUS.md`](docs/MIGRATION_STATUS.md)。最新 12-case
solver-enabled 矩阵已在 `--recursion-limit 80` 下通过，所有 case 都生成
成功的 `execution_status.json`、有效的 `post_processing_report.md` 和通过的
`artifact_contract.json`。
