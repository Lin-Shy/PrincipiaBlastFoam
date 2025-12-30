--- OpenFOAM Tutorial Case Description: Reacting Particles ---

## Case Overview
**Case Name:** reactingParticles
**Solver:** blastEulerFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case simulates a two-phase flow with reacting granular particles suspended in a gas. The simulation involves combustion of the particles, which are ignited in a specific region. The flow is compressible and modeled using an Eulerian-Eulerian approach for both the gas and particle phases. Adaptive mesh refinement is used to capture the reaction front.

## Geometry
- **Type:** 2D rectangular domain
- **Dimensions:** 1m × 1m × 0.1m
- **Description:** A simple 2D box.

## Mesh Configuration
- **Type:** Uniform structured mesh with adaptive refinement.
- **Initial Cells:** 50 × 50 × 1
- **Mesh Generator:** blockMesh
- **Adaptive Refinement:** Enabled via `dynamicMeshDict`, based on density gradient, with a maximum refinement level of 1.

## Boundary Conditions
- **walls:**
  - Type: `wall`
  - Velocity (U.gas, U.particles): `slip`
  - Other fields: `zeroGradient`
- **defaultFaces:**
  - Type: `empty` (for 2D simulation)

## Initial Conditions
- **p (pressure):** uniform 101298 Pa
- **T.gas, T.particles (temperature):** uniform 300 K
- **U.gas, U.particles (velocity):** uniform (0 0 0) m/s
- **alpha.particles (particle volume fraction):** Initialized to 0.5 in a `boxToCell` region from (0.25 0 0) to (0.75 1 0.1) using `setFieldsDict`.
- **ignitor.gas (ignitor species fraction):** Initialized to 1 in a small `boxToCell` region from (0.45 0.45 0) to (0.55 0.55 0.1) to trigger the reaction.

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.0025 s
- **Delta T:** 1e-7 s (adaptive time stepping is on)
- **Write Interval:** 1e-4 s

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` time integrator.
- **Flux Schemes:**
  - **gas:** HLLC
  - **particles:** AUSM+Up
- **Gradient:** `cellMDLimited leastSquares 1.0`
- **Interpolation:** `quadraticMUSCL vanAlbada` for reconstructed fields.

## Solution Methods
- **Solvers:**
  - `(rho|alpahRhoU|alphaRhoE|alpha).*`: `diagonal`
  - `(U|e|Yi).*`: `PBiCGStab` with `DIC` preconditioner

## Physical Properties
- **Phases:** `particles` (granular) and `gas` (multicomponent).
- **Gas Species:** `ignitor`, `air`, `products`.
- **Particle Phase:**
  - Granular flow with kinetic theory model.
  - Diameter changes based on a pressure-based reaction rate model.
- **Gas Phase:**
  - Multicomponent mixture with Abel-Nobel equation of state.
- **Inter-phase Models:**
  - **Drag:** `GidaspowErgunWenYu`
  - **Heat Transfer:** `RanzMarshall`
  - **Mass Transfer:** `reactingParticle` model, where particles react to form `products`.

## Key Features
- **Solver:** `blastEulerFoam` for multiphase, compressible, reacting flows.
- **Two-Phase Flow:** Eulerian-Eulerian modeling of gas and granular particles.
- **Combustion:** Simulates particle reaction and heat release.
- **Adaptive Mesh Refinement (AMR):** Captures the flame front and high-gradient regions.

## Use Cases
- Simulating dust explosions or solid fuel combustion.
- Validating multiphase reacting flow models.
- Studying inter-phase drag, heat, and mass transfer phenomena.
- Tutorial for `blastEulerFoam` with complex physics.
