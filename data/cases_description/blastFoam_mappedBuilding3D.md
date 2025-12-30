--- OpenFOAM Tutorial Case Description: 3D Building with Mapped Blast Wave ---

## Case Overview
**Case Name:** mappedBuilding3D
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case demonstrates a common workflow for simulating blast wave interaction with complex structures. Instead of simulating the explosive detonation directly within the complex geometry, the blast wave is first simulated in a simpler, separate domain (like a wedge or sector) and then the results are mapped onto the larger, more complex domain containing the building. This approach saves significant computational cost. This master case appears to contain the setup for the final `building3D` simulation, which receives the mapped data.

## Geometry
- **Type:** Complex 3D domain with an L-shaped building.
- **Domain:** A 10m x 10m x 5m box.
- **Building:** An L-shaped structure imported from `L_Wall.stl` and meshed using `snappyHexMesh`.

## Mesh Configuration
- **Type:** Hybrid mesh from `blockMesh` and `snappyHexMesh`.
- **Mesh Generators:** `blockMesh`, `snappyHexMesh`.
- **Adaptive Refinement:** Enabled via `dynamicMeshDict` with a maximum refinement level of 2.

## Boundary Conditions
- **walls (building):** `slip`
- **ground:** `slip`
- **outlet:** `zeroGradient`

## Initial Conditions
- **Mapping:** The initial fields (pressure, velocity, etc.) for this case are not set by `setFieldsDict`. Instead, they are intended to be mapped from a precursor simulation (like `wedge` or `sector`) using a utility like `mapFields`. The explosive charge (`alpha.c4`) is not initialized here, as the detonation has already occurred in the precursor simulation.
- **Default State:** Ambient conditions (p=101298 Pa, T=300 K, U=(0 0 0) m/s).

## Time Control
- **Start Time:** 0 s (This would typically be adjusted to match the time of mapping from the source case).
- **End Time:** 0.0025 s
- **Delta T:** 1e-7 s (adaptive).

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` integrator.
- **Flux Scheme:** Tadmor
- **Interpolation:** `quadraticMUSCL Minmod` for reconstructed fields.

## Physical Properties
- **Phases:** `c4` (detonating) and `air` (basic).
- **Note:** While the `c4` phase is defined, it is not expected to be present in this simulation, as only the resulting blast wave in the `air` phase is mapped and propagated.

## Key Features
- **Solver:** `blastFoam`.
- **Field Mapping Workflow:** The primary feature is the use of field mapping to initialize the simulation. This is a powerful technique for handling complex scenarios by breaking them into simpler, sequential simulations.
- **Complex Geometry:** Use of `snappyHexMesh` for an imported STL file.
- **Computational Efficiency:** Avoids the need to run the computationally expensive detonation and initial blast wave expansion phase on the large, complex mesh.

## Use Cases
- A tutorial demonstrating the `mapFields` utility for blast simulations.
- Simulating blast effects on large-scale or complex geometries (e.g., urban environments, industrial plants).
- Efficiently studying the late-time effects of a blast wave interacting with structures.
