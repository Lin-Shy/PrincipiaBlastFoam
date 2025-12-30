---
title: "OpenFOAM & preCICE: Partitioned FSI of a Flexible Flap"
author: "blastFoam + preCICE"
description: "This document describes the fluid participant of a partitioned Fluid-Structure Interaction (FSI) simulation. The case simulates a blast wave interacting with a flexible flap, using `blastFoam` for the fluid dynamics and the preCICE library to couple with an external solid mechanics solver."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastFoam"
dependencies: "preCICE, a solid mechanics solver (e.g., CalculiX)"
---

## Case Overview

This case demonstrates a partitioned approach to Fluid-Structure Interaction (FSI), simulating the response of a flexible flap to a blast wave. Unlike the monolithic, multi-region `blastFSIFoam` solver, this setup uses two separate solvers—one for the fluid and one for the solid—that run concurrently and exchange data via the **preCICE** coupling library.

This file bundle describes only the **fluid participant**, which is an OpenFOAM case run with the `blastFoam` solver. An accompanying case for a solid mechanics solver (e.g., CalculiX, not included in this bundle) would constitute the other participant in this coupled simulation.

The physical problem is similar to other `flap` tutorials: a C4 charge detonates, and the resulting shock wave impinges on and deforms a flexible structure. The key feature here is the methodology of the coupling itself.

## Physics and Solvers

### Fluid Participant (`blastFoam`)

- **Solver**: `blastFoam`, a multi-phase, compressible solver.
- **Physics**:
    - **Phases**: A two-phase model of `c4` and `air`. The `c4` phase is configured as a `detonating` explosive using the `Murnaghan` EOS for reactants and `JWL` EOS for products.
    - **Dynamic Mesh**: The fluid mesh deforms to accommodate the moving solid. The `dynamicMeshDict` configures a `dynamicMotionSolverFvMesh` with a `displacementLaplacian` solver. This solver smoothly propagates the displacement from the FSI interface (`flap` patch) throughout the fluid mesh.

### Solid Participant (External)

- This case requires a separate simulation for the solid mechanics of the flap. This would typically be set up in a dedicated structural solver like CalculiX or even another OpenFOAM case using a solids solver. This participant is not described in the current file bundle.

## Partitioned Coupling with preCICE

The magic of this partitioned simulation lies in the configuration of the preCICE adapter.

- **`controlDict`**: A `preciceAdapterFunctionObject` is loaded at runtime. This function object is the bridge between OpenFOAM and the preCICE library.

- **`system/preciceDict`**: This dictionary configures the OpenFOAM side of the coupling.
    - **`participant Fluid`**: Identifies this OpenFOAM simulation as the "Fluid" participant to preCICE.
    - **`mesh Fluid-Mesh`**: Provides the name of the mesh that will be exposed to preCICE.
    - **`patches (flap)`**: Specifies that the `flap` boundary is the FSI interface.
    - **`readData (Displacement)`**: At each coupling step, the adapter will read `Displacement` data from preCICE. This data, computed by the solid solver, is used to move the `flap` patch and deform the fluid mesh.
    - **`writeData (Force)`**: After solving the fluid dynamics, the adapter computes the pressure and viscous forces on the `flap` patch and sends this `Force` data to preCICE for the solid solver to use as a boundary condition.

- **`precice-config.xml` (External File)**: This crucial file (not included here) defines the master plan for the coupling. It specifies:
    - The participants involved (e.g., `Fluid` and `Solid`).
    - The data to be exchanged (`Force`, `Displacement`).
    - The coupling scheme (e.g., serial-implicit, parallel-explicit).
    - The time step management and communication channels.

## Purpose and Learning Points

This case is an excellent example for users interested in multi-physics simulations with best-of-breed solvers.
- **Partitioned FSI**: It provides a clear template for setting up a partitioned (co-simulation) FSI problem, which offers flexibility in choosing the most suitable solver for each physics domain.
- **preCICE Integration**: It demonstrates the non-intrusive integration of preCICE into an OpenFOAM case using a function object, requiring no changes to the solver itself.
- **Data Exchange**: Shows the explicit definition of data (`Force`, `Displacement`) being read and written at the coupling interface.
- **Modular Simulation**: Highlights a modular and powerful approach to solving complex multi-physics problems that may be difficult to tackle with a single, monolithic solver.
