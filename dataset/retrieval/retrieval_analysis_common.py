#!/usr/bin/env python3
"""
Shared helpers for retrieval dataset analysis scripts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

try:
    from benchmark_registry import get_benchmark_config
    from strict_retrieval_evaluator import StrictRetrievalEvaluator
except ModuleNotFoundError:
    from dataset.retrieval.benchmark_registry import get_benchmark_config
    from dataset.retrieval.strict_retrieval_evaluator import StrictRetrievalEvaluator


RETRIEVAL_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = Path(get_benchmark_config("case_content")["default_dataset"])

STRICT_CASE_HINTS: Dict[str, Sequence[str]] = {
    "blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass": (
        "window",
        "glass",
        "obstacle",
        "internal detonation",
        "pburst",
        "damage",
        "fracture",
        "orthotropic",
        "elasticplastic",
        "fragile",
    ),
    "blastEulerFoam/reactingParticles": (
        "particle",
        "particles",
        "granular",
        "gidaspow",
        "schillernaumann",
        "packing",
        "restitution",
        "gas phase",
        "solid particles",
        "drag model",
    ),
    "blastXiFoam/deflagrationToDetonationTransition": (
        "deflagration",
        "detonation transition",
        "ddt",
        "arrhenius",
        "equivalence ratio",
        "flame speed",
        "su",
        "thermophysical",
    ),
    "blastFoam/movingCone": (
        "moving cone",
        "cone",
        "500 m/s",
        "velocity field",
    ),
    "blastFoam/mappedBuilding3D": (
        "building",
        "mapped building",
        "building3d",
    ),
    "blastFoam/triplePointShockInteration": (
        "triple point",
        "shock interaction",
    ),
    "blastFoam/freeField": (
        "free field",
        "blast wave",
        "overpressure",
        "ambient",
        "probe",
    ),
}

FILE_HINTS: Sequence[tuple[str, Sequence[str]]] = (
    (
        "constant/turbulenceProperties.gas",
        (
            "gas phase turbulence",
            "gas phase",
            "gas turbulence",
        ),
    ),
    (
        "constant/turbulenceProperties.particles",
        (
            "particle phase",
            "granular viscosity",
            "particle turbulence",
            "thermal conductivity model",
        ),
    ),
    (
        "constant/thermophysicalProperties",
        (
            "thermophysical",
            "thermo",
            "janaf",
            "perfectthermo",
            "econst",
        ),
    ),
    (
        "constant/turbulenceProperties",
        (
            "turbulence",
            "ras",
            "laminar",
            "komega",
            "kepsilon",
            "spalart",
            "sst",
        ),
    ),
    (
        "system/controlDict",
        (
            "endtime",
            "maxco",
            "deltat",
            "time step",
            "duration",
            "courant",
            "write interval",
            "output",
            "longer",
            "stable",
            "simulation time",
        ),
    ),
    (
        "system/blockMeshDict",
        (
            "mesh",
            "cells",
            "blockmesh",
            "resolution",
            "x-direction",
            "y-direction",
            "z-direction",
        ),
    ),
    (
        "constant/dynamicMeshDict",
        (
            "refinement",
            "amr",
            "adaptive",
            "maxrefinement",
            "dynamic mesh",
        ),
    ),
    (
        "constant/phaseProperties",
        (
            "density",
            "eos",
            "equation of state",
            "material",
            "phase",
            "explosive",
            "rho0",
            "jwl",
            "bkw",
            "window",
            "particle",
            "packing",
            "restitution",
            "orthotropic",
            "damage",
        ),
    ),
    (
        "constant/combustionProperties",
        (
            "combustion",
            "flame",
            "reaction",
            "arrhenius",
            "equivalence",
            "su",
            "detonation",
            "deflagration",
        ),
    ),
    (
        "system/setFieldsDict",
        (
            "initial",
            "charge",
            "location",
            "setfield",
            "setfields",
            "sphere",
            "box",
        ),
    ),
    (
        "system/fvSchemes",
        (
            "scheme",
            "discretization",
            "muscl",
            "limiter",
            "vanleer",
            "vanalbada",
            "numerical",
            "flux",
        ),
    ),
    (
        "system/fvSolution",
        (
            "pimple",
            "solver",
            "tolerance",
            "relaxation",
            "fvsolution",
        ),
    ),
    (
        "system/fvOptions",
        (
            "temperature limiter",
            "limiters on temperature",
            "fvoptions",
        ),
    ),
    (
        "0/U",
        (
            "velocity",
            "moving cone",
            "m/s",
            "inlet velocity",
        ),
    ),
)

FILE_PRIOR_CASES: Dict[str, Sequence[str]] = {
    "constant/turbulenceProperties.gas": ("blastEulerFoam/reactingParticles",),
    "constant/turbulenceProperties.particles": ("blastEulerFoam/reactingParticles",),
    "constant/thermophysicalProperties": ("blastXiFoam/deflagrationToDetonationTransition",),
    "0/U": ("blastFoam/movingCone", "blastFoam/freeField"),
    "constant/combustionProperties": ("blastXiFoam/deflagrationToDetonationTransition",),
    "system/setFieldsDict": (
        "blastFoam/freeField",
        "blastFoam/movingCone",
        "blastEulerFoam/reactingParticles",
    ),
}


def unique_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def is_strict_dataset(dataset: Sequence[Dict[str, object]]) -> bool:
    if not dataset:
        return False
    target_files = dataset[0].get("target_files", [])
    return bool(target_files) and isinstance(target_files[0], dict)


def dataset_mode(dataset: Sequence[Dict[str, object]]) -> str:
    if not is_strict_dataset(dataset):
        raise ValueError("Legacy retrieval datasets are no longer supported. Please use the strict dataset format.")
    return "strict"


def target_identifier(target: object) -> str:
    if not isinstance(target, dict):
        raise TypeError(f"Strict target must be a mapping, got {type(target).__name__}")

    canonical_id = target.get("canonical_id")
    if canonical_id:
        return str(canonical_id)

    case_path = target.get("case_path")
    file_path = target.get("file_path")
    if case_path and file_path:
        return f"{case_path}::{file_path}"

    raise ValueError(f"Invalid strict target entry: {target}")


def target_file_path(target: object) -> str:
    if not isinstance(target, dict) or not target.get("file_path"):
        raise ValueError(f"Invalid strict target file entry: {target}")
    return str(target["file_path"])


def target_case_path(target: object) -> str:
    if not isinstance(target, dict) or not target.get("case_path"):
        raise ValueError(f"Invalid strict target case entry: {target}")
    return str(target["case_path"])


def entry_target_identifiers(entry: Dict[str, object]) -> List[str]:
    return [target_identifier(target) for target in entry.get("target_files", [])]


def entry_target_file_paths(entry: Dict[str, object]) -> List[str]:
    return [target_file_path(target) for target in entry.get("target_files", [])]


def entry_target_case_paths(entry: Dict[str, object]) -> List[str]:
    return [target_case_path(target) for target in entry.get("target_files", [])]


class ResultNormalizer:
    """Normalize retrieval outputs for the strict retrieval dataset."""

    def __init__(self, dataset_path: str, dataset: Sequence[Dict[str, object]], tutorials_dir: Optional[str] = None):
        if not is_strict_dataset(dataset):
            raise ValueError("Legacy retrieval datasets are no longer supported.")
        resolved_tutorials_dir = tutorials_dir or os.getenv("BLASTFOAM_TUTORIALS")
        self._strict_evaluator = StrictRetrievalEvaluator(dataset_path, resolved_tutorials_dir)

    def normalize(self, results: Sequence[object]) -> List[str]:
        normalized_ids: List[str] = []
        seen = set()
        for item in results:
            candidate = self._strict_evaluator.normalize_result(item) if self._strict_evaluator else None
            if not candidate or candidate.canonical_id in seen:
                continue
            seen.add(candidate.canonical_id)
            normalized_ids.append(candidate.canonical_id)
        return normalized_ids


def infer_file_candidates(query: str) -> List[str]:
    query_lower = query.lower()
    files: List[str] = []

    for file_path, keywords in FILE_HINTS:
        if any(keyword in query_lower for keyword in keywords):
            files.append(file_path)

    if "particle" in query_lower and "turbulence" in query_lower:
        files.append("constant/turbulenceProperties.particles")
    if "gas phase" in query_lower and "turbulence" in query_lower:
        files.append("constant/turbulenceProperties.gas")
    if "temperature" in query_lower and "limiter" in query_lower:
        files.append("system/fvOptions")

    if not files:
        files.append("system/controlDict")

    return unique_preserve_order(files)


def infer_case_candidates(query: str, file_candidates: Sequence[str]) -> List[str]:
    query_lower = query.lower()
    case_scores = {case_path: 0.0 for case_path in STRICT_CASE_HINTS}

    for case_path, keywords in STRICT_CASE_HINTS.items():
        for keyword in keywords:
            if keyword in query_lower:
                case_scores[case_path] += max(1.0, len(keyword.split()))

    if "window" in query_lower or "glass" in query_lower:
        case_scores["blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass"] += 6.0
    if "particle" in query_lower or "granular" in query_lower:
        case_scores["blastEulerFoam/reactingParticles"] += 5.0
    if "deflagration" in query_lower or "arrhenius" in query_lower:
        case_scores["blastXiFoam/deflagrationToDetonationTransition"] += 5.0
    if "cone" in query_lower:
        case_scores["blastFoam/movingCone"] += 5.0
    if "building" in query_lower:
        case_scores["blastFoam/mappedBuilding3D"] += 4.0

    for file_path in file_candidates:
        for case_path in FILE_PRIOR_CASES.get(file_path, ()):  # file-family prior
            case_scores[case_path] += 3.0

        if file_path == "constant/phaseProperties":
            if any(token in query_lower for token in ("window", "glass", "damage", "orthotropic", "pburst")):
                case_scores["blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass"] += 4.0
            if any(token in query_lower for token in ("particle", "packing", "restitution", "drag")):
                case_scores["blastEulerFoam/reactingParticles"] += 4.0

    ranked = [case_path for case_path, score in sorted(case_scores.items(), key=lambda item: item[1], reverse=True) if score > 0]
    if ranked:
        return ranked[:3]

    fallbacks: List[str] = []
    for file_path in file_candidates:
        fallbacks.extend(FILE_PRIOR_CASES.get(file_path, ()))

    if not fallbacks:
        fallbacks = [
            "blastFoam/freeField",
            "blastEulerFoam/reactingParticles",
            "blastXiFoam/deflagrationToDetonationTransition",
        ]

    return unique_preserve_order(fallbacks)[:3]


def example_retrieval_function(query: str) -> List[str]:
    file_candidates = infer_file_candidates(query)
    case_candidates = infer_case_candidates(query, file_candidates)
    ranked_results: List[str] = []
    for case_path in case_candidates:
        for file_path in file_candidates[:3]:
            ranked_results.append(f"{case_path}::{file_path}")

    return unique_preserve_order(ranked_results)
