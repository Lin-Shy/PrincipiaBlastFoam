--- OpenFOAM Tutorial Case Description: Polydisperse Shock Tube ---

## Case Overview
**Case Name:** shockTube_polydisperse
**Solver:** blastEulerFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case simulates a one-dimensional shock tube problem with a polydisperse mixture of solid particles suspended in a gas. The simulation uses an Eulerian-Eulerian approach to model the gas phase and five distinct particle phases, each representing a different particle size. The setup involves a high-pressure driver section and a low-pressure driven section containing the particle mixture. The shock wave propagates through the two-phase medium.

## Geometry
- **Type:** 1D rectangular domain (modeled as a thin 3D block)
- **Dimensions:** 1m × 0.01m × 0.01m
- **Description:** A long, thin tube, effectively representing a 1D shock tube.

## Mesh Configuration
- **Type:** Uniform structured mesh
- **Cells:** 400 × 1 × 1
- **Mesh Generator:** blockMesh

## Boundary Conditions
- **inlet, outlet:** `patch` type, with conditions effectively managed by the initial state and wave propagation.
- **defaultFaces:** `empty` type for the sides, enforcing 2D/1D behavior.

## Initial Conditions
The domain is initialized into two distinct regions using `setFieldsDict`:
- **High-Pressure Region (Driver, x < 0.5m):**
  - **p (pressure):** 142040 Pa
  - **T.gas (temperature):** 370.13 K
  - **U.gas (velocity):** (198.9 0 0) m/s
  - **Particles:** No particles present (`alpha.particles* = 0`).
- **Low-Pressure Region (Driven, x >= 0.5m):**
  - **p (pressure):** 67000 Pa
  - **T.gas (temperature):** 295 K
  - **U.gas (velocity):** (0 0 0) m/s
  - **T.particles (temperature):** 270 K for all particle phases.
  - **alpha.particles (volume fraction):** Each of the 5 particle phases is initialized with a small volume fraction (`1e-4`).

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.001 s
- **Delta T:** 1e-8 s (adaptive time stepping is enabled)
- **Write Interval:** 5e-5 s

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` time integrator.
- **Flux Schemes:**
  - **gas:** HLLC
  - **particles:** AUSM+Up
- **Gradient:** `cellMDLimited leastSquares 1.0`
- **Interpolation:** `vanLeer` for reconstructed fields.

## Solution Methods
- **Solvers:**
  - `(rho|alphaRhoU|alphaRhoE|alpha).*`: `diagonal`
  - `(U|e).*`: `PBiCGStab` with `DIC` preconditioner

## Physical Properties
- **Phases:** `gas` and five particle phases (`particles0` through `particles4`).
- **Polydisperse Particles:** Each particle phase is granular and has a constant, distinct diameter, creating a polydisperse system:
  - `particles0`: 1 µm
  - `particles1`: 5 µm
  - `particles2`: 10 µm
  - `particles3`: 20 µm
  - `particles4`: 50 µm
- **Gas Phase:** Modeled as an ideal gas.
- **Inter-phase Models:**
  - **Drag:** `GidaspowErgunWenYu`
  - **Heat Transfer:** `RanzMarshall`

## Key Features
- **Solver:** `blastEulerFoam` for multiphase, compressible flows.
- **Polydisperse Flow:** Models particles of multiple sizes simultaneously.
- **Shock Tube:** Classic CFD validation case for compressible multiphase solvers.
- **Eulerian-Eulerian Model:** Treats both gas and solid particles as interpenetrating continua.

## Use Cases
- Validating compressible multiphase solvers and inter-phase models.
- Studying shock wave interaction with particle clouds.
- Analyzing particle dispersion and velocity/thermal relaxation in high-speed flows.
- A tutorial for setting up polydisperse simulations in `blastEulerFoam`.
