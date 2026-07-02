from __future__ import annotations

import json
from pathlib import Path

from principia_deepagents import legacy_cli


def test_legacy_workflow_maps_old_args_and_prints_completion_marker(monkeypatch, capsys) -> None:
    captured: list[list[str]] = []
    for name in (
        "RETRIEVAL_LLM_ACTIVE_PROFILE",
        "RETRIEVAL_LLM_API_KEY",
        "RETRIEVAL_LLM_API_BASE_URL",
        "RETRIEVAL_LLM_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    def fake_deepagents_main(argv: list[str]) -> int:
        captured.append(argv)
        return 0

    monkeypatch.setattr(legacy_cli, "deepagents_main", fake_deepagents_main)

    return_code = legacy_cli.workflow_main(
        [
            "--case-path",
            "/tmp/case",
            "--user-request",
            "run a smoke case",
            "--tutorial-path",
            "/tmp/tutorials",
            "--llm-active-profile",
            "deepseek_v4_flash",
            "--retrieval-llm-active-profile",
            "deepseek_v4_flash",
            "--retrieval-llm-api-key",
            "retrieval-key",
            "--retrieval-llm-base-url",
            "https://retrieval.example/v1",
            "--retrieval-llm-model",
            "retrieval-model",
            "--recursion-limit",
            "80",
            "--agent-timeout",
            "300",
            "--execution-timeout-seconds",
            "900",
            "--no-mcp",
        ]
    )

    output = capsys.readouterr().out
    assert return_code == 0
    assert captured == [
        [
            "run",
            "--case-path",
            "/tmp/case",
            "--user-request",
            "run a smoke case",
            "--tutorial-path",
            "/tmp/tutorials",
            "--recursion-limit",
            "80",
            "--agent-timeout",
            "300",
            "--execution-timeout-seconds",
            "900",
            "--llm-active-profile",
            "deepseek_v4_flash",
            "--retrieval-llm-active-profile",
            "deepseek_v4_flash",
            "--no-mcp",
        ]
    ]
    assert "Workflow reached completion state" in output
    assert "Workflow Run Test Passed" in output
    assert legacy_cli.os.environ["RETRIEVAL_LLM_API_KEY"] == "retrieval-key"
    assert legacy_cli.os.environ["RETRIEVAL_LLM_API_BASE_URL"] == "https://retrieval.example/v1"
    assert legacy_cli.os.environ["RETRIEVAL_LLM_MODEL"] == "retrieval-model"


def test_legacy_workflow_prints_failure_marker(monkeypatch, capsys) -> None:
    monkeypatch.setattr(legacy_cli, "deepagents_main", lambda _argv: 1)

    return_code = legacy_cli.workflow_main(["--case-path", "/tmp/case"])

    output = capsys.readouterr().out
    assert return_code == 1
    assert "Workflow Run Test Failed" in output
    assert "Workflow Run Test Passed" not in output


def test_legacy_batch_writes_old_style_results(tmp_path: Path, monkeypatch) -> None:
    modifications = [
        {
            "case_path": "freeField",
            "case_name": "freeField_charge_50kg",
            "modified_files": ["system/setFieldsDict"],
            "description": "Simulate a free-field explosion.",
            "modification": "Change charge mass to 50 kg.",
        },
        {
            "case_path": "building3D",
            "case_name": "building3D_short",
            "modified_files": ["system/controlDict"],
            "description": "Run a short building case.",
            "modification": "Set endTime to 0.0005.",
        },
    ]
    modifications_file = tmp_path / "mods.json"
    modifications_file.write_text(json.dumps(modifications), encoding="utf-8")
    output_base = tmp_path / "outputs"
    results_file = tmp_path / "batch_results.json"
    workflow_calls: list[list[str]] = []

    def fake_workflow_main(argv: list[str]) -> int:
        workflow_calls.append(argv)
        return 0

    monkeypatch.setattr(legacy_cli, "workflow_main", fake_workflow_main)

    return_code = legacy_cli.batch_main(
        [
            "--modifications-file",
            str(modifications_file),
            "--output-base-dir",
            str(output_base),
            "--results-file",
            str(results_file),
            "--tutorial-path",
            "/tmp/tutorials",
            "--recursion-limit",
            "20",
            "--agent-timeout",
            "60",
            "--no-mcp",
        ]
    )

    payload = json.loads(results_file.read_text(encoding="utf-8"))
    assert return_code == 0
    assert len(workflow_calls) == 2
    assert payload["total_cases"] == 2
    assert payload["summary"] == {"success": 2, "failed": 0, "incomplete": 0}
    assert payload["results"][0]["status"] == "success"
    assert payload["results"][0]["case_path"] == str(output_base / "freeField_charge_50kg")
    assert "--user-request" in workflow_calls[0]
    request_value = workflow_calls[0][workflow_calls[0].index("--user-request") + 1]
    assert "Change charge mass to 50 kg." in request_value
    assert "--no-mcp" in workflow_calls[0]
