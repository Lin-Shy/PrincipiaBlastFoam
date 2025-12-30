---
title: "OpenFOAM FSI with solids4Foam: Blast on a Flexible Flap"
author: "solids4Foam"
description: "This document describes a Fluid-Structure Interaction (FSI) case simulating a blast wave deforming a flexible flap. The simulation is performed using the `solids4Foam` solver, extended with custom blast physics capabilities."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "solids4Foam"
dependencies: "libblastSolids4Foam.so"
---

## Case Overview

This case demonstrates a monolithic approach to Fluid-Structure Interaction (FSI) using the `solids4Foam` solver. It simulates the interaction between a detonating fluid and a flexible solid structure, specifically a blast wave from a C4 charge impinging on an elastic flap.

The simulation is set up using OpenFOAM's multi-region capabilities, with a `fluid` region and a `solid` region. The `solids4Foam` solver, a powerful tool for solid mechanics and FSI, is extended via the `libblastSolids4Foam.so` library to incorporate the multi-phase compressible blast physics required for this problem. This provides an alternative monolithic FSI workflow to the `blastFSIFoam` solver.

## Physics and Solvers

- **Application**: `solids4Foam`, a multi-region solver for FSI and solid mechanics.
- **Physics Model**: The top-level `physicsProperties` dictionary specifies the `fluidSolidInteraction` model.

### Fluid Region

- **Model**: The `fluidProperties` dictionary specifies the `blast` model, enabling detonation and multi-phase compressible flow physics.
- **Phases**: `phaseProperties` defines a `detonating` `c4` phase (Murnaghan/JWL EOS) and a `basic` `air` phase (ideal gas).
- **Dynamic Mesh**: A `movingAdaptiveFvMesh` is used.
    - **Motion**: `velocityLaplacian` deforms the mesh based on the interface movement.
    - **Refinement**: `densityGradient` is used as the criterion for adaptive mesh refinement to capture the shock front.

### Solid Region

- **Solid Model**: `solidProperties` specifies a `linearGeometryTotalDisplacement` model, suitable for linear elastic materials with small to moderate deformations.
- **Material**: The `mechanicalProperties` define a `linearElastic` material named `rubber` with a density of 7850 kg/m³, Young's modulus of 190 GPa, and Poisson's ratio of 0.3.

## Monolithic FSI Coupling

The coupling is managed within the solver based on the settings in `constant/fsiProperties`.

- **Coupling Strategy**: `weakCoupling` is selected. This is an iterative approach where, within each time step, the solver performs an outer loop (`nOuterCorr`) that sequentially solves fluid and solid physics and exchanges data until the interface solution converges.
- **Interface Transfer**: `interfaceTransferMethod` is set to `AMI` (Arbitrary Mesh Interface), which handles the mapping of data between the potentially non-conforming fluid and solid meshes at their shared `interface` patch.
- **Boundary Conditions**: The coupling is implemented through specialized boundary conditions:
    - **Solid `D` (Displacement)**: The `interface` patch uses the `solidTraction` boundary condition. This condition receives the pressure and stress data from the fluid solver and applies it as a load to the solid.
    - **Fluid `U` (Velocity)**: The `interface` patch uses `movingWallVelocity` to ensure the no-slip condition on the deforming solid surface.
    - **Fluid `pointMotionU`**: The motion of the fluid mesh points at the interface is driven by the velocity of the solid, ensuring the fluid domain conforms to the deforming solid.

## Purpose and Learning Points

This case provides a valuable alternative perspective on monolithic FSI in OpenFOAM.
- **`solids4Foam` for FSI**: It showcases the powerful and flexible `solids4Foam` framework for setting up and solving FSI problems.
- **Extensible Physics**: Demonstrates how a base solver can be extended with custom libraries (`libblastSolids4Foam.so`) to handle highly specialized physics like detonations.
- **Weak Coupling Scheme**: Provides a clear example of configuring a `weakCoupling` FSI approach, including the iterative loop and relaxation factors.
- **AMI for FSI**: Illustrates the use of AMI for robustly mapping data between disparate fluid and solid meshes in an FSI context.
