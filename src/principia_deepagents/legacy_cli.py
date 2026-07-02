from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv

from principia_deepagents.cli import main as deepagents_main


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_PROJECT_ROOT = Path(os.getenv("PRINCIPIA_LEGACY_PROJECT_ROOT", "/data/graduation-projects/PrincipiaBlastFoam"))
DEFAULT_CASE_PATH = "/data/PrincipiaBlastFoam_output/deepagents_surfaceburst"
DEFAULT_USER_REQUEST = "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。"
DEFAULT_TUTORIAL_PATH = "/data/graduation-projects/blastFoam_tutorials"
DEFAULT_BATCH_OUTPUT_ROOT = "/data/PrincipiaBlastFoam_output/agent-batch_runs"


def _common_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--case-path", default=DEFAULT_CASE_PATH, help="Target case directory.")
    parser.add_argument("--user-request", default=DEFAULT_USER_REQUEST, help="User task description.")
    parser.add_argument(
        "--tutorial-path",
        default=os.getenv("BLASTFOAM_TUTORIALS", DEFAULT_TUTORIAL_PATH),
        help="blastFoam tutorial root directory.",
    )
    parser.add_argument("--env-file", default=None, help="Optional .env file. Defaults to this project .env.")
    parser.add_argument("--model-profile", default=os.getenv("PRINCIPIA_MODEL_PROFILE"))
    parser.add_argument("--llm-active-profile", default=os.getenv("LLM_ACTIVE_PROFILE"))
    parser.add_argument("--llm-provider", default=None)
    parser.add_argument("--llm-api-base-url", default=None)
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--retrieval-llm-active-profile", default=None)
    parser.add_argument("--retrieval-llm-api-key", default=None)
    parser.add_argument("--retrieval-llm-base-url", default=None)
    parser.add_argument("--retrieval-llm-model", default=None)
    parser.add_argument("--recursion-limit", type=int, default=200)
    parser.add_argument(
        "--agent-timeout",
        type=int,
        default=int(os.getenv("DEEPAGENTS_AGENT_TIMEOUT_SECONDS", "900")),
        help="Wall-clock timeout for Deep Agent planning.",
    )
    parser.add_argument(
        "--execution-timeout-seconds",
        type=int,
        default=int(os.getenv("DEEPAGENTS_EXECUTION_TIMEOUT_SECONDS", "3600")),
        help="Timeout for deterministic solver execution.",
    )
    parser.add_argument("--no-mcp", action="store_true", help="Disable MCP retrieval tools.")
    parser.add_argument("--skip-prepare", action="store_true", help="Skip tutorial initialization.")


def build_workflow_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Legacy-compatible PrincipiaBlastFoam workflow entry point backed by Deep Agents."
    )
    _common_runtime_args(parser)
    return parser


def _set_env_if_value(name: str, value: str | None) -> None:
    if value:
        os.environ[name] = value


def _export_legacy_retrieval_env(args: argparse.Namespace) -> None:
    _set_env_if_value("RETRIEVAL_LLM_ACTIVE_PROFILE", args.retrieval_llm_active_profile)
    _set_env_if_value("RETRIEVAL_LLM_API_KEY", args.retrieval_llm_api_key)
    _set_env_if_value("RETRIEVAL_LLM_API_BASE_URL", args.retrieval_llm_base_url)
    _set_env_if_value("RETRIEVAL_LLM_MODEL", args.retrieval_llm_model)


def workflow_args_for_deepagents(args: argparse.Namespace) -> list[str]:
    command = [
        "run",
        "--case-path",
        args.case_path,
        "--user-request",
        args.user_request,
        "--tutorial-path",
        args.tutorial_path,
        "--recursion-limit",
        str(args.recursion_limit),
        "--agent-timeout",
        str(args.agent_timeout),
        "--execution-timeout-seconds",
        str(args.execution_timeout_seconds),
    ]
    optional_pairs = [
        ("--env-file", args.env_file),
        ("--model-profile", args.model_profile),
        ("--llm-active-profile", args.llm_active_profile),
        ("--retrieval-llm-active-profile", args.retrieval_llm_active_profile),
        ("--llm-provider", args.llm_provider),
        ("--llm-api-base-url", args.llm_api_base_url),
        ("--llm-api-key", args.llm_api_key),
        ("--llm-model", args.llm_model),
    ]
    for flag, value in optional_pairs:
        if value:
            command.extend([flag, str(value)])
    if args.no_mcp:
        command.append("--no-mcp")
    if args.skip_prepare:
        command.append("--skip-prepare")
    return command


def workflow_main(argv: Sequence[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    parser = build_workflow_parser()
    args = parser.parse_args(argv)
    _export_legacy_retrieval_env(args)

    return_code = deepagents_main(workflow_args_for_deepagents(args))
    if return_code == 0:
        print("✅ Workflow reached completion state.")
        print("\n--- Workflow Run Test Passed ---")
    else:
        print("\n--- Workflow Run Test Failed ---")
    return int(return_code)


def default_modifications_file(mode: str) -> str:
    local = PROJECT_ROOT / "dataset" / "modification" / f"blastfoam_{mode}_modifications.json"
    if local.exists():
        return str(local)
    return str(LEGACY_PROJECT_ROOT / "dataset" / "modification" / f"blastfoam_{mode}_modifications.json")


def default_output_base_dir(mode: str) -> str:
    root = os.getenv("PRINCIPIA_BATCH_OUTPUT_ROOT", DEFAULT_BATCH_OUTPUT_ROOT)
    return str(Path(root) / f"blastfoam_{mode}_modifications")


def build_batch_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Legacy-compatible PrincipiaBlastFoam batch workflow backed by Deep Agents."
    )
    parser.add_argument("--mode", default="basic")
    parser.add_argument("--tutorial-path", default=os.getenv("BLASTFOAM_TUTORIALS", DEFAULT_TUTORIAL_PATH))
    parser.add_argument("--modifications-file", default=None)
    parser.add_argument("--output-base-dir", default=None)
    parser.add_argument("--results-file", default=None)
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--model-profile", default=os.getenv("PRINCIPIA_MODEL_PROFILE"))
    parser.add_argument("--llm-active-profile", default=os.getenv("LLM_ACTIVE_PROFILE"))
    parser.add_argument("--llm-provider", default=None)
    parser.add_argument("--llm-api-base-url", default=None)
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--retrieval-llm-active-profile", default=None)
    parser.add_argument("--retrieval-llm-api-key", default=None)
    parser.add_argument("--retrieval-llm-base-url", default=None)
    parser.add_argument("--retrieval-llm-model", default=None)
    parser.add_argument("--recursion-limit", type=int, default=200)
    parser.add_argument("--agent-timeout", type=int, default=int(os.getenv("DEEPAGENTS_AGENT_TIMEOUT_SECONDS", "900")))
    parser.add_argument(
        "--execution-timeout-seconds",
        type=int,
        default=int(os.getenv("DEEPAGENTS_EXECUTION_TIMEOUT_SECONDS", "3600")),
    )
    parser.add_argument("--no-mcp", action="store_true")
    parser.add_argument("--skip-prepare", action="store_true")
    return parser


def _load_modifications(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Batch modifications file must contain a JSON list: {path}")
    return payload


def _save_batch_results(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _workflow_argv_for_batch(args: argparse.Namespace, case_path: Path, user_request: str) -> list[str]:
    values = [
        "--case-path",
        str(case_path),
        "--user-request",
        user_request,
        "--tutorial-path",
        args.tutorial_path,
        "--recursion-limit",
        str(args.recursion_limit),
        "--agent-timeout",
        str(args.agent_timeout),
        "--execution-timeout-seconds",
        str(args.execution_timeout_seconds),
    ]
    optional_pairs = [
        ("--env-file", args.env_file),
        ("--model-profile", args.model_profile),
        ("--llm-active-profile", args.llm_active_profile),
        ("--retrieval-llm-active-profile", args.retrieval_llm_active_profile),
        ("--llm-provider", args.llm_provider),
        ("--llm-api-base-url", args.llm_api_base_url),
        ("--llm-api-key", args.llm_api_key),
        ("--llm-model", args.llm_model),
        ("--retrieval-llm-api-key", args.retrieval_llm_api_key),
        ("--retrieval-llm-base-url", args.retrieval_llm_base_url),
        ("--retrieval-llm-model", args.retrieval_llm_model),
    ]
    for flag, value in optional_pairs:
        if value:
            values.extend([flag, str(value)])
    if args.no_mcp:
        values.append("--no-mcp")
    if args.skip_prepare:
        values.append("--skip-prepare")
    return values


def run_batch(args: argparse.Namespace) -> dict[str, object]:
    modifications_file = Path(args.modifications_file or default_modifications_file(args.mode))
    output_base_dir = Path(args.output_base_dir or default_output_base_dir(args.mode))
    results_file = Path(args.results_file or output_base_dir / "batch_execution_results.json")
    output_base_dir.mkdir(parents=True, exist_ok=True)

    modifications = _load_modifications(modifications_file)
    batch_results: dict[str, object] = {
        "batch_start_time": datetime.now().isoformat(),
        "total_cases": len(modifications),
        "mode": args.mode,
        "modifications_file": str(modifications_file),
        "output_directory": str(output_base_dir),
        "tutorial_path": args.tutorial_path,
        "model_profile": args.model_profile,
        "llm_active_profile": args.llm_active_profile,
        "results": [],
    }
    results = batch_results["results"]
    assert isinstance(results, list)
    success_count = 0
    failed_count = 0

    for index, modification in enumerate(modifications, start=1):
        case_name = str(modification["case_name"])
        case_path = output_base_dir / case_name
        user_request = f"{modification.get('description', '')} {modification.get('modification', '')}".strip()
        print("\n" + "=" * 80)
        print(f"Processing Case [{index}/{len(modifications)}]: {case_name}")
        print("=" * 80)
        print(f"User Request: {user_request}")
        print(f"Output Path: {case_path}")

        result = {
            "case_name": case_name,
            "case_path": str(case_path),
            "base_case": modification.get("case_path"),
            "user_request": user_request,
            "modified_files": modification.get("modified_files", []),
            "start_time": datetime.now().isoformat(),
            "status": "pending",
            "error": None,
        }
        try:
            return_code = workflow_main(_workflow_argv_for_batch(args, case_path, user_request))
            result["return_code"] = return_code
            if return_code == 0:
                result["status"] = "success"
                success_count += 1
            else:
                result["status"] = "failed"
                failed_count += 1
                result["error"] = f"workflow exited with code {return_code}"
        except Exception as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
            failed_count += 1
        result["end_time"] = datetime.now().isoformat()
        results.append(result)

        batch_results["current_summary"] = {
            "processed": index,
            "remaining": len(modifications) - index,
            "success": success_count,
            "failed": failed_count,
            "incomplete": index - success_count - failed_count,
        }
        _save_batch_results(results_file, batch_results)

    batch_results["batch_end_time"] = datetime.now().isoformat()
    batch_results["summary"] = {
        "success": success_count,
        "failed": failed_count,
        "incomplete": len(modifications) - success_count - failed_count,
    }
    _save_batch_results(results_file, batch_results)
    print(f"\nBatch results saved to: {results_file}")
    return batch_results


def batch_main(argv: Sequence[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    parser = build_batch_parser()
    args = parser.parse_args(argv)
    run_batch(args)
    return 0
