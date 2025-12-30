--- OpenFOAM Tutorial Case Description: Mapped Blast - Sector Source ---

## Case Overview
**Case Name:** sector (part of mappedBuilding3D)
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case is the *source* simulation for the `mappedBuilding3D` workflow. It simulates the initial detonation of a 25kg spherical charge in a simple, 1D axisymmetric "sector" domain. The purpose is to efficiently generate the early-time blast wave data, which is then saved and mapped onto a more complex domain (like `building3D`) for further analysis. This avoids running the expensive initial detonation phase on a large, complex mesh.

## Geometry
- **Type:** 1D axisymmetric sector.
- **Dimensions:** A 1-meter long line of cells, defined using a clever `blockMeshDict` that creates a degenerate hex block, effectively forming a 1D domain suitable for representing a spherically symmetric outflow from the origin.
- **Description:** This is not a physical geometry but a computational domain designed to produce a 1D spherical blast wave profile.

## Mesh Configuration
- **Type:** 1D line of cells.
- **Cells:** 500 cells in the radial direction.
- **Mesh Generator:** blockMesh
- **Adaptive Refinement:** This precursor simulation does not use adaptive mesh refinement; it relies on a fine initial mesh to resolve the blast wave.

## Boundary Conditions
- **outlet:** `pressureWaveTransmissive`, a non-reflecting boundary condition.
- **wedge0, wedge1, wedge2, wedge3:** `wedge` boundaries are used to create the 1D line of cells from a hex block.
- **ground:** This patch is not present in the `sector` case itself, as it's a free-air detonation.

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 101298 Pa
- **T (temperature):** uniform 288 K
- **alpha.c4 (c4 volume fraction):** Initialized to 1 in a spherical region at the origin representing a 25kg mass of C4 explosive, using `setFieldsDict`.

## Time Control
- **Start Time:** 0 s
- **End Time:** 1e-4 s (a very short duration, just enough to establish the blast wave).
- **Delta T:** 1e-8 s (adaptive).
- **Write Interval:** 1e-5 s.

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` integrator.
- **Flux Scheme:** Kurganov
- **Interpolation:** `Minmod` limiter for reconstructed fields.

## Physical Properties
- **Phases:** `c4` (detonating) and `air` (basic).
- **c4:**
  - Type: `detonating` with a `pressureBased` activation model.
  - Reactants EOS: `Murnaghan`.
  - Products EOS: `JWL`.
- **Air:** `idealGas` equation of state.

## Key Features
- **Solver:** `blastFoam`.
- **Precursor Simulation:** This case's sole purpose is to generate data for another, larger simulation.
- **Computational Efficiency:** By running the detonation on a tiny 1D mesh, the most computationally intensive part of the simulation is performed very quickly.
- **Field Mapping Source:** The results from this case at `t=1e-4`s are intended to be used as the input for the `mapFields` utility.

## Use Cases
- Generating initial conditions for large-scale blast simulations.
- A key component of the `mapFields` workflow tutorial.
- Demonstrating how to decouple the source detonation from the target interaction for efficiency.
