from __future__ import annotations

import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator, Optional


_active_case_path: ContextVar[Optional[str]] = ContextVar("active_case_path", default=None)
NUMERIC_TIME_DIR_RE = re.compile(r"^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")


def _normalize_path(path: str | os.PathLike[str]) -> str:
    return str(Path(path).expanduser().resolve())


def set_tool_context(case_path: str | os.PathLike[str] | None = None) -> None:
    """Set the active generated case directory used by filesystem tools."""
    if case_path:
        _active_case_path.set(_normalize_path(case_path))


@contextmanager
def scoped_tool_context(case_path: str | os.PathLike[str] | None = None) -> Iterator[None]:
    token = None
    if case_path:
        token = _active_case_path.set(_normalize_path(case_path))
    try:
        yield
    finally:
        if token is not None:
            _active_case_path.reset(token)


def get_active_case_path() -> Optional[Path]:
    case_path = _active_case_path.get()
    return Path(case_path) if case_path else None


def _looks_case_relative(path: str) -> bool:
    normalized = path.replace("\\", "/").strip().strip("'\"")
    if not normalized:
        return False
    first_part = normalized.split("/", 1)[0]
    if first_part != "0" and NUMERIC_TIME_DIR_RE.fullmatch(first_part):
        return True
    return first_part in {
        "0",
        "0.orig",
        "constant",
        "system",
        "postProcessing",
        "processor0",
        "processor1",
        "Allrun",
        "Allclean",
        "log.blastFoam",
        "execution_report.md",
        "workflow_evidence.md",
        "workflow_evidence.json",
        "artifact_contract.json",
        "physics_report.md",
        "review_report.md",
    } or first_part.startswith(("processor", "log."))


def resolve_tool_path(
    path: str | os.PathLike[str] | None,
    *,
    default_to_case: bool = False,
) -> Path:
    """Resolve relative tool paths against the active generated case when appropriate."""
    active_case = get_active_case_path()
    if path is None or str(path).strip() == "":
        return active_case if default_to_case and active_case else Path(".")

    candidate = Path(str(path).strip().strip("'\"")).expanduser()
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate

    if active_case and (default_to_case or _looks_case_relative(str(path))):
        return active_case / candidate

    return candidate


def display_path(path: Path) -> str:
    try:
        active_case = get_active_case_path()
        if active_case:
            return str(path.relative_to(active_case))
    except ValueError:
        pass
    return str(path)
