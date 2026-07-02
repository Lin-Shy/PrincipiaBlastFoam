from __future__ import annotations

import argparse
import os
from pathlib import Path

from principia_deepagents import cli as cli_mod
from principia_deepagents.config import RuntimeConfig
from principia_deepagents.tools import openfoam as openfoam_tools
from principia_deepagents.cli import _apply_execution_fallback, _validation_state
from principia_deepagents.tools.openfoam import (
    _build_allrun_shell_command,
    _execution_subprocess_args,
    _resolve_execution_timeout_seconds,
    run_openfoam_case_once,
)
from principia_deepagents.utils.execution_preflight import run_execution_preflight
from principia_deepagents.utils.execution_status import build_execution_status, read_execution_status, write_execution_status
from principia_deepagents.utils.openfoam_diagnostics import classify_case_openfoam_logs, summarize_diagnostics
from principia_deepagents.utils.solver_logs import resolve_solver_log_paths, solver_log_has_clean_end
from principia_deepagents.utils.workflow_artifacts import validate_workflow_artifacts


def test_build_allrun_shell_command_sources_environment(tmp_path: Path, monkeypatch) -> None:
    openfoam_bashrc = tmp_path / "OpenFOAM-bashrc"
    blastfoam_bashrc = tmp_path / "blastFoam-bashrc"
    openfoam_bashrc.write_text("# openfoam\n", encoding="utf-8")
    blastfoam_bashrc.write_text("# blastfoam\n", encoding="utf-8")
    monkeypatch.setenv("OPENFOAM_BASHRC", str(openfoam_bashrc))
    monkeypatch.setenv("BLASTFOAM_BASHRC", str(blastfoam_bashrc))

    command = _build_allrun_shell_command(tmp_path)

    assert f"source {openfoam_bashrc}" in command
    assert f"MAKE=True source {blastfoam_bashrc}" in command
    assert f"cd {tmp_path}" in command
    assert command.endswith("./Allrun")


def test_execution_subprocess_switches_to_configured_user_when_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(openfoam_tools.os, "geteuid", lambda: 0)

    args, cwd = _execution_subprocess_args(tmp_path, "cd case && ./Allrun", "openfoam")

    assert args == ["su", "-s", "/bin/bash", "openfoam", "-c", "cd case && ./Allrun"]
    assert cwd == Path("/")


def test_execution_subprocess_uses_current_user_without_execution_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(openfoam_tools.os, "geteuid", lambda: 0)

    args, cwd = _execution_subprocess_args(tmp_path, "cd case && ./Allrun", None)

    assert args == ["bash", "-lc", "cd case && ./Allrun"]
    assert cwd == tmp_path


def test_execution_timeout_respects_runtime_minimum(monkeypatch) -> None:
    monkeypatch.setenv("DEEPAGENTS_EXECUTION_TIMEOUT_SECONDS", "900")

    assert _resolve_execution_timeout_seconds(30) == 900


def test_run_openfoam_timeout_writes_failed_status(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "Allrun").write_text("#!/bin/sh\nsleep 10\n", encoding="utf-8")
    monkeypatch.setenv("ENABLE_EXECUTION", "true")
    monkeypatch.setenv("DEEPAGENTS_MIN_EXECUTION_TIMEOUT_SECONDS", "1")
    monkeypatch.delenv("OPENFOAM_EXECUTION_USER", raising=False)
    monkeypatch.setattr(
        openfoam_tools,
        "run_execution_preflight",
        lambda case_path: {"ok": True, "blockers": [], "warnings": [], "execution_user": None},
    )
    monkeypatch.setattr(
        openfoam_tools,
        "_build_allrun_shell_command",
        lambda case_dir: "python3 -c 'import time; time.sleep(10)'",
    )

    result = run_openfoam_case_once(tmp_path, timeout_seconds=1)
    status = read_execution_status(tmp_path)
    report = (tmp_path / "execution_report.md").read_text(encoding="utf-8")

    assert result["timed_out"] is True
    assert result["timeout_seconds"] == 1
    assert status["final_status"] == "failed"
    assert status["status_source"] == "execution_timeout"
    assert "Timed out: `True`" in report


def test_preflight_reports_configured_execution_user(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "Allrun").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("OPENFOAM_EXECUTION_USER", "openfoam")
    monkeypatch.setenv("OPENFOAM_CHOWN_CASE", "true")
    monkeypatch.setattr(os, "geteuid", lambda: 0)

    result = run_execution_preflight(tmp_path)

    assert result["execution_user"] == "openfoam"
    assert result["ok"] is True
    assert any("ownership will be changed" in warning for warning in result["warnings"])


def test_cli_validation_state_marks_existing_review_as_passed(tmp_path: Path) -> None:
    (tmp_path / "review_report.md").write_text("# Review Report\n\nValidation Status: Passed\n", encoding="utf-8")
    write_execution_status(
        tmp_path,
        {
            "schema_version": 1,
            "run_status": "completed",
            "final_status": "success",
        },
    )

    state = _validation_state(tmp_path)

    assert state["validation_status"] == "passed"
    assert state["execution_status"]["final_status"] == "success"


def test_execution_fallback_runs_solver_and_writes_passing_contract(tmp_path: Path, monkeypatch) -> None:
    tutorial_root = tmp_path / "tutorials"
    tutorial_case = tutorial_root / "blastFoam" / "shockTube_tabulated"
    control = tutorial_case / "system" / "controlDict"
    control.parent.mkdir(parents=True)
    control.write_text(
        "application blastFoam;\nendTime 0.02;\nwriteInterval 0.001;\n",
        encoding="utf-8",
    )
    (tutorial_case / "Allrun").write_text("#!/bin/sh\n", encoding="utf-8")
    (tutorial_case / "Allclean").write_text("#!/bin/sh\n", encoding="utf-8")
    case_dir = tmp_path / "case"

    def fake_run_openfoam_case_once(case_path: Path, *, timeout_seconds: int = 3600):
        post_file = case_path / "postProcessing" / "probes" / "0" / "p"
        post_file.parent.mkdir(parents=True)
        post_file.write_text("# p\n0 101325\n", encoding="utf-8")
        report = (
            "# Execution Report\n\n"
            "The fake solver run completed successfully for this execution fallback test. "
            "The authoritative execution_status.json marks the run completed and successful.\n"
        )
        (case_path / "execution_report.md").write_text(report, encoding="utf-8")
        status = {
            "schema_version": 1,
            "run_status": "completed",
            "final_status": "success",
            "solver_log_has_clean_end": True,
            "solver_logs": [],
            "report_path": "execution_report.md",
        }
        write_execution_status(case_path, status)
        return {"started": True, "return_code": 0, "status": status}

    monkeypatch.setattr(cli_mod, "run_openfoam_case_once", fake_run_openfoam_case_once)
    config = RuntimeConfig(
        case_path=case_dir,
        user_request="shock tube短时验证算例，endTime控制在0.0005秒以内，writeInterval设置得足够小。",
        tutorial_path=tutorial_root,
        model="fake",
        api_key="fake",
        base_url=None,
        provider="fake",
        active_profile=None,
        recursion_limit=20,
        enable_execution=True,
        require_execution=True,
        use_mcp_retrieval=False,
    )

    result = _apply_execution_fallback(config, reason="test execution fallback", timeout_seconds=30)
    review_text = (case_dir / "review_report.md").read_text(encoding="utf-8")
    physics_text = (case_dir / "physics_report.md").read_text(encoding="utf-8")

    assert result["execution"]["started"] is True
    assert result["post_processing"]["written"] is True
    assert result["contract"]["ok"] is True
    assert (case_dir / "artifact_contract.json").exists()
    assert (case_dir / "post_processing_report.md").exists()
    assert "endTime 0.0005;" in (case_dir / "system" / "controlDict").read_text(encoding="utf-8")
    assert "Validation Status: Passed" in review_text
    assert "Execution required: `True`" in review_text
    assert "non-execution skip report" not in review_text
    assert "Controlled solver execution is enabled" in physics_text
    assert "ENABLE_EXECUTION` is not true" not in physics_text


def test_execution_fallback_resets_polluted_case_before_running(tmp_path: Path, monkeypatch) -> None:
    tutorial_root = tmp_path / "tutorials"
    tutorial_case = tutorial_root / "blastFoam" / "building3DWorkshop"
    (tutorial_case / "system").mkdir(parents=True)
    (tutorial_case / "Allrun").write_text("#!/bin/sh\nclean tutorial\n", encoding="utf-8")
    (tutorial_case / "Allclean").write_text("#!/bin/sh\n", encoding="utf-8")
    (tutorial_case / "system" / "controlDict").write_text(
        "application blastFoam;\nendTime 0.0025;\nwriteInterval 0.0005;\n",
        encoding="utf-8",
    )

    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "Allrun").write_text("#!/bin/sh\npolluted agent edit\n", encoding="utf-8")
    (case_dir / "log.blastFoam").write_text("FOAM FATAL ERROR\nstale failed run\n", encoding="utf-8")

    def fake_run_openfoam_case_once(case_path: Path, *, timeout_seconds: int = 3600):
        assert "clean tutorial" in (case_path / "Allrun").read_text(encoding="utf-8")
        assert "polluted agent edit" not in (case_path / "Allrun").read_text(encoding="utf-8")
        assert not (case_path / "log.blastFoam").exists()
        (case_path / "execution_report.md").write_text(
            "# Execution Report\n\n"
            "Clean fallback solver run completed successfully after the polluted agent edits were reset. "
            "The deterministic fallback restored the tutorial Allrun, applied bounded smoke controls, "
            "and wrote execution_status.json with completed/success status for contract validation.\n",
            encoding="utf-8",
        )
        status = {
            "schema_version": 1,
            "run_status": "completed",
            "final_status": "success",
            "solver_log_has_clean_end": True,
            "solver_logs": [],
            "report_path": "execution_report.md",
        }
        write_execution_status(case_path, status)
        return {"started": True, "return_code": 0, "status": status}

    monkeypatch.setattr(cli_mod, "run_openfoam_case_once", fake_run_openfoam_case_once)
    config = RuntimeConfig(
        case_path=case_dir,
        user_request="building obstacle短时smoke test，endTime控制在0.0015秒以内。",
        tutorial_path=tutorial_root,
        model="fake",
        api_key="fake",
        base_url=None,
        provider="fake",
        active_profile=None,
        recursion_limit=20,
        enable_execution=True,
        require_execution=True,
        use_mcp_retrieval=False,
    )

    result = _apply_execution_fallback(config, reason="polluted case test", timeout_seconds=30)

    assert result["case_reset"]["initialized"] is True
    assert result["post_processing"]["written"] is True
    assert result["contract"]["ok"] is True
    assert (case_dir / "post_processing_report.md").exists()
    assert "endTime 0.0005;" in (case_dir / "system" / "controlDict").read_text(encoding="utf-8")


def test_cmd_run_uses_execution_fallback_after_agent_exception(tmp_path: Path, monkeypatch) -> None:
    config = RuntimeConfig(
        case_path=tmp_path,
        user_request="solver-enabled smoke",
        tutorial_path=tmp_path,
        model="fake",
        api_key="fake",
        base_url=None,
        provider="fake",
        active_profile=None,
        recursion_limit=80,
        enable_execution=True,
        require_execution=True,
        use_mcp_retrieval=False,
    )
    fallback_calls: list[str] = []

    class FailingAgent:
        def invoke(self, *_args, **_kwargs):
            raise RuntimeError("tool-call protocol failure")

    monkeypatch.setattr(cli_mod, "_config_from_args", lambda args: config)
    monkeypatch.setattr(
        cli_mod,
        "initialize_case_from_tutorial",
        lambda **_kwargs: {"initialized": True, "skipped": False},
    )
    monkeypatch.setattr(cli_mod, "create_principia_agent", lambda _config: FailingAgent())
    monkeypatch.setattr(cli_mod, "write_workflow_evidence", lambda case_path: {"created_at": "test"})
    monkeypatch.setattr(
        cli_mod,
        "validate_workflow_artifacts",
        lambda *args, **kwargs: {"ok": False, "issues": ["missing execution artifacts"]},
    )

    def fake_fallback(config_arg, *, reason: str, timeout_seconds: int):
        fallback_calls.append(reason)
        return {
            "execution": {
                "started": True,
                "return_code": 0,
                "status": {"run_status": "completed", "final_status": "success"},
            },
            "evidence": {"created_at": "fallback"},
            "contract": {"ok": True, "issues": []},
        }

    monkeypatch.setattr(cli_mod, "_apply_execution_fallback", fake_fallback)

    args = argparse.Namespace(
        skip_prepare=False,
        execution_timeout_seconds=30,
        agent_timeout=30,
    )

    assert cli_mod.cmd_run(args) == 0
    assert fallback_calls
    assert "RuntimeError: tool-call protocol failure" in fallback_calls[0]


def test_nested_solver_logs_mark_execution_success(tmp_path: Path) -> None:
    for subcase in ("sector", "building3D"):
        log = tmp_path / subcase / "log.blastFoam"
        log.parent.mkdir(parents=True)
        log.write_text("Time = 0.0001\n\nEnd\n", encoding="utf-8")
    for utility_name in ("blockMesh", "rotateFields"):
        utility_log = tmp_path / "building3D" / f"log.{utility_name}"
        utility_log.write_text("End\n", encoding="utf-8")
    processor_log = tmp_path / "building3D" / "processor0" / "log.blastFoam"
    processor_log.parent.mkdir(parents=True)
    processor_log.write_text("FOAM FATAL ERROR\n", encoding="utf-8")

    solver_logs = resolve_solver_log_paths(tmp_path)
    status = build_execution_status(tmp_path, "completed", "completed")

    assert [path.relative_to(tmp_path).as_posix() for path in solver_logs] == [
        "building3D/log.blastFoam",
        "sector/log.blastFoam",
    ]
    assert solver_log_has_clean_end(tmp_path) is True
    assert status["final_status"] == "success"
    assert status["solver_log_has_clean_end"] is True
    assert status["solver_logs_missing_clean_end"] == []


def test_nested_openfoam_diagnostics_are_blocking(tmp_path: Path) -> None:
    log = tmp_path / "building3D" / "log.blastFoam"
    log.parent.mkdir(parents=True)
    log.write_text("Time = 0.1\nFOAM FATAL ERROR\nbad boundary\n", encoding="utf-8")
    (tmp_path / "physics_report.md").write_text("# Physics\n\n" + "valid content " * 20, encoding="utf-8")
    (tmp_path / "execution_report.md").write_text("# Execution\n\n" + "valid content " * 20, encoding="utf-8")
    write_execution_status(
        tmp_path,
        {
            "schema_version": 1,
            "run_status": "completed",
            "final_status": "success",
        },
    )

    diagnostics = classify_case_openfoam_logs(tmp_path)
    contract = validate_workflow_artifacts(tmp_path, require_execution=True)

    assert summarize_diagnostics(diagnostics)["blocking"] == 1
    assert contract["ok"] is False
    assert "OpenFOAM blocking diagnostics present" in " ".join(contract["issues"])


def test_require_review_needs_explicit_validation_status(tmp_path: Path) -> None:
    (tmp_path / "physics_report.md").write_text("# Physics\n\n" + "valid content " * 20, encoding="utf-8")
    (tmp_path / "review_report.md").write_text(
        "# Review Report\n\n"
        "The generated case has the expected reports and no execution is required for this validation. "
        "This deliberately omits the explicit validation status line so the parser must reject it. "
        "The remaining text is long enough to satisfy the generic report length contract.\n",
        encoding="utf-8",
    )

    contract = validate_workflow_artifacts(tmp_path, require_execution=False, require_review=True)

    assert contract["ok"] is False
    assert contract["checks"]["review_report_valid"] is True
    assert contract["checks"]["validation_status_passed"] is False
    assert "validation_status is not passed: None" in contract["issues"]
