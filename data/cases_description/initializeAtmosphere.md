---
title: "OpenFOAM Utility: initializeAtmosphere"
author: "N/A"
description: "This document describes the `initializeAtmosphere` utility, a pre-processing tool used to generate hydrostatically balanced initial conditions for two-phase, compressible flow simulations, typically involving an air-water interface."
case-type: "utility"
openfoam-version: "v2406"
openfoam-solver: "N/A (Utility)"
---

## Utility Overview

The `initializeAtmosphere` case is not a simulation case but rather a demonstration of the `initializeAtmosphere` utility. This tool is a pre-processor designed to set up realistic, hydrostatically balanced initial fields for pressure and temperature in a two-phase system under gravity. This is a crucial step for simulations involving a free surface, such as naval or coastal engineering applications, as it prevents the generation of spurious waves and currents at the start of the simulation.

The utility runs for a single time step (`endTime` is 0) to modify the initial fields (`p` and `T`) in the `0` directory according to a specified atmospheric model.

## Physics and Configuration

The core of this utility is the `system/atmosphereProperties` dictionary, which controls how the initial fields are generated.

- **Phases**: The `constant/phaseProperties` file defines the two phases involved: `air` and `water`. Both are modeled using a `stiffenedGas` equation of state, which is suitable for representing a compressible liquid and a gas.
- **Gravity**: A standard gravity vector is defined in `constant/g`.

### Initialization Models

The `atmosphereProperties` dictionary allows for two main types of initialization:

1.  **`hydrostatic`**:
    - This is the primary mode. It calculates the pressure distribution according to the hydrostatic equation: `dp/dh = -rho * g`.
    - It requires a reference pressure `pRef` at a reference height `hRef`.
    - The utility iteratively solves for a consistent pressure and density field that is in equilibrium with the gravitational force. The `nHydrostaticCorrectors` entry controls the number of iterations.

2.  **`table`**:
    - This mode allows the user to specify the pressure and temperature profiles directly using tables of data (`pTable`, `TTable`).
    - Each table defines field values at corresponding heights (`h`).
    - The utility interpolates from these tables to initialize the fields across the domain.

## Domain and Fields

- **Meshing**: The case includes `blockMeshDict` and a more complex `snappyHexMeshDict`. The utility can operate on any given mesh.
- **Field Initialization**: The `setFieldsDict` is used first to define the initial regions of `air` and `water` by setting the `alpha.air` phase fraction field. For example, a box is defined where `alpha.air` is 1, and the rest of the domain is implicitly `water`.
- **Execution**: Running the `initializeAtmosphere` application reads this setup and overwrites the `p` and `T` fields in the `0` directory with the calculated hydrostatic values.

## Purpose and Workflow

The typical workflow for using this utility is:
1.  Create a mesh for your domain.
2.  Define the fluid phases in `constant/phaseProperties`.
3.  Set the initial location of the different phases using `setFields` on the `alpha` field.
4.  Configure the desired atmospheric model in `system/atmosphereProperties`.
5.  Run the `initializeAtmosphere` application.
6.  The resulting fields in the `0` directory are now hydrostatically balanced and can be used as the starting point for a main simulation using a solver like `blastFoam` or `interFoam`.
