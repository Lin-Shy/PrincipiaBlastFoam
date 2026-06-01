# 多智能体blastFoam端到端评测指标矩阵

## 设计原则

第3章端到端评测不应只报告最终准确率。对于OpenFOAM/blastFoam自动化仿真，最终是否通过只是结果变量，失败原因可能来自案例检索、文件修改、物理参数、执行环境、求解器日志、后处理字段、审查路由或多智能体交接。因此扩展评测采用“任务结果+过程轨迹+物理可比性+系统成本”的组合指标。

## 指标分层

| 层级 | 指标 | 含义 | 数据来源 |
| --- | --- | --- | --- |
| 任务结果 | 严格通过率 | runner中`benchmark_passed=true`的比例 | `benchmark_report.json` |
| 任务结果 | 部分得分 | 将关键检查项映射为0到1后取平均，反映接近成功的程度 | `summary.checks` |
| 任务结果 | pass@k/稳定通过率 | 同一案例重复运行k次至少一次通过，或k次均值/方差 | 多次benchmark报告 |
| 案例选择 | tutorial命中率 | 选择的参考案例是否包含预期关键词 | workflow log、runner解析 |
| 案例选择 | 来源覆盖率 | 物理报告是否引用/解释了需求中的真实场景要素 | `physics_report.md`、人工或LLM审查 |
| 文件产物 | 报告完整率 | 物理、执行、状态、审查报告是否齐全 | case目录 |
| 文件产物 | 配置约束满足率 | `endTime`、`writeInterval`、探针字段、重要文件是否满足约束 | case配置文件 |
| 执行可靠性 | 退出码成功率 | workflow进程退出码为0的比例 | runner |
| 执行可靠性 | 超时率 | runner超时或子流程超时比例 | runner |
| 执行可靠性 | 求解器正常结束率 | solver log是否包含clean end | solver log |
| 执行可靠性 | 状态契约一致率 | `execution_status.json`与日志、报告是否一致 | 状态文件、日志 |
| 物理合理性 | 比例距离一致性 | 爆源、测点和等价药量是否与任务描述一致 | `setFieldsDict`、探针配置 |
| 物理合理性 | 时间步/CFL合理性 | `deltaT`、Courant数、写出间隔是否支持短时冲击波观测 | solver log |
| 物理合理性 | 网格和域约束 | 是否避免无必要扩大计算域或大规模网格加密 | 配置diff、网格日志 |
| 物理可比性 | 峰值超压误差 | 有参考数据时比较峰值超压相对误差 | 探针文件、实验表格 |
| 物理可比性 | 到达时间误差 | 比较冲击波到达测点时间 | 探针文件、实验表格 |
| 物理可比性 | 正相冲量误差 | 比较压力正相积分 | 探针文件、后处理 |
| 后处理 | 可观测字段完整率 | `p`、`overpressure`、`impulse`等字段是否实际落盘 | `postProcessing` |
| 后处理 | 曲线可绘制率 | 压力/冲量时间序列是否非空且列数合理 | 探针文件 |
| 多智能体过程 | 轨迹保真度 | 实际阶段序列是否覆盖物理分析、案例设置、执行、审查 | workflow log |
| 多智能体过程 | 交接契约完整率 | 上游产物是否满足下游输入要求，如探针路径、压力字段、状态文件 | 报告、日志 |
| 多智能体过程 | 工具调用准确率 | 工具选择和参数是否与当前任务相关且路径有效 | tool trace/log |
| 多智能体过程 | 重复工具调用率 | 短窗口内重复读取同一无新增信息文件或重复失败命令的比例 | tool trace/log |
| 多智能体过程 | 错误恢复率 | 出现可恢复错误后能否修正并继续完成 | workflow log、状态文件 |
| 成本效率 | 总耗时 | 单案例wall time | runner |
| 成本效率 | agent耗时分布 | 各agent执行时间均值、P95、最大值 | metrics JSON |
| 成本效率 | token总量和分布 | 总输入/输出token、按agent聚合 | metrics JSON |
| 成本效率 | 成本/成功案例 | token或API成本除以通过案例数 | metrics JSON、价格表 |
| 鲁棒性 | 外部服务失败率 | LLM连接错误、检索服务异常、工具服务异常 | workflow log |
| 鲁棒性 | 上下文污染率 | 日志中出现无关diff、无关文件、敏感文件尝试等 | workflow log |
| 清理与复现 | 磁盘占用 | 运行前后case目录大小、清理释放字节数 | runner cleanup |
| 清理与复现 | 输出可追溯率 | 是否保存报告、日志、benchmark JSON和关键配置 | run目录 |

## 建议综合得分

为避免“能跑完但物理和后处理不可用”的案例被高估，建议将扩展benchmark的部分得分拆成五个维度：

```text
S_total = 0.25 S_task + 0.20 S_execution + 0.20 S_physics + 0.20 S_observability + 0.15 S_agent
```

- `S_task`：tutorial命中、报告齐全、需求约束满足。
- `S_execution`：退出码、超时、状态文件、solver clean end。
- `S_physics`：比例距离、源项/边界条件、时间步/CFL、网格和域约束。
- `S_observability`：压力字段、探针文件、曲线可绘制、峰值/冲量/到达时间可提取。
- `S_agent`：工具调用准确、重复调用少、交接契约完整、错误恢复有效。

没有实验参考数据的短时smoke案例只报告可观测性指标；有实验表格或曲线的案例再补充峰值超压、到达时间和冲量误差。

## 可视化建议

| 图 | 用途 | 输入 |
| --- | --- | --- |
| 历史运行通过率柱状图 | 观察workflow是否回归 | 多个`benchmark_report.json` |
| 案例-检查项热力图 | 快速定位哪个环节失败 | `summary.checks` |
| 失败原因Pareto图 | 区分主要工程问题和偶发问题 | false检查项、日志错误类型 |
| agent耗时/token堆叠图 | 分析成本瓶颈 | metrics JSON |
| 压力-时间曲线 | 验证探针输出和到达时间 | `postProcessing`探针文件 |
| 冲量-时间曲线 | 验证正相积分输出 | `impulse`或二次后处理 |
| 压力云图/截面图 | 展示冲击波传播、反射和遮挡 | ParaView或`foamToVTK`输出 |
| 案例选择桑基图 | 展示真实需求到tutorial选择的映射 | workflow log |

## 调研参考

- NVIDIA NeMo Agentic Evaluation Metrics强调工具调用准确率、目标完成、主题保持、答案正确性和轨迹评价：https://docs.nvidia.com/nemo/microservices/latest/evaluator/metrics/agentic.html
- CLEAR框架指出只看准确率会忽略成本、延迟、可靠性、稳定性和合规性：https://arxiv.org/abs/2511.14136
- AgentChangeBench提出任务完成、工具效率、重复调用、目标变化恢复和鲁棒性等多维指标：https://openreview.net/pdf?id=ZCi58UP9uR
- Agentic Success Rate强调仅看最终成功会掩盖执行路径缺失，应比较预期和实际状态转移：https://arxiv.org/abs/2605.06457
