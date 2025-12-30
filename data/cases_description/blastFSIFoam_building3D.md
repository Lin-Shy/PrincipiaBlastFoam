---
title: "OpenFOAM Case: 3D Building Fluid-Structure Interaction (FSI)"
author: "blastFSIFoam"
description: "This document describes the 'building3D' case for the `blastFSIFoam` solver, a comprehensive tutorial for simulating the two-way coupled Fluid-Structure Interaction (FSI) of a blast wave impacting a flexible 3D building."
case-type: "tutorial"
openfoam-version: "v2406"
openfoam-solver: "blastFSIFoam"
---

## Case Overview

The `building3D` case is a sophisticated example demonstrating the capabilities of the `blastFSIFoam` solver for fully coupled Fluid-Structure Interaction (FSI). It models a C4 detonation near a 3D building, simulating the blast wave propagation in the air and the resulting deformation of the building structure. This is a two-way coupled simulation: the fluid pressure exerts a load on the structure, and the structural deformation, in turn, affects the fluid flow by moving the domain boundaries.

This case is set up using OpenFOAM's multi-region framework. The domain is divided into two distinct regions: `air` (the fluid) and `building` (the solid).

## Physics and Solvers

- **Solver**: `blastFSIFoam`, a multi-region solver designed for FSI problems, combining a compressible flow solver for the fluid region with a solid mechanics solver for the solid region.

### Fluid Region (`air`)

- **Physics**:
    - **Phases**: A two-phase model is used, consisting of `c4` (the explosive) and `air` (the surrounding medium).
    - **Detonation**: The `c4` phase is of type `detonating`, with reactants modeled by a `BirchMurnaghan3` Equation of State (EOS) and products by a `JWL` EOS.
    - **Dynamic Mesh**: `movingAdaptiveFvMesh` is used. This is critical for FSI.
        - **Motion Solver**: `velocityLaplacian` deforms the fluid mesh to conform to the moving solid boundary.
        - **Adaptive Refinement**: `densityGradient` is used to refine the mesh around the propagating shock wave, ensuring accuracy while managing computational cost.
- **Initial Conditions**: The domain is filled with air, and a spherical charge of C4 is initialized using `setFieldsDict`.

### Solid Region (`building`)

- **Solver**: A finite volume-based, linear elastic solid mechanics solver.
- **Physics**:
    - **Solid Model**: `linearTotalDisplacement` is used to calculate the deformation of the structure.
    - **Material Properties**: The building is modeled as a `linearElastic` material with a Young's modulus (`E`) of 1e9 Pa and a Poisson's ratio (`nu`) of 0.3.

## Multi-Region Coupling

- **Interface**: The interaction between the fluid and solid regions occurs at the `air_to_building` (in the `air` region) and `building_to_air` (in the `building` region) boundaries.
- **Data Exchange**:
    - **Fluid to Solid**: The pressure from the `air` region is applied as a traction force on the `building_to_air` boundary. This is handled by the `coupledSolidTraction` boundary condition for the displacement field `D` in the solid region.
    - **Solid to Fluid**: The displacement of the `building` is transferred to the `air` region to move the mesh. The `pointMotionU` field on the `air_to_building` boundary uses a `globalInterpolated` condition to receive the velocity of the deforming solid boundary. The `movingWallVelocity` condition on the fluid velocity `U` ensures the no-slip condition is met on the moving surface.
- **Mapping**: The `regionProperties` file defines the interface connections and specifies that an `AMI` (Arbitrary Mesh Interface) is used to map data between the non-conforming fluid and solid meshes at the interface.

## Domain and Geometry

- **Meshing**: The `blockMeshDict` creates a multi-block mesh that defines both the `air` and `building` cell zones simultaneously.
- **Boundaries**:
    - **`buildingBase`**: The base of the building is fixed (`fixedValue` for displacement `D`).
    - **`ground`**: The ground in the air domain is a `slip` wall.
    - **`outlet`**: A `pressureWaveTransmissive` condition allows the blast wave to exit the fluid domain with minimal reflections.

## Purpose and Learning Points

This case is a premier example for users interested in:
- **Two-Way Coupled FSI**: The core of the simulation is the continuous, two-way exchange of data between the fluid and solid solvers.
- **Multi-Region Simulations**: Setting up and solving problems with distinct fluid and solid regions in OpenFOAM.
- **Blast Loading on Structures**: A practical application of CFD and solid mechanics to predict the response of a structure to an explosion.
- **Dynamic Mesh for FSI**: Using mesh deformation to handle moving and deforming boundaries.
- **Combining AMR with FSI**: Leveraging adaptive mesh refinement in a complex, coupled physics simulation to enhance accuracy.
