--- OpenFOAM Tutorial Case Description: Internal Detonation ---

## Case Overview
**Case Name:** internalDetonation
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case simulates the detonation of an explosive charge inside a 2D L-shaped confined space. The blast wave propagates within the structure, reflecting off the internal walls and eventually exiting through an opening. The simulation includes an "afterburn" model, which accounts for secondary energy release from the reaction of detonation products with the surrounding air.

## Geometry
- **Type:** 2D L-shaped domain.
- **Dimensions:** The domain is constructed from four hexagonal blocks to form an L-shape with an overall size of roughly 5m x 2.5m x 2m (though it's a 2D case).
- **Description:** A confined space with rigid walls and one outlet to the ambient environment.

## Mesh Configuration
- **Type:** Structured mesh composed of multiple blocks.
- **Mesh Generator:** blockMesh
- **Adaptive Refinement:** Enabled via `dynamicMeshDict`, based on density gradient, with a maximum refinement level of 2.

## Boundary Conditions
- **walls:** `slip` wall condition.
- **outlet:** `zeroGradient` (outflow).
- **defaultFaces:** `empty` for 2D simulation.

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 101298 Pa
- **T (temperature):** uniform 300 K
- **alpha.c4 (c4 volume fraction):** Initialized to 1 in a small spherical region at the origin `(0 0 0)` with a radius of 0.05m, representing the explosive charge.

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.005 s
- **Delta T:** 1e-8 s (adaptive time stepping is on)
- **Write Interval:** 1e-4 s

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` integrator.
- **Flux Scheme:** Kurganov
- **Gradient:** `cellMDLimited leastSquares 1.0`
- **Interpolation:** `Minmod` limiter for reconstructed fields.

## Solution Methods
- **Solvers:** `diagonal` solver for all fields (fully explicit).

## Physical Properties
- **Phases:** `c4` (detonating) and `air` (basic).
- **c4:**
  - Type: `detonating` with a `linear` activation model (point detonation).
  - Reactants EOS: `Murnaghan`.
  - Products EOS: `JWL`.
- **Afterburn Model:** A `Miller` model is enabled to simulate the secondary combustion of detonation products with entrained air.
- **Air:** `idealGas` equation of state.

## Key Features
- **Solver:** `blastFoam`.
- **Internal Blast:** Focuses on the complex shock wave reflections and channeling that occur during an explosion within a confined space.
- **Afterburn Modeling:** Includes a model for the secondary energy release, which can significantly contribute to the total impulse in oxygen-deficient explosions.
- **Adaptive Mesh Refinement (AMR):** Captures the multiple interacting shock and rarefaction waves inside the structure.

## Use Cases
- Simulating internal explosions in rooms, tunnels, or vessels.
- Studying the effects of confinement on blast wave parameters.
- Validating afterburn models in combustion and explosion simulations.
- A tutorial for setting up confined explosion scenarios with `blastFoam`.
