---
title: "OpenFOAM Case: Mapped Blast - Wedge Source"
author: "blastFoam"
description: "This document provides a detailed description of the 'mappedBuilding3D/wedge' OpenFOAM case, which serves as a 1D axisymmetric source simulation for a larger 3D field mapping workflow. It uses the blastFoam solver to model a detonation in a wedge geometry."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastFoam"
---

## Case Overview

This case, `mappedBuilding3D/wedge`, is a precursor simulation designed to efficiently generate a 1D axisymmetric blast wave profile. It is part of a larger workflow where the results from this simple case are mapped onto a more complex 3D domain (like the `mappedBuilding3D` case) using the `mapFields` utility. This approach significantly reduces computational cost by avoiding the need to simulate the initial high-resolution detonation phase in the full 3D geometry.

The simulation models the detonation of a C4 explosive charge in a 1D wedge geometry, capturing the resulting shock wave propagation. Adaptive Mesh Refinement (AMR) is employed to accurately resolve the steep gradients at the shock front.

## Physics and Solver

- **Solver**: `blastFoam`, a compressible, multi-phase solver designed for high-explosive detonation and blast modeling.
- **Phases**:
    - **`c4`**: The explosive material, modeled as a `detonating` phase.
        - **Reactants Equation of State**: `Murnaghan`.
        - **Products Equation of State**: `JWL` (Jones-Wilkins-Lee).
        - **Activation**: A `pressureBased` model initiates the detonation.
    - **`air`**: The surrounding medium, modeled as an `idealGas`.
- **Mesh Motion**: `adaptiveFvMesh` is used for dynamic mesh refinement. The refinement is triggered by the `densityGradient` error estimator, adding resolution where needed (e.g., at the shock front) and coarsening the mesh behind it to save computational resources.

## Domain and Geometry

- **Geometry**: The computational domain is a 1D axisymmetric wedge with a small angle (1 degree), created using `blockMesh`. This setup is a standard and efficient way to simulate axisymmetric problems in OpenFOAM.
- **Dimensions**: The wedge extends 1.5 meters in the radial direction and 1.5 meters in the axial direction.
- **Initial Conditions**:
    - The domain is initially filled with air at standard atmospheric conditions.
    - The `setFieldsDict` utility is used to place a cylindrical mass of C4 explosive (`alpha.c4 = 1`) at the center of the domain.

## Boundary Conditions

- **`ground`**: Modeled as a `slip` wall, allowing the flow to move parallel to the surface without friction.
- **`outlet`**: A `pressureWaveTransmissive` boundary condition is applied to the pressure field (`p`) to allow the blast wave to exit the domain with minimal reflections. Other fields use `zeroGradient`.
- **`wedge0` and `wedge1`**: These patches are of type `wedge`, defining the axisymmetric nature of the simulation.

## Numerical Schemes and Solution

- **Time Integration**: `ddtSchemes` uses the `Euler` method with a `RK2SSP` (Runge-Kutta 2nd Order, Strong Stability Preserving) integrator.
- **Flux Scheme**: The `Kurganov` scheme is used for robustly handling shocks.
- **Interpolation**: `Minmod` is used as the limiter for reconstruction of field variables (`alpha`, `rho`, `U`, `p`, `e`), ensuring stability in the presence of strong discontinuities.
- **Solvers**: Explicit solvers (`diagonal`) are used for the primary phase-intensive fields, which is typical for transient, compressible blast simulations.

## Workflow Purpose

The primary purpose of this case is to serve as the **source** for a field mapping procedure. The steps are:
1.  Run this `wedge` simulation to generate the initial blast wave data.
2.  Use the `mapFields` utility to map the results from this 1D axisymmetric simulation onto a larger, more complex 3D mesh (e.g., one containing a building).
3.  Run the 3D simulation, which now starts with a well-developed blast wave, saving significant computational time.

This case, along with its `sector` counterpart, demonstrates a powerful and efficient workflow for complex blast simulations.
