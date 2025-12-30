---
title: "OpenFOAM Case: Deflagration-to-Detonation Transition (DDT)"
author: "blastXiFoam"
description: "This document describes the 'deflagrationToDetonationTransition' case, a complex tutorial for the `blastXiFoam` solver that models the transition from a slow-burning flame (deflagration) to a supersonic detonation wave."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastXiFoam"
---

## Case Overview

The `deflagrationToDetonationTransition` (DDT) case is a highly advanced simulation that models one of the most complex phenomena in combustion: the process by which a slow, subsonic flame (a deflagration) accelerates due to turbulence and confinement, eventually transitioning into a powerful, supersonic detonation wave. This is a critical safety consideration in many industries. The simulation is performed using the `blastXiFoam` solver, which is specifically designed for such problems.

## Physics and Solver

- **Solver**: `blastXiFoam`, a solver based on the Xi (reaction progress variable) combustion model, suitable for both deflagrations and detonations.
- **Combustion Model**:
    - **`Xi` Model**: The core of the solver is the transport equation for `Xi`, a reaction progress variable that tracks the state of the mixture from unburnt (`Xi=0`) to burnt (`Xi=1`). The model is `algebraic`, meaning the reaction progress is determined by local flow conditions rather than a time-dependent source term.
    - **Laminar Flame Speed**: The `RaviPetersen` correlation is used to calculate the laminar flame speed (`Su`) of the `HydrogenInAir` mixture as a function of pressure, temperature, and equivalence ratio. This is a key input for the Xi model.
    - **Ignition**: The combustion is initiated by an `ignitionSite` defined in `combustionProperties`. A spherical region is "ignited" at the start of the simulation.
- **Turbulence Model**:
    - **Model**: `kOmegaSST`, a robust two-equation RANS model that is well-suited for flows with boundary layers and separation, which are critical for flame acceleration in confined spaces.
    - **Interaction**: The turbulence model interacts with the combustion model, as turbulence wrinkles and stretches the flame front, increasing the burning rate and driving the DDT process.
- **Thermophysical Model**:
    - **`heheuPsiThermo`**: A sophisticated thermo model for inhomogeneous mixtures (fuel and oxidant are not pre-mixed).
    - **Mixture**: The model considers an `inhomogeneousMixture` of a `fuel` (Hydrogen) and an `oxidant` (Air), along with their `burntProducts`. Detailed thermodynamic and transport properties for each are provided.

## Domain and Geometry

- **Geometry**: A long, narrow, 2D channel created with `blockMesh`. The confinement provided by the channel walls is essential for the flame to accelerate and for pressure waves to build up, which are key mechanisms for DDT.
- **Boundary Conditions**:
    - **`walls`**: The channel walls are `noSlip` and have appropriate `wallFunction` boundary conditions for the turbulence quantities (`alphat`, `nut`, `epsilon`, `omega`). These walls are critical for generating turbulence and accelerating the flame.
    - **`defaultFaces`**: `empty` type for a 2D simulation.

## Numerical Schemes and Solution

- **Flux Scheme**: `HLLC` is used for its robustness in handling the compressible flow and the strong shocks that form during the transition to detonation.
- **Divergence Schemes**: A variety of schemes are used.
    - `div(rhoPhi, k/omega/epsilon)`: `Gauss upwind` is a stable choice for the turbulence transport equations.
    - `div(phiXi,Xi)`: A `limitedLinear` scheme is used for the reaction progress variable to maintain a sharp but stable interface between burnt and unburnt gas.
- **Interpolation**: `Minmod` limiters are used for reconstructing the main flow variables (`rho`, `U`, `p`, `e`), which is essential for capturing shocks without oscillations.

## Purpose and Learning Points

This case is a capstone tutorial for advanced combustion modeling in OpenFOAM, demonstrating:
- **Deflagration-to-Detonation Transition (DDT)**: The complete modeling of this complex, multi-physics phenomenon.
- **Xi Combustion Model**: A powerful and flexible approach for modeling premixed and non-premixed combustion.
- **Turbulent Combustion Interaction**: How turbulence models are coupled with combustion models to simulate flame acceleration.
- **Advanced Thermophysical Modeling**: Setting up inhomogeneous mixtures with detailed species properties.
- **Complex Solver Setup**: Configuring the numerous sub-models and numerical schemes required for a stable and accurate DDT simulation.
