--- OpenFOAM Tutorial Case Description: Axisymmetric Charge ---

## Case Overview
**Case Name:** axisymmetricCharge
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This case simulates the detonation of an axisymmetric charge and the resulting blast wave propagation in the air. It is a multiphase problem involving a detonating material (c4) and air. The simulation uses an adaptive mesh refinement to capture the shock front accurately.

## Geometry
- **Type:** 2D axisymmetric wedge
- **Dimensions:** 20m radius, 20m height
- **Description:** A 5-degree wedge is used to simulate an axisymmetric domain.

## Mesh Configuration
- **Type:** Structured mesh generated with `blockMesh`, with adaptive refinement.
- **Initial Cells:** 20 x 20 x 1
- **Mesh Generator:** blockMesh
- **Adaptive Refinement:** Enabled via `dynamicMeshDict`, based on density gradient. Maximum refinement level is 4.

## Boundary Conditions

### Velocity (U)
- **outlet:** `zeroGradient`
- **ground:** `slip`
- **wedge0, wedge1:** `wedge`

### Pressure (p)
- **outlet:** `pressureWaveTransmissive`
- **ground:** `zeroGradient`
- **wedge0, wedge1:** `wedge`

### Temperature (T)
- **outlet:** `zeroGradient`
- **ground:** `zeroGradient`
- **wedge0, wedge1:** `wedge`

### Phase Fraction (alpha.c4)
- **outlet:** `zeroGradient`
- **ground:** `zeroGradient`
- **wedge0, wedge1:** `wedge`

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 101298 Pa
- **T (temperature):** uniform 288 K
- **alpha.c4 (c4 volume fraction):** Initialized to 1 in a sphere of radius 0.25m at the origin using `setFieldsDict`, and 0 elsewhere.

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.025 s
- **Delta T:** 1e-8 s (adaptive time stepping is on)
- **Write Interval:** 0.0005 s

## Numerical Schemes
- **Time derivative:** Euler
- **Time Integrator:** RK2SSP
- **Flux Scheme:** Kurganov
- **Gradient:** cellMDLimited leastSquares 1.0
- **Divergence:** Riemann for `div(alphaRhoPhi.c4,lambda.c4)`
- **Interpolation:** cubic, with Minmod for reconstructed fields

## Solution Methods
- **Solvers:**
  - `(rho|rhoU|rhoE|alpha)`: `diagonal`
  - `(U|e)`: `PBiCGStab` with `DIC` preconditioner

## Physical Properties
- **Phases:** c4 (detonating), air (basic)
- **c4 (Reactants):** Murnaghan equation of state
- **c4 (Products):** JWL equation of state
- **Detonation Velocity (vDet):** 7850 m/s
- **Air:** Ideal gas, gamma = 1.4

## Key Features
- **Solver:** `blastFoam` for compressible, multiphase, explosive flows.
- **Adaptive Mesh Refinement (AMR):** Used to capture the blast wave with high fidelity.
- **Detonation Model:** Simulates the detonation of high explosives.
- **Axisymmetric Simulation:** Uses a wedge geometry to reduce computational cost.

## Use Cases
- Simulating explosions and blast wave effects.
- Validating detonation models and compressible flow solvers.
- Studying shock wave propagation and interaction with the environment.
- As a tutorial for `blastFoam` and adaptive mesh refinement.
