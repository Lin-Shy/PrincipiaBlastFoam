"""
Build and audit a strict retrieval validation dataset.

The legacy retrieval dataset in this repository only labels relative file paths
such as ``system/controlDict``. That works for single-case retrieval, but it is
not suitable for evaluating retrieval across all tutorials because many cases
contain files with the same relative path.

This script addresses that gap in three ways:
1. Builds a tutorial-case manifest from the tutorial root.
2. Audits the legacy dataset to show how many entries are ambiguous or invalid
   under strict ``case_path + file_path`` evaluation.
3. Builds a strict retrieval dataset from the case-specific modification
   datasets and audits each generated entry against real tutorial files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_DIR = PROJECT_ROOT / "dataset" / "retrieval"
MODIFICATION_DATASETS: Sequence[Tuple[str, Path]] = (
    ("basic", PROJECT_ROOT / "dataset" / "modification" / "blastfoam_basic_modifications.json"),
    ("advanced", PROJECT_ROOT / "dataset" / "modification" / "blastfoam_senior_modifications.json"),
)
LEGACY_DATASET_PATH = RETRIEVAL_DIR / "blastfoam_retrieval_validation_dataset.json"

STRICT_DATASET_PATH = RETRIEVAL_DIR / "blastfoam_retrieval_validation_dataset_strict.json"
STRICT_AUDIT_PATH = RETRIEVAL_DIR / "blastfoam_retrieval_validation_dataset_strict_audit.json"
LEGACY_AUDIT_PATH = RETRIEVAL_DIR / "blastfoam_retrieval_validation_dataset_legacy_case_audit.json"
CASE_MANIFEST_PATH = RETRIEVAL_DIR / "tutorial_case_manifest.json"
SUMMARY_PATH = RETRIEVAL_DIR / "STRICT_RETRIEVAL_AUDIT_SUMMARY.md"

# The current strict dataset is intentionally rooted in the seven case-specific
# modification sources, because those are already tied to concrete tutorial
# cases and are much easier to validate than the generic legacy retrieval set.
EXPLICIT_CASE_MAP = {
    "deflagrationToDetonationTransition": "blastXiFoam/deflagrationToDetonationTransition",
    "freeField": "blastFoam/freeField",
    "internalDetonation_withObstacleAndGlass": "blastFoam/internalDetonation/internalDetonation_withObstacleAndGlass",
    "mappedBuilding3D": "blastFoam/mappedBuilding3D",
    "movingCone": "blastFoam/movingCone",
    "reactingParticles": "blastEulerFoam/reactingParticles",
    "triplePointShockInteration": "blastFoam/triplePointShockInteration",
}

TARGET_FILE_OVERRIDES = {
    "deflagrationToDetonationTransition_thermo_eConst": {
        "modified_files": ["constant/thermophysicalProperties"],
        "note": "The DDT tutorial stores thermo settings in thermophysicalProperties, not phaseProperties.",
    }
}

CONFIG_ROOTS = {"0", "0.orig", "constant", "system"}
OPTIONAL_IDENTIFIER_FILE_PREFIXES = ("0/", "0.orig/", "system/blockMeshDict")
STOPWORDS = {
    "a",
    "add",
    "addition",
    "adjust",
    "air",
    "and",
    "approximate",
    "as",
    "at",
    "ascii",
    "binary",
    "box",
    "but",
    "capture",
    "case",
    "cells",
    "center",
    "change",
    "closed",
    "coarser",
    "computation",
    "configure",
    "constant",
    "control",
    "criterion",
    "definition",
    "definitions",
    "detailed",
    "different",
    "direction",
    "distribution",
    "domain",
    "enable",
    "equivalent",
    "example",
    "explosion",
    "field",
    "finer",
    "for",
    "format",
    "frequency",
    "from",
    "gas",
    "ground",
    "higher",
    "in",
    "increase",
    "initial",
    "interaction",
    "into",
    "less",
    "level",
    "location",
    "longer",
    "lower",
    "make",
    "maximum",
    "mesh",
    "model",
    "more",
    "move",
    "moving",
    "number",
    "of",
    "one",
    "output",
    "particle",
    "phase",
    "position",
    "pressure",
    "process",
    "refined",
    "region",
    "run",
    "scenario",
    "set",
    "shorter",
    "simlate",
    "simulate",
    "simulation",
    "size",
    "smaller",
    "space",
    "speed",
    "switch",
    "than",
    "the",
    "this",
    "threshold",
    "time",
    "to",
    "transition",
    "use",
    "value",
    "velocity",
    "wave",
    "where",
    "with",
}


@dataclass(frozen=True)
class TutorialCase:
    case_path: str
    absolute_path: Path
    files: Tuple[str, ...]
    config_files: Tuple[str, ...]

    def has_files(self, relative_paths: Iterable[str]) -> bool:
        config_set = set(self.config_files)
        return all(path in config_set for path in relative_paths)

    def file_content(self, relative_path: str) -> str:
        file_path = self.absolute_path / relative_path
        return file_path.read_text(encoding="utf-8", errors="ignore")


def canonical_id(case_path: str, file_path: str) -> str:
    return f"{case_path}::{file_path}"


def discover_tutorial_cases(tutorials_dir: Path) -> Dict[str, TutorialCase]:
    cases: Dict[str, TutorialCase] = {}

    for allrun in sorted(tutorials_dir.rglob("Allrun")):
        case_dir = allrun.parent
        case_path = str(case_dir.relative_to(tutorials_dir))

        files: List[str] = []
        config_files: List[str] = []
        for file_path in sorted(p for p in case_dir.rglob("*") if p.is_file()):
            relative = str(file_path.relative_to(case_dir))
            files.append(relative)

            parts = Path(relative).parts
            if any(part in CONFIG_ROOTS for part in parts):
                config_files.append(relative)

        cases[case_path] = TutorialCase(
            case_path=case_path,
            absolute_path=case_dir,
            files=tuple(files),
            config_files=tuple(config_files),
        )

    return cases


def resolve_case_alias(case_alias: str, cases: Dict[str, TutorialCase]) -> Tuple[Optional[str], List[str]]:
    explicit = EXPLICIT_CASE_MAP.get(case_alias)
    if explicit:
        return (explicit, [explicit]) if explicit in cases else (None, [explicit])

    matches = []
    for case_path in cases:
        if case_path == case_alias or case_path.endswith(f"/{case_alias}") or Path(case_path).name == case_alias:
            matches.append(case_path)

    matches = sorted(set(matches))
    if len(matches) == 1:
        return matches[0], matches
    return None, matches


def infer_category(file_paths: Sequence[str], description: str, modification: str) -> str:
    text = f"{description} {modification}".lower()
    files = {path.lower() for path in file_paths}

    if "system/fvschemes" in files:
        return "numerical_schemes"
    if "system/fvsolution" in files:
        return "solver_control"
    if "system/setfieldsdict" in files:
        return "initial_conditions"
    if any(path.startswith("0/") or path.startswith("0.orig/") for path in files):
        return "boundary_conditions"
    if "constant/combustionproperties" in files:
        return "combustion"
    if "constant/turbulenceproperties.particles" in files:
        return "multiphase"
    if "constant/turbulenceproperties" in files:
        return "turbulence_model"
    if "system/blockmeshdict" in files or "constant/dynamicmeshdict" in files:
        return "mesh"
    if "system/controldict" in files:
        if any(token in text for token in ("writeinterval", "writeformat", "binary", "ascii", "output")):
            return "output_control"
        return "time_control"
    if "constant/phaseproperties" in files:
        if any(token in text for token in ("jwl", "bkw", "stiffenedgas", "equation of state", "eos")):
            return "equation_of_state"
        if any(token in text for token in ("janaf", "econst", "thermo", "specific heat")):
            return "thermodynamics"
        if any(token in text for token in ("elasticplastic", "principalstrain", "principalstress", "fracture", "window", "pburst")):
            return "structural_mechanics"
        if any(token in text for token in ("drag", "heat transfer", "granular", "particle")):
            return "multiphase"
        if any(token in text for token in ("rho0", "density")):
            return "material_properties"
        return "physics_models"
    return "physics_models"


def extract_identifier_candidates(text: str) -> List[str]:
    candidates: List[str] = []

    for match in re.findall(r"[\"']([A-Za-z_][A-Za-z0-9_.+-]*)[\"']", text):
        candidates.append(match)

    for match in re.findall(r"\b[A-Za-z_][A-Za-z0-9_.+-]*\b", text):
        lowered = match.lower()
        if lowered in STOPWORDS:
            continue
        if len(match) <= 2 and not any(ch.isupper() for ch in match):
            continue
        if match.isupper() and len(match) > 6:
            continue
        if any(ch.isupper() for ch in match) or any(ch.isdigit() for ch in match) or "." in match:
            candidates.append(match)

    seen: Set[str] = set()
    ordered: List[str] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def build_case_manifest(cases: Dict[str, TutorialCase]) -> Dict[str, object]:
    return {
        "tutorial_case_count": len(cases),
        "cases": [
            {
                "case_path": case.case_path,
                "file_count": len(case.files),
                "config_file_count": len(case.config_files),
                "config_files": list(case.config_files),
            }
            for case in cases.values()
        ],
    }


def audit_legacy_dataset(legacy_dataset: Sequence[Dict[str, object]], cases: Dict[str, TutorialCase]) -> Dict[str, object]:
    results = []
    status_counter: Counter[str] = Counter()

    for entry in legacy_dataset:
        target_files = list(entry["target_files"])
        matched_cases = [
            case.case_path
            for case in cases.values()
            if case.has_files(target_files)
        ]

        if not matched_cases:
            status = "missing"
        elif len(matched_cases) == 1:
            status = "unique"
        else:
            status = "ambiguous"

        status_counter[status] += 1
        results.append(
            {
                "id": entry["id"],
                "query": entry["query"],
                "target_files": target_files,
                "status": status,
                "matched_case_count": len(matched_cases),
                "matched_cases_preview": matched_cases[:10],
            }
        )

    return {
        "summary": {
            "total_entries": len(results),
            "unique": status_counter["unique"],
            "ambiguous": status_counter["ambiguous"],
            "missing": status_counter["missing"],
        },
        "entries": results,
    }


def build_strict_dataset(cases: Dict[str, TutorialCase]) -> List[Dict[str, object]]:
    strict_entries: List[Dict[str, object]] = []
    entry_id = 1

    for difficulty, source_path in MODIFICATION_DATASETS:
        source_data = json.loads(source_path.read_text(encoding="utf-8"))
        for item in source_data:
            resolved_case_path, matches = resolve_case_alias(item["case_path"], cases)
            override = TARGET_FILE_OVERRIDES.get(item["case_name"])
            modified_files = override["modified_files"] if override else item["modified_files"]
            strict_entries.append(
                {
                    "id": entry_id,
                    "query": item["description"],
                    "description": item["description"],
                    "modification": item["modification"],
                    "difficulty": difficulty,
                    "source_dataset": source_path.name,
                    "source_case_alias": item["case_path"],
                    "case_name": item["case_name"],
                    "case_path": resolved_case_path,
                    "case_resolution_candidates": matches,
                    "category": infer_category(modified_files, item["description"], item["modification"]),
                    "correction_note": override["note"] if override else None,
                    "target_files": [
                        {
                            "case_path": resolved_case_path,
                            "file_path": file_path,
                            "canonical_id": canonical_id(resolved_case_path, file_path) if resolved_case_path else None,
                        }
                        for file_path in modified_files
                    ],
                }
            )
            entry_id += 1

    return strict_entries


def audit_strict_dataset(strict_entries: Sequence[Dict[str, object]], cases: Dict[str, TutorialCase]) -> Dict[str, object]:
    results = []
    status_counter: Counter[str] = Counter()

    for entry in strict_entries:
        case_path = entry.get("case_path")
        case = cases.get(case_path) if case_path else None
        issues: List[str] = []
        warnings: List[str] = []
        file_audits: List[Dict[str, object]] = []

        if not case_path:
            issues.append("Case alias could not be resolved to a unique tutorial case.")
        elif not case:
            issues.append(f"Resolved case path does not exist in tutorial manifest: {case_path}")

        identifiers = extract_identifier_candidates(
            f"{entry['query']} {entry.get('modification', '')}"
        )
        for target in entry["target_files"]:
            file_path = target["file_path"]
            exists = bool(case and case.has_files([file_path]))
            identifier_hits: List[str] = []

            if not exists:
                issues.append(f"Missing target file in resolved case: {file_path}")
            else:
                content = case.file_content(file_path)
                lowered_content = content.lower()
                identifier_hits = [
                    identifier for identifier in identifiers if identifier.lower() in lowered_content
                ]

                if identifiers and not identifier_hits and not file_path.startswith(OPTIONAL_IDENTIFIER_FILE_PREFIXES):
                    warnings.append(
                        f"No identifier candidates from query/description were found in {file_path}."
                    )

            file_audits.append(
                {
                    "file_path": file_path,
                    "exists": exists,
                    "identifier_hits": identifier_hits,
                }
            )

        if issues:
            status = "fail"
        elif warnings:
            status = "warn"
        else:
            status = "pass"

        status_counter[status] += 1
        results.append(
            {
                "id": entry["id"],
                "case_path": case_path,
                "query": entry["query"],
                "status": status,
                "issues": issues,
                "warnings": warnings,
                "file_audits": file_audits,
            }
        )

    return {
        "summary": {
            "total_entries": len(results),
            "pass": status_counter["pass"],
            "warn": status_counter["warn"],
            "fail": status_counter["fail"],
        },
        "entries": results,
    }


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_summary_markdown(
    tutorials_dir: Path,
    case_manifest: Dict[str, object],
    legacy_audit: Dict[str, object],
    strict_entries: Sequence[Dict[str, object]],
    strict_audit: Dict[str, object],
) -> str:
    legacy_summary = legacy_audit["summary"]
    strict_summary = strict_audit["summary"]
    strict_case_counter = Counter(entry["case_path"] for entry in strict_entries if entry["case_path"])

    lines = [
        "# Strict Retrieval Dataset Audit Summary",
        "",
        f"- Tutorials root: `{tutorials_dir}`",
        f"- Tutorial case count: `{case_manifest['tutorial_case_count']}`",
        f"- Strict dataset size: `{len(strict_entries)}`",
        "",
        "## Legacy Dataset Audit",
        "",
        f"- Unique case-resolvable entries: `{legacy_summary['unique']}`",
        f"- Ambiguous entries: `{legacy_summary['ambiguous']}`",
        f"- Missing entries: `{legacy_summary['missing']}`",
        "",
        "## Strict Dataset Audit",
        "",
        f"- Pass: `{strict_summary['pass']}`",
        f"- Warn: `{strict_summary['warn']}`",
        f"- Fail: `{strict_summary['fail']}`",
        "",
        "## Strict Dataset Case Coverage",
        "",
    ]

    for case_path, count in sorted(strict_case_counter.items()):
        lines.append(f"- `{case_path}`: `{count}` entries")

    lines.extend(
        [
            "",
            "## Legacy Dataset Examples",
            "",
        ]
    )

    ambiguous_examples = [entry for entry in legacy_audit["entries"] if entry["status"] == "ambiguous"][:5]
    missing_examples = [entry for entry in legacy_audit["entries"] if entry["status"] == "missing"][:5]

    for entry in ambiguous_examples:
        lines.append(
            f"- Ambiguous `{entry['id']}`: `{entry['query']}` -> {entry['matched_case_count']} candidate cases"
        )
    for entry in missing_examples:
        lines.append(
            f"- Missing `{entry['id']}`: `{entry['query']}` -> target files {entry['target_files']}"
        )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and audit a strict retrieval dataset.")
    parser.add_argument(
        "--tutorials-dir",
        default=os.getenv("BLASTFOAM_TUTORIALS"),
        help="Path to the BlastFOAM tutorials directory. Defaults to BLASTFOAM_TUTORIALS.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.tutorials_dir:
        raise SystemExit("Please provide --tutorials-dir or set BLASTFOAM_TUTORIALS.")

    tutorials_dir = Path(args.tutorials_dir).resolve()
    if not tutorials_dir.is_dir():
        raise SystemExit(f"Tutorial directory does not exist: {tutorials_dir}")

    cases = discover_tutorial_cases(tutorials_dir)
    legacy_dataset = json.loads(LEGACY_DATASET_PATH.read_text(encoding="utf-8"))

    case_manifest = build_case_manifest(cases)
    legacy_audit = audit_legacy_dataset(legacy_dataset, cases)
    strict_entries = build_strict_dataset(cases)
    strict_audit = audit_strict_dataset(strict_entries, cases)

    write_json(CASE_MANIFEST_PATH, case_manifest)
    write_json(LEGACY_AUDIT_PATH, legacy_audit)
    write_json(STRICT_DATASET_PATH, strict_entries)
    write_json(STRICT_AUDIT_PATH, strict_audit)
    SUMMARY_PATH.write_text(
        build_summary_markdown(tutorials_dir, case_manifest, legacy_audit, strict_entries, strict_audit),
        encoding="utf-8",
    )

    print(f"Wrote tutorial case manifest to: {CASE_MANIFEST_PATH}")
    print(f"Wrote legacy strictness audit to: {LEGACY_AUDIT_PATH}")
    print(f"Wrote strict retrieval dataset to: {STRICT_DATASET_PATH}")
    print(f"Wrote strict dataset audit to: {STRICT_AUDIT_PATH}")
    print(f"Wrote summary to: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
