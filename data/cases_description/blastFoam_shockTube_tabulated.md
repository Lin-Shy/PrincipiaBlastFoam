---
title: "OpenFOAM Case: Shock Tube with Tabulated EOS"
author: "blastFoam"
description: "This document describes the 'shockTube_tabulated' OpenFOAM case, which demonstrates the use of a tabulated equation of state (EOS) for a classic shock tube problem."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastFoam"
---

## Case Overview

The `shockTube_tabulated` case simulates a standard 1D shock tube problem, a fundamental test for compressible flow solvers. Its unique feature is the use of a **tabulated equation of state (EOS)**. Instead of calculating thermodynamic properties using analytical functions (like the ideal gas law), this case interpolates them from pre-computed tables. This approach is highly efficient and can be used to model materials with very complex thermodynamic behavior that cannot be easily described by simple equations.

## Physics and Solver

- **Solver**: `blastFoam`, a solver for compressible flows.
- **Flow Physics**:
    - **Phase Type**: `basic`, representing a single-phase fluid.
    - **Equation of State**: `tabulatedMG`. This is the key feature. It signifies that the material properties are read from tables.
    - **Thermodynamics**: `eTabulated`. Similar to the EOS, the thermal properties (like temperature) are also interpolated from tables.
- **Tabulated Properties**:
    - The `phaseProperties` dictionary points to CSV files (`p.csv`, `T.csv`) that contain the tabulated data.
    - The tables define properties (like pressure and temperature) as a function of other state variables, typically density (`rho`) and internal energy (`e`).
    - The `rhoCoeffs` and `eCoeffs` entries define the axes of the table, specifying the range and spacing of the independent variables (density and energy). For example, `mod log10` indicates that the density axis in the table is logarithmically scaled.

## Domain and Geometry

- **Geometry**: A simple 1D tube, 100 meters long, created with `blockMesh`.
- **Initial Conditions**: The `setFieldsDict` utility initializes two distinct states, creating the classic shock tube setup:
    - **Driver Section (0m to 50m)**: High-pressure (1.0e6 Pa) and high-density (1 kg/m³) region.
    - **Driven Section (50m to 100m)**: Low-pressure (1.0e5 Pa) and low-density (0.125 kg/m³) region.

## Boundary Conditions

- **`walls`**: The ends of the tube are defined as `patch` type boundaries. In the field files, they are treated as `zeroGradient` or `noSlip`, effectively acting as closed, adiabatic, frictionless walls.
- **`defaultFaces`**: These are `empty` patches, standard for 1D simulations in OpenFOAM.

## Numerical Schemes and Solution

- **Time Integration**: `ddtSchemes` uses the `Euler` method with a high-order `RK4SSP` (4th Order Runge-Kutta) integrator for improved accuracy.
- **Flux Scheme**: `HLLC` (Harten-Lax-van Leer-Contact) is used for its robustness in capturing the shock, rarefaction, and contact discontinuity that form in a shock tube.
- **Interpolation**: `quadraticMUSCL` with a `Minmod` limiter is used for reconstruction. This higher-order scheme provides sharp resolution of the flow features while preventing numerical oscillations.
- **Solvers**: The solution is advanced explicitly, with `diagonal` solvers used for the primary flow variables.

## Post-Processing

- **`sampleDict`**: This dictionary is included to demonstrate post-processing. It sets up a `lineCell` set named `Centerline` to sample and record the values of `p`, `rho`, and `U` along the central axis of the tube at specified time intervals. This is useful for plotting the evolution of the flow profile and comparing it with analytical solutions.

## Purpose and Learning Points

This case is an excellent resource for learning about:
- The use of tabulated equations of state in OpenFOAM.
- How to format and reference data tables for material properties.
- Setting up and solving a classic compressible flow validation case.
- Using higher-order numerical schemes (`RK4SSP`, `quadraticMUSCL`) for accurate shock capturing.
- Basic post-processing with the `sample` utility.
