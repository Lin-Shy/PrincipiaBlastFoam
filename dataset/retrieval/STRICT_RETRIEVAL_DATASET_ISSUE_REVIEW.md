# Strict Retrieval Dataset Issue Review

## Scope

This note reviews residual dataset-side risks for the strict retrieval benchmark after the move from case-local retrieval to full-tutorial retrieval.

Strict evaluation unit:

- `case_path::file_path`

Current strict dataset facts:

- Total entries: `130`
- Covered tutorial cases: `7`
- Target files per entry: always `1`
- Audit status: `122 pass / 8 warn / 0 fail`

Source references:

- `dataset/retrieval/benchmarks/case_content/blastfoam_retrieval_validation_dataset_strict.json`
- `dataset/retrieval/benchmarks/case_content/blastfoam_retrieval_validation_dataset_strict_audit.json`
- `dataset/retrieval/STRICT_RETRIEVAL_AUDIT_SUMMARY.md`

## Main Findings

### 1. The dataset is structurally usable, but not purely lexical

The strict split is internally consistent enough to evaluate retrieval:

- all `130` entries resolve to an existing tutorial case and file
- there are no hard audit failures
- strict matching is unambiguous at the evaluator level

But a subset of entries cannot be solved by filename or in-file token overlap alone. They require:

- case-level reasoning
- file-family priors
- understanding which configuration file would be edited for a hypothetical change

This is expected for a retrieval benchmark aimed at edit planning, but it should be documented so we do not misread all misses as retriever bugs.

### 2. Eight entries are intentionally "implicit target" items

These eight audit warnings all mean the same thing:

- the query/description does not contain obvious identifiers that directly appear in the target file
- the target file is still plausible, but the mapping is knowledge-based rather than lexical

Current warning set:

| ID | Case | Target file | Why it is hard |
| --- | --- | --- | --- |
| 32 | `blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass` | `constant/phaseProperties` | "stronger window" does not mention `phaseProperties` |
| 33 | same | `constant/phaseProperties` | "more fragile window" is also implicit |
| 34 | same | `constant/phaseProperties` | query mentions `pBurst`, but base file still needs case-specific interpretation |
| 57 | `blastEulerFoam/reactingParticles` | `constant/turbulenceProperties.gas` | query says "different turbulence model for the gas phase" without naming the file |
| 90 | `blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass` | `constant/phaseProperties` | "progressive damage model for the window" is a semantic mapping |
| 98 | same | `constant/phaseProperties` | "orthotropic material model" is also semantic, not lexical |
| 122 | `blastEulerFoam/reactingParticles` | `constant/phaseProperties` | "higher particle packing limit" does not name the file |
| 124 | same | `constant/phaseProperties` | "higher coefficient of restitution" does not name the file |

Recommendation:

- keep these entries
- tag them explicitly as `implicit_target` in future dataset metadata

### 3. Some targets require adding new content, not editing an already-mentioned token

The most important example is the internal-detonation window group:

- IDs `32, 33, 34, 90, 92, 93, 94, 95, 97, 98`
- target file: `blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass::constant/phaseProperties`

In the current base file, the relevant "window" / fracture / material terms are not directly present as obvious lexical anchors. This means the task is effectively:

- choose the right case
- choose the right configuration family
- add or revise the right block in that file

So these entries are valid for edit-oriented retrieval, but they are difficult for token-matching retrievers and can look like "dataset mistakes" if we only inspect surface text.

### 4. Some entries are hypothetical model swaps rather than value lookups

Examples:

- ID `57`: gas-phase turbulence model -> `constant/turbulenceProperties.gas`
- ID `109`: particle-phase thermal conductivity model -> `constant/turbulenceProperties.particles`
- IDs `120, 121, 122, 124`: interfacial/packing/restitution changes -> `constant/phaseProperties`

These queries ask where a change should be made, not whether the current file already contains the requested target value. A retriever that looks only for the requested model name in the existing file can fail even when the dataset label is correct.

Recommendation:

- evaluate these as retrieval-to-edit-location tasks
- do not expect current-file exact token presence as a prerequisite for label validity

### 5. There is at least one explicit correction exception

ID `74` is a known special case:

- query/modification text describes changing thermo settings in "`phaseProperties`"
- dataset correction note says the actual DDT tutorial stores this in `constant/thermophysicalProperties`

This entry is still usable, but it is a deliberate exception and should remain documented wherever benchmark caveats are listed.

### 6. Case coverage is narrow relative to the full tutorial corpus

The tutorial root has `34` cases, but the strict dataset covers only `7`:

- `blastXiFoam/deflagrationToDetonationTransition`
- `blastFoam/freeField`
- `blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass`
- `blastFoam/mappedBuilding3D`
- `blastFoam/movingCone`
- `blastFoam/triplePointShockInteration`
- `blastEulerFoam/reactingParticles`

This is acceptable for a focused benchmark, but it means:

- non-target but semantically similar cases are common
- case discrimination quality matters a lot
- benchmark scores can be dominated by a few hard case families

## Recommended Dataset Actions

### Keep the current strict split, but add metadata

Suggested extra fields per entry:

- `implicit_target`: true/false
- `requires_case_reasoning`: true/false
- `target_family`: one of `controlDict`, `fvSchemes`, `fvSolution`, `setFieldsDict`, `phaseProperties`, `combustionProperties`, `turbulenceProperties`, `dynamicMeshDict`, ...
- `notes`: short free-text audit note

### Do not "fix" the eight warning entries by changing labels casually

Those eight entries are better treated as:

- hard but valid semantic retrieval examples

Changing them just to improve lexical match would weaken the benchmark.

### Add a future multi-file split instead of overloading the strict split

The current strict dataset is intentionally single-target. That is good for clean scoring, but it under-represents composite edits.

Recommended future addition:

- `blastfoam_retrieval_validation_dataset_multi_file.json`

This split should include requests whose natural edit set spans multiple files, instead of forcing them into a single-file label.

## Recommended Evaluation Actions

When reporting benchmark results, include:

- strict `case+file` metrics
- `case_hit@k`
- per-file-family breakdown
- a separate summary on the `implicit_target` subset

This will help separate:

- real retrieval failures
- case confusion
- file-family confusion
- unavoidable ambiguity from implicit-target entries

## Bottom Line

The strict dataset is usable and mostly correct.

The main issue is not label corruption, but that a small set of entries are semantic edit-location tasks rather than lexical file-lookup tasks. Those entries should stay in the benchmark, but they should be explicitly tagged so model behavior and dataset difficulty are not conflated.
