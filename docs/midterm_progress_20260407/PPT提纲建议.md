# 中期答辩 PPT 提纲建议

## 第 1 页：课题背景与研究目标

- 说明 blastFoam / OpenFOAM 案例配置复杂、知识门槛高、自动化程度不足。
- 引出本课题目标：面向仿真任务构建一个知识增强的多智能体辅助系统。

## 第 2 页：系统总体架构

- 放图：
  `[01_system_architecture.png](/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/docs/midterm_progress_20260407/figures/01_system_architecture.png)`
- 讲清楚多智能体分工，以及知识库和验证模块在系统中的位置。

## 第 3 页：知识底座与实验数据

- 放图：
  `[03_asset_and_benchmark_overview.png](/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/docs/midterm_progress_20260407/figures/03_asset_and_benchmark_overview.png)`
- 强调目前已经完成的数据建设规模：
  `28` 个 tutorial case、`542` 个文件节点、`3420` 个变量节点、`233` 个用户手册节点。

## 第 4 页：检索方法设计

- 放图：
  `[02_retrieval_pipelines.png](/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/docs/midterm_progress_20260407/figures/02_retrieval_pipelines.png)`
- 左边讲 embedding baseline，右边讲 Knowledge Graph 检索。
- 重点突出：图谱法不是普通向量检索，而是带有结构关系和推理循环的检索方式。

## 第 5 页：案例内容检索结果

- 放图：
  `[04_case_content_overall_metrics.png](/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/docs/midterm_progress_20260407/figures/04_case_content_overall_metrics.png)`
- 结论建议：
  “在 case-content 任务中，知识图谱方法相较 embedding baseline 有数量级上的提升。”

## 第 6 页：为什么图谱法更有效

- 放图：
  `[05_case_content_granularity_gap.png](/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/docs/midterm_progress_20260407/figures/05_case_content_granularity_gap.png)`
- 推荐口径：
  “embedding 往往能找到相关案例，但无法稳定定位到正确文件，而图谱法通过 Case-File-Variable 关系把问题细化到了文件层。”

## 第 7 页：用户手册检索结果

- 放图：
  `[07_user_guide_overall_metrics.png](/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/docs/midterm_progress_20260407/figures/07_user_guide_overall_metrics.png)`
  或
  `[08_user_guide_granularity_and_difficulty.png](/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/docs/midterm_progress_20260407/figures/08_user_guide_granularity_and_difficulty.png)`
- 推荐口径：
  “在结构更规整的用户手册场景中，embedding 已经具备较好的章节级定位能力，但图谱重排仍能显著提升精确节点命中率。”

## 第 8 页：当前阶段结论

- 放图：
  `[09_accuracy_efficiency_tradeoff.png](/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/docs/midterm_progress_20260407/figures/09_accuracy_efficiency_tradeoff.png)`
- 建议总结三点：
  1. 知识图谱检索显著提升准确率。
  2. 提升最明显的场景是精细文件定位。
  3. 当前仍需继续优化效率。

## 第 9 页：已完成工作与待完成工作

- 已完成：
  多智能体框架搭建、知识图谱构建、严格检索 benchmark、端到端验证脚本。
- 待完成：
  批量端到端实验、效率优化、论文实验章节完善。

## 第 10 页：下一阶段计划

- 补齐端到端案例生成验证结果。
- 继续优化知识图谱检索效率。
- 增加消融实验与论文写作整理。

## 答辩时的节奏建议

- 如果时间只有 8 分钟，建议重点讲第 2、3、5、6、8、10 页。
- 如果老师更关注“你到底做了什么”，就多讲知识图谱构建规模和 benchmark 设计。
- 如果老师更关注“结果是否有效”，就重点讲 `case_content` 的精细定位提升和精度-效率权衡。
