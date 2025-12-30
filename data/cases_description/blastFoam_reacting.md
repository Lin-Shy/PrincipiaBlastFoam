---
title: "OpenFOAM Case: Reacting Flow"
author: "blastFoam"
description: "This document details the 'reacting' OpenFOAM case, a tutorial for simulating compressible, reacting flows involving chemical reactions, specifically the combustion of methane."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastFoam"
---

## Case Overview

The `reacting` case is designed to demonstrate the capabilities of `blastFoam` for simulating compressible flows with chemical reactions. It models a simple 1D shock tube problem where a region of high-pressure methane (`CH4`) is separated from a region of air (oxygen `O2` and nitrogen `N2`). When the simulation starts, the "membrane" breaks, a shock wave forms, and the resulting high temperatures initiate a chemical reaction (combustion) between the methane and oxygen.

## Physics and Solver

- **Solver**: `blastFoam`, configured to handle reacting flows.
- **Flow Physics**:
    - **Phase Type**: `reacting`. This enables the solver to account for changes in species concentrations due to chemical reactions.
    - **Equation of State**: `VanderWaals`, a real gas model that is more accurate than the ideal gas law at high pressures.
    - **Thermodynamics**: `janaf` model is used for calculating thermodynamic properties (like specific heat) from polynomial functions of temperature.
    - **Transport**: `sutherland` model is used for viscosity.
    - **Turbulence**: The simulation is `laminar`.
- **Chemistry**:
    - **Chemistry Model**: An `ode` (Ordinary Differential Equation) solver is used to solve the species transport and reaction equations.
    - **Reaction**: A single-step, irreversible Arrhenius reaction is defined in `constant/reactions`:
      `CH4 + 2O2 = CO2 + 2H2O`
      This represents the combustion of methane with oxygen to produce carbon dioxide and water.

## Domain and Geometry

- **Geometry**: A simple 1D tube created with `blockMesh`. The domain is 100 meters long.
- **Initial Conditions**: The `setFieldsDict` utility is used to create two distinct regions:
    - **Driver Section (50m to 100m)**: A high-pressure (1e6 Pa), high-temperature (500 K) region filled with pure methane (`CH4`).
    - **Driven Section (0m to 50m)**: A lower-pressure (1e5 Pa), ambient temperature (300 K) region filled with air (modeled as 23% `O2` and 77% `N2` by mass).

## Boundary Conditions

- **`walls`**: The ends of the 1D tube are defined as `patch` type boundaries. In the field files (`p`, `T`, `U`, etc.), they are treated as `zeroGradient` or `noSlip`, effectively acting as closed, adiabatic, frictionless walls.
- **`defaultFaces`**: These are `empty` patches, standard for 2D or 1D simulations in OpenFOAM to signify that the mesh has no extent in that direction.

## Numerical Schemes and Solution

- **Time Integration**: `ddtSchemes` uses the `Euler` method with a `RK2SSP` (Runge-Kutta 2nd Order, Strong Stability Preserving) integrator.
- **Flux Scheme**: `HLLC` (Harten-Lax-van Leer-Contact) is employed for its robustness in handling compressible flows with shocks and contact discontinuities.
- **Divergence Scheme**: For the species transport equation (`div(rhoPhi,Yi)`), a `Riemann` scheme is used, which is appropriate for hyperbolic conservation laws.
- **Interpolation**: `quadraticMUSCL` with a `Minmod` limiter is used for reconstruction. This is a higher-order scheme that provides sharp resolution of shocks and reaction fronts while maintaining stability.
- **Solvers**: Explicit solvers (`diagonal`) are used for the main flow equations, while a preconditioned biconjugate gradient stabilized method (`PBiCGStab`) is used for the implicit solution of species and energy equations.

## Purpose and Learning Points

This case is a fundamental example for users interested in:
- Setting up and running compressible, reacting flow simulations.
- Defining chemical species and reactions.
- Using real gas equations of state (`VanderWaals`).
- Understanding how to initialize different regions of a domain with different compositions and thermodynamic states using `setFieldsDict`.
- Applying appropriate numerical schemes for combustion and shock-driven problems.
