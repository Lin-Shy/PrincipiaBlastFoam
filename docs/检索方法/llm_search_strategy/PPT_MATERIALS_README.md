# 基于LLM生成搜索策略的知识图谱检索方法 - PPT资料包

本资料包包含了展示"基于LLM生成搜索策略的知识图谱检索方法"的完整PPT素材。

## 📁 文件清单

### 1. **llm_search_strategy_presentation.md**
完整的PPT内容文档，包含：
- 核心思想与方法特点
- 技术架构详解
- 性能数据与对比
- 应用场景与未来拓展
- 完整的Mermaid流程图
- 搜索策略示例

**适用场景**: 作为演讲稿或详细技术文档

### 2. **llm_search_strategy_flowchart.mmd**
完整详细的技术流程图（Mermaid格式）
- 展示从查询输入到结果输出的完整流程
- 包含所有关键步骤和数据流
- 多维度评分机制详解

**适用场景**: 技术细节展示，方法论说明

### 3. **llm_search_strategy_flowchart_simple.mmd**
简化版流程图（Mermaid格式）
- 突出核心步骤
- 适合PPT单页展示
- 包含关键性能指标

**适用场景**: PPT主流程图，概览性展示

### 4. **llm_search_strategy_example.mmd**
搜索策略生成示例图（Mermaid格式）
- 展示具体的输入输出示例
- 包含真实的查询案例
- 清晰的策略JSON结构

**适用场景**: 方法原理讲解，案例演示

### 5. **performance_comparison.mmd**
性能对比可视化图表（Mermaid格式）
- 嵌入检索 vs 知识图谱检索
- 5项核心指标对比
- 提升百分比标注

**适用场景**: 效果展示，优势说明

## 🎨 如何使用

### 在线渲染Mermaid图表

1. **Mermaid Live Editor** (推荐)
   - 访问: https://mermaid.live/
   - 复制`.mmd`文件内容粘贴进去
   - 自动渲染，可导出为PNG/SVG

2. **GitHub/GitLab**
   - 直接在Markdown中引用`.mmd`文件
   - 平台会自动渲染

### 本地编辑器渲染

1. **VS Code**
   - 安装插件: "Markdown Preview Mermaid Support"
   - 在Markdown预览中查看

2. **Typora**
   - 原生支持Mermaid语法
   - 直接粘贴代码即可渲染

3. **Obsidian**
   - 原生支持Mermaid
   - 使用代码块: ````mermaid

### 导出为图片

1. **使用Mermaid CLI**
   ```bash
   npm install -g @mermaid-js/mermaid-cli
   mmdc -i llm_search_strategy_flowchart.mmd -o flowchart.png
   ```

2. **在线工具导出**
   - Mermaid Live Editor提供PNG/SVG导出
   - 高分辨率，适合PPT使用

## 📊 推荐的PPT结构

### 第1页: 标题页
- 标题: 基于LLM生成搜索策略的知识图谱检索方法
- 副标题: 智能化、自适应的技术文档检索

### 第2页: 核心思想
- 使用`llm_search_strategy_presentation.md`中的"核心思想"部分
- 可配简化流程图

### 第3页: 方法流程
- 主图: `llm_search_strategy_flowchart_simple.mmd`（简化版）
- 简要说明关键步骤

### 第4页: 技术细节
- 主图: `llm_search_strategy_flowchart.mmd`（完整版）
- 或使用`llm_search_strategy_example.mmd`展示具体案例

### 第5页: 性能表现
- 主图: `performance_comparison.mmd`
- 数据表格（从presentation.md复制）

### 第6页: 应用与展望
- 应用场景列举
- 未来拓展方向

## 📈 关键数据速查

### 整体性能（vs 嵌入检索）
- MRR提升: **+130.7%** (0.2294 → 0.5292)
- Hit@1提升: **+169.9%** (16.67% → 45.00%)
- Hit@5提升: **+82.5%** (33.33% → 60.83%)

### 最佳表现
- 基础查询 Hit@5: **65.71%**
- 高级查询 MRR: **0.5000**

## 🎯 核心卖点（演讲要点）

1. **智能化**: LLM自动理解查询意图，生成精确搜索策略
2. **结构化**: 充分利用知识图谱的关系和层次结构
3. **高精度**: 相比传统方法提升80%+，Hit@5达60%+
4. **可解释**: 搜索策略透明，匹配逻辑清晰
5. **领域优势**: 在复杂技术领域（CFD仿真）表现卓越

## 💡 演讲建议

### 开场（1分钟）
- 问题: 技术文档检索的痛点
- 传统方法的局限性

### 方法介绍（3分钟）
- 展示简化流程图
- 讲解核心创新点
- 用具体案例说明

### 技术深入（2分钟）
- 展示完整流程图或策略示例
- 说明多维度评分机制

### 效果展示（2分钟）
- 展示性能对比图
- 重点强调提升幅度
- 不同难度级别的表现

### 总结展望（1分钟）
- 核心优势回顾
- 应用前景

## 🔗 相关代码

如需查看实现细节：
- 用户手册检索: `principia_ai/tools/user_guide_knowledge_graph_tool.py`
- 案例内容检索: `principia_ai/tools/case_content_knowledge_graph_tool.py`
- 评估脚本: `experiments/evaluate_knowledge_graph_retriever.py`
- 评估结果: `experiments/results/comparison_report_20251028_144031.md`

## 📝 引用建议

如需在论文或报告中引用：

```
基于LLM生成搜索策略的知识图谱检索方法，通过将大语言模型的自然语言理解能力
与知识图谱的结构化知识表示相结合，实现了智能化、自适应的技术文档检索。
在BlastFOAM数据集上的实验表明，该方法在MRR、Hit@K等指标上相比传统嵌入检索
提升超过80%，在复杂查询场景中Hit@5达到60.83%。
```

## 🆘 问题排查

### Mermaid图表无法渲染
- 检查代码块标记是否正确: ````mermaid
- 确认工具/插件已安装
- 尝试在线编辑器: https://mermaid.live/

### 图表导出模糊
- 使用SVG格式（矢量图）
- 或调整PNG导出的DPI设置

### 需要修改图表
- `.mmd`文件是纯文本，可直接编辑
- 参考Mermaid官方文档: https://mermaid.js.org/

---

**创建时间**: 2025-10-28  
**适用场景**: 技术汇报、学术演讲、项目展示  
**预计演讲时长**: 8-10分钟
