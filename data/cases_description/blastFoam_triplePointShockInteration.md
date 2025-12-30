---
title: "OpenFOAM Case: Triple Point Shock Interaction"
author: "blastFoam"
description: "This document describes the 'triplePointShockInteration' OpenFOAM case, a classic validation problem for compressible flow solvers involving the complex interaction of multiple shock waves."
case-type: "validation"
openfoam-version: "v2406"
openfoam-solver: "blastFoam"
---

## Case Overview

The `triplePointShockInteration` case simulates a well-known gas dynamics problem where a planar shock wave diffracts over a corner, leading to the formation of a complex wave structure including a Mach stem, a reflected shock, a contact discontinuity, and a triple point. This case is a stringent test for a solver's ability to accurately capture the position and interaction of multiple discontinuities. It also demonstrates the use of Adaptive Mesh Refinement (AMR) to efficiently resolve these sharp features.

## Physics and Solver

- **Solver**: `blastFoam`, a compressible, multi-phase solver.
- **Flow Physics**:
    - **Phases**: The simulation is set up with two phases, `gas` and `air`, both modeled as `basic` ideal gases but with different properties. This allows for tracking the interface (contact discontinuity) between the two regions.
        - `gas`: Has a heat capacity ratio (`gamma`) of 1.5.
        - `air`: Has a heat capacity ratio (`gamma`) of 1.4.
    - **Dynamic Mesh**: `adaptiveFvMesh` is used to dynamically refine the mesh.
        - **Refinement Trigger**: The `densityGradient` error estimator is used, which concentrates grid cells in regions where the density changes sharply, i.e., across the shock waves and contact surface.
        - **Refinement Level**: The mesh can be refined up to 4 levels.

## Domain and Geometry

- **Geometry**: The domain is a 2D axisymmetric wedge created with `blockMesh`. It represents a long channel with a step or corner.
- **Initial Conditions**: The `setFieldsDict` utility is used to initialize a complex initial state, which is crucial for setting up the problem correctly.
    1.  A region of high-pressure `gas` (`alpha.gas = 1`, `p = 1.0`) is placed at the beginning of the channel, acting as the driver for the initial shock wave.
    2.  A second region of low-density `gas` (`rho.gas = 0.125`) is placed above the "step".
    3.  The rest of the domain is filled with `air` at a low initial pressure (`p = 0.1`).
    This setup creates a planar shock that travels down the channel and interacts with the corner and the different gas regions.

## Boundary Conditions

- **`outlet`**: A simple `zeroGradient` condition is used, allowing flow structures to exit the domain.
- **`wedge0` and `wedge1`**: These patches are of type `wedge`, defining the 2D axisymmetric nature of the simulation.
- **Implicit Walls**: The geometry created by `blockMesh` and the initial field setup implicitly define the solid walls and the corner over which the shock diffracts.

## Numerical Schemes and Solution

- **Time Integration**: `ddtSchemes` uses the `Euler` method with a `RK2SSP` (Runge-Kutta 2nd Order, Strong Stability Preserving) integrator.
- **Flux Scheme**: `HLLC` (Harten-Lax-van Leer-Contact) is employed, a standard and robust choice for problems involving strong shocks and contact discontinuities.
- **Interpolation**: `quadraticMUSCL` with a `Minmod` limiter is used for high-order reconstruction of the primitive variables (`rho`, `U`, `p`, `e`). This combination is excellent for capturing sharp features without introducing spurious oscillations.
- **Solvers**: The system is solved explicitly, with `diagonal` solvers for the main transport equations.

## Purpose and Learning Points

This case is a valuable example for understanding:
- The simulation of complex shock-shock and shock-contact interactions.
- A classic validation case for compressible flow solvers.
- The power of Adaptive Mesh Refinement (AMR) to make such simulations computationally feasible by focusing resolution only where it is needed.
- Advanced setup using `setFieldsDict` to create non-trivial initial conditions.
- The use of higher-order numerical schemes (`HLLC`, `quadraticMUSCL`) for high-fidelity results.
