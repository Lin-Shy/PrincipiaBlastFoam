---
title: "OpenFOAM Case: Two Charge Detonation"
author: "blastFoam"
description: "This document describes the 'twoChargeDetonation' OpenFOAM case, which simulates the interaction of blast waves from the detonation of two different explosive charges, RDX and TNT."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastFoam"
---

## Case Overview

The `twoChargeDetonation` case is a multi-phase, multi-explosive simulation that demonstrates how to model the detonation of two different types of high explosives, RDX and TNT, within the same domain. It showcases the interaction of the resulting blast waves, a phenomenon known as shock wave superposition or Mach reflection, depending on the geometry and timing. The simulation uses Adaptive Mesh Refinement (AMR) to efficiently capture the high-gradient shock fronts.

## Physics and Solver

- **Solver**: `blastFoam`, a compressible, multi-phase solver for high-explosive modeling.
- **Flow Physics**:
    - **Phases**: The simulation involves three phases:
        1.  **`RDX`**: A high explosive, modeled as a `detonating` phase.
        2.  **`tnt`**: A second high explosive, also modeled as a `detonating` phase.
        3.  **`gas`**: The surrounding air, modeled as a `basic` `idealGas`.
    - **Equations of State (EOS)**: Different EOS models are used for the reactants of each explosive, demonstrating the solver's flexibility.
        - RDX Reactants: `Murnaghan` EOS.
        - TNT Reactants: `BirchMurnaghan3` EOS.
        - All Products: `JWL` (Jones-Wilkins-Lee) EOS, which is standard for modeling the expansion of detonation products.
    - **Activation Models**: Different models are used to initiate the detonation in each charge.
        - RDX: `linear` activation, where detonation is initiated at a specific point (`points`) and propagates at a defined velocity (`vDet`).
        - TNT: `pressureBased` activation, where detonation begins once the local pressure exceeds a certain threshold (`pMin`), simulating sympathetic detonation.
    - **Dynamic Mesh**: `adaptiveFvMesh` is used with a `densityGradient` error estimator to refine the mesh around the shock waves.

## Domain and Geometry

- **Geometry**: A 2D axisymmetric wedge is created using `blockMesh`.
- **Initial Conditions**: The `setFieldsDict` utility is used to place the two explosive charges in the domain, which is otherwise filled with air (`alpha.gas = 1`).
    - **RDX Charge**: A `sphereToCell` region is defined to place a spherical charge of RDX (`alpha.RDX = 1`).
    - **TNT Charge**: A `cylinderToCell` region is defined to place a cylindrical charge of TNT (`alpha.tnt = 1`).

## Boundary Conditions

- **`walls`**: A `slip` wall condition is used, allowing the flow to move along the wall without friction.
- **`outlet`**: A `pressureWaveTransmissive` boundary condition is applied to the pressure field (`p`) to allow the blast waves to exit the domain with minimal reflections.
- **`wedge0` and `wedge1`**: Standard `wedge` patches to enforce axisymmetry.

## Numerical Schemes and Solution

- **Time Integration**: `ddtSchemes` uses the `Euler` method with a `RK2SSP` (Runge-Kutta 2nd Order, Strong Stability Preserving) integrator.
- **Flux Scheme**: The `Kurganov` scheme is used for its robustness in handling strong shocks from multiple sources.
- **Divergence Schemes**: For the reaction progress variables (`lambda.tnt`, `lambda.RDX`), a `Riemann` scheme is used, which is suitable for the advection of sharp fronts.
- **Interpolation**: `vanLeer` limiters are used for reconstruction of field variables (`alpha`, `rho`, `U`, `p`, `e`). This provides a good balance between accuracy and stability for shock-capturing.
- **Solvers**: The system is solved explicitly using `diagonal` solvers.

## Purpose and Learning Points

This case is a comprehensive tutorial for users interested in:
- Simulating multiple, different high-explosive charges in a single simulation.
- Modeling complex shock wave interactions and superposition.
- Using different equation of state and activation models for different materials.
- Setting up complex initial geometries with multiple materials using `setFieldsDict`.
- Applying Adaptive Mesh Refinement (AMR) to resolve interacting shock fronts.
- Understanding the multi-phase capabilities of `blastFoam`.
