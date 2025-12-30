---
title: "OpenFOAM Case: Flexible Flap Fluid-Structure Interaction (FSI)"
author: "blastFSIFoam"
description: "This document describes the 'flap' case, a validation and tutorial case for the `blastFSIFoam` solver. It simulates a blast wave from a C4 detonation interacting with a flexible, elasto-plastic flap, demonstrating two-way coupled FSI with a non-linear material model."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastFSIFoam"
---

## Case Overview

The `flap` case is a canonical Fluid-Structure Interaction (FSI) problem that demonstrates the `blastFSIFoam` solver's ability to handle strong, two-way coupling between a compressible, detonating fluid and a deforming solid with a non-linear material response.

The simulation involves a C4 charge detonating near a thin, cantilevered flap. The resulting blast wave impinges on the flap, causing it to deform significantly. The key aspects of this case are the two-way coupling—the fluid pressure deforms the flap, and the flap's movement, in turn, alters the fluid domain and flow—and the advanced material model used for the flap, which accounts for plastic deformation.

The problem is set up using OpenFOAM's multi-region framework, with an `air` region for the fluid and a `flap` region for the solid.

## Physics and Solvers

- **Solver**: `blastFSIFoam`, a multi-region solver for coupled FSI simulations.

### Fluid Region (`air`)

- **Physics**:
    - **Phases**: A two-phase model consisting of `c4` (the explosive) and `air`.
    - **Detonation**: The `c4` phase is of type `detonating`, with reactants modeled by a `Murnaghan` Equation of State (EOS) and products by a `JWL` EOS. Detonation is initiated via a `pressureBased` activation model.
    - **Dynamic Mesh**: `movingAdaptiveFvMesh` is employed.
        - **Motion Solver**: `velocityLaplacian` with `inverseDistance` diffusivity deforms the fluid mesh to follow the moving flap.
        - **Adaptive Refinement (AMR)**: The mesh is refined based on `densityGradient` to accurately capture the propagating shock front.

### Solid Region (`flap`)

- **Solver**: A finite volume solid mechanics solver capable of handling large deformations and non-linear materials.
- **Physics**:
    - **Solid Model**: `linearTotalDisplacement` is used to compute the structural response.
    - **Material Model**: `linearJohnsonCookPlastic`. This is a sophisticated model for the 'steel' material that captures elasto-plastic behavior. It accounts for strain hardening, strain rate hardening, and thermal softening, making it suitable for high-energy impact and blast scenarios. This is a significant step up in complexity from a simple linear elastic model.

## Multi-Region Coupling

- **Interface**: The `air_to_flap` and `flap_to_air` boundaries form the FSI interface.
- **Data Exchange**: The coupling mechanism is identical to that in the `building3D` case:
    - **Fluid to Solid**: The fluid pressure is passed as a traction load to the solid via the `coupledSolidTraction` boundary condition on the displacement field `D`.
    - **Solid to Fluid**: The structural velocity is passed to the fluid mesh motion solver via the `globalInterpolated` boundary condition on `pointMotionU`. The `movingWallVelocity` condition on the fluid `U` field ensures the no-slip condition on the deforming flap surface.
- **Mapping**: `regionProperties` defines the interface link, using an `AMI` (Arbitrary Mesh Interface) to map data between the potentially non-conforming meshes.

## Domain and Geometry

- **Meshing**: Separate `blockMeshDict` files are used for the `air` and `flap` regions, which are then combined by the solver at runtime. The `flap` is a simple, thin block, cantilevered at its base.
- **Boundaries**:
    - **`flapBase`**: The base of the flap is fixed (`fixedValue` displacement).
    - **`ground`**: The ground in the `air` domain is a `slip` wall.
    - **`outlet`**: A `pressureWaveTransmissive` condition allows the blast wave to exit the domain cleanly.

## Purpose and Learning Points

This case is a crucial tutorial for users looking to perform advanced FSI simulations:
- **Non-Linear Solid Mechanics**: Demonstrates the use of an advanced, non-linear material model (`JohnsonCook`) for the solid, which is essential for accurately predicting permanent deformation in structures under blast loading.
- **Two-Way Coupled FSI**: Provides a clear example of the robust two-way coupling between a compressible fluid and a deforming solid.
- **Multi-Region Meshing**: Shows a common workflow where fluid and solid regions are meshed independently.
- **Blast-Structure Interaction**: A practical and challenging validation case for FSI solvers.
