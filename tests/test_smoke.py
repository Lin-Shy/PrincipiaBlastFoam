from __future__ import annotations

from pathlib import Path

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from principia_deepagents import agent as agent_mod
from principia_deepagents.config import RuntimeConfig
from principia_deepagents.utils.fallback_finalize import finalize_nonexecution_artifacts
from principia_deepagents.utils.final_summary import format_final_artifact_summary
from principia_deepagents.utils.execution_status import write_execution_status
from principia_deepagents.utils.postprocessing_report import write_post_processing_report
from principia_deepagents.utils.report_contracts import report_error_reasons
from principia_deepagents.tools.mcp import _syncify_mcp_tool
from principia_deepagents.tools.openfoam import initialize_case_from_tutorial, make_openfoam_tools
from principia_deepagents.utils.workflow_artifacts import validate_workflow_artifacts, write_artifact_contract
from principia_deepagents.utils.workflow_evidence import write_workflow_evidence


TUTORIAL_ROOT = Path("/data/graduation-projects/blastFoam_tutorials")
SURFACE_BURST_REQUEST = "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。"


def test_prepare_selects_axisymmetric_charge_for_surface_burst(tmp_path: Path) -> None:
    result = initialize_case_from_tutorial(
        case_path=tmp_path,
        user_request=SURFACE_BURST_REQUEST,
        tutorial_path=TUTORIAL_ROOT,
    )

    assert result["initialized"] is True
    assert result["tutorial_case_path"] == "blastFoam/axisymmetricCharge"
    assert (tmp_path / "Allrun").exists()
    assert (tmp_path / "system" / "controlDict").exists()


def test_prepare_prefers_blastfoam_internal_case_over_setrefinedfields_symlink(tmp_path: Path) -> None:
    request = (
        "构建一个ERDC小尺度内部空气爆炸风格的短时验证算例："
        "优先从internalDetonation或internalDetonation_withObstacleAndGlass初始化，"
        "保留封闭空间和出口/管道传播特征。"
    )

    result = initialize_case_from_tutorial(
        case_path=tmp_path,
        user_request=request,
        tutorial_path=TUTORIAL_ROOT,
    )

    assert result["initialized"] is True
    assert result["tutorial_case_path"].startswith("blastFoam/")
    assert "internalDetonation" in result["tutorial_case_path"]


def test_prepare_prefers_light_building_case_for_hemicylinder_obstacle_smoke(tmp_path: Path) -> None:
    request = (
        "构建一个半圆柱障碍物冲击波反射实验风格的短时算例："
        "优先选择movingCone、mappedBuilding3D、building3D或可表达刚性障碍物的tutorial；"
        "沿来波方向和障碍物前后设置压力探针，endTime控制在0.0015秒以内。"
    )

    result = initialize_case_from_tutorial(
        case_path=tmp_path,
        user_request=request,
        tutorial_path=TUTORIAL_ROOT,
    )

    assert result["initialized"] is True
    assert result["tutorial_case_path"] == "blastFoam/building3DWorkshop"


def test_artifact_validation_without_execution(tmp_path: Path) -> None:
    initialize_case_from_tutorial(
        case_path=tmp_path,
        user_request=SURFACE_BURST_REQUEST,
        tutorial_path=TUTORIAL_ROOT,
    )
    physics_report = (
        "# Physics Report\n\n"
        "This axisymmetric blastFoam case is initialized from the axisymmetricCharge tutorial. "
        "The requested surface-burst scaled-distance scenario should preserve the tutorial solver, "
        "initial explosive region, mesh controls, time stepping, and probe/reporting settings while "
        "adjusting only parameters explicitly required by the user request. "
        "Relevant evidence files are system/controlDict, system/setFieldsDict, system/blockMeshDict, "
        "constant/phaseProperties, and the initial fields under 0/.\n"
    )
    (tmp_path / "physics_report.md").write_text(physics_report, encoding="utf-8")

    evidence = write_workflow_evidence(tmp_path)
    contract = validate_workflow_artifacts(tmp_path, {}, require_execution=False, require_review=False)
    path = write_artifact_contract(tmp_path, contract)

    assert evidence["case_path"] == str(tmp_path)
    assert path.exists()
    assert contract["ok"] is True


def test_deep_agent_factory_compiles_without_mcp(tmp_path: Path, monkeypatch) -> None:
    config = RuntimeConfig(
        case_path=tmp_path,
        user_request="inspect this case",
        tutorial_path=TUTORIAL_ROOT,
        model="fake",
        api_key="fake",
        base_url=None,
        provider="fake",
        model_provider="openai",
        active_profile=None,
        model_profile=None,
        model_profile_label=None,
        api_key_env=None,
        recursion_limit=20,
        enable_execution=False,
        require_execution=False,
        use_mcp_retrieval=False,
    )
    fake_model = FakeMessagesListChatModel(responses=[AIMessage(content="ok")])
    monkeypatch.setattr(agent_mod, "build_chat_model", lambda _config: fake_model)

    app = agent_mod.create_principia_agent(config)

    assert hasattr(app, "invoke")


def test_validate_artifacts_tool_defaults_to_runtime_execution_contract(tmp_path: Path) -> None:
    (tmp_path / "physics_report.md").write_text("# Physics Report\n\n" + "valid content " * 20, encoding="utf-8")
    tools = make_openfoam_tools(
        case_path=tmp_path,
        user_request="run solver",
        tutorial_path=TUTORIAL_ROOT,
        default_require_execution=True,
        default_require_review=True,
    )
    validate_tool = next(tool for tool in tools if tool.name == "validate_artifacts")

    result = validate_tool.invoke({})

    assert '"ok": false' in result
    assert "execution_status.json is missing or unreadable" in result
    assert "review_report.md invalid" in result
    assert '"terminal_success": false' in result


def test_write_post_processing_report_tool_summarizes_probe_outputs(tmp_path: Path) -> None:
    probe_file = tmp_path / "postProcessing" / "pressureProbes" / "0" / "p"
    probe_file.parent.mkdir(parents=True)
    probe_file.write_text("# Probe pressure data\n0 101325\n", encoding="utf-8")
    (tmp_path / "0.0005").mkdir()
    tools = make_openfoam_tools(
        case_path=tmp_path,
        user_request="summarize outputs",
        tutorial_path=TUTORIAL_ROOT,
    )
    post_tool = next(tool for tool in tools if tool.name == "write_post_processing_report")

    result = post_tool.invoke({})
    report = (tmp_path / "post_processing_report.md").read_text(encoding="utf-8")

    assert '"post_processing_exists": true' in result
    assert '"pressureProbes": [\n      "p"\n    ]' in result
    assert "`postProcessing/pressureProbes/0/p`" in report
    assert "Last available time: `0.0005`" in report
    assert "probe fields: `pressureProbes: p`" in report


def test_write_post_processing_report_summarizes_nested_time_dirs(tmp_path: Path) -> None:
    nested_time = tmp_path / "building3D" / "processor0" / "0.0005"
    nested_time.mkdir(parents=True)

    result = write_post_processing_report(tmp_path)
    report = (tmp_path / "post_processing_report.md").read_text(encoding="utf-8")

    assert result["time_dir_count"] == 1
    assert result["last_time"] == "0.0005"
    assert result["time_dir_locations"][0]["path"] == "building3D/processor0/0.0005"
    assert "Last available time: `0.0005`" in report
    assert "`building3D/processor0/0.0005`" in report


def test_complete_workflow_tool_finishes_nonexecution_contract(tmp_path: Path) -> None:
    control = tmp_path / "system" / "controlDict"
    control.parent.mkdir(parents=True)
    control.write_text("application blastFoam;\nendTime 0.02;\nwriteInterval 0.001;\n", encoding="utf-8")
    tools = make_openfoam_tools(
        case_path=tmp_path,
        user_request="endTime控制在0.0005秒以内，writeInterval设置得足够小。",
        tutorial_path=TUTORIAL_ROOT,
    )
    complete_tool = next(tool for tool in tools if tool.name == "complete_workflow")

    result = complete_tool.invoke({"timeout_seconds": 30})

    assert '"terminal_success": true' in result
    assert '"artifact_contract_ok": true' in result
    assert (tmp_path / "physics_report.md").exists()
    assert (tmp_path / "post_processing_report.md").exists()
    assert (tmp_path / "artifact_contract.json").exists()
    assert "endTime 0.0005;" in control.read_text(encoding="utf-8")


def test_run_openfoam_tool_applies_deterministic_controls_before_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    control = tmp_path / "system" / "controlDict"
    control.parent.mkdir(parents=True)
    control.write_text("application blastFoam;\nendTime 0.0025;\nwriteInterval 0.0005;\n", encoding="utf-8")

    def fake_run(case_path: Path, *, timeout_seconds: int = 3600):
        return {"started": True, "timeout_seconds": timeout_seconds, "status": {"final_status": "success"}}

    monkeypatch.setattr("principia_deepagents.tools.openfoam.run_openfoam_case_once", fake_run)
    tools = make_openfoam_tools(
        case_path=tmp_path,
        user_request="短时smoke test，endTime控制在0.0015秒以内，writeInterval不超过0.0005秒。",
        tutorial_path=TUTORIAL_ROOT,
        default_require_execution=True,
        default_require_review=True,
    )
    run_tool = next(tool for tool in tools if tool.name == "run_openfoam_case")

    result = run_tool.invoke({"timeout_seconds": 30})
    text = control.read_text(encoding="utf-8")

    assert '"started": true' in result
    assert "endTime 0.0005;" in text
    assert (tmp_path / "physics_report.md").exists()
    assert (tmp_path / "post_processing_report.md").exists()


def test_async_mcp_tool_is_sync_invokable() -> None:
    async def async_lookup(query: str) -> str:
        return f"hit:{query}"

    async_tool = StructuredTool.from_function(
        coroutine=async_lookup,
        name="async_lookup",
        description="Async lookup.",
    )

    sync_tool = _syncify_mcp_tool(async_tool)

    assert sync_tool.invoke({"query": "axisymmetricCharge"}) == "hit:axisymmetricCharge"


def test_fallback_finalize_applies_short_shock_tube_controls(tmp_path: Path) -> None:
    request = (
        "基于blastFoam的shockTube_tabulated或最接近的shock tube tutorial，"
        "将system/controlDict的endTime控制在0.0005秒以内，"
        "writeInterval设置得足够小以便至少写出一个非零时间结果。"
    )
    initialize_case_from_tutorial(
        case_path=tmp_path,
        user_request=request,
        tutorial_path=TUTORIAL_ROOT,
    )

    result = finalize_nonexecution_artifacts(
        tmp_path,
        user_request=request,
        reason="test recursion recovery",
    )
    contract = validate_workflow_artifacts(tmp_path, {}, require_execution=False, require_review=False)

    control = (tmp_path / "system" / "controlDict").read_text(encoding="utf-8")
    assert "endTime         0.0005;" in control
    assert "writeInterval   0.0001;" in control
    assert result["written"]["physics_report.md"] is True
    assert contract["ok"] is True


def test_fallback_finalize_updates_nested_control_dicts(tmp_path: Path) -> None:
    for subcase in ("sector", "building3D"):
        control = tmp_path / subcase / "system" / "controlDict"
        control.parent.mkdir(parents=True)
        control.write_text(
            "application blastFoam;\nendTime 0.01;\nwriteInterval 0.001;\n",
            encoding="utf-8",
        )

    result = finalize_nonexecution_artifacts(
        tmp_path,
        user_request="endTime控制在0.0015秒以内，writeInterval不超过0.0005秒。",
        reason="nested case test",
    )

    assert result["endTime"] == 0.0015
    assert result["writeInterval"] == 0.0005
    assert len(result["control_update"]["controls"]) == 2
    for subcase in ("sector", "building3D"):
        text = (tmp_path / subcase / "system" / "controlDict").read_text(encoding="utf-8")
        assert "endTime 0.0015;" in text
        assert "writeInterval 0.0005;" in text


def test_fallback_finalize_caps_short_smoke_end_time(tmp_path: Path) -> None:
    control = tmp_path / "system" / "controlDict"
    control.parent.mkdir(parents=True)
    control.write_text(
        "application blastFoam;\nendTime 0.0025;\nwriteInterval 0.0005;\n",
        encoding="utf-8",
    )

    result = finalize_nonexecution_artifacts(
        tmp_path,
        user_request=(
            "构建一个短时smoke test，endTime控制在0.0015秒以内，"
            "writeInterval不超过0.0005秒。"
        ),
    )
    text = control.read_text(encoding="utf-8")

    assert result["endTime"] == 0.0005
    assert "endTime 0.0005;" in text
    assert "writeInterval 0.0005;" in text


def test_fallback_finalize_overwrites_invalid_report_with_safe_recovery_note(tmp_path: Path) -> None:
    control = tmp_path / "system" / "controlDict"
    control.parent.mkdir(parents=True)
    control.write_text("application blastFoam;\nendTime 0.0015;\nwriteInterval 0.0005;\n", encoding="utf-8")
    (tmp_path / "physics_report.md").write_text(
        "# Physics Report\n\nconnection error from previous agent call. " + "details " * 40,
        encoding="utf-8",
    )

    result = finalize_nonexecution_artifacts(
        tmp_path,
        user_request="短时smoke test，endTime控制在0.0015秒以内。",
        reason="Deep Agent exceeded agent timeout; using deterministic artifact validation: agent.invoke exceeded 360 seconds",
        execution_enabled=True,
    )
    report = (tmp_path / "physics_report.md").read_text(encoding="utf-8")

    assert result["written"]["physics_report.md"] is True
    assert "planner did not complete the strict artifact contract" in report
    assert "agent timeout" not in report.lower()
    assert report_error_reasons(report) == []


def test_fallback_finalize_adjusts_surface_blast_pressure_probes(tmp_path: Path) -> None:
    control = tmp_path / "system" / "controlDict"
    control.parent.mkdir(parents=True)
    control.write_text(
        """
application blastFoam;
endTime 0.025;
writeInterval 0.0005;
functions
{
    pressureProbes
    {
        type blastProbes;
        probeLocations
        (
            (1 0 0)
            (2 0 0)
            (5 0 0)
            (10 0 0)
            (15 0 0)
            (20 0 0)
        );
        fields (p impulse dynamicP);
    }
}
""".lstrip(),
        encoding="utf-8",
    )

    result = finalize_nonexecution_artifacts(
        tmp_path,
        user_request="触地地表爆炸smoke test，最远地面压力probe接近Z=2到3，endTime控制在0.001秒以内。",
    )
    text = control.read_text(encoding="utf-8")

    assert result["control_update"]["controls"][0]["probe_update"]["kind"] == "surface_blast_pressure_probes"
    assert "(0.5 0 0)" in text
    assert "(2.5 0 0)" in text
    assert "(3.0 0 0)" in text
    assert "(20 0 0)" not in text


def test_fallback_finalize_adds_shock_tube_probes_to_empty_functions(tmp_path: Path) -> None:
    control = tmp_path / "system" / "controlDict"
    control.parent.mkdir(parents=True)
    control.write_text(
        "application blastFoam;\nendTime 0.02;\nwriteInterval 0.001;\nfunctions\n{}\n",
        encoding="utf-8",
    )

    result = finalize_nonexecution_artifacts(
        tmp_path,
        user_request="shock tube短时验证，保留或添加压力采样probe，endTime控制在0.0005秒以内。",
    )
    text = control.read_text(encoding="utf-8")

    assert result["control_update"]["controls"][0]["probe_update"]["kind"] == "shock_tube_probes"
    assert "type            probes;" in text
    assert "fields          (p rho U);" in text
    assert "(25 0 0)" in text
    assert "(50 0 0)" in text
    assert "(75 0 0)" in text


def test_final_artifact_summary_reports_actual_probe_locations(tmp_path: Path) -> None:
    control = tmp_path / "system" / "controlDict"
    control.parent.mkdir(parents=True)
    control.write_text(
        """
application blastFoam;
endTime 0.001;
writeInterval 0.0001;
functions
{
    pressureProbes
    {
        type blastProbes;
        probeLocations
        (
            (0.5 0 0)
            (1.0 0 0)
            (1.5 0 0)
            (2.0 0 0)
            (2.5 0 0)
            (3.0 0 0)
        );
        fields (p impulse);
    }
}
""".lstrip(),
        encoding="utf-8",
    )
    post_file = tmp_path / "postProcessing" / "pressureProbes" / "0" / "p"
    post_file.parent.mkdir(parents=True)
    post_file.write_text("# p\n0 101325\n", encoding="utf-8")
    (tmp_path / "post_processing_report.md").write_text("# Post-Processing Report\n", encoding="utf-8")
    write_execution_status(
        tmp_path,
        {
            "schema_version": 1,
            "run_status": "completed",
            "final_status": "success",
            "status_source": "solver_log",
            "solver_logs": ["log.blastFoam"],
        },
    )

    summary = format_final_artifact_summary(
        tmp_path,
        contract={"ok": True, "issues": []},
        evidence={
            "post_processing": {
                "exists": True,
                "files": [{"path": "postProcessing/pressureProbes/0/p", "bytes": 13}],
            }
        },
    )

    assert "artifact_contract ok: True" in summary
    assert "execution_status: completed / success (source=solver_log)" in summary
    assert "system/controlDict: application=blastFoam, endTime=0.001, writeInterval=0.0001" in summary
    assert "probeLocations[1]: (0.5 0 0), (1.0 0 0), (1.5 0 0)" in summary
    assert "(3.0 0 0)" in summary
    assert "(20 0 0)" not in summary
    assert "post_processing_report.md: exists=True" in summary
    assert "postProcessing/pressureProbes/0/p" in summary
