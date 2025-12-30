---
title: "OpenFOAM Case: Reacting Shock Tube"
author: "blastReactingFoam"
description: "This document describes the 'reacting' case for the `blastReactingFoam` solver, a tutorial for simulating shock-induced combustion in a 1D tube."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastReactingFoam"
---

## Case Overview

This `reacting` case is a fundamental tutorial for simulating compressible, multi-species, reacting flows. It models a classic 1D shock tube problem where the initial high temperature and pressure from a shock wave are used to initiate a chemical reaction—in this instance, the combustion of methane.

The domain is initialized with two regions: a high-pressure "driver" section containing pure methane (`CH4`), and a low-pressure "driven" section containing air (a mixture of oxygen `O2` and nitrogen `N2`). At time t=0, the conceptual diaphragm separating these regions ruptures, generating a shock wave that propagates into the air, heating it and causing the methane to combust when they mix.

## Physics and Solver

- **Solver**: `blastReactingFoam`, a solver designed for compressible, multi-component, reacting flows.
- **Flow Physics**:
    - **Thermo Model**: `hePsiThermo`, a standard thermophysical model for reacting flows based on compressibility (`psi`).
    - **Mixture**: `multiComponentMixture` is used to handle the multiple chemical species involved (CH4, O2, N2, CO2, H2O).
    - **Thermodynamics**: The `janaf` model is used to calculate temperature-dependent thermodynamic properties like specific heat (`Cp`) from NASA polynomial coefficients.
    - **Transport**: The `sutherland` model calculates temperature-dependent viscosity.
    - **Combustion**: The `combustionModel` is set to `laminar`.
- **Chemistry**:
    - **Chemistry Model**: An `ode` (Ordinary Differential Equation) solver is enabled to solve the system of species reaction equations.
    - **Reaction**: A single-step, irreversible Arrhenius reaction is defined in `constant/reactions`:
      `CH4 + 2O2 = CO2 + 2H2O`
      The rate of this reaction is governed by the Arrhenius parameters `A` (pre-exponential factor) and `Ta` (activation temperature).

## Domain and Geometry

- **Geometry**: A simple 1D tube, 100 meters long, created with `blockMesh`.
- **Initial Conditions**: The `setFieldsDict` utility is used to create the two distinct regions:
    - **Driver Section (50m to 100m)**: High-pressure (1e6 Pa), high-temperature (500 K) region filled with pure methane (`CH4`).
    - **Driven Section (0m to 50m)**: Lower-pressure (1e5 Pa), ambient temperature (300 K) region filled with air (modeled as 23% `O2` and 77% `N2` by mass fraction).

## Boundary Conditions

- **`walls`**: The ends of the 1D tube are defined as `patch` type boundaries. They are treated as `zeroGradient` or `noSlip`, effectively acting as closed, adiabatic, frictionless walls.
- **`defaultFaces`**: These are `empty` patches, required for 2D or 1D simulations in OpenFOAM.

## Numerical Schemes and Solution

- **Time Integration**: `ddtSchemes` uses the `Euler` method with a `RK2SSP` (Runge-Kutta 2nd Order, Strong Stability Preserving) integrator.
- **Flux Scheme**: `HLLC` (Harten-Lax-van Leer-Contact) is employed for its robustness in handling compressible flows with both shocks and contact discontinuities.
- **Divergence Scheme**: For the species transport equation (`div(rhoPhi,Yi)`), a `Riemann` scheme is used, which is appropriate for the advection of sharp concentration fronts.
- **Interpolation**: `quadraticMUSCL` with a `Minmod` limiter provides high-order, non-oscillatory reconstruction of flow variables, which is crucial for accurately capturing both the shock and the flame front.
- **Solvers**: The system is solved with a mix of explicit (`diagonal`) and implicit (`PBiCGStab`) solvers.

## Purpose and Learning Points

This case is a cornerstone for learning about combustion modeling in OpenFOAM:
- Setting up a multi-component mixture with detailed species data.
- Defining chemical reactions and using an ODE solver for chemistry.
- Initializing a domain with different chemical compositions using `setFieldsDict`.
- Simulating shock-induced combustion.
- Using appropriate high-resolution numerical schemes for reacting flows.
