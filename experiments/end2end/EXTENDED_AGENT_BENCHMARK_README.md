# Principia Agent扩展真实案例Benchmark

## 定位

`agent_benchmark_cases.json`中的3个案例保持不变，继续作为快速smoke benchmark。扩展benchmark单独保存在`agent_benchmark_cases_extended.json`，用于第3章后续端到端实验扩展，不覆盖原有基准。

扩展集当前包含8个真实案例启发任务，覆盖内部爆炸、外部建筑爆炸、城市转角绕射、两箱体干扰、通风受限空间压力释放、半圆柱障碍物反射、建筑室内压力历史和平面波壁面载荷。所有任务都被压缩为短时OpenFOAM/blastFoam工作流验证，目标是评价agent能否完成案例选择、配置修改、运行、后处理和审查，而不是复现实验全部工程尺度。

## 新增案例

| ID | 真实来源 | 推荐tutorial方向 | 核心验证点 |
| --- | --- | --- | --- |
| `erdc_internal_airblast_vent_pipe_probe` | ERDC小尺度内部空气爆炸实验 | `internalDetonation`、`burstingWindow` | 通道/出口压力探针、内部压力传播 |
| `reconass_400kg_external_facade_smoke` | RECONASS 400kg TNT NEQ外部爆炸测试 | `building3D`、`building3DWorkshop` | 建筑迎爆面压力输出、缩放说明 |
| `building_corner_diffraction_probe_grid` | 建筑转角后方TNT压力测量实验 | `mappedBuilding3D`、`sector`、`wedge` | 直达测点和遮挡测点的超压/冲量 |
| `bls_two_box_interference_pressure_history` | ERDC Blast Load Simulator两箱体实验 | `building3D`、`mappedBuilding3D` | 两个障碍物间反射和表面压力历史 |
| `vented_confined_gas_explosion_window_smoke` | 通风受限空间气体爆炸实验 | `burstingWindow_workshop`、`internalDetonation_withObstacleAndGlass` | 室内、开口、外部压力传播链路 |
| `hemicylinder_obstacle_reflection_probe_smoke` | 半圆柱障碍物爆炸波反射实验 | `movingCone`、`mappedBuilding3D` | 入射、反射、绕流后测点 |
| `three_level_building_room_pressure_smoke` | 三层建筑爆炸波相互作用实验 | `building3D`、`internalDetonation_withObstacle` | 建筑内外压力历史输出 |
| `blast_simulator_planar_wave_wall_load` | Blast Load Simulator平面波载荷实验 | `blastEquation/planarWall`、`shockTube_tabulated` | 平面波到达时间和壁面压力 |

## 运行方式

只做集成检查，不执行LLM和OpenFOAM：

```bash
python experiments/end2end/run_agent_benchmark.py \
  --cases-file experiments/end2end/agent_benchmark_cases_extended.json \
  --dry-run
```

运行单个扩展案例：

```bash
python experiments/end2end/run_agent_benchmark.py \
  --cases-file experiments/end2end/agent_benchmark_cases_extended.json \
  --case-id building_corner_diffraction_probe_grid \
  --workflow-timeout 1200 \
  --cleanup-interval 1 \
  --cleanup-final
```

建议先按案例类别分批运行，不建议一次性跑完整扩展集。扩展案例比3案例smoke benchmark更强调真实场景覆盖和失败诊断，运行成本和不确定性更高。

## 评估口径

扩展benchmark应同时报告三层结果：

1. 严格通过率：沿用runner的`benchmark_passed`。
2. 部分得分：按产物完整性、执行完成、物理约束、后处理可观测性、工作流异常缺失等检查项计分。
3. 诊断指标：统计失败原因、token和耗时分布、agent重试、工具调用重复、后处理字段缺失、压力历史是否可用于峰值/冲量/到达时间比较。

更完整的指标矩阵见`agent_benchmark_metrics_extended.md`。

## 结果汇总和可视化

已有benchmark运行结果可用下面脚本汇总为CSV、Markdown和SVG图：

```bash
python experiments/end2end/summarize_benchmark_reports.py
```

默认输出目录：

```text
/data/PrincipiaBlastFoam_output/e2e_agent_benchmark_analysis/run_<timestamp>/
```

生成内容包括：

- `benchmark_case_rows.csv`：逐案例结果表。
- `benchmark_case_rows.json`：逐案例结构化数据。
- `summary.md`：通过率、部分得分、失败原因摘要。
- `pass_rate_by_run.svg`：历史运行严格通过率。
- `partial_score_by_case.svg`：各案例平均部分得分。
- `failure_reason_counts.svg`：失败原因计数。

后续若保留OpenFOAM运行输出，可进一步补充ParaView截图、压力-时间曲线、冲量曲线和关键截面的压力云图。

## 调研来源

- blastFoam ERDC内部空气爆炸示例：https://www.blastfoam.org/examples/erdc-internal-blast-test/
- blastFoam RECONASS 400kg测试示例：https://www.blastfoam.org/examples/reconass-explosive-test.md/
- blastFoam城市爆炸威胁示例：https://www.blastfoam.org/examples/cityscape-modeling/
- 建筑转角后方爆炸载荷实验：https://link.springer.com/article/10.1007/s00193-020-00936-1
- ERDC Blast Load Simulator Report 5：https://erdc-library.erdc.dren.mil/items/81b728f7-ab65-4ef8-e053-411ac80adeb3
- 通风受限空间气体爆炸实验：https://repository.lib.ncsu.edu/items/a1ffa2b9-261c-49c4-b3d3-0e3a0d82f9ec
- 半圆柱障碍物爆炸波实验：https://link.springer.com/article/10.1007/s00193-023-01135-4
- 三层建筑爆炸波相互作用实验：https://cris.bgu.ac.il/en/publications/experimental-and-numerical-investigation-of-blast-wave-interactio/
