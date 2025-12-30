# BlastFOAM Retrieval Validation Dataset

## Overview
This dataset contains 120 carefully curated test cases for validating retrieval methods in OpenFOAM case modification systems. Each entry represents a realistic user query or modification request that the retrieval system must correctly map to the appropriate configuration files.

## Dataset Structure

Each entry in `blastfoam_retrieval_validation_dataset.json` contains:

```json
{
    "id": <unique_identifier>,
    "query": "<user_query_or_modification_request>",
    "description": "<detailed_explanation>",
    "target_files": ["<file_path_1>", "<file_path_2>", ...],
    "difficulty": "<basic|intermediate|advanced>",
    "category": "<category_name>"
}
```

### Fields Description

- **id**: Unique integer identifier (1-120)
- **query**: Natural language query or modification request as a user might phrase it
- **description**: Detailed explanation of what needs to be modified and why
- **target_files**: Array of OpenFOAM file paths that should be retrieved/modified
- **difficulty**: Complexity level (basic, intermediate, advanced)
- **category**: Thematic classification of the query type

## Categories (20 types)

1. **turbulence_model** (6 entries): Turbulence modeling changes (RANS models, laminar)
2. **time_control** (8 entries): Simulation time parameters (endTime, maxCo, deltaT)
3. **mesh** (9 entries): Mesh generation and adaptation settings
4. **material_properties** (3 entries): Density, EOS, physical properties
5. **combustion** (8 entries): Reaction models, flame speed, kinetics
6. **output_control** (7 entries): Write intervals, formats, compression
7. **initial_conditions** (8 entries): setFieldsDict configurations
8. **boundary_conditions** (8 entries): BC specifications in 0/ directory
9. **equation_of_state** (4 entries): EOS model selection (JWL, BKW, stiffenedGas)
10. **thermodynamics** (2 entries): Thermo models (eConst, JANAF, perfectThermo)
11. **structural_mechanics** (6 entries): Material models, fracture criteria
12. **numerical_schemes** (5 entries): Discretization schemes, flux limiters
13. **multiphase** (13 entries): Drag models, heat transfer, granular flow
14. **file_location** (10 entries): Questions about which file controls what
15. **goal_based** (15 entries): High-level objectives without technical details
16. **physics_models** (8 entries): Complex multi-physics configurations
17. **solver_control** (5 entries): Algorithm settings, tolerances, relaxation
18. **post_processing** (4 entries): Function objects, probes, sampling
19. **parallel_computing** (3 entries): Domain decomposition settings
20. **model_tuning** (1 entry): Advanced parameter adjustment

## Difficulty Levels

### Basic (40 entries, ~33%)
- Single file modifications
- Simple parameter changes
- Direct user queries with clear intent
- Example: "Set the maximum Courant number to 0.3"

### Intermediate (40 entries, ~33%)
- Multiple related file modifications
- Requires some OpenFOAM knowledge
- Goal-oriented requests needing interpretation
- Example: "Refine mesh to 200x100x50 cells and increase maxRefinement to 3"

### Advanced (40 entries, ~33%)
- Complex physics model changes
- Multiple interdependent modifications
- High-level objectives requiring expert knowledge
- Example: "Switch explosive modeling to use JWL EOS and Arrhenius reaction kinetics"

## Query Types

### 1. Direct Technical Queries (45 entries)
Users specify exact technical changes:
- "Change RASModel from kOmegaSST to SpalartAllmaras"
- "Set maxCo to 0.3"
- "Use MUSCL scheme instead of vanAlbada"

### 2. File Location Queries (10 entries)
Users ask which file to modify:
- "What file controls the turbulence model selection?"
- "Where do I change the simulation duration?"

### 3. Goal-Based Queries (15 entries)
Users describe objectives without technical details:
- "Make the simulation run longer"
- "I want more detailed results in space"
- "The simulation is unstable"

### 4. Complex Configuration (50 entries)
Multi-parameter or multi-file modifications:
- "Setup window failure: pBurst 40 kPa and elasticPlastic material"
- "Configure multiphase drag and heat transfer models"

## Target Files Distribution

Most frequently targeted files:
1. `system/controlDict` (25 occurrences) - Time control, output, solver settings
2. `constant/phaseProperties` (35 occurrences) - Material properties, EOS, multiphase
3. `constant/turbulenceProperties` (12 occurrences) - Turbulence models
4. `constant/combustionProperties` (10 occurrences) - Reaction models
5. `system/fvSchemes` (6 occurrences) - Numerical schemes
6. `system/blockMeshDict` (8 occurrences) - Mesh generation
7. `constant/dynamicMeshDict` (7 occurrences) - Adaptive mesh refinement
8. `system/setFieldsDict` (8 occurrences) - Initial conditions
9. `0/U`, `0/p`, `0/T` (12 occurrences) - Boundary/initial conditions
10. `system/fvSolution` (4 occurrences) - Solver algorithms

## Use Cases

### 1. Retrieval System Evaluation
Measure precision and recall of file retrieval:
```python
for entry in dataset:
    retrieved_files = retrieval_system.query(entry['query'])
    precision = len(set(retrieved_files) & set(entry['target_files'])) / len(retrieved_files)
    recall = len(set(retrieved_files) & set(entry['target_files'])) / len(entry['target_files'])
```

### 2. RAG System Testing
Evaluate retrieval-augmented generation:
- Use queries to retrieve relevant documentation
- Compare retrieved content relevance to target files
- Measure context sufficiency for LLM modification

### 3. Semantic Search Benchmarking
Test embedding-based retrieval:
- Query embeddings vs. file content embeddings
- Measure top-k retrieval accuracy
- Evaluate across difficulty levels

### 4. Query Understanding
Train/evaluate query interpretation:
- Technical term extraction
- Intent classification
- Parameter value extraction

### 5. Multi-hop Reasoning
Test complex query handling:
- Queries requiring multiple files
- Interdependent modifications
- Implicit requirement detection

## Evaluation Metrics

### Primary Metrics
1. **Exact Match Accuracy**: Retrieved files exactly match target_files
2. **Precision@K**: Proportion of top-K retrieved files that are correct
3. **Recall@K**: Proportion of target files found in top-K results
4. **F1 Score**: Harmonic mean of precision and recall
5. **Mean Reciprocal Rank (MRR)**: Average reciprocal rank of first correct file

### Secondary Metrics
6. **Category-wise Accuracy**: Performance breakdown by category
7. **Difficulty-wise Accuracy**: Performance by difficulty level
8. **Query Type Accuracy**: Performance by query formulation type
9. **Multi-file Accuracy**: Performance on queries requiring multiple files
10. **False Positive Rate**: Incorrect files retrieved per query

## Coverage Analysis

### OpenFOAM Directory Coverage
- **0/ directory**: Initial/boundary conditions (15 entries)
- **constant/ directory**: Physical models and properties (60 entries)
- **system/ directory**: Numerical settings and mesh (45 entries)

### BlastFOAM-Specific Coverage
- Explosive modeling (EOS): 8 entries
- Detonation/deflagration: 10 entries
- Structural response: 6 entries
- Multiphase explosives: 13 entries

### General OpenFOAM Coverage
- Turbulence: 12 entries
- Time stepping: 15 entries
- Meshing: 15 entries
- Numerical schemes: 10 entries
- Boundary conditions: 12 entries

## Realistic User Scenarios

The dataset includes queries reflecting actual usage patterns:

1. **Parametric Studies**: Varying single parameters (endTime, maxCo, density)
2. **Model Comparison**: Switching between alternative models (turbulence, EOS)
3. **Mesh Refinement**: Improving spatial resolution
4. **Stability Issues**: Adjusting for numerical stability
5. **Accuracy Improvement**: Higher-order schemes, finer meshes
6. **Physics Enhancement**: Adding complexity (multiphase, combustion)
7. **Computational Efficiency**: Parallel settings, output control
8. **Troubleshooting**: Goal-based queries for problem solving

## Challenging Cases

Specific entries designed to test edge cases:

- **Ambiguous queries** (e.g., "Make simulation more stable" - could be maxCo or schemes)
- **Implicit requirements** (e.g., "Add turbulence" requires multiple files)
- **Technical synonyms** (e.g., "equation of state" vs "EOS" vs "thermodynamic model")
- **Multi-file coordination** (e.g., changing turbulence model requires consistent BC updates)
- **Hierarchical modifications** (e.g., adding new phase requires properties, ICs, and BCs)

## Extension Possibilities

This dataset can be extended with:
1. **Negative examples**: Queries that shouldn't match certain files
2. **Partial matches**: Queries where multiple valid file sets exist
3. **Context-dependent**: Same query different targets based on case type
4. **Error cases**: Common mistakes and their corrections
5. **Multi-language**: Non-English query variations

## Validation Procedure

To validate retrieval system:

```python
def evaluate_retrieval(dataset_path, retrieval_function):
    with open(dataset_path) as f:
        dataset = json.load(f)
    
    results = {
        'exact_match': 0,
        'precision': [],
        'recall': [],
        'f1': []
    }
    
    for entry in dataset:
        retrieved = set(retrieval_function(entry['query']))
        target = set(entry['target_files'])
        
        if retrieved == target:
            results['exact_match'] += 1
        
        if len(retrieved) > 0:
            p = len(retrieved & target) / len(retrieved)
            r = len(retrieved & target) / len(target)
            results['precision'].append(p)
            results['recall'].append(r)
            results['f1'].append(2*p*r/(p+r) if (p+r) > 0 else 0)
    
    return {
        'exact_match_accuracy': results['exact_match'] / len(dataset),
        'mean_precision': np.mean(results['precision']),
        'mean_recall': np.mean(results['recall']),
        'mean_f1': np.mean(results['f1'])
    }
```

## Citation

If you use this dataset, please cite:
```
BlastFOAM Retrieval Validation Dataset
PrincipiaBlastFoam Project
Version 1.0, 2025
120 test cases for OpenFOAM file retrieval evaluation
```

## License

This dataset is part of the PrincipiaBlastFoam project and follows the same licensing terms.
