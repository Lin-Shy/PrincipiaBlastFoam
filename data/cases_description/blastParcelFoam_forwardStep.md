---
title: "OpenFOAM Case: Forward Step with Lagrangian Particles"
author: "blastParcelFoam"
description: "This document describes the 'forwardStep' case, a tutorial for the `blastParcelFoam` solver, which simulates supersonic gas flow over a step with the injection of solid Lagrangian particles."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastParcelFoam"
---

## Case Overview

The `forwardStep` case is a comprehensive tutorial demonstrating the capabilities of the `blastParcelFoam` solver. It models a classic fluid dynamics problem: supersonic, turbulent flow over a forward-facing step. The key feature is the addition of a Lagrangian phase, where solid particles are injected into the flow and their trajectories and interactions are tracked. This type of simulation is crucial for applications involving particle-laden flows, such as sand ingestion in jet engines, solid-propellant rockets, or industrial spray processes.

## Physics and Solvers

- **Gas-Phase Solver**: `blastParcelFoam`, which is a pressure-based solver for compressible, turbulent flow, coupled with a Lagrangian particle tracking capability.
- **Gas-Phase Physics**:
    - **Flow Regime**: Supersonic. The inlet velocity is 1041 m/s.
    - **Turbulence Model**: The simulation is configured for `laminar` flow in `turbulenceProperties`, but the presence of `k` and `epsilon` files and wall functions suggests it can be run with a RANS model like `kEpsilon`.
    - **Equation of State**: The gas phase is modeled as an `idealGas`.
    - **Dynamic Mesh**: `adaptiveFvMesh` is enabled with a `densityGradient` estimator to refine the mesh in areas of high compressibility, such as around shock waves and in the recirculation zone behind the step.

- **Particle-Phase (Lagrangian) Solver**:
    - **Cloud Type**: `thermoCloud`, indicating the particles have thermal properties.
    - **Injection**: Particles are injected from the `inlet` patch using a `patchInjection` model.
        - A total mass of 10 kg is injected over a duration of 0.025 seconds.
        - The particle size follows a specified `general` distribution.
    - **Particle Forces**: The particles are influenced by `sphereDrag` from the gas phase and `gravity`.
    - **Collision Model**:
        - **Particle-Particle**: `pairSpringSliderDashpot` model is specified in `pairCollisionCoeffs` to handle inter-particle collisions.
        - **Particle-Wall**: `wallLocalSpringSliderDashpot` is used to model collisions with the boundaries.

## Domain and Geometry

- **Geometry**: A 2D channel with a forward-facing step, created using `blockMesh`.
- **Boundary Conditions**:
    - **`inlet`**: A fixed velocity of (1041 0 0) m/s is specified for the gas. This is also the patch from which Lagrangian particles are injected.
    - **`outlet`**: `zeroGradient` conditions are applied.
    - **`obstacle`**: The step and channel walls are treated as `slip` walls for the gas and have specific `wallFunction` boundary conditions for turbulence quantities. For particles, this is a `wall` they can collide with.
    - **`top` and `bottom`**: `symmetryPlane` conditions are used.

## Numerical Schemes and Solution

- **Solution Control**: The simulation is transient, run for a short duration of 0.0025 seconds. The time step is adaptive (`adjustTimeStep yes`) with a maximum Courant number (`maxCo`) of 0.5.
- **Coupling**: The gas phase and particle phase are `coupled`, meaning there is two-way momentum and energy exchange between them.
- **Discretization**: Standard finite volume schemes are used, with `PIMPLE` or `PISO` loops implicitly handling the pressure-velocity coupling for the gas phase.

## Purpose and Learning Points

This case is an advanced tutorial that covers several key topics:
- **Eulerian-Lagrangian Simulations**: Coupling a continuous fluid phase (Eulerian) with a discrete particle phase (Lagrangian).
- **Supersonic Flow**: Simulating flow over a step at supersonic speeds, leading to shock waves and expansion fans.
- **Particle Injection**: Using the `patchInjection` model to introduce particles into the domain with a specific mass flow rate and size distribution.
- **Particle Physics**: Modeling particle forces (drag, gravity) and collisions (particle-particle and particle-wall).
- **Adaptive Mesh Refinement**: Using AMR in a coupled, multi-physics simulation to improve accuracy efficiently.
- **Turbulence Modeling**: Setting up wall functions for RANS turbulence models in compressible flow.
