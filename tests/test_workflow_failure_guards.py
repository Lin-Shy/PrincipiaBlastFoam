import threading
import time
from dataclasses import dataclass

from principia_ai.agents.orchestrator import OrchestratorAgent
from principia_ai.agents.execution_agent import ExecutionAgent
from principia_ai.agents.reviewer import ReviewerAgent
from principia_ai.tools.tutorial_initializer import TutorialInitializer
from principia_ai.utils.execution_status import build_execution_status, status_run_completed
from principia_ai.utils.solver_logs import resolve_solver_log_paths, solver_log_has_clean_end


@dataclass
class FakeResponse:
    content: str
    usage_metadata: dict | None = None


class FakeLLM:
    model_name = "fake-model"

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def invoke(self, _messages):
        if self.error:
            raise self.error
        return self.response


class EmptyAgent:
    def invoke(self, _payload):
        return {"output": ""}


def test_tutorial_initializer_accepts_missing_usage_metadata():
    cases = [
        {
            "path": "/tmp/solids4Foam/flap",
            "relative_path": "solids4Foam/flap",
            "description": "solid flap case",
            "readme_content": "",
        },
        {
            "path": "/tmp/blastFoam/axisymmetricCharge",
            "relative_path": "blastFoam/axisymmetricCharge",
            "description": "axisymmetric charge blastFoam case",
            "readme_content": "Axisymmetric charge",
        },
    ]

    initializer = TutorialInitializer(FakeLLM(FakeResponse("[1]", usage_metadata=None)))

    selected = initializer.find_relevant_tutorial_cases("触地 地表 爆炸 axisymmetricCharge", cases, top_k=1)

    assert selected[0]["relative_path"] == "blastFoam/axisymmetricCharge"


def test_tutorial_initializer_does_not_fallback_to_first_unrelated_case():
    cases = [
        {
            "path": "/tmp/solids4Foam/flap",
            "relative_path": "solids4Foam/flap",
            "description": "solid flap case",
            "readme_content": "",
        },
        {
            "path": "/tmp/blastFoam/building3D",
            "relative_path": "blastFoam/building3D",
            "description": "building blast loading case",
            "readme_content": "Building 3D blast case",
        },
    ]

    initializer = TutorialInitializer(FakeLLM(error=RuntimeError("provider error")))

    selected = initializer.find_relevant_tutorial_cases("建筑 外立面 冲击 pressure probe", cases, top_k=1)

    assert selected[0]["relative_path"] == "blastFoam/building3D"


def test_orchestrator_empty_output_marks_workflow_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_EXECUTION", "false")

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator.agent = EmptyAgent()

    result = orchestrator.route(
        {
            "user_request": "run a smoke test",
            "case_path": str(tmp_path),
            "plan": None,
            "completed_tasks": [],
        }
    )

    assert result["current_agent"] == "end"
    assert result["run_status"] == "failed"
    assert "no parseable JSON" in result["workflow_error"]


def test_orchestrator_fails_fast_after_execution_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_EXECUTION", "true")
    monkeypatch.delenv("AUTO_REPAIR_EXECUTION_FAILURES", raising=False)

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)

    result = orchestrator.route(
        {
            "user_request": "run a smoke test",
            "case_path": str(tmp_path),
            "plan": "run the case",
            "run_status": "failed",
            "completed_tasks": [
                {"assigned_agent": "execution_agent", "status": "failed"},
            ],
        }
    )

    assert result["current_agent"] == "end"
    assert result["run_status"] == "failed"
    assert "execution_status.json marked execution failed" in result["workflow_error"]


def test_orchestrator_routes_execution_before_pending_physics_update(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_EXECUTION", "true")
    monkeypatch.setenv("ASYNC_PHYSICS_UPDATE_WITH_EXECUTION", "true")

    (tmp_path / "physics_report.md").write_text("physics report", encoding="utf-8")

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)

    result = orchestrator.route(
        {
            "user_request": "run a smoke test",
            "case_path": str(tmp_path),
            "plan": "run the case",
            "needs_physics_update": True,
            "completed_tasks": [
                {"assigned_agent": "case_setup_agent", "status": "completed"},
            ],
        }
    )

    assert result["current_agent"] == "execution_agent"
    assert result["needs_physics_update"] is False
    assert result["physics_update_status"] == "deferred_for_execution"


def test_async_physics_update_runner_receives_changed_files(tmp_path):
    finished = threading.Event()
    seen_changed_files = []

    def fake_runner(state):
        seen_changed_files.append(state["changed_files"])
        finished.set()

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator._async_physics_update_runner = fake_runner
    orchestrator._active_async_physics_updates = set()

    started = orchestrator._start_async_physics_update(
        {"case_path": str(tmp_path), "user_request": "update report"},
        ["system/controlDict"],
    )

    assert started is True
    assert finished.wait(timeout=2)
    assert seen_changed_files == [["system/controlDict"]]
    deadline = time.time() + 2
    while str(tmp_path) in orchestrator._active_async_physics_updates and time.time() < deadline:
        time.sleep(0.01)
    assert str(tmp_path) not in orchestrator._active_async_physics_updates


def test_physics_change_filter_ignores_runtime_outputs():
    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)

    relevant, ignored = orchestrator._filter_physics_relevant_changes(
        [
            "system/controlDict",
            "constant/thermophysicalProperties",
            "0/U",
            "constant/polyMesh/boundary",
            "postProcessing/probes/0/p",
            "processor0/0/U",
            "0.0005/U",
            "log.sonicFoam",
        ]
    )

    assert relevant == ["0/U", "constant/thermophysicalProperties", "system/controlDict"]
    assert "constant/polyMesh/boundary" in ignored
    assert "postProcessing/probes/0/p" in ignored
    assert "log.sonicFoam" in ignored


def test_solver_log_detection_uses_current_case_application(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text("application sonicFoam;\n", encoding="utf-8")

    (tmp_path / "log.blockMesh").write_text("Mesh ok\nEnd\n", encoding="utf-8")

    assert resolve_solver_log_paths(tmp_path) == []
    assert not solver_log_has_clean_end(tmp_path)

    suffix_log = tmp_path / "log.sonicFoam.1"
    suffix_log.write_text("Solver ok\nEnd\n", encoding="utf-8")

    assert resolve_solver_log_paths(tmp_path) == [suffix_log]
    assert solver_log_has_clean_end(tmp_path)

    suffix_log.unlink()
    solver_log = tmp_path / "log.sonicFoam"
    solver_log.write_text("Solver ok\nEnd\n", encoding="utf-8")

    assert resolve_solver_log_paths(tmp_path) == [solver_log]
    assert solver_log_has_clean_end(tmp_path)


def test_execution_status_parser_ignores_negated_error_mentions():
    agent = ExecutionAgent.__new__(ExecutionAgent)

    status = agent._parse_execution_status(
        "Execution completed successfully.\n\nThe run completed without runtime errors."
    )

    assert status == "completed"


def test_execution_status_uses_current_solver_log_over_handled_failure_text(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text("application blastFoam;\n", encoding="utf-8")
    (tmp_path / "log.blastFoam").write_text("Earlier output\nEnd\n", encoding="utf-8")

    status = build_execution_status(
        tmp_path,
        "First execution failed due to mpirun missing.\nSecond execution completed successfully.",
        parsed_report_status="failed",
    )

    assert status_run_completed(status)
    assert status["status_source"] == "solver_log"


def test_execution_status_rejects_success_text_without_solver_end(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text("application blastFoam;\n", encoding="utf-8")
    (tmp_path / "log.blastFoam").write_text("FOAM FATAL ERROR\n", encoding="utf-8")

    status = build_execution_status(
        tmp_path,
        "Execution completed successfully.",
        parsed_report_status="completed",
    )

    assert not status_run_completed(status)
    assert status["run_status"] == "failed"
    assert status["status_source"] == "solver_log_guard"


def test_benchmark_wraps_workflow_command_for_non_root_user(monkeypatch):
    from experiments.end2end import run_agent_benchmark

    monkeypatch.setattr(run_agent_benchmark.os, "geteuid", lambda: 0)

    command = run_agent_benchmark.wrap_command_for_user("echo hello", "openfoam")

    assert command == "runuser -u openfoam -- bash -lc 'echo hello'"


def test_reviewer_status_parser_uses_explicit_status_line():
    agent = ReviewerAgent.__new__(ReviewerAgent)

    status = agent._parse_validation_status(
        "Validation Status: Passed\n\nGeneral Findings:\nNo FOAM FATAL ERROR was observed."
    )

    assert status == "passed"
