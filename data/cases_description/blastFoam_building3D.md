--- OpenFOAM Tutorial Case Description: 3D Building Blast ---

## Case Overview
**Case Name:** building3D
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case simulates the detonation of a cylindrical explosive charge near a rigid L-shaped 3D building. The simulation models the propagation of the resulting blast wave in the air and its interaction with the building's surfaces. It is a compressible, multiphase problem involving a detonating material (c4) and air, utilizing adaptive mesh refinement to capture the shock front.

## Geometry
- **Type:** Complex 3D domain with an L-shaped building.
- **Domain:** A 10m x 10m x 5m box created by `blockMesh`.
- **Building:** An L-shaped structure is imported from an STL file (`L_Wall.stl`) and meshed using `snappyHexMesh`.
- **Charge:** A cylindrical charge with 25kg mass is defined near the origin.

## Mesh Configuration
- **Type:** Hybrid mesh combining a background mesh from `blockMesh` with a body-fitted mesh from `snappyHexMesh`.
- **Mesh Generators:** `blockMesh`, `snappyHexMesh`.
- **Adaptive Refinement:** Enabled via `dynamicMeshDict`, based on density gradient, with a maximum refinement level of 1.
- **Surface Refinement:** The building (`walls`) and a cylindrical region are refined during the `snappyHexMesh` process.

## Boundary Conditions

### Velocity (U)
- **walls (building):** `slip`
- **ground:** `slip`
- **outlet:** `zeroGradient`

### Pressure (p)
- **walls (building):** `zeroGradient`
- **ground:** `zeroGradient`
- **outlet:** `zeroGradient` (acts as a non-reflecting boundary)

### Other Fields (T, alpha.c4, etc.)
- **All boundaries:** `zeroGradient`

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 101298 Pa (atmospheric pressure)
- **T (temperature):** uniform 300 K
- **alpha.c4 (c4 volume fraction):** Initialized to 1 within a cylindrical region using `setFieldsDict` to represent the explosive charge, and 0 elsewhere.

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.0025 s
- **Delta T:** 1e-7 s (adaptive time stepping is on)
- **Write Interval:** 5e-5 s

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` time integrator.
- **Flux Scheme:** Kurganov
- **Gradient:** `cellMDLimited leastSquares 1.0`
- **Interpolation:** `quadraticMUSCL Minmod` for reconstructed fields.

## Solution Methods
- **Solvers:** `diagonal` solver for all fields, as it's an explicit solver.

## Physical Properties
- **Phases:** `c4` (detonating) and `air` (basic).
- **c4:**
  - Type: `detonating` with a `pressureBased` activation model.
  - Reactants EOS: `BirchMurnaghan3`.
  - Products EOS: `JWL` (Jones-Wilkins-Lee).
- **Air:**
  - Type: `basic` with `idealGas` equation of state.

## Key Features
- **Solver:** `blastFoam` for compressible, multiphase, explosive flows.
- **Complex Geometry:** Use of `snappyHexMesh` to handle an imported STL file.
- **Blast Wave Loading:** Simulates the impact of a blast wave on a 3D structure.
- **Adaptive Mesh Refinement (AMR):** Dynamically refines the mesh to accurately capture the propagating shock wave.
- **Detonation Modeling:** Utilizes advanced equations of state (JWL) to model the explosive material.

## Use Cases
- Simulating blast effects on urban structures.
- Validating `blastFoam` for fluid-structure interaction scenarios (with rigid structures).
- A tutorial for using `snappyHexMesh` in conjunction with `blastFoam` and AMR.
- Assessing blast loads and impulse on buildings.
