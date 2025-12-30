--- OpenFOAM Tutorial Case Description: Bursting Window (Workshop) ---

## Case Overview
**Case Name:** burstingWindow_workshop
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case simulates the detonation of a hemispherical charge on the ground near a building with windows designed to burst under pressure. The simulation models the blast wave propagation, its interaction with the building, and the subsequent failure of the windows, allowing the blast to enter the structure. The problem is symmetric, so only half of the domain is modeled.

## Geometry
- **Type:** 3D domain featuring a building with windows.
- **Domain:** A large computational box defined by `blockMesh`.
- **Building:** A structure imported from an STL file (`building.stl`) and meshed using `snappyHexMesh`.
- **Windows:** Defined as a `faceZone` within the mesh, which is later converted into a special `burstCyclicAMI` boundary.
- **Symmetry:** A symmetry plane is used to reduce the computational domain by half.

## Mesh Configuration
- **Type:** Hybrid mesh from `blockMesh` and `snappyHexMesh`.
- **Initial Cells:** 60 x 40 x 40 from `blockMesh`.
- **Mesh Generators:** `blockMesh`, `snappyHexMesh`, `topoSet`, `createBaffles`.
- **Special Feature:** The `createBaffles` utility is used to create the `burstCyclicAMI` patches for the windows from a `faceZone`.
- **Adaptive Refinement:** Enabled via `dynamicMeshDict`, based on density gradient, with a maximum refinement level of 1.

## Boundary Conditions

### Windows (`windows_master`, `windows_slave`)
- **Type:** `burstCyclicAMI`
- **Intact Behavior:** Acts as a `slip` wall.
- **Burst Model:** `pressure`-based. The windows burst when the pressure difference across them exceeds a threshold (`pBurst` = 5e6 Pa, though this seems high and might be a placeholder).
- **Post-Burst Behavior:** The boundary becomes a cyclic Arbitrary Mesh Interface (AMI), allowing flow to pass through the opening.

### Other Boundaries
- **building, ground:** `slip` wall.
- **outlet:** `zeroGradient` (outflow).
- **symmetry:** `symmetry`.

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 101298 Pa
- **T (temperature):** uniform 300 K
- **alpha.c4 (c4 volume fraction):** Initialized to 1 in a hemispherical region on the ground plane to represent a 25kg charge, using `setFieldsDict`.

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.01 s
- **Delta T:** 1e-7 s (adaptive time stepping is on)
- **Write Interval:** 1e-4 s

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` integrator.
- **Flux Scheme:** Tadmor
- **Gradient:** `cellMDLimited leastSquares 1.0`
- **Interpolation:** `Minmod` limiter for reconstructed fields.

## Physical Properties
- **Phases:** `c4` (detonating) and `air` (basic).
- **c4:**
  - Reactants EOS: `BirchMurnaghan3`.
  - Products EOS: `JWL`.
- **Air:** `idealGas` equation of state.

## Key Features
- **Solver:** `blastFoam`.
- **Bursting Windows:** Demonstrates the use of the `burstCyclicAMI` boundary condition to model structural failure (window glazing) under blast loading.
- **Complex Workflow:** Requires a multi-step mesh generation process (`blockMesh`, `snappyHexMesh`, `topoSet`, `createBaffles`).
- **Symmetry:** Utilizes a symmetry boundary condition to simplify the problem.
- **Adaptive Mesh Refinement (AMR):** Captures the blast wave as it propagates and interacts with the building.

## Use Cases
- Simulating blast effects on buildings with breakable components.
- A tutorial for advanced boundary conditions like `burstCyclicAMI`.
- Modeling internal and external blast loading scenarios.
- Validating models for structural failure due to overpressure.
