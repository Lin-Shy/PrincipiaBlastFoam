--- OpenFOAM Tutorial Case Description: Cavity Flow ---

## Case Overview
**Case Name:** cavity  
**Solver:** icoFoam  
**OpenFOAM Version:** v2406  

## Physics Description
Laminar, incompressible, isothermal flow in a 2D square cavity. This is a classic benchmark case demonstrating lid-driven cavity flow, where the top wall moves tangentially while other walls remain stationary.

## Geometry
- **Type:** 2D rectangular domain
- **Dimensions:** 0.1m × 0.1m × 0.01m (width × height × depth)
- **Origin:** (0, 0, 0)
- **Description:** Square cavity with one moving wall at the top

## Mesh Configuration
- **Type:** Uniform structured mesh
- **Cells:** 20 × 20 × 1 (typical configuration)
- **Mesh Generator:** blockMesh
- **Mesh Quality:** Orthogonal, uniform cell distribution

## Boundary Conditions

### Velocity (U)
- **movingWall (top wall):**
  - Type: fixedValue
  - Value: uniform (1 0 0) m/s
  - Description: Top wall moving in positive x-direction

- **fixedWalls (bottom, left, right):**
  - Type: noSlip
  - Value: uniform (0 0 0) m/s
  - Description: Stationary walls with no-slip condition

- **frontAndBack:**
  - Type: empty
  - Description: 2D simulation, empty boundary for front and back faces

### Pressure (p)
- **movingWall:**
  - Type: zeroGradient
  - Description: No pressure gradient at moving wall

- **fixedWalls:**
  - Type: zeroGradient
  - Description: No pressure gradient at fixed walls

- **frontAndBack:**
  - Type: empty
  - Description: 2D simulation

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 0 Pa (gauge pressure)

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.5 s
- **Delta T:** 0.005 s
- **Write Control:** timeStep
- **Write Interval:** 20 (writes every 0.1 s)

## Numerical Schemes
- **Time derivative:** Euler (first-order implicit)
- **Gradient:** Gauss linear
- **Divergence:** Gauss linear
- **Laplacian:** Gauss linear orthogonal

## Solution Methods
- **Solver:** PISO algorithm (icoFoam)
- **Pressure:** PCG with DIC preconditioner
- **Velocity:** PBiCGStab with DILU preconditioner

## Physical Properties
- **Kinematic Viscosity (nu):** 0.01 m²/s
- **Density:** 1 kg/m³ (incompressible, constant)
- **Transport Model:** Newtonian

## Expected Results
- Formation of primary vortex in cavity center
- Secondary vortices in corners (for higher Reynolds numbers)
- Steady-state solution reached around t = 0.5 s
- Reynolds Number: Re = UL/ν = 1 × 0.1 / 0.01 = 10

## Key Features
- Classic CFD benchmark case
- Simple geometry but complex flow physics
- Good test case for solver validation
- Demonstrates recirculating flow patterns

## Use Cases
- Learning OpenFOAM basics
- Testing new solvers or schemes
- Mesh independence studies
- Validation of numerical methods

## Common Modifications
1. Varying moving wall velocity (changing Reynolds number)
2. Different mesh resolutions (10×10, 40×40, 80×80)
3. Time-varying wall velocity (sinusoidal, ramp)
4. Different aspect ratios
5. Multiple moving walls

--- End of Context ---
