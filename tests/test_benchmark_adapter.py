from __future__ import annotations

import sys
from pathlib import Path

from experiments.end2end.run_deepagents_benchmark import (
    collect_summary,
    command_for_case,
    model_profile_metadata,
    parse_control_end_time_from_text,
    result_passed,
    run_command,
)


def _write_control(path: Path, end_time: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "application blastFoam;",
                "stopAt endTime;",
                f"endTime {end_time};",
                "writeInterval 0.0001;",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_parse_control_end_time_accepts_openfoam_leading_decimal() -> None:
    assert parse_control_end_time_from_text("endTime .02;") == 0.02


def test_benchmark_command_prefers_model_profile_over_legacy_profile(tmp_path: Path) -> None:
    args = type(
        "Args",
        (),
        {
            "workflow_mode": "run",
            "tutorial_path": tmp_path / "tutorials",
            "no_mcp": False,
            "env_file": None,
            "model_profile": "minimax_m27",
            "llm_active_profile": "deepseek_v4_flash",
            "retrieval_llm_active_profile": None,
            "recursion_limit": 80,
            "agent_timeout": 300,
            "execution_timeout_seconds": 900,
            "force_prepare": False,
            "skip_prepare": False,
        },
    )()

    command = command_for_case(args, tmp_path / "case", "run a case")

    assert "--model-profile" in command
    assert command[command.index("--model-profile") + 1] == "minimax_m27"
    assert "--llm-active-profile" not in command


def test_benchmark_model_profile_metadata_omits_secret_value(monkeypatch) -> None:
    monkeypatch.setenv("MINIMAX_API_KEY", "secret-value")
    args = type(
        "Args",
        (),
        {
            "model_profile": "minimax_m27",
            "llm_active_profile": None,
            "retrieval_llm_active_profile": "deepseek_v4_flash",
        },
    )()

    metadata = model_profile_metadata(args)

    assert metadata["resolved_profile"]["id"] == "minimax_m27"
    assert metadata["resolved_profile"]["selected_api_key_env"] == "MINIMAX_API_KEY"
    assert "secret-value" not in str(metadata)


def test_collect_summary_uses_nested_control_dict_max_end_time(tmp_path: Path) -> None:
    _write_control(tmp_path / "sector" / "system" / "controlDict", "0.001")
    _write_control(tmp_path / "building3D" / "system" / "controlDict", "0.0015")
    (tmp_path / "building3D" / "processor0" / "0.0015").mkdir(parents=True)
    (tmp_path / "artifact_contract.json").write_text('{"ok": true}\n', encoding="utf-8")
    (tmp_path / "post_processing_report.md").write_text("# Post-Processing Report\n\nnested output\n", encoding="utf-8")
    log = tmp_path / "case.log"
    log.write_text("Initialized from blastFoam/mappedBuilding3D\n", encoding="utf-8")

    summary = collect_summary(
        tmp_path,
        log,
        {"max_end_time": 0.0015, "preferred_case_keywords": ["mappedBuilding3D"]},
    )

    assert summary["configured_end_time"] == 0.0015
    assert summary["configured_end_times"] == {
        "building3D/system/controlDict": 0.0015,
        "sector/system/controlDict": 0.001,
    }
    assert summary["time_dir_count"] == 1
    assert summary["time_dir_locations"][0]["path"] == "building3D/processor0/0.0015"
    assert summary["reports"]["post_processing_report.md"] is True
    assert summary["checks"]["end_time_within_expected"] is True


def test_run_result_fails_when_expected_end_time_is_unparseable() -> None:
    result = {
        "workflow_mode": "run",
        "run": {"dry_run": False, "exit_code": 0, "timed_out": False},
        "summary": {
            "checks": {
                "selected_tutorial_matches_expected": True,
                "end_time_within_expected": None,
                "artifact_contract_ok": True,
            }
        },
    }

    assert result_passed(result) is False


def test_run_command_timeout_marks_timeout_and_kills_process_group(tmp_path: Path) -> None:
    result = run_command(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        tmp_path / "timeout.log",
        timeout=1,
        dry_run=False,
        enable_execution=False,
        execution_user=None,
        chown_case=False,
    )

    assert result["timed_out"] is True
    assert result["exit_code"] != 0
