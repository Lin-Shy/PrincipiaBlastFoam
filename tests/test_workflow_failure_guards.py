import threading
import time
import subprocess
from dataclasses import dataclass

import pytest
from langchain.schema import AIMessage

from principia_ai.agents.orchestrator import OrchestratorAgent
from principia_ai.agents.execution_agent import ExecutionAgent
from principia_ai.agents.reviewer import ReviewerAgent
from principia_ai.agents.workflow import WorkflowApp, _checkpointing_enabled
from principia_ai.agents.orchestrator import RouteDecision
from principia_ai.tools.context import scoped_tool_context
from principia_ai.tools.read.read_file import read_file
from principia_ai.tools.search.get_changes import get_changes
from principia_ai.tools.mcp_retrieval_tools import _filter_adapter_tools
from principia_ai.tools.tutorial_initializer import TutorialInitializer
from principia_ai.utils.redaction import filter_sensitive_diff, is_sensitive_path, redact_text
from principia_ai.utils.execution_status import build_execution_status, status_run_completed
from principia_ai.utils.execution_preflight import run_execution_preflight
from principia_ai.utils.llm_profiles import chat_openai_kwargs, resolve_llm_profile
from principia_ai.utils.postprocessing_contracts import validate_post_processing_output
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


class StructuredDecisionLLM:
    model_name = "structured-test-model"

    def with_structured_output(self, _schema):
        return self

    def invoke(self, _messages):
        return RouteDecision(
            next_agent="case_setup_agent",
            task_instructions="Update system/controlDict only.",
        )


class StructuredResponseLLM:
    model_name = "structured-response-test-model"

    def __init__(self, response):
        self.response = response

    def with_structured_output(self, _schema):
        return self

    def invoke(self, _messages):
        return self.response


class JsonObjectRouteLLM:
    model_name = "deepseek-v4-pro"

    def __init__(self):
        self.metadata = {
            "principia_llm_profile": {
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
                "base_url": "https://api.deepseek.com/v1",
                "structured_output": "json_object",
                "thinking": "disabled",
                "thinking_disabled_extra_body": {"thinking": {"type": "disabled"}},
                "thinking_enabled_extra_body": {"thinking": {"type": "enabled"}},
                "reasoning_roundtrip": False,
            }
        }
        self.response_format = None
        self.structured_requested = False

    def with_structured_output(self, _schema):
        self.structured_requested = True
        raise AssertionError("json_object profile should not request json_schema binding")

    def invoke(self, _messages, **kwargs):
        self.response_format = kwargs.get("response_format")
        return AIMessage(content='{"next_agent": "physics", "task_instructions": "Analyze physics."}')


class ExplodingAgent:
    def invoke(self, _payload):
        raise AssertionError("legacy orchestrator agent should not be called")


class DummyWorkflow:
    def invoke(self, _input_state, config=None, *_args, **_kwargs):
        return config


class DummyTool:
    def __init__(self, name):
        self.name = name


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


def test_llm_profile_disables_thinking_for_reasoning_providers(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_THINKING", raising=False)
    monkeypatch.delenv("LLM_STRUCTURED_OUTPUT", raising=False)

    deepseek_kwargs = chat_openai_kwargs(
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-pro",
        api_key="test",
    )
    qwen_kwargs = chat_openai_kwargs(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen3.6-plus",
        api_key="test",
    )
    glm_kwargs = chat_openai_kwargs(
        base_url="https://open.bigmodel.cn/api/paas/v4",
        model="glm-4.7",
        api_key="test",
    )

    assert deepseek_kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
    assert qwen_kwargs["extra_body"] == {"enable_thinking": False}
    assert glm_kwargs["extra_body"] == {"thinking": {"type": "disabled"}}
    assert deepseek_kwargs["metadata"]["principia_llm_profile"]["structured_output"] == "json_object"


def test_llm_profile_allows_env_overrides(monkeypatch):
    monkeypatch.setenv("LLM_THINKING", "enabled")
    monkeypatch.setenv("LLM_STRUCTURED_OUTPUT", "prompt_only")

    profile = resolve_llm_profile("https://api.deepseek.com/v1", "deepseek-v4-pro")
    kwargs = chat_openai_kwargs(
        base_url="https://api.deepseek.com/v1",
        model="deepseek-v4-pro",
        api_key="test",
    )

    assert profile.thinking == "enabled"
    assert profile.structured_output == "prompt_only"
    assert kwargs["extra_body"] == {"thinking": {"type": "enabled"}}


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


def test_orchestrator_structured_decision_path(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_STRUCTURED_OUTPUT", "true")

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator.llm = StructuredDecisionLLM()
    orchestrator.system_prompt = "route tasks"
    orchestrator.agent = EmptyAgent()

    decision, raw_output = orchestrator._invoke_route_decision([], "decide next")

    assert decision.next_agent == "case_setup_agent"
    assert decision.task_instructions == "Update system/controlDict only."
    assert "case_setup_agent" in raw_output


def test_orchestrator_structured_decision_accepts_message_content(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_STRUCTURED_OUTPUT", "true")

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator.llm = StructuredResponseLLM(
        AIMessage(content='{"next_agent": "FINISH", "task_instructions": ""}')
    )
    orchestrator.system_prompt = "route tasks"
    orchestrator.agent = ExplodingAgent()

    decision, raw_output = orchestrator._invoke_route_decision([], "decide next")

    assert decision.next_agent == "end"
    assert "end" in raw_output


def test_orchestrator_structured_decision_accepts_tool_call_arguments(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_STRUCTURED_OUTPUT", "true")

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator.llm = StructuredResponseLLM(
        AIMessage(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "function": {
                            "arguments": (
                                '{"next_agent": "review", '
                                '"task_instructions": "Validate execution outputs."}'
                            )
                        }
                    }
                ]
            },
        )
    )
    orchestrator.system_prompt = "route tasks"
    orchestrator.agent = ExplodingAgent()

    decision, _raw_output = orchestrator._invoke_route_decision([], "decide next")

    assert decision.next_agent == "reviewer"
    assert decision.task_instructions == "Validate execution outputs."


def test_orchestrator_structured_decision_accepts_content_blocks(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_STRUCTURED_OUTPUT", "true")

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator.llm = StructuredResponseLLM(
        AIMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        "```json\n"
                        '{"next_agent": "case-setup", "task_instructions": "Prepare controlDict."}'
                        "\n```"
                    ),
                }
            ]
        )
    )
    orchestrator.system_prompt = "route tasks"
    orchestrator.agent = ExplodingAgent()

    decision, _raw_output = orchestrator._invoke_route_decision([], "decide next")

    assert decision.next_agent == "case_setup_agent"
    assert decision.task_instructions == "Prepare controlDict."


def test_orchestrator_json_object_profile_avoids_schema_binding(monkeypatch):
    monkeypatch.delenv("LLM_STRUCTURED_OUTPUT", raising=False)
    monkeypatch.setenv("ORCHESTRATOR_STRUCTURED_OUTPUT", "true")

    llm = JsonObjectRouteLLM()
    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator.llm = llm
    orchestrator.system_prompt = "route tasks"
    orchestrator.agent = ExplodingAgent()

    decision, raw_output = orchestrator._invoke_route_decision([], "decide next")

    assert decision.next_agent == "physics_analyst_agent"
    assert decision.task_instructions == "Analyze physics."
    assert llm.response_format == {"type": "json_object"}
    assert llm.structured_requested is False
    assert "physics" in raw_output


def test_orchestrator_rejects_unknown_route_target():
    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)

    with pytest.raises(ValueError, match="unknown next_agent"):
        orchestrator._coerce_route_decision(
            {"next_agent": "shell_agent", "task_instructions": "Run a shell command."}
        )


def test_orchestrator_can_disable_legacy_fallback(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_STRUCTURED_OUTPUT", "true")
    monkeypatch.setenv("ORCHESTRATOR_LEGACY_FALLBACK", "false")

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    orchestrator.llm = StructuredResponseLLM(AIMessage(content="not json"))
    orchestrator.system_prompt = "route tasks"
    orchestrator.agent = ExplodingAgent()

    with pytest.raises(ValueError, match="no parseable JSON"):
        orchestrator._invoke_route_decision([], "decide next")


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


def test_workflow_app_adds_default_thread_id():
    wrapped = WorkflowApp(DummyWorkflow(), checkpointing_enabled=True)

    config = wrapped.invoke({"task_id": "task-123"}, {"recursion_limit": 12})

    assert config["recursion_limit"] == 12
    assert config["configurable"]["thread_id"] == "task-123"


def test_checkpointing_explicit_string_false_disables_checkpointer():
    assert _checkpointing_enabled("false") is False
    assert _checkpointing_enabled("0") is False
    assert _checkpointing_enabled("true") is True


def test_mcp_adapter_tool_filter_respects_retriever_flags():
    tools = [
        DummyTool("principia_retrieval__get_case_by_intent"),
        DummyTool("search_user_guide"),
        DummyTool("get_status"),
    ]

    tutorial_only = _filter_adapter_tools(
        tools,
        use_knowledge_manager=False,
        use_tutorial_retriever=True,
    )
    guide_only = _filter_adapter_tools(
        tools,
        use_knowledge_manager=True,
        use_tutorial_retriever=False,
    )

    assert [tool.name for tool in tutorial_only] == ["principia_retrieval__get_case_by_intent"]
    assert [tool.name for tool in guide_only] == ["search_user_guide"]


def test_secret_redaction_masks_common_secret_shapes():
    secret_value = "sk-" + "x" * 24
    text = (
        f"OPENAI_API_KEY={secret_value}\n"
        '{"api_key": "another-secret-value"}\n'
        "{'access_token': 'single-quoted-secret'}\n"
        '{"auth": "auth-secret"}\n'
        "Authorization: Bearer abcdefghijklmnop123456\n"
    )

    redacted = redact_text(text)

    assert "secret-value" not in redacted
    assert "single-quoted-secret" not in redacted
    assert "auth-secret" not in redacted
    assert "abcdefghijklmnop" not in redacted
    assert '{"api_key": "<REDACTED>"}' in redacted
    assert "{'access_token': '<REDACTED>'}" in redacted
    assert '{"auth": "<REDACTED>"}' in redacted
    assert "Authorization: Bearer <REDACTED>" in redacted
    assert redacted.count("<REDACTED>") == 5


def test_sensitive_env_diff_is_removed():
    env_name = "." + "env"
    secret_value = "sk-" + "x" * 24
    diff = (
        f"diff --git a/{env_name} b/{env_name}\n"
        f"--- a/{env_name}\n"
        f"+++ b/{env_name}\n"
        f"+OPENAI_API_KEY={secret_value}\n"
        "diff --git a/principia_ai/example.py b/principia_ai/example.py\n"
        "--- a/principia_ai/example.py\n"
        "+++ b/principia_ai/example.py\n"
        "+TOKEN = 'should-still-redact'\n"
        "+print('safe')\n"
    )

    filtered = filter_sensitive_diff(diff)

    assert ".env" not in filtered
    assert secret_value not in filtered
    assert "should-still-redact" not in filtered
    assert "+TOKEN = <REDACTED>" in filtered
    assert "+print('safe')" in filtered


def test_read_file_refuses_sensitive_env_file(tmp_path):
    env_file = tmp_path / ".env"
    secret_value = "sk-" + "x" * 24
    env_file.write_text(f"OPENAI_API_KEY={secret_value}\n", encoding="utf-8")

    assert is_sensitive_path(env_file)
    output = read_file.invoke({"path": str(env_file)})

    assert "Refusing to read sensitive file" in output
    assert secret_value not in output


def test_read_file_resolves_case_relative_path(tmp_path):
    control_dict = tmp_path / "system" / "controlDict"
    control_dict.parent.mkdir()
    control_dict.write_text("application blastFoam;\n", encoding="utf-8")

    with scoped_tool_context(tmp_path):
        output = read_file.invoke({"path": "system/controlDict"})

    assert "application blastFoam;" in output


def test_get_changes_is_scoped_to_active_case(tmp_path):
    repo = tmp_path / "repo"
    case_dir = repo / "cases" / "active"
    system_dir = case_dir / "system"
    system_dir.mkdir(parents=True)
    (repo / "unrelated.txt").write_text("before\n", encoding="utf-8")
    control_dict = system_dir / "controlDict"
    control_dict.write_text("application blastFoam;\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)

    (repo / "unrelated.txt").write_text("after\n", encoding="utf-8")
    control_dict.write_text("application sonicFoam;\n", encoding="utf-8")

    with scoped_tool_context(case_dir):
        output = get_changes.invoke({})

    assert "cases/active/system/controlDict" in output
    assert "unrelated.txt" not in output


def test_get_changes_hides_repo_diff_without_scope():
    output = get_changes.invoke({})

    assert "repository-wide git diff is hidden" in output


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


def test_execution_preflight_blocks_parallel_without_mpi(tmp_path, monkeypatch):
    import principia_ai.utils.execution_preflight as preflight

    (tmp_path / "Allrun").write_text("runParallel blastFoam\n", encoding="utf-8")
    monkeypatch.setattr(preflight.shutil, "which", lambda _command: None)

    status = run_execution_preflight(tmp_path)

    assert not status["ok"]
    assert "mpirun" in status["blockers"][0]


def test_post_processing_contract_rejects_missing_pressure_probe_field(tmp_path):
    probe_dir = tmp_path / "postProcessing" / "pressureProbes" / "0"
    probe_dir.mkdir(parents=True)
    (probe_dir / "U").write_text("# velocity data\n", encoding="utf-8")

    status = validate_post_processing_output(
        tmp_path,
        'calculateImpulse -p p pressureProbes\n"p" was not found in "postProcessing/pressureProbes"',
    )

    assert not status["ok"]
    assert any("calculateImpulse" in issue for issue in status["issues"])
    assert any("available probe fields are: U" in issue for issue in status["issues"])


def test_workflow_failure_preserves_completed_solver_status(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_EXECUTION", "true")
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text("application blastFoam;\n", encoding="utf-8")
    (tmp_path / "log.blastFoam").write_text("Solver ok\nEnd\n", encoding="utf-8")
    execution_status = build_execution_status(tmp_path, "Execution completed successfully.", "completed")

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)

    result = orchestrator.route(
        {
            "user_request": "run a smoke test",
            "case_path": str(tmp_path),
            "plan": "run the case",
            "execution_status": execution_status,
            "run_status": "completed",
            "validation_status": "failed",
            "completed_tasks": [
                {"assigned_agent": "execution_agent", "status": "completed"},
                {"assigned_agent": "reviewer", "status": "completed"},
            ],
        }
    )

    assert result["workflow_status"] == "failed"
    assert result["run_status"] == "completed"
    assert "reviewer marked validation as failed" in result["workflow_error"]


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
