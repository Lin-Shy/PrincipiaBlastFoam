--- OpenFOAM Tutorial Case Description: 3D Building Blast (Workshop Version) ---

## Case Overview
**Case Name:** building3DWorkshop
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case is a variation of the `building3D` tutorial, designed for a workshop setting. It simulates the detonation of a spherical explosive charge near a rigid L-shaped 3D building. The primary focus is on the blast wave propagation and its interaction with the structure. The simulation uses adaptive mesh refinement (AMR) and includes extensive post-processing functions.

## Geometry
- **Type:** 3D domain with an L-shaped building.
- **Domain:** A 10m x 10m x 5m box created by `blockMesh`.
- **Building:** An L-shaped structure is imported from an STL file (`L_Wall.stl`) and embedded in the mesh using `snappyHexMesh`.
- **Charge:** A 10kg spherical charge is defined at `(0 0 0.5)`.

## Mesh Configuration
- **Type:** Hybrid mesh created with `blockMesh` (background) and `snappyHexMesh` (body-fitting).
- **Initial Cells:** 25 x 25 x 10 from `blockMesh`.
- **Mesh Generators:** `blockMesh`, `snappyHexMesh`.
- **Adaptive Refinement:** Enabled via `dynamicMeshDict`, based on density gradient, with a maximum refinement level of 2. The mesh is re-balanced during the simulation.

## Boundary Conditions

### Velocity (U)
- **walls (building):** `slip`
- **ground:** `slip`
- **outlet:** `zeroGradient`

### Pressure (p)
- **walls (building):** `zeroGradient`
- **ground:** `zeroGradient`
- **outlet:** `zeroGradient`

### Other Fields (T, alpha.c4, etc.)
- **All boundaries:** `zeroGradient`

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 101298 Pa
- **T (temperature):** uniform 300 K
- **alpha.c4 (c4 volume fraction):** Initialized to 1 in a spherical region representing the 10kg charge using `setFieldsDict`.

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.0025 s
- **Delta T:** 1e-7 s (adaptive time stepping is on)
- **Write Interval:** 5e-5 s

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` time integrator.
- **Flux Scheme:** Tadmor
- **Gradient:** `cellMDLimited leastSquares 1.0`
- **Interpolation:** `vanAlbada` limiter for reconstructed fields.

## Solution Methods
- **Solvers:** `diagonal` solver for all fields (explicit scheme).

## Physical Properties
- **Phases:** `c4` (detonating) and `air` (basic).
- **c4:**
  - Type: `detonating` with a `linear` activation model (point detonation).
  - Reactants EOS: `Murnaghan`.
  - Products EOS: `JWL` (Jones-Wilkins-Lee).
- **Air:**
  - Type: `basic` with `idealGas` equation of state.

## Key Features
- **Workshop Focus:** Simplified setup compared to the standard `building3D` case, with more focus on post-processing.
- **Extensive Post-Processing:** Includes `surfaces` function to write out data on patches, iso-surfaces, and cutting planes, and `blastProbes` to record time-history data at specific points.
- **Adaptive Mesh Refinement (AMR):** Dynamically refines and re-balances the mesh to efficiently capture the blast wave.
- **Detonation Modeling:** Uses the JWL equation of state for accurate modeling of high-explosive products.

## Use Cases
- A hands-on tutorial for learning `blastFoam`, `snappyHexMesh`, and AMR.
- Demonstrating advanced post-processing capabilities in OpenFOAM.
- Simulating blast wave propagation and loading on structures in a simplified 3D environment.
