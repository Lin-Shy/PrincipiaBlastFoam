import threading
import time
import subprocess
from dataclasses import dataclass

import pytest
from langchain.schema import AIMessage

from principia_ai.agents.orchestrator import OrchestratorAgent
from principia_ai.agents.execution_agent import ExecutionAgent
from principia_ai.agents.physics_analyst_agent import PhysicsAnalystAgent
from principia_ai.agents.reviewer import ReviewerAgent
from principia_ai.agents.workflow import WorkflowApp, _checkpointing_enabled
from principia_ai.agents.orchestrator import RouteDecision
from principia_ai.tools.context import scoped_tool_context
from principia_ai.tools.read.read_file import read_file
from principia_ai.tools.search.file_search import file_search
from principia_ai.tools.search.get_changes import get_changes
from principia_ai.tools.search.text_search import text_search
from principia_ai.tools.mcp_retrieval_tools import _filter_adapter_tools
from principia_ai.tools.tutorial_initializer import TutorialInitializer
from principia_ai.utils.redaction import filter_sensitive_diff, is_sensitive_path, redact_text
from principia_ai.utils.execution_status import build_execution_status, status_run_completed, write_execution_status
from principia_ai.utils.execution_preflight import run_execution_preflight
from principia_ai.utils.llm_profiles import chat_openai_kwargs, resolve_llm_profile
from principia_ai.utils.openfoam_diagnostics import classify_openfoam_log_text, summarize_diagnostics
from principia_ai.utils.postprocessing_contracts import validate_post_processing_output
from principia_ai.utils.report_contracts import validate_agent_report
from principia_ai.utils.solver_logs import resolve_solver_log_paths, solver_log_has_clean_end
from principia_ai.utils.workflow_artifacts import validate_workflow_artifacts
from principia_ai.utils.workflow_evidence import write_workflow_evidence


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


class SequentialAgent:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.inputs = []

    def invoke(self, payload):
        self.inputs.append(payload.get("input", ""))
        if not self.outputs:
            return {"output": ""}
        return {"output": self.outputs.pop(0)}


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


def test_post_processing_contract_accepts_successful_calculate_impulse(tmp_path):
    probe_dir = tmp_path / "postProcessing" / "pressureProbes" / "0"
    probe_dir.mkdir(parents=True)
    (probe_dir / "p").write_text("0 101298\n", encoding="utf-8")
    (probe_dir / "impulse").write_text("0 0\n", encoding="utf-8")

    status = validate_post_processing_output(
        tmp_path,
        'Exec   : calculateImpulse pressureProbes\nUsing "p" in "postProcessing/pressureProbes/0"\nDone.\n',
    )

    assert status["ok"]
    assert status["issues"] == []


def test_openfoam_diagnostics_classifies_dynamicp_as_nonblocking():
    diagnostics = classify_openfoam_log_text(
        "--> FOAM Warning :     functionObjects::fieldMinMax fieldMinMax cannot find required object dynamicP\n"
        "Selected 0 cells for refinement out of 712.\n",
        source="log.blastFoam",
    )

    assert diagnostics
    assert diagnostics[0].severity == "nonblocking_warning"
    assert diagnostics[0].category == "derived_field_unavailable"
    assert diagnostics[0].blocking is False
    assert "final field" in diagnostics[0].hint


def test_openfoam_diagnostics_classifies_probe_relocation_as_nonblocking():
    diagnostics = classify_openfoam_log_text(
        "--> FOAM Warning : \n"
        "    From function virtual void Foam::blastProbes::findElements(const Foam::fvMesh&, bool, bool)\n"
        "    in file blastProbes/blastProbes.C at line 153\n"
        "    Did not find location (2 0 0.5) in any cell. Skipping location.\n"
        "\n"
        "4 blastProbes were not found in any domain.\n"
        "These blastProbes are being moved to the nearest patch face.\n",
        source="log.blastFoam",
    )

    assert diagnostics
    assert diagnostics[0].severity == "nonblocking_warning"
    assert diagnostics[0].category == "probe_location_adjusted"
    assert diagnostics[0].blocking is False


def test_openfoam_diagnostics_classifies_charge_mass_discretization_warning():
    diagnostics = classify_openfoam_log_text(
        "--> FOAM Warning :\n"
        "From function void Foam::massToCell::checkMass(const labelHashSet&, const Foam::polyMesh&) const\n"
        "Requested mass is 10 but set mass is 16.01, 60.1% different\n",
        source="log.setRefinedFields",
    )

    assert diagnostics
    assert diagnostics[0].severity == "warning"
    assert diagnostics[0].category == "charge_mass_discretization"
    assert diagnostics[0].blocking is False


def test_openfoam_diagnostics_marks_fatal_as_blocking():
    diagnostics = classify_openfoam_log_text(
        "Time = 0.1\n"
        "FOAM FATAL ERROR:\n"
        "Cannot find patchField entry for inlet\n"
        "FOAM exiting\n",
        source="log.blastFoam",
    )
    summary = summarize_diagnostics([item.to_dict() for item in diagnostics])

    assert any(item.blocking for item in diagnostics)
    assert summary["blocking"] >= 1
    assert summary["fatal"] >= 1


def test_openfoam_diagnostics_classifies_parallel_internal_patch_fatal():
    diagnostics = classify_openfoam_log_text(
        "[0] --> FOAM FATAL ERROR:\n"
        "[0] When balancing is enabled, an internal patch should be added to the mesh.\n"
        "[0] To add the necessary patch to the mesh and the fields, use the command\n",
        source="log.blastFoam",
    )

    assert diagnostics
    assert diagnostics[0].category == "parallel_internal_patch_missing"
    assert diagnostics[0].blocking is True


def test_openfoam_diagnostics_classifies_field_dictionary_type_fatal():
    diagnostics = classify_openfoam_log_text(
        "[2] --> FOAM FATAL IO ERROR:\n"
        "[2] Expected a '(' while reading VectorSpace<Form, Cmpt, Ncmpts>, found on line 34 the word 'uniform'\n"
        "[2] file: processor2/0/U/boundaryField/outlet/fieldInf at line 34.\n",
        source="log.addEmptyPatch",
    )

    assert diagnostics
    assert diagnostics[0].category == "field_dictionary_type_mismatch"
    assert diagnostics[0].blocking is True


def test_openfoam_diagnostics_classifies_blast_function_library_warning():
    diagnostics = classify_openfoam_log_text(
        "--> FOAM Warning :\n"
        "    dlopen error : libblastFunctionObject.so: cannot open shared object file: No such file or directory\n"
        "--> FOAM Warning :\n"
        "    could not load \"libblastFunctionObject.so\"\n",
        source="log.blastFoam",
    )

    assert diagnostics
    assert any(item.category == "blast_function_library_unavailable" for item in diagnostics)
    assert all(item.blocking is False for item in diagnostics)


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

    assert command == (
        "runuser -u openfoam -- env LANG=C.utf8 LC_ALL=C.utf8 "
        "PYTHONUTF8=1 PYTHONIOENCODING=utf-8 bash -lc 'echo hello'"
    )


def test_benchmark_subprocess_env_forces_utf8_locale(monkeypatch):
    from experiments.end2end import run_agent_benchmark

    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv("LC_ALL", "C")

    env = run_agent_benchmark.workflow_subprocess_env()

    assert env["LANG"] == "C.utf8"
    assert env["LC_ALL"] == "C.utf8"
    assert env["PYTHONUTF8"] == "1"
    assert env["PYTHONIOENCODING"] == "utf-8"


def test_reviewer_status_parser_uses_explicit_status_line():
    agent = ReviewerAgent.__new__(ReviewerAgent)

    status = agent._parse_validation_status(
        "Validation Status: Passed\n\nGeneral Findings:\nNo FOAM FATAL ERROR was observed."
    )

    assert status == "passed"


def test_reviewer_status_parser_accepts_markdown_and_nonblocking_issue_text():
    agent = ReviewerAgent.__new__(ReviewerAgent)

    status = agent._parse_validation_status(
        "## Validation Status: **Passed**\n\n"
        "## Issues:\n"
        "- A probe file was not found, but this is not a configuration error and is non-blocking.\n"
    )

    assert status == "passed"


def test_reviewer_status_parser_detects_explicit_failed_status():
    agent = ReviewerAgent.__new__(ReviewerAgent)

    status = agent._parse_validation_status(
        "**Validation Status**: failed\n\n"
        "The execution status did not mark the run completed."
    )

    assert status == "failed"


def test_report_contract_rejects_placeholder_and_raw_tool_output():
    placeholder = validate_agent_report("Sorry, need more steps to process this request.", "review_report")
    raw_tool = validate_agent_report(
        "--- Retrieved Documentation Information ---\n\n## Section 15.11 impulse\nraw docs",
        "physics_report",
    )

    assert not placeholder["valid"]
    assert "placeholder continuation" in placeholder["reason"]
    assert not raw_tool["valid"]
    assert "raw tool" in raw_tool["reason"]


def test_physics_analyst_react_prompt_uses_programmatic_digest(tmp_path, monkeypatch):
    monkeypatch.setenv("PHYSICS_ANALYST_CASE_DIGEST", "true")

    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text(
        "application blastFoam;\n"
        "endTime 0.0005;\n"
        "writeInterval 0.00025;\n"
        "functions\n"
        "{\n"
        "    pressureProbes\n"
        "    {\n"
        "        type blastProbes;\n"
        "        probeLocations ((1 0 0) (2 0 0));\n"
        "        fields (p impulse dynamicP);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    (system_dir / "setFieldsDict").write_text(
        "regions\n(\n    sphereToCell\n    {\n        centre (0 0 0);\n        radius 0.1;\n    }\n);\n",
        encoding="utf-8",
    )

    valid_report = (
        "Physics Report\n\n"
        "The current blastFoam case uses blastFoam with endTime 0.0005 and pressure probes. "
        "The setFieldsDict contains a sphereToCell source centered at the origin, so the case "
        "has enough evidence for the requested short smoke configuration. "
        "No direct file edits are made by the physics analyst."
    )
    agent = PhysicsAnalystAgent.__new__(PhysicsAnalystAgent)
    agent.agent = SequentialAgent([valid_report])

    result = agent.analyze(
        {
            "user_request": "Create a short blastFoam smoke case with pressure probes.",
            "case_path": str(tmp_path),
            "tutorial_case_path": "blastFoam/shockTube_tabulated",
            "tutorial_source_path": "/tutorials/blastFoam/shockTube_tabulated",
            "current_task": {"description": "Analyze current case."},
        }
    )

    assert result["physics_report_status"] == "completed"
    assert (tmp_path / "physics_report.md").read_text(encoding="utf-8") == valid_report
    assert len(agent.agent.inputs) == 1
    react_input = agent.agent.inputs[0]
    assert "PROGRAMMATIC CASE DIGEST" in react_input
    assert "system/controlDict" in react_input
    assert "application=blastFoam" in react_input
    assert "Stay in the ReAct workflow" in react_input


def test_physics_analyst_react_repair_path_remains_available(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_REPAIR_ATTEMPTS", "1")

    agent = PhysicsAnalystAgent.__new__(PhysicsAnalystAgent)
    agent.agent = SequentialAgent(
        [
            "Sorry, need more steps to process this request.",
            "Physics Report\n\nThe case has a defined OpenFOAM configuration and enough evidence for analysis. "
            "The report identifies the current physical setup, relevant files, and remaining discrepancies.",
        ]
    )

    output, report_status = agent._run_report_task(str(tmp_path), "Analyze the case using ReAct.")

    assert report_status["valid"]
    assert output.startswith("Physics Report")
    assert len(agent.agent.inputs) == 2
    assert "previous physics_report.md did not satisfy" in agent.agent.inputs[1].lower()


def test_reviewer_retries_invalid_placeholder_report(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_REPAIR_ATTEMPTS", "1")

    valid_report = (
        "Validation Status: Passed\n\n"
        "Checklist:\n"
        "- Solver log contains a clean End marker.\n"
        "- execution_status.json marks the run completed.\n"
        "- Requested pressure probes and reports are present.\n\n"
        "Conclusion: the generated case satisfies the requested smoke validation."
    )
    agent = ReviewerAgent.__new__(ReviewerAgent)
    agent.agent = SequentialAgent([
        "Sorry, need more steps to process this request.",
        valid_report,
    ])

    output, report_status = agent._run_review_task(str(tmp_path), "Review the completed case.")

    assert report_status["valid"]
    assert output == valid_report
    assert len(agent.agent.inputs) == 2
    assert "previous review_report.md did not satisfy" in agent.agent.inputs[1].lower()


def test_execution_report_retry_still_marks_invalid_when_repair_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_REPAIR_ATTEMPTS", "1")

    agent = ExecutionAgent.__new__(ExecutionAgent)
    agent.agent = SequentialAgent([
        "Sorry, need more steps to process this request.",
        "No output generated.",
    ])

    output, report_status = agent._run_report_task(str(tmp_path), "Execute the case.")

    assert output == "No output generated."
    assert not report_status["valid"]
    assert len(agent.agent.inputs) == 2


def test_workflow_artifact_contract_rejects_placeholder_review_report(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text("application blastFoam;\n", encoding="utf-8")
    (tmp_path / "log.blastFoam").write_text("Solver ok\nEnd\n", encoding="utf-8")
    (tmp_path / "physics_report.md").write_text("Physics report. " * 20, encoding="utf-8")
    (tmp_path / "execution_report.md").write_text("Execution report. " * 20, encoding="utf-8")
    (tmp_path / "review_report.md").write_text(
        "Sorry, need more steps to process this request.",
        encoding="utf-8",
    )
    execution_status = build_execution_status(tmp_path, "Execution completed successfully.", "completed")
    write_execution_status(tmp_path, execution_status)

    contract = validate_workflow_artifacts(
        tmp_path,
        {"execution_status": execution_status, "validation_status": "passed"},
        require_execution=True,
        require_review=True,
    )

    assert not contract["ok"]
    assert contract["checks"]["review_report_valid"] is False
    assert any("review_report.md invalid" in issue for issue in contract["issues"])


def test_orchestrator_rejects_completed_workflow_with_invalid_review_report(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_EXECUTION", "true")

    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text("application blastFoam;\n", encoding="utf-8")
    (tmp_path / "log.blastFoam").write_text("Solver ok\nEnd\n", encoding="utf-8")
    (tmp_path / "physics_report.md").write_text("Physics report. " * 20, encoding="utf-8")
    (tmp_path / "execution_report.md").write_text("Execution report. " * 20, encoding="utf-8")
    (tmp_path / "review_report.md").write_text(
        "Sorry, need more steps to process this request.",
        encoding="utf-8",
    )
    execution_status = build_execution_status(tmp_path, "Execution completed successfully.", "completed")
    write_execution_status(tmp_path, execution_status)

    orchestrator = OrchestratorAgent.__new__(OrchestratorAgent)
    result = orchestrator.route(
        {
            "user_request": "run a smoke test",
            "case_path": str(tmp_path),
            "plan": "run the case",
            "execution_status": execution_status,
            "run_status": "completed",
            "validation_status": "passed",
            "completed_tasks": [
                {"assigned_agent": "execution_agent", "status": "completed"},
                {"assigned_agent": "reviewer", "status": "completed"},
            ],
        }
    )

    assert result["workflow_status"] == "failed"
    assert result["run_status"] == "completed"
    assert "artifact contract failed" in result["workflow_error"]
    assert result["artifact_contract"]["checks"]["review_report_valid"] is False
    evidence = (tmp_path / "workflow_evidence.md").read_text(encoding="utf-8")
    assert "`artifact_contract.json`: exists=True" in evidence


def test_workflow_evidence_writes_compact_solver_and_artifact_summary(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text(
        "application blastFoam;\nendTime 0.0015;\nwriteInterval 0.0005;\n",
        encoding="utf-8",
    )
    (tmp_path / "log.blastFoam").write_text("Time = 0.0015\nEnd\n", encoding="utf-8")
    (tmp_path / "physics_report.md").write_text("Physics report. " * 20, encoding="utf-8")
    (tmp_path / "execution_report.md").write_text("Execution report. " * 20, encoding="utf-8")
    status = build_execution_status(tmp_path, "Execution completed successfully.", "completed")
    write_execution_status(tmp_path, status)
    probe_dir = tmp_path / "postProcessing" / "nearProbe" / "0"
    probe_dir.mkdir(parents=True)
    (probe_dir / "p").write_text("0 101325\n", encoding="utf-8")

    evidence = write_workflow_evidence(tmp_path)
    evidence_md = (tmp_path / "workflow_evidence.md").read_text(encoding="utf-8")

    assert evidence["control"]["endTime"] == "0.0015"
    assert evidence["solver"]["clean_end"] is True
    assert "postProcessing/nearProbe/0/p" in evidence_md
    assert "Solver clean End" in evidence_md


def test_search_tools_exclude_runtime_outputs_by_default(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text("application blastFoam;\nneedle yes;\n", encoding="utf-8")
    runtime_dir = tmp_path / "processor0" / "0.0013"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "alpha.c4").write_text("needle\n" * 200, encoding="utf-8")

    with scoped_tool_context(tmp_path):
        search_output = text_search.invoke({"query": "needle"})
        file_output = file_search.invoke({"pattern": "**/*"})

    assert "system/controlDict" in search_output
    assert "processor0" not in search_output
    assert "system/controlDict" in file_output
    assert "processor0" not in file_output
    assert "runtime output directories excluded" in search_output


def test_text_search_has_output_budget(tmp_path):
    for index in range(10):
        (tmp_path / f"case_{index}.txt").write_text("needle\n", encoding="utf-8")

    with scoped_tool_context(tmp_path):
        output = text_search.invoke({"query": "needle", "max_matches": 3})

    assert output.count("needle") == 3
    assert "truncated after 3 matches" in output


def test_read_file_requires_targeted_range_for_large_files(tmp_path):
    large_file = tmp_path / "0.001" / "p"
    large_file.parent.mkdir()
    large_file.write_text("1\n" * 2000, encoding="utf-8")

    with scoped_tool_context(tmp_path):
        output = read_file.invoke({"path": "0.001/p", "max_chars": 1000})

    assert "is large" in output
    assert "Specify start_line/end_line" in output


def test_workflow_evidence_samples_long_time_directory_lists(tmp_path):
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text("application blastFoam;\n", encoding="utf-8")
    for index in range(40):
        (tmp_path / f"0.{index:04d}").mkdir()

    evidence = write_workflow_evidence(tmp_path)
    evidence_md = (tmp_path / "workflow_evidence.md").read_text(encoding="utf-8")

    assert evidence["time_dir_count"] == 40
    assert "..." in evidence["time_dirs"]
    assert len(evidence["time_dirs"]) < 20
    assert "Time directory count" in evidence_md


def test_reviewer_prompt_includes_compact_workflow_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("REPORT_REPAIR_ATTEMPTS", "0")

    system_dir = tmp_path / "system"
    system_dir.mkdir()
    (system_dir / "controlDict").write_text(
        "application blastFoam;\nendTime 0.0015;\nwriteInterval 0.0005;\n",
        encoding="utf-8",
    )
    (tmp_path / "log.blastFoam").write_text("Time = 0.0015\nEnd\n", encoding="utf-8")
    (tmp_path / "physics_report.md").write_text("Physics report. " * 20, encoding="utf-8")
    (tmp_path / "execution_report.md").write_text("Execution report. " * 20, encoding="utf-8")
    status = build_execution_status(tmp_path, "Execution completed successfully.", "completed")
    write_execution_status(tmp_path, status)

    review_output = (
        "Validation Status: Passed\n\n"
        "Checklist:\n"
        "- Execution status is completed.\n"
        "- Solver log has a clean End marker.\n"
        "- Required reports are present.\n\n"
        "The compact workflow evidence supports this validation."
    )
    agent = ReviewerAgent.__new__(ReviewerAgent)
    agent.agent = SequentialAgent([review_output])

    result = agent.review_task(
        {
            "user_request": "run a short validation case",
            "case_path": str(tmp_path),
            "tutorial_case_path": None,
        }
    )

    assert result["validation_status"] == "passed"
    assert result["review_report_status"] == "completed"
    assert "Compact Workflow Evidence" in agent.agent.inputs[0]
    assert "Avoid reading full solver logs" in agent.agent.inputs[0]
    assert (tmp_path / "workflow_evidence.md").exists()
