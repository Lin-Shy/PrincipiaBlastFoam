--- OpenFOAM Tutorial Case Description: Free Field Blast ---

## Case Overview
**Case Name:** freeField
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case simulates the detonation of an explosive charge in a free field, meaning an open space without obstructions. The setup uses a quarter-symmetry model to reduce computational cost. A block of explosive material is initiated at two points, and the resulting blast wave propagates outwards. The ground is modeled as a reflective (slip) wall.

## Geometry
- **Type:** 3D quarter-symmetry domain.
- **Dimensions:** 10ft x 10ft x 10ft (note `convertToMeters 0.3048`).
- **Symmetry:** Two symmetry planes (`midPlane1`, `midPlane2`) are used, modeling only one quadrant of the full 3D space.

## Mesh Configuration
- **Type:** Uniform structured mesh with adaptive refinement.
- **Initial Cells:** 10 x 10 x 10
- **Mesh Generator:** blockMesh
- **Adaptive Refinement:** Enabled via `dynamicMeshDict`, based on density gradient, with a maximum refinement level of 3.

## Boundary Conditions
- **ground:** `slip` wall for velocity, `zeroGradient` for other fields.
- **midPlane1, midPlane2:** `symmetry`.
- **outlet:** `zeroGradient` (non-reflecting outflow).

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 101298 Pa
- **T (temperature):** uniform 300 K
- **alpha.c4 (c4 volume fraction):** Initialized to 1 in a `boxToCell` region from (0 0 0) to (0.5 0.25 0.25) ft, representing the explosive charge.

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.0005 s
- **Delta T:** 1e-7 s (adaptive time stepping is on)
- **Write Interval:** 1e-5 s

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` integrator.
- **Flux Scheme:** Kurganov
- **Gradient:** `cellMDLimited leastSquares 1.0`
- **Interpolation:** `vanAlbada` limiter for reconstructed fields.

## Solution Methods
- **Solvers:** `diagonal` solver for all fields (fully explicit).

## Physical Properties
- **Phases:** `c4` (detonating) and `air` (basic).
- **c4:**
  - Type: `detonating` with a `linear` activation model.
  - Initiation: Two initiation points are specified at `(0.125 0.125 0.125)` and `(0.375 0.125 0.125)`.
  - Reactants EOS: `Murnaghan`.
  - Products EOS: `JWL`.
- **Air:** `idealGas` equation of state.

## Key Features
- **Solver:** `blastFoam`.
- **Free Field Simulation:** A fundamental case for validating blast wave propagation in an unconfined environment.
- **Quarter Symmetry:** Efficiently models a full 3D problem by exploiting symmetry.
- **Adaptive Mesh Refinement (AMR):** Essential for accurately capturing the thin shock front as it expands, while keeping the overall cell count manageable.
- **Multi-Point Initiation:** The charge is detonated from two points simultaneously.

## Use Cases
- Basic validation of a blast solver and its underlying physics models.
- A starting point for more complex blast scenarios.
- Tutorial for setting up a simple `blastFoam` case with AMR and symmetry.
- Generating free-field pressure-time histories for comparison with empirical models or experimental data.
