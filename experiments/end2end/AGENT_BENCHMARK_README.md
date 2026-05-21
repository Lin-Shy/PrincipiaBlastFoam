# Principia Agent 端到端 Benchmark

这个 benchmark 用黑盒方式测试现有多智能体 workflow。runner 只调用 `run_workflow.py`。每个样例都是一个短时、真实感较强的仿真需求，用来观察系统能否完成 tutorial 选择、配置修改、执行、报告生成和结果清理。

## 文件说明

- `agent_benchmark_cases.json`：端到端测试样例、目标约束和参考来源。
- `run_agent_benchmark.py`：benchmark runner，负责调用 `run_workflow.py`、记录耗时/结果、按间隔清理重型 OpenFOAM 输出。

## 当前样例

初版 benchmark 保持小规模，避免占满数据盘：

- `shock_tube_short_validation`：短时激波管验证。
- `surface_burst_scaled_probe_smoke`：触地爆/地表爆炸比例距离和压力 probe smoke test。
- `building_facade_pressure_probe_smoke`：建筑迎爆面压力 probe smoke test。

这些样例来自常见 blast/CFD 工作流：激波管验证、地表爆炸比例距离检查、建筑周围爆炸载荷评估。`agent_benchmark_cases.json` 中记录了参考来源 URL。

## 运行方式

只打印将要执行的命令：

```bash
python experiments/end2end/run_agent_benchmark.py --limit 2 --dry-run
```

运行一个样例：

```bash
python experiments/end2end/run_agent_benchmark.py \
  --case-id shock_tube_short_validation \
  --workflow-timeout 900 \
  --cleanup-final
```

运行全部小样例，并每 1 个样例清理一次重型仿真输出：

```bash
python experiments/end2end/run_agent_benchmark.py \
  --limit 3 \
  --workflow-timeout 900 \
  --cleanup-interval 1 \
  --cleanup-final
```

默认输出目录：

```text
/data/PrincipiaBlastFoam_output/e2e_agent_benchmark/run_<timestamp>/
```

## 清理策略

runner 会清理：

- 非零数值时间目录，例如 `0.00025`、`0.001`；
- `postProcessing`；
- `processor*` 并行分区目录；
- `.foam` 标记文件。

默认保留：

- `0/`、`constant/`、`system/`；
- `physics_report.md`、`execution_report.md`、`review_report.md`；
- `log.*`；
- benchmark JSON 报告。

如果希望连 `log.*` 也清理，可以加：

```bash
--cleanup-logs
```

## 报告字段

`benchmark_report.json` 会记录：

- workflow 退出码和是否超时；
- 单样例 wall time；
- `physics_report.md` / `execution_report.md` / `execution_status.json` / `review_report.md` 是否生成；
- 实际选择/初始化的 tutorial case；
- `system/controlDict` 中实际配置的 `endTime`；
- 生成的数值时间目录数量；
- metrics report 摘要；
- 清理释放的字节数；
- 基础检查项，例如 `endTime` 是否满足 benchmark 约束。

## 指标解释

初版 smoke benchmark 不追求大样本统计，主要看：

- `exit_code_zero`：workflow 是否正常退出；
- `timed_out`：是否触发 runner 超时；
- `physics_reports`：是否完成物理分析；
- `execution_reports`：是否进入执行并产出执行报告；
- `end_time_within_expected`：是否满足短仿真时间约束；
- `workflow_log_has_completion_marker`：workflow 是否达到 completion state。

runner 会以端到端方式执行 `run_workflow.py`，并显式设置：

```text
ENABLE_EXECUTION=1
REQUIRE_EXECUTION=1
```

### 非 root 执行 OpenFOAM

OpenFOAM 的 `#calc` / `#codeStream` 会触发动态代码编译加载。root 用户执行这类 case 时可能被 OpenFOAM 安全检查拒绝。benchmark runner 支持把每个 workflow/OpenFOAM 子进程切到普通用户：

```bash
python experiments/end2end/run_agent_benchmark.py \
  --limit 3 \
  --run-as-user openfoam \
  --workflow-timeout 1200 \
  --cleanup-interval 1 \
  --cleanup-final
```

如果系统还没有专门用户，可以先创建一个普通用户并确保输出目录可写：

```bash
sudo useradd -m -d /data/openfoam-runner -s /bin/bash openfoam
sudo mkdir -p /data/PrincipiaBlastFoam_output
sudo chown -R openfoam:openfoam /data/PrincipiaBlastFoam_output
```

也可以通过环境变量设置：

```bash
export OPENFOAM_RUN_AS_USER=openfoam
```

如果 runner 本身以 root 启动且没有指定普通用户，它会优先自动查找 `openfoam`、`foam`、`ofuser`。若都不存在，会直接退出并提示配置普通用户。runner 会把本轮 `run_<timestamp>/` 输出目录授权给该用户，然后用 `runuser -u <user> -- bash -lc ...` 启动 workflow。

只有明确接受 root 执行风险时，才使用：

```bash
--allow-root-openfoam
```

## 相关环境变量

执行检查会读取当前 case 的 `system/controlDict` 中的 `application`，并检查对应的 `log.<application>` 或 `log.<application>.*`，不再固定检查 `log.blastFoam`。

physics report 增量更新默认只响应 case 配置文件变化，运行输出不会触发更新：

- `UPDATE_PHYSICS_REPORT=true`：允许执行 `physics_updater`。
- `PHYSICS_UPDATE_MODE=config_only`：默认模式，只对 `system/`、`constant/`、`0/`、`0.orig/` 中的相关配置变化更新。
- `PHYSICS_UPDATE_MODE=off`：关闭增量 physics update。
- `ASYNC_PHYSICS_UPDATE_WITH_EXECUTION=true`：默认设置。若 execution 已启用，配置变化会尝试在后台启动 physics update，同时 solver execution 立即开始，不等待 physics update。
- `ASYNC_PHYSICS_UPDATE_WITH_EXECUTION=false`：恢复阻塞式行为，先更新 physics report，再进入 execution。

因此，样例通过不再只看 workflow 是否打印 completion marker。可以把同时满足以下条件的样例视为初步通过：

- workflow 退出码为 0；
- 未超时；
- 未出现 orchestrator 空输出或 case selection 错误；
- 选择的 tutorial 与样例预期一致；
- 生成 `physics_report.md`；
- 生成 `execution_report.md`；
- 生成 `execution_status.json` 且其中 `final_status=success`、`run_status=completed`；
- solver 日志包含正常 `End` 标记；
- `endTime` 不超过样例约束；
- workflow log 有 completion marker。

## 当前定位

这是小规模 smoke benchmark，目标是尽早发现 workflow 回归、性能瓶颈和明显质量问题。大规模测评前，应先用它确认 agent 系统的端到端链路稳定。
