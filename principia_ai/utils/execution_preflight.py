from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List


PARALLEL_RE = re.compile(r"(^|\s)(runParallel|mpirun|mpiexec)(\s|$)")
DYNAMIC_CODE_RE = re.compile(r"#\s*(calc|codeStream)\b|\bdynamicCode\b")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def allrun_uses_parallel(case_path: str | os.PathLike[str] | None) -> bool:
    if not case_path:
        return False
    allrun = Path(case_path) / "Allrun"
    return bool(PARALLEL_RE.search(_read_text(allrun)))


def case_uses_dynamic_code(case_path: str | os.PathLike[str] | None) -> bool:
    if not case_path:
        return False
    root = Path(case_path)
    for relative_root in ("system", "constant", "0", "0.orig"):
        directory = root / relative_root
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and DYNAMIC_CODE_RE.search(_read_text(path)):
                return True
    return False


def _missing_case_commands(case_path: Path) -> List[str]:
    allrun_text = _read_text(case_path / "Allrun")
    required: set[str] = set()
    for match in re.finditer(r"\b(?:runApplication|runParallel)\s+(?:-[A-Za-z]\s+\S+\s+)*([A-Za-z][A-Za-z0-9_.+-]*)", allrun_text):
        command = match.group(1)
        if command not in {"$(getApplication)", "getApplication"}:
            required.add(command)

    missing = []
    for command in sorted(required):
        if shutil.which(command) is None:
            missing.append(command)
    return missing


def run_execution_preflight(case_path: str | os.PathLike[str] | None) -> Dict[str, Any]:
    blockers: List[str] = []
    warnings: List[str] = []
    case_dir = Path(case_path or "")

    if not case_path:
        blockers.append("case_path is not set")
    elif not case_dir.exists():
        blockers.append(f"case directory does not exist: {case_dir}")
    elif not (case_dir / "Allrun").exists():
        warnings.append("Allrun is missing; execution agent may need to create it")

    if case_path and allrun_uses_parallel(case_dir):
        if shutil.which("mpirun") is None and shutil.which("mpiexec") is None:
            blockers.append("Allrun uses parallel execution, but neither mpirun nor mpiexec is available")

    if case_path and os.geteuid() == 0 and case_uses_dynamic_code(case_dir):
        if os.getenv("ALLOW_ROOT_OPENFOAM", "false").lower() not in {"1", "true", "yes", "on"}:
            blockers.append(
                "case uses OpenFOAM dynamic code (#calc/#codeStream), but execution is running as root"
            )

    if case_path and case_dir.exists():
        missing_commands = _missing_case_commands(case_dir)
        if missing_commands:
            warnings.append(
                "OpenFOAM commands not found in PATH before execution: " + ", ".join(missing_commands)
            )

    return {
        "ok": not blockers,
        "blockers": blockers,
        "warnings": warnings,
    }


def format_preflight_report(preflight: Dict[str, Any]) -> str:
    lines = ["Execution failed: environment preflight blocked execution.", ""]
    lines.append("Environment blockers:")
    for blocker in preflight.get("blockers") or []:
        lines.append(f"- {blocker}")
    warnings = preflight.get("warnings") or []
    if warnings:
        lines.extend(["", "Warnings:"])
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.append("")
    lines.append("No solver command was started.")
    return "\n".join(lines)
