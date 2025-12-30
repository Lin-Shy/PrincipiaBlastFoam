---
title: "OpenFOAM Case: Oblique Shock"
author: "blastReactingFoam"
description: "This document describes the 'obliqueShock' case, a classic validation problem for supersonic, compressible flow solvers, using the `blastReactingFoam` solver."
case-type: "validation"
openfoam-version: "v2406"
openfoam-solver: "blastReactingFoam"
---

## Case Overview

The `obliqueShock` case is a fundamental validation test for compressible flow solvers. It simulates a supersonic flow (Mach 2.9) that encounters a wedge, generating a stationary oblique shock wave. The angle and properties of the flow behind the shock can be predicted by analytical gas dynamics theory (the theta-beta-Mach relation), making this an excellent case for verifying the accuracy of a solver's shock-capturing capabilities.

Although the solver used is `blastReactingFoam`, this particular case is set up as a non-reacting, single-phase flow problem to focus purely on the gas dynamics.

## Physics and Solver

- **Solver**: `blastReactingFoam`. In this case, its reacting capabilities are not used, and it functions as a standard compressible flow solver.
- **Flow Physics**:
    - **Thermo Model**: `heRhoThermo`, a standard thermophysical model for compressible flows where density is calculated from the transport equation and temperature is derived from energy.
    - **Equation of State**: `perfectGas`.
    - **Mixture**: A `pureMixture` is used, representing a single-component gas. The properties are normalized for simplicity.
    - **Turbulence**: The simulation is `laminar`.

## Domain and Geometry

- **Geometry**: The domain is a simple 2D rectangular channel created with `blockMesh`. The oblique shock is generated not by a physical wedge in the mesh, but by cleverly setting the boundary conditions.
- **Boundary Conditions**:
    - **`inlet`**: A supersonic flow with a Mach number of 2.9 is specified with a `fixedValue` condition for velocity `U`, pressure `p`, and temperature `T`.
    - **`top`**: This boundary acts as the "wedge". Instead of a geometric deflection, a `fixedValue` boundary condition is applied, imposing the known analytical post-shock flow conditions (velocity and temperature). The flow entering at the `inlet` must therefore pass through a shock to meet these conditions, causing the oblique shock to form and stabilize in the domain.
    - **`bottom`**: A `symmetryPlane` condition is used, effectively making the `top` boundary a 10-degree wedge (based on the analytical solution for the given inlet/top conditions).
    - **`outlet`**: `zeroGradient` conditions allow the flow to exit the domain.
    - **`frontAndBack`**: `empty` type for a 2D simulation.

## Numerical Schemes and Solution

- **Time Integration**: `ddtSchemes` uses the `Euler` method with a `RK2SSP` (Runge-Kutta 2nd Order, Strong Stability Preserving) integrator.
- **Flux Scheme**: The `Kurganov` scheme is used, which is a robust and accurate choice for capturing shock waves.
- **Interpolation**: `vanLeer` limiters are used for the reconstruction of primitive variables (`rho`, `U`, `e`, `p`). This ensures sharp shock profiles without numerical oscillations.
- **Solvers**: The system is solved explicitly. The main transport equations (`rho`, `rhoU`, `rhoE`) use a `diagonal` solver, while the energy and velocity fields are smoothed.

## Purpose and Learning Points

This case is a classic CFD validation problem and serves to:
- Verify the accuracy of a compressible solver's shock-capturing ability.
- Demonstrate an alternative way to set up wedge flow problems using boundary conditions instead of a complex mesh.
- Provide a clear example of applying analytical solutions as boundary conditions for validation.
- Showcase the use of robust numerical schemes (`Kurganov`, `vanLeer`) for supersonic flows.
