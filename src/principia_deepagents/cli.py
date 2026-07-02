from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import queue
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

from principia_deepagents.agent import create_principia_agent
from principia_deepagents.config import export_runtime_environment, load_project_env, resolve_runtime_config
from principia_deepagents.prompts import workflow_user_prompt
from principia_deepagents.tools.mcp import load_mcp_retrieval_tools
from principia_deepagents.tools.openfoam import initialize_case_from_tutorial, run_openfoam_case_once
from principia_deepagents.utils.execution_preflight import run_execution_preflight
from principia_deepagents.utils.execution_status import read_execution_status, status_run_completed
from principia_deepagents.utils.fallback_finalize import finalize_nonexecution_artifacts
from principia_deepagents.utils.final_summary import format_final_artifact_summary
from principia_deepagents.utils.postprocessing_report import write_post_processing_report as write_post_processing_report_file
from principia_deepagents.utils.review_report import read_review_validation_status, write_deterministic_review_report
from principia_deepagents.utils.workflow_artifacts import validate_workflow_artifacts, write_artifact_contract
from principia_deepagents.utils.workflow_evidence import write_workflow_evidence

try:
    from langgraph.errors import GraphRecursionError
except Exception:  # pragma: no cover - defensive for dependency changes
    GraphRecursionError = RuntimeError  # type: ignore[assignment]


DEFAULT_CASE_PATH = "/data/PrincipiaBlastFoam_output/deepagents_surfaceburst"
DEFAULT_USER_REQUEST = "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。"
DEFAULT_TUTORIAL_PATH = "/data/graduation-projects/blastFoam_tutorials"


def _add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--case-path", default=DEFAULT_CASE_PATH, help="Target OpenFOAM case directory.")
    parser.add_argument("--user-request", default=DEFAULT_USER_REQUEST, help="Natural-language task.")
    parser.add_argument("--tutorial-path", default=os.getenv("BLASTFOAM_TUTORIALS", DEFAULT_TUTORIAL_PATH))
    parser.add_argument("--env-file", default=None, help="Optional .env file path.")
    parser.add_argument("--llm-active-profile", default=os.getenv("LLM_ACTIVE_PROFILE"))
    parser.add_argument(
        "--retrieval-llm-active-profile",
        default=None,
        help="Optional profile override for MCP retrieval LLM calls.",
    )
    parser.add_argument("--llm-provider", default=None)
    parser.add_argument("--llm-api-base-url", default=None)
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--recursion-limit", type=int, default=None)
    parser.add_argument("--no-mcp", action="store_true", help="Disable MCP retrieval tool loading.")
    parser.add_argument(
        "--agent-timeout",
        type=int,
        default=int(os.getenv("DEEPAGENTS_AGENT_TIMEOUT_SECONDS", "900")),
        help="Wall-clock timeout in seconds for agent.invoke in run mode. Use 0 to disable.",
    )


def _config_from_args(args: argparse.Namespace):
    load_project_env(args.env_file)
    config = resolve_runtime_config(
        case_path=args.case_path,
        user_request=args.user_request,
        tutorial_path=args.tutorial_path,
        llm_active_profile=args.llm_active_profile,
        llm_provider=args.llm_provider,
        llm_api_base_url=args.llm_api_base_url,
        llm_api_key=args.llm_api_key,
        llm_model=args.llm_model,
        recursion_limit=args.recursion_limit,
        use_mcp_retrieval=not args.no_mcp,
    )
    export_runtime_environment(
        config,
        retrieval_active_profile=getattr(args, "retrieval_llm_active_profile", None),
    )
    return config


def _last_message_text(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    if not messages:
        return ""
    content = getattr(messages[-1], "content", messages[-1])
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if text:
                    parts.append(str(text))
        return "\n".join(parts)
    return str(content)


def _agent_worker(config: Any, prompt: str, task_id: str, output_queue: Any) -> None:
    try:
        agent = create_principia_agent(config)
        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={
                "recursion_limit": config.recursion_limit,
                "configurable": {"thread_id": task_id},
            },
        )
        output_queue.put({"final_text": _last_message_text(result), "warning": ""})
    except GraphRecursionError as exc:
        output_queue.put(
            {
                "final_text": "",
                "warning": f"Deep Agent reached recursion limit; using deterministic artifact validation: {exc}",
            }
        )
    except Exception as exc:
        output_queue.put(
            {
                "final_text": "",
                "warning": (
                    "Deep Agent raised an exception; using deterministic artifact validation: "
                    f"{type(exc).__name__}: {exc}"
                ),
            }
        )


def _multiprocessing_context() -> mp.context.BaseContext:
    try:
        return mp.get_context("fork")
    except ValueError:  # pragma: no cover - non-POSIX fallback
        return mp.get_context()


def _invoke_agent_with_timeout(
    config: Any,
    *,
    prompt: str,
    task_id: str,
    timeout_seconds: int,
) -> tuple[str, str]:
    if timeout_seconds <= 0:
        output: queue.Queue[dict[str, str]] = queue.Queue()
        _agent_worker(config, prompt, task_id, output)
        payload = output.get()
        return payload.get("final_text", ""), payload.get("warning", "")

    context = _multiprocessing_context()
    output_queue = context.Queue()
    process = context.Process(target=_agent_worker, args=(config, prompt, task_id, output_queue))
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(20)
        if process.is_alive():
            process.kill()
            process.join()
        return (
            "",
            f"Deep Agent exceeded planning deadline; using deterministic artifact validation: "
            f"agent.invoke exceeded {timeout_seconds} seconds",
        )

    try:
        payload = output_queue.get_nowait()
    except queue.Empty:
        return (
            "",
            "Deep Agent produced no completion payload; using deterministic artifact validation.",
        )
    return payload.get("final_text", ""), payload.get("warning", "")


def _validation_state(case_path: Path) -> dict[str, Any]:
    return {
        "execution_status": read_execution_status(case_path),
        "validation_status": read_review_validation_status(case_path),
    }


def _clear_case_directory(case_path: Path) -> None:
    case_path.mkdir(parents=True, exist_ok=True)
    for child in case_path.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def _reset_case_for_execution_fallback(config: Any) -> dict[str, Any]:
    """Restore a clean tutorial case before deterministic execution recovery."""
    try:
        _clear_case_directory(config.case_path)
        return initialize_case_from_tutorial(
            case_path=config.case_path,
            user_request=config.user_request,
            tutorial_path=config.tutorial_path,
            force=True,
        )
    except Exception as exc:  # pragma: no cover - recovery should continue
        return {
            "initialized": False,
            "skipped": False,
            "message": f"case reset failed before execution fallback: {exc}",
            "case_path": str(config.case_path),
        }


def _apply_execution_fallback(config: Any, *, reason: str, timeout_seconds: int) -> dict[str, Any]:
    reset = _reset_case_for_execution_fallback(config)
    finalization = finalize_nonexecution_artifacts(
        config.case_path,
        user_request=config.user_request,
        reason=reason or "artifact contract failed before deterministic solver execution finalization",
        execution_enabled=True,
    )
    execution = run_openfoam_case_once(config.case_path, timeout_seconds=timeout_seconds)
    post_processing = write_post_processing_report_file(config.case_path)
    review = write_deterministic_review_report(
        config.case_path,
        require_execution=True,
        reason="Deterministic solver execution fallback completed after the agent did not finish the strict contract.",
    )
    evidence = write_workflow_evidence(config.case_path)
    contract = validate_workflow_artifacts(
        config.case_path,
        _validation_state(config.case_path),
        require_execution=True,
        require_review=True,
    )
    write_artifact_contract(config.case_path, contract)
    return {
        "case_reset": reset,
        "finalization": finalization,
        "execution": execution,
        "post_processing": post_processing,
        "review": review,
        "evidence": evidence,
        "contract": contract,
    }


def cmd_prepare(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    result = initialize_case_from_tutorial(
        case_path=config.case_path,
        user_request=config.user_request,
        tutorial_path=config.tutorial_path,
        force=args.force,
    )
    print(result)
    return 0 if result.get("initialized") or result.get("skipped") else 1


def cmd_validate(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    evidence = write_workflow_evidence(config.case_path)
    contract = validate_workflow_artifacts(
        config.case_path,
        _validation_state(config.case_path),
        require_execution=args.require_execution,
        require_review=args.require_review,
    )
    path = write_artifact_contract(config.case_path, contract)
    print(f"workflow_evidence: {evidence.get('created_at')}")
    print(f"artifact_contract: {path}")
    print(f"ok: {contract['ok']}")
    if contract["issues"]:
        print("issues:")
        for issue in contract["issues"]:
            print(f"- {issue}")
    return 0 if contract["ok"] else 1


def cmd_preflight(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    result = run_execution_preflight(config.case_path)
    print(json_dump(result))
    return 0 if result["ok"] else 1


def cmd_execute(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    result = run_openfoam_case_once(config.case_path, timeout_seconds=args.timeout_seconds)
    print(json_dump(result))
    status = result.get("status") if isinstance(result, dict) else None
    return 0 if status_run_completed(status) else 1


def cmd_mcp_smoke(args: argparse.Namespace) -> int:
    load_project_env(args.env_file)
    if args.llm_active_profile:
        os.environ["LLM_ACTIVE_PROFILE"] = args.llm_active_profile
    if args.retrieval_llm_active_profile:
        os.environ["RETRIEVAL_LLM_ACTIVE_PROFILE"] = args.retrieval_llm_active_profile
    tools = load_mcp_retrieval_tools()
    print(f"Loaded {len(tools)} MCP tools:")
    for item in tools:
        print(f"- {getattr(item, 'name', item)}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = _config_from_args(args)
    os.environ["DEEPAGENTS_EXECUTION_TIMEOUT_SECONDS"] = str(args.execution_timeout_seconds)
    config.case_path.mkdir(parents=True, exist_ok=True)

    if not args.skip_prepare:
        print("=== Preparation ===", flush=True)
        prepare = initialize_case_from_tutorial(
            case_path=config.case_path,
            user_request=config.user_request,
            tutorial_path=config.tutorial_path,
            force=False,
        )
        print(f"Preparation: {prepare}", flush=True)

    print("=== Building Deep Agent ===", flush=True)
    prompt = workflow_user_prompt(
        user_request=config.user_request,
        case_path=str(config.case_path),
        tutorial_path=str(config.tutorial_path),
        enable_execution=config.enable_execution,
        require_execution=config.require_execution,
    )
    task_id = str(uuid.uuid4())
    print(f"=== Invoking Deep Agent task_id={task_id} ===", flush=True)

    final_text, run_warning = _invoke_agent_with_timeout(
        config,
        prompt=prompt,
        task_id=task_id,
        timeout_seconds=args.agent_timeout,
    )
    if run_warning:
        print(f"Agent warning: {run_warning}", flush=True)
    print("\n=== Agent Final Response ===")
    print(final_text)

    require_execution_artifacts = config.require_execution or config.enable_execution
    evidence = write_workflow_evidence(config.case_path)
    contract = validate_workflow_artifacts(
        config.case_path,
        _validation_state(config.case_path),
        require_execution=require_execution_artifacts,
        require_review=require_execution_artifacts,
    )
    fallback_result = None
    execution_fallback_result = None
    if not require_execution_artifacts and (run_warning or not contract["ok"]):
        fallback_result = finalize_nonexecution_artifacts(
            config.case_path,
            user_request=config.user_request,
            reason=run_warning or "artifact contract failed before deterministic non-execution finalization",
        )
        evidence = write_workflow_evidence(config.case_path)
        contract = validate_workflow_artifacts(
            config.case_path,
            _validation_state(config.case_path),
            require_execution=False,
            require_review=False,
        )
    elif require_execution_artifacts and not contract["ok"]:
        execution_fallback_result = _apply_execution_fallback(
            config,
            reason=run_warning or "artifact contract failed before deterministic solver execution finalization",
            timeout_seconds=getattr(args, "execution_timeout_seconds", 3600),
        )
        evidence = execution_fallback_result["evidence"]
        contract = execution_fallback_result["contract"]
    write_artifact_contract(config.case_path, contract)
    print("\n=== Deterministic Final Check ===")
    print(f"workflow_evidence created_at: {evidence.get('created_at')}")
    print(f"artifact_contract ok: {contract['ok']}")
    if run_warning:
        print(f"agent_warning: {run_warning}")
    if fallback_result:
        print(f"fallback_finalization: {fallback_result}")
    if execution_fallback_result:
        execution = execution_fallback_result.get("execution") or {}
        status = execution.get("status") if isinstance(execution, dict) else None
        print(
            "execution_fallback: "
            + json_dump(
                {
                    "started": execution.get("started") if isinstance(execution, dict) else None,
                    "return_code": execution.get("return_code") if isinstance(execution, dict) else None,
                    "final_status": status.get("final_status") if isinstance(status, dict) else None,
                    "run_status": status.get("run_status") if isinstance(status, dict) else None,
                    "contract_ok": contract["ok"],
                }
            )
        )
    if contract["issues"]:
        for issue in contract["issues"]:
            print(f"- {issue}")
    print("\n=== Deterministic Artifact Summary ===")
    print(format_final_artifact_summary(config.case_path, contract=contract, evidence=evidence))
    return 0 if contract["ok"] else 1


def json_dump(data: Any) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PrincipiaBlastFoam DeepAgents CLI")
    parser.add_argument("--env-file", default=None, help="Optional .env file for mcp-smoke.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the full Deep Agents workflow.")
    _add_runtime_args(run_parser)
    run_parser.add_argument("--skip-prepare", action="store_true")
    run_parser.add_argument(
        "--execution-timeout-seconds",
        type=int,
        default=int(os.getenv("DEEPAGENTS_EXECUTION_TIMEOUT_SECONDS", "3600")),
        help="Timeout for deterministic solver execution fallback in run mode.",
    )
    run_parser.set_defaults(func=cmd_run)

    prepare_parser = subparsers.add_parser("prepare", help="Initialize a case directory without LLM calls.")
    _add_runtime_args(prepare_parser)
    prepare_parser.add_argument("--force", action="store_true", help="Overwrite an existing case.")
    prepare_parser.set_defaults(func=cmd_prepare)

    validate_parser = subparsers.add_parser("validate", help="Validate artifacts for a case directory.")
    _add_runtime_args(validate_parser)
    validate_parser.add_argument("--require-execution", action="store_true")
    validate_parser.add_argument("--require-review", action="store_true")
    validate_parser.set_defaults(func=cmd_validate)

    preflight_parser = subparsers.add_parser("preflight", help="Check solver execution readiness.")
    _add_runtime_args(preflight_parser)
    preflight_parser.set_defaults(func=cmd_preflight)

    execute_parser = subparsers.add_parser("execute", help="Run a prepared case through the deterministic execution tool.")
    _add_runtime_args(execute_parser)
    execute_parser.add_argument("--timeout-seconds", type=int, default=3600)
    execute_parser.set_defaults(func=cmd_execute)

    smoke_parser = subparsers.add_parser("mcp-smoke", help="Load MCP retrieval tools.")
    smoke_parser.add_argument("--env-file", default=None)
    smoke_parser.add_argument("--llm-active-profile", default=os.getenv("LLM_ACTIVE_PROFILE"))
    smoke_parser.add_argument("--retrieval-llm-active-profile", default=None)
    smoke_parser.set_defaults(func=cmd_mcp_smoke)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
