--- OpenFOAM Tutorial Case Description: Internal Detonation with Obstacles and Glass ---

## Case Overview
**Case Name:** internalDetonation_withObstacleAndGlass
**Solver:** blastFoam
**OpenFOAM Version:** Not specified

## Physics Description
This is an advanced version of the `internalDetonation` case. It simulates an explosion within a 2D confined space that contains internal obstacles (baffles) and windows that can burst under a combination of pressure and impulse loading. The blast wave interacts with these complex internal features. The simulation also includes an afterburn model.

## Geometry
- **Type:** 2D confined space with internal features.
- **Domain:** A rectangular domain (5m x 2m x 2m) created by `blockMesh`.
- **Obstacles:** Three solid baffles are created inside the domain using `topoSet` and `createBaffles`.
- **Windows:** Three windows are defined on the baffles. These are modeled using the `burstCyclicAMI` boundary condition.
- **Outlet:** An outlet is created on one of the far walls using `createPatch`.

## Mesh Configuration
- **Type:** Structured mesh with significant modification post-generation.
- **Mesh Workflow:**
  1. `blockMesh`: Creates the initial simple block.
  2. `topoSet`: Defines `cellSet` and `faceZone` for the obstacles and windows based on box selections.
  3. `createBaffles`: Creates the internal baffle walls and the `burstCyclicAMI` patches for the windows from the previously defined zones.
  4. `createPatch`: Modifies a portion of the `walls` boundary to become an `outlet`.
- **Adaptive Refinement:** Enabled via `dynamicMeshDict`, based on density gradient, with a maximum refinement level of 2.

## Boundary Conditions
- **windows_master/slave:**
  - **Type:** `burstCyclicAMI`.
  - **Intact Behavior:** `slip` wall.
  - **Burst Model:** `field`-based. The windows burst when a combination of pressure (`p > 4e7` Pa) and impulse (`impulse > 10000` Pa-s) is reached.
- **baffles_master/slave:** `slip` wall (implicitly, as they are internal walls).
- **walls:** `slip` wall.
- **outlet:** `zeroGradient`.

## Initial Conditions
- **U (velocity):** uniform (0 0 0) m/s
- **p (pressure):** uniform 101298 Pa
- **T (temperature):** uniform 300 K
- **alpha.c4 (c4 volume fraction):** Initialized to 1 in a spherical region at the origin with a radius of 0.1m.

## Time Control
- **Start Time:** 0 s
- **End Time:** 0.005 s
- **Delta T:** 1e-8 s (adaptive time stepping is on)
- **Write Interval:** 5e-5 s

## Numerical Schemes
- **Time derivative:** Euler with `RK2SSP` integrator.
- **Flux Scheme:** Kurganov
- **Interpolation:** `Minmod` limiter for reconstructed fields.

## Physical Properties
- **Phases:** `c4` (detonating) and `air` (basic).
- **c4:**
  - Reactants EOS: `Murnaghan`.
  - Products EOS: `JWL`.
- **Afterburn Model:** `Miller` model is active.
- **Air:** `idealGas` equation of state.

## Key Features
- **Solver:** `blastFoam`.
- **Complex Internal Geometry:** Demonstrates a complex workflow using `topoSet`, `createBaffles`, and `createPatch` to generate a sophisticated internal geometry from a simple block mesh.
- **Pressure-Impulse Window Failure:** Uses a `field`-based `burstModel` that allows window failure based on a combination of both pressure and impulse, which is more realistic than a simple pressure threshold.
- **Blast-Obstacle Interaction:** Simulates the complex shock reflections, diffractions, and channeling caused by internal structures.

## Use Cases
- Advanced simulation of urban or industrial explosion scenarios with complex internal layouts.
- Modeling component failure (e.g., walls, windows) based on combined load criteria.
- A comprehensive tutorial for advanced meshing and boundary condition setup in OpenFOAM for blast applications.
