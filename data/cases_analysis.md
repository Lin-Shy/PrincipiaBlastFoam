Created [](file:///media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/analyze_cases.py)

Ran terminal command: python /media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/analyze_cases.py

以下是基于 cases_description 目录下 28 个 case 文件的统计数据概览：

### 1. 总体规模
*   **Case 总数**: 28 个

### 2. 求解器分布 (Solver Distribution)
绝大多数 case 使用 `blastFoam` 及其衍生求解器，显示了该集合以爆炸和可压缩流模拟为核心。
*   **blastFoam**: 17 个 (核心求解器，用于爆炸、激波)
*   **blastFSIFoam**: 2 个 (流固耦合)
*   **blastEulerFoam**: 2 个 (欧拉-欧拉多相流)
*   **blastReactingFoam**: 2 个 (反应流)
*   **blastXiFoam**: 1 个 (燃烧/爆轰转变)
*   **blastParcelFoam**: 1 个 (拉格朗日粒子)
*   **solids4Foam**: 1 个 (固体力学/FSI)
*   **icoFoam**: 1 个 (基础流体基准)
*   **Utility**: 1 个 (辅助工具 `initializeAtmosphere`)

### 3. 物理特性 (Physical Features)
*   **反应与爆轰 (Reaction & Detonation)**: 21 个 (75%)
    *   绝大部分 case 都涉及化学反应、燃烧或高能炸药的爆轰过程，这是该 case 集合最显著的特征。
*   **自适应网格 (AMR/Dynamic Mesh)**: 21 个 (75%)
    *   为了捕捉激波锋面，大部分 case 都启用了自适应网格细化技术。
*   **流固耦合 (FSI)**: 8 个 (29%)
    *   约三分之一的 case 涉及流体与固体结构的相互作用，包括刚性体和柔性体。

### 4. 几何维度 (Geometry Dimensions)
*   **3D**: 11 个 (包括复杂的建筑物外爆、内爆场景)
*   **2D**: 8 个 (包括平面激波、方腔流等)
*   **2D Axisymmetric (轴对称)**: 5 个 (利用楔形网格模拟球形或圆柱形爆炸，以降低计算量)
*   **1D**: 1 个 (基础激波管原理演示)
*   **Unknown/Other**: 3 个 (主要是工具或特殊设置)

### 5. Case 类型 (Case Types)
*   **Tutorial (教程)**: 19 个 (主要用于教学和演示功能)
*   **Validation (验证)**: 5 个 (用于与理论解或实验数据对比，验证求解器准确性)
*   **Utility (工具)**: 4 个 (辅助性工具或脚本说明)

### 总结
这个集合是一个**高度专业化**的 OpenFOAM 算例库，**核心聚焦于高能物理模拟**（爆炸、冲击波、爆轰）。它不仅包含基础的理论验证算例，还提供了大量复杂的工程应用场景（如城市环境爆炸、流固耦合），并且广泛采用了**自适应网格 (AMR)** 技术来平衡计算精度与效率。

Made changes.