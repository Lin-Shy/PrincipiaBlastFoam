# Strict Retrieval Dataset Audit Summary

- Tutorials root: `/media/dev/vdb1/linshihao/cases/blastFoam-cases-dataset/blastFoam_tutorials`
- Tutorial case count: `34`
- Strict dataset size: `130`

## Legacy Dataset Audit

- Unique case-resolvable entries: `6`
- Ambiguous entries: `108`
- Missing entries: `6`

## Strict Dataset Audit

- Pass: `122`
- Warn: `8`
- Fail: `0`

## Strict Dataset Case Coverage

- `blastEulerFoam/reactingParticles`: `28` entries
- `blastFoam/freeField`: `23` entries
- `blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass`: `21` entries
- `blastFoam/mappedBuilding3D`: `8` entries
- `blastFoam/movingCone`: `17` entries
- `blastFoam/triplePointShockInteration`: `13` entries
- `blastXiFoam/deflagrationToDetonationTransition`: `20` entries

## Legacy Dataset Examples

- Ambiguous `1`: `Change the turbulence model from Spalart-Allmaras to kOmegaSST` -> 4 candidate cases
- Ambiguous `2`: `Increase the simulation end time to 0.005 seconds` -> 29 candidate cases
- Ambiguous `3`: `Adjust the mesh resolution to have 100 cells in x-direction, 50 in y, and 25 in z` -> 27 candidate cases
- Ambiguous `4`: `Set the maximum Courant number to 0.3` -> 29 candidate cases
- Ambiguous `5`: `Change the explosive density to 1700 kg/m³` -> 21 candidate cases
- Missing `41`: `Switch explosive modeling to use JWL EOS and Arrhenius reaction kinetics` -> target files ['constant/phaseProperties', 'constant/combustionProperties']
- Missing `81`: `Set inlet velocity to 100 m/s with 5% turbulence intensity` -> target files ['0/U', '0/k', '0/omega']
- Missing `114`: `Configure radiative heat transfer with P1 model` -> target files ['constant/radiationProperties']
- Missing `116`: `Add MRF (Multiple Reference Frame) zone rotating at 1000 RPM` -> target files ['constant/MRFProperties']
- Missing `119`: `Use limiters on temperature between 250K and 5000K` -> target files ['system/fvOptions']
