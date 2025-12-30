# BlastFOAM Modification Dataset

## Overview
This dataset contains 130 carefully curated OpenFOAM case modification examples for training and validating automated case generation systems. Each entry represents a specific modification to a reference BlastFOAM case, ranging from simple parameter adjustments (basic) to complex physics model changes (senior).

## Dataset Structure

The dataset is split into two files based on modification complexity:

### 1. `blastfoam_basic_modifications.json` (69 entries)
Simple, single-parameter modifications suitable for beginners or basic automation tasks. These modifications typically involve changing a single value in one configuration file.

### 2. `blastfoam_senior_modifications.json` (61 entries)
Advanced modifications involving complex physics models, numerical schemes, equation of state changes, and sophisticated parameter adjustments.

Each entry contains:

```json
{
    "case_path": "<reference_case_name>",
    "case_name": "<modified_case_name>",
    "modified_files": ["<file_path_1>", "<file_path_2>", ...],
    "description": "<detailed_explanation>",
    "modification": "<specific_change_description>"
}
```

### Fields Description

- **case_path**: Name of the reference case from which the modification is derived
- **case_name**: Unique name for the modified case (typically `{case_path}_{modification_tag}`)
- **modified_files**: Array of OpenFOAM file paths that need to be modified
- **description**: Natural language description of what the modification achieves
- **modification**: Detailed technical specification of the exact changes to make

## Reference Cases (7 types)

The modifications are based on 7 representative BlastFOAM cases:

1. **reactingParticles** (28 entries total: 10 basic + 18 senior)
   - Granular flow with combustion, multiphase drag models, heat transfer, and granular stress models
   - Most diverse case covering multiphase phenomena

2. **freeField** (23 entries total: 12 basic + 11 senior)
   - Free-field explosion with various EOS models, mesh refinement, and thermodynamics
   - Classic explosion scenario with comprehensive coverage

3. **internalDetonation_withObstacleAndGlass** (21 entries total: 12 basic + 9 senior)
   - Closed-space explosion with structural mechanics, window failure, and numerical schemes
   - Structural interaction and complex boundary conditions

4. **deflagrationToDetonationTransition** (20 entries total: 11 basic + 9 senior)
   - DDT process simulation with turbulence, combustion, reaction kinetics, and flux schemes
   - Combustion-focused modifications

5. **movingCone** (17 entries total: 9 basic + 8 senior)
   - Moving mesh with shock interaction and numerical schemes
   - Dynamic mesh and flux limiter variations

6. **triplePointShockInteration** (13 entries total: 9 basic + 4 senior)
   - Complex shock physics with various flux limiters and mesh settings
   - High-resolution shock capturing schemes

7. **mappedBuilding3D** (8 entries: 6 basic + 2 senior)
   - Large-scale building explosion simulation with adaptive mesh refinement
   - AMR and output control focus

## Modification Categories

### Basic Modifications (69 entries)

#### 1. Time Control - endTime (15 entries)
Simulation duration adjustments in `system/controlDict`:
- Extending simulations for longer physical time
- Shortening simulations for quick tests
- Examples: 20e-3 → 30e-3, 0.0005 → 0.001

#### 2. Mesh Generation (11 entries)
Changes in `system/blockMeshDict`:
- Cell count variations (mesh refinement/coarsening)
- Examples: (10 10 10) → (20 20 20), 3000 cells → 4000 cells
- Domain discretization for different resolutions

#### 3. Output Control (8 entries)
Write settings in `system/controlDict`:
- writeInterval changes (output frequency)
- writeFormat modifications (binary/ascii)
- Examples: 1e-5 → 5e-6, ascii → binary

#### 4. Boundary Conditions (6 entries)
Field value modifications in `0/U`, `0/U.orig`:
- Velocity field adjustments
- Initial velocity distributions

#### 5. Time Control - maxCo (6 entries)
Courant number adjustments in `system/controlDict`:
- Stability control through maxCo
- Examples: 0.5 → 0.4, 0.5 → 0.3

#### 6. Initial Conditions (6 entries)
Field initialization in `system/setFieldsDict`:
- Explosive charge size/position
- Initial field distributions
- Region definitions

#### 7. Combustion Parameters (4 entries)
Simple parameter changes in `constant/combustionProperties`:
- Laminar flame speed (Su) modifications
- Equivalence ratio adjustments
- Examples: Su 0.434 → 0.5, equivalenceRatio 1 → 0.8

#### 8. Turbulence Models (3 entries)
Basic model switches in `constant/turbulenceProperties`:
- kOmegaSST ↔ SpalartAllmaras
- laminar ↔ RANS models

#### 9. Adaptive Mesh Refinement (3 entries)
AMR settings in `constant/dynamicMeshDict`:
- maxRefinement level changes
- Examples: maxRefinement 3 → 4

#### 10. Window Failure (3 entries)
Burst pressure in `constant/phaseProperties`:
- pBurst threshold modifications
- Examples: 40 kPa → 50 kPa

#### 11. Phase Properties - Other (3 entries)
Various phase property modifications in `constant/phaseProperties`:
- Phase-specific parameter adjustments

#### 12. Material Properties (1 entry)
Basic property changes in `constant/phaseProperties`:
- Density (rho0) modifications

### Senior Modifications (61 entries)

#### 1. Numerical Schemes - Flux (9 entries)
Flux scheme selection in `system/fvSchemes`:
- Flux limiter changes: vanAlbada, MUSCL, vanLeer, HLLC, AUSM+
- Riemann solver selection: HLLC, Kurganov, AUSM+up
- Examples: Kurganov → HLLC, vanAlbada → MUSCL

#### 2. Numerical Schemes - Other (9 entries)
Additional scheme modifications in `system/fvSchemes`:
- Reconstruction schemes
- Divergence schemes
- Gradient schemes

#### 3. Turbulence Models (7 entries)
Advanced turbulence modeling in `constant/turbulenceProperties`:
- Complex RANS model switches
- Two-equation model configurations
- Turbulence model parameter tuning

#### 4. Structural Mechanics (7 entries)
Material models in `constant/phaseProperties`:
- linearElastic → elasticPlastic (with yield stress)
- Fracture criteria (pBurst → principalStrain, principalStress)
- Damage models and failure criteria

#### 5. Phase Properties - Other (6 entries)
Complex phase property modifications in `constant/phaseProperties`:
- Multi-parameter adjustments
- Phase interaction parameters

#### 6. Granular Stress Models (6 entries)
Particle-phase stress in `constant/turbulenceProperties.particles`:
- Schaeffer model
- Lun model
- Gidaspow model
- Princeton model variations

#### 7. Equation of State (5 entries)
EOS model changes in `constant/phaseProperties`:
- perfectGas → JWL (Jones-Wilkins-Lee)
- perfectGas → BKW (Becker-Kistiakowsky-Wilson)
- perfectGas → stiffenedGas
- perfectGas → rhoConst (constant density)

#### 8. Solver Settings (3 entries)
Algorithm parameters in `system/fvSolution`:
- Solver tolerances
- Relaxation factors
- Solution algorithms

#### 9. Reaction Kinetics (2 entries)
Combustion rate models in `constant/combustionProperties`:
- Laminar flame speed → Arrhenius kinetics
- Arrhenius → infinitelyFast
- Reaction rate model switches

#### 10. Thermodynamics (2 entries)
Thermodynamic models in `constant/phaseProperties`:
- perfectThermo → eConstThermo (constant specific heat)
- perfectThermo → janafThermo (JANAF tables)
- perfectThermo → hPolynomialThermo

#### 11. Multiphase Drag (2 entries)
Interphase drag in `constant/phaseProperties`:
- Drag model selection (GidaspowErgunWenYu, SchillerNaumann, WenYu, Ergun)
- Drag coefficient modifications

#### 12. Heat Transfer (2 entries)
Interphase heat transfer in `constant/phaseProperties`:
- RanzMarshall model
- Heat transfer coefficient modifications

#### 13. Adaptive Mesh Refinement (1 entry)
Advanced AMR in `constant/dynamicMeshDict`:
- Refinement criteria adjustments

## File Distribution

### Overall File Frequency (All 130 entries)
1. `constant/phaseProperties` (31 entries, 23.8%) - Physics models, EOS, materials, drag, heat transfer
2. `system/controlDict` (24 entries, 18.5%) - Time control and output settings
3. `system/fvSchemes` (16 entries, 12.3%) - Numerical schemes and flux limiters
4. `system/blockMeshDict` (11 entries, 8.5%) - Mesh generation
5. `constant/turbulenceProperties` (8 entries, 6.2%) - Turbulence models
6. `constant/combustionProperties` (6 entries, 4.6%) - Combustion and reaction models
7. `system/setFieldsDict` (6 entries, 4.6%) - Initial conditions
8. `constant/turbulenceProperties.particles` (6 entries, 4.6%) - Granular stress models
9. `building3D/system/controlDict` (5 entries, 3.8%) - Building case control
10. `0/U` (3 entries, 2.3%) - Velocity fields
11. `constant/dynamicMeshDict` (3 entries, 2.3%) - AMR settings
12. `system/fvSolution` (3 entries, 2.3%) - Solver settings
13. Others (8 entries, 6.2%) - Various configuration files

### Basic Modifications - Most Modified Files
1. `system/controlDict` (23 entries) - Time control (endTime, maxCo) and output (writeInterval)
2. `system/blockMeshDict` (11 entries) - Mesh generation
3. `system/setFieldsDict` (6 entries) - Initial field setup
4. `0/U` and `0/U.orig` (6 entries) - Velocity boundary conditions
5. `building3D/system/controlDict` (5 entries) - Building simulation control
6. `constant/combustionProperties` (4 entries) - Combustion parameters
7. `constant/phaseProperties` (4 entries) - Basic material properties
8. `constant/turbulenceProperties` (3 entries) - Turbulence model selection
9. `constant/dynamicMeshDict` (3 entries) - AMR settings
10. Others (4 entries) - Miscellaneous files

### Senior Modifications - Most Modified Files
1. `constant/phaseProperties` (27 entries) - Advanced physics models (EOS, thermo, drag, heat transfer, materials)
2. `system/fvSchemes` (16 entries) - Numerical discretization schemes and flux limiters
3. `constant/turbulenceProperties` (7 entries) - Advanced turbulence models
4. `constant/turbulenceProperties.particles` (6 entries) - Granular stress models
5. `system/fvSolution` (3 entries) - Solver algorithms and tolerances
6. `constant/combustionProperties` (2 entries) - Reaction kinetics
7. Others (0 entries) - Minimal other files

## Difficulty Breakdown

### Basic Level (69 entries, 53.1%)
**Characteristics:**
- Single-file modifications (100% are single-file)
- Single-parameter changes
- Numerical value adjustments
- Simple model switches (e.g., turbulence model A → B)
- Direct parameter → value mappings
- No complex physics model changes

**Skill Requirements:**
- Basic OpenFOAM file structure knowledge
- Understanding of common parameters (endTime, maxCo, mesh cells, writeInterval)
- Ability to locate and edit specific keywords
- No deep physics knowledge required

**Common Modifications:**
- Time control: endTime, maxCo, deltaT
- Mesh settings: cell counts, domain size
- Output: writeInterval, writeFormat
- Simple parameters: Su, equivalenceRatio, rho0, pBurst

**Example:**
```
Description: "Run simulation for longer duration"
Modification: "Change endTime from 20e-3 to 30e-3"
File: system/controlDict
```

### Senior Level (61 entries, 46.9%)
**Characteristics:**
- Single-file modifications (100% are single-file)
- Complex physics model replacements
- Numerical scheme selections
- Multi-parameter model changes (within same file)
- Requires understanding of model-specific parameters
- Dictionary structure modifications

**Skill Requirements:**
- Deep understanding of OpenFOAM physics models
- Knowledge of model-specific parameters (e.g., JWL EOS parameters)
- Awareness of appropriate model selections
- Familiarity with advanced BlastFOAM features
- Understanding of numerical methods (flux schemes, limiters)
- CFD expertise for scheme selection

**Common Modifications:**
- EOS models: perfectGas → JWL/BKW/stiffenedGas
- Flux schemes: Kurganov → HLLC/AUSM+/MUSCL
- Turbulence models: Complex RANS model switches
- Material models: linearElastic → elasticPlastic
- Granular stress: Schaeffer/Lun/Gidaspow models
- Reaction kinetics: Su → Arrhenius → infinitelyFast

**Example:**
```
Description: "Use AUSM flux scheme for better shock capturing"
Modification: "In fvSchemes, change fluxScheme from Kurganov to AUSM+up"
File: system/fvSchemes
```

### Key Difference
- **Basic**: "What value to change" - straightforward parameter adjustments
- **Senior**: "What model to use" - requires domain expertise and model selection knowledge

## Use Cases

### 1. Training Case Generation Systems
Use the dataset to train or validate automated case generation:
```python
for entry in dataset:
    reference_case = load_case(entry['case_path'])
    generated_case = system.generate(reference_case, entry['modification'])
    validate(generated_case, entry['modified_files'], entry['case_name'])
```

### 2. Testing LLM-based Modification Agents
Evaluate natural language → code modification capabilities:
- Input: `entry['description']` or `entry['modification']`
- Expected output: Correct file modifications in `entry['modified_files']`
- Metric: Exact match of modified content

### 3. Benchmarking Code Modification Tools
Compare different approaches:
- Template-based systems
- Rule-based transformations
- LLM-powered code editors
- Graph-based knowledge systems

### 4. Curriculum Learning
Progressive difficulty training:
1. Start with basic modifications (simple parameter changes)
2. Progress to senior modifications (complex model changes)
3. Eventually handle novel modifications not in dataset

### 5. Modification Intent Understanding
Train systems to map natural language descriptions to precise modifications:
- **Input**: "Make simulation more stable"
- **Output**: Identify need to reduce maxCo or adjust numerical schemes
- **Dataset**: Provides ground truth mapping examples

## Evaluation Metrics

### Primary Metrics
1. **Exact File Match**: Correct files identified for modification
2. **Modification Accuracy**: Exact parameters changed correctly
3. **Value Accuracy**: Correct new values assigned
4. **Syntax Validity**: Generated files pass OpenFOAM parsing
5. **Semantic Correctness**: Modified case is physically meaningful

### Secondary Metrics
6. **Category-wise Accuracy**: Performance by modification type (EOS, mesh, etc.)
7. **Difficulty-wise Accuracy**: Basic vs. Senior performance gap
8. **Case-wise Accuracy**: Performance across different reference cases
9. **Multi-file Accuracy**: Success rate on modifications requiring multiple files
10. **Robustness**: Handling of edge cases and model combinations

### Advanced Metrics
11. **Generalization**: Performance on held-out reference cases
12. **Interpolation**: Generating modifications with parameter values between training examples
13. **Extrapolation**: Handling parameter values outside training range
14. **Composition**: Combining multiple atomic modifications correctly

## Coverage Analysis

### OpenFOAM Directory Coverage
- **0/ directory**: 6 entries (4.6%) - Initial/boundary conditions
- **constant/ directory**: 80 entries (61.5%) - Physics models and properties
- **system/ directory**: 44 entries (33.8%) - Numerical settings and mesh

### BlastFOAM-Specific Features
- **Equation of State**: 5 entries (JWL, BKW, stiffenedGas, rhoConst)
- **Multiphase Models**: 4 entries (drag, heat transfer)
- **Granular Flow**: 6 entries (granular stress models)
- **Structural Mechanics**: 7 entries (material models, fracture criteria)
- **Combustion**: 6 entries (reaction models, flame speed)
- **Flux Schemes**: 18 entries (HLLC, AUSM+, MUSCL, limiters)

### General OpenFOAM Features
- **Time Control**: 21 entries (endTime, maxCo, deltaT)
- **Mesh Generation**: 11 entries (blockMesh settings)
- **Turbulence**: 10 entries (RANS models, granular models)
- **Numerical Schemes**: 19 entries (fvSchemes, fvSolution)
- **Adaptive Mesh Refinement**: 4 entries (AMR settings)
- **Output Control**: 8 entries (write settings)
- **Initial Conditions**: 6 entries (setFields)

### Physics Model Types
- **Thermodynamics**: 2 entries (eConst, janaf, hPolynomial)
- **Turbulence Models**: 10 entries (kOmegaSST, SpalartAllmaras, etc.)
- **Material Models**: 7 entries (elastic, plastic, damage)
- **Reaction Models**: 2 entries (Arrhenius, infinitelyFast)

## Realistic Modification Scenarios

The dataset reflects common user workflows:

1. **Parametric Studies**: Systematically varying parameters (density, mesh size, time steps)
2. **Model Comparison**: Switching between alternative physics models (EOS, turbulence, drag)
3. **Mesh Convergence**: Refining mesh and AMR settings
4. **Stability Tuning**: Adjusting Courant number and time stepping
5. **Accuracy Enhancement**: Higher-fidelity models (JWL vs. perfectGas, Arrhenius vs. Su)
6. **Computational Efficiency**: Balancing accuracy and cost (mesh, output frequency)
7. **Physics Extension**: Adding complexity (multiphase drag, heat transfer, reactions)

## Challenging Cases

The dataset includes cases that test edge conditions:

### Ambiguous Modifications
- **"Improve accuracy"**: Could mean finer mesh OR higher-order schemes OR better physics models
- Multiple valid solutions requiring context understanding

### Cascading Requirements
- **EOS change**: Often requires new thermodynamics model and compatible parameters
- **Multiphase activation**: May need drag model + heat transfer + granular stress

### Model-Specific Parameters
- **JWL EOS**: Requires A, B, R1, R2, omega (not present in perfectGas)
- **elasticPlastic material**: Needs sigmaY (yield stress) not in linearElastic

### Implicit Knowledge
- **"Use more realistic explosive model"**: Implies switching to JWL or BKW
- **"Account for plastic deformation"**: Implies elasticPlastic material model

## Multi-file Modifications

**Important Note**: All modifications in this dataset are **single-file modifications**.
- Basic modifications: 0/69 (0%) are multi-file
- Senior modifications: 0/61 (0%) are multi-file

This design choice simplifies the dataset and makes it ideal for:
- Learning individual file modification patterns
- Understanding file-specific configuration changes
- Training systems on atomic modification operations
- Avoiding complex interdependency handling

For multi-file workflow training, users should combine multiple single-file modifications.

## Dataset Validation

All modifications have been:
1. ✅ **Manually verified** for correctness
2. ✅ **Tested** to ensure valid OpenFOAM syntax
3. ✅ **Documented** with clear descriptions
4. ✅ **Based on realistic cases** from BlastFOAM tutorials
5. ✅ **Categorized** by difficulty and type
6. ✅ **Single-file** for clarity and simplicity

## Version Information

- **Dataset Version**: 2.0
- **Creation Date**: 2025年11月10日
- **Last Updated**: 2025年11月10日
- **BlastFOAM Compatibility**: v4.0+
- **OpenFOAM Compatibility**: v7+
- **Total Entries**: 130 (69 basic + 61 senior)
- **Reference Cases**: 7
- **Unique Files Modified**: 16

## Extending the Dataset

To add new modifications:

1. **Choose a reference case**: From existing 7 or add new
2. **Define clear modification**: Specific parameter changes
3. **Write natural description**: How a user would request it
4. **Specify affected files**: Complete list of modified files
5. **Assign difficulty**: Basic (single param) or Senior (complex physics)
6. **Validate**: Ensure OpenFOAM can parse the modified case
7. **Categorize**: Map to existing categories or create new ones

## Citation

If you use this dataset in your research or development, please cite:
```
PrincipiaBlastFoam Modification Dataset
BlastFOAM Case Modification Examples for Automated CFD Case Generation
Version 1.0 (2025)
```

## License

[Specify license if applicable]

## Contact

For questions, corrections, or contributions, please contact [specify contact information].
