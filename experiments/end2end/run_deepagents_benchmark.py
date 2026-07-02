#!/usr/bin/env python3
"""Run old Principia benchmark prompts against the Deep Agents CLI.

The script is intentionally black-box: it invokes `principia-deepagents` and
collects filesystem artifacts. Use `--workflow-mode prepare` for no-LLM case
selection smoke tests, and `--workflow-mode run` for full agent parity runs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from principia_deepagents.utils.model_profiles import (
    get_model_profile,
    normalize_profile_id,
    resolve_profile_api_key,
)
from principia_deepagents.utils.time_dirs import discover_numeric_time_dirs, unique_numeric_time_values


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES_FILE = PROJECT_ROOT / "experiments" / "end2end" / "agent_benchmark_cases_extended.json"
DEFAULT_OUTPUT_ROOT = Path("/data/PrincipiaBlastFoam_output/deepagents_e2e_benchmark")
DEFAULT_TUTORIAL_PATH = Path(os.getenv("BLASTFOAM_TUTORIALS", "/data/graduation-projects/blastFoam_tutorials"))
CONTROL_NUMBER_RE = r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_cases(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("cases"), list):
        raise ValueError(f"Benchmark file has no cases list: {path}")
    return payload


def select_cases(cases: list[dict[str, Any]], limit: int | None, case_ids: list[str]) -> list[dict[str, Any]]:
    requested = set(case_ids)
    selected = [case for case in cases if not requested or case.get("id") in requested]
    if requested:
        found = {case.get("id") for case in selected}
        missing = sorted(requested - found)
        if missing:
            raise ValueError(f"Unknown benchmark case id(s): {', '.join(missing)}")
    if limit and limit > 0:
        selected = selected[:limit]
    return selected


def safe_case_dir_name(case_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", case_id).strip("_") or "case"


def command_for_case(args: argparse.Namespace, case_path: Path, user_request: str) -> list[str]:
    executable = PROJECT_ROOT / ".venv" / "bin" / "principia-deepagents"
    command = [
        str(executable),
        args.workflow_mode,
        "--case-path",
        str(case_path),
        "--user-request",
        user_request,
        "--tutorial-path",
        str(args.tutorial_path),
    ]
    if args.no_mcp:
        command.append("--no-mcp")
    if args.env_file:
        command.extend(["--env-file", str(args.env_file)])
    if args.model_profile:
        command.extend(["--model-profile", args.model_profile])
    elif args.llm_active_profile:
        command.extend(["--llm-active-profile", args.llm_active_profile])
    if args.retrieval_llm_active_profile:
        command.extend(["--retrieval-llm-active-profile", args.retrieval_llm_active_profile])
    if args.recursion_limit:
        command.extend(["--recursion-limit", str(args.recursion_limit)])
    if args.agent_timeout:
        command.extend(["--agent-timeout", str(args.agent_timeout)])
    if args.workflow_mode == "run" and args.execution_timeout_seconds:
        command.extend(["--execution-timeout-seconds", str(args.execution_timeout_seconds)])
    if args.workflow_mode == "prepare" and args.force_prepare:
        command.append("--force")
    if args.workflow_mode == "run" and args.skip_prepare:
        command.append("--skip-prepare")
    return command


def run_command(
    command: list[str],
    log_path: Path,
    timeout: int,
    *,
    dry_run: bool,
    enable_execution: bool,
    execution_user: str | None,
    chown_case: bool,
) -> dict[str, Any]:
    if dry_run:
        return {"exit_code": None, "elapsed_seconds": 0.0, "timed_out": False, "dry_run": True}

    started = time.time()
    timed_out = False
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env["ENABLE_EXECUTION"] = "true" if enable_execution else "false"
    env["REQUIRE_EXECUTION"] = "true" if enable_execution else "false"
    if execution_user:
        env["OPENFOAM_EXECUTION_USER"] = execution_user
        env["OPENFOAM_CHOWN_CASE"] = "true" if chown_case else "false"
    with log_path.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            start_new_session=True,
        )
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_process_group(process, signal.SIGTERM)
            try:
                exit_code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                _kill_process_group(process, signal.SIGKILL)
                exit_code = process.wait()
    return {
        "exit_code": exit_code,
        "elapsed_seconds": time.time() - started,
        "timed_out": timed_out,
        "dry_run": False,
    }


def load_benchmark_env(env_file: Path | None) -> None:
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)


def _legacy_profile_env_prefix(profile_name: str) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in profile_name.strip().upper())
    normalized = "_".join(part for part in normalized.split("_") if part)
    return f"LLM_PROFILE_{normalized}" if normalized else ""


def selected_model_profile(args: argparse.Namespace) -> str | None:
    return (
        args.model_profile
        or args.llm_active_profile
        or os.getenv("PRINCIPIA_MODEL_PROFILE")
        or os.getenv("LLM_ACTIVE_PROFILE")
    )


def model_profile_metadata(args: argparse.Namespace) -> dict[str, Any]:
    profile_name = selected_model_profile(args)
    payload: dict[str, Any] = {
        "requested_model_profile": args.model_profile,
        "legacy_llm_active_profile": args.llm_active_profile,
        "retrieval_llm_active_profile": args.retrieval_llm_active_profile,
        "resolved_profile": None,
    }
    if not profile_name:
        payload["legacy_llm_env"] = {
            "provider": os.getenv("LLM_PROVIDER"),
            "model": os.getenv("LLM_MODEL"),
            "base_url": os.getenv("LLM_API_BASE_URL"),
        }
        return payload

    profile = get_model_profile(profile_name)
    if profile is not None:
        _, selected_api_key_env = resolve_profile_api_key(profile)
        payload["resolved_profile"] = profile.public_metadata(selected_api_key_env=selected_api_key_env)
        return payload

    prefix = _legacy_profile_env_prefix(profile_name)
    payload["resolved_profile"] = {
        "id": normalize_profile_id(profile_name),
        "display_name": profile_name,
        "source": "legacy_llm_profile_env",
        "provider": os.getenv(f"{prefix}_PROVIDER"),
        "model": os.getenv(f"{prefix}_MODEL"),
        "base_url": os.getenv(f"{prefix}_API_BASE_URL") or os.getenv(f"{prefix}_BASE_URL"),
        "selected_api_key_env": f"{prefix}_API_KEY" if prefix else None,
    }
    return payload


def _kill_process_group(process: subprocess.Popen, sig: int) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def parse_selected_tutorial(log_text: str) -> str | None:
    patterns = [
        r"Initialized from ([A-Za-z0-9_./-]+)",
        r"'tutorial_case_path': '([^']+)'",
        r'"tutorial_case_path":\s*"([^"]+)"',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, log_text)
        if matches:
            return matches[-1]
    return None


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def parse_control_end_time_from_text(text: str) -> float | None:
    match = re.search(rf"\bendTime\s+([+-]?{CONTROL_NUMBER_RE})\s*;", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def find_control_dicts(case_path: Path) -> list[Path]:
    root_control = case_path / "system" / "controlDict"
    if root_control.exists():
        return [root_control]
    return sorted(path for path in case_path.glob("**/system/controlDict") if path.is_file())


def parse_control_end_times(case_path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    for control in find_control_dicts(case_path):
        text = control.read_text(encoding="utf-8", errors="ignore")
        value = parse_control_end_time_from_text(text)
        if value is not None:
            values[str(control.relative_to(case_path))] = value
    return values


def count_time_dirs(case_path: Path) -> int:
    return len(unique_numeric_time_values(discover_numeric_time_dirs(case_path)))


def preferred_case_matched(selected_tutorial: str | None, expected: dict[str, Any]) -> bool | None:
    keywords = expected.get("preferred_case_keywords")
    if not keywords:
        return None
    if not selected_tutorial:
        return False
    lowered = selected_tutorial.lower()
    return any(str(keyword).lower() in lowered for keyword in keywords)


def collect_summary(case_path: Path, log_path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    log_text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
    selected_tutorial = parse_selected_tutorial(log_text)
    reports = {
        name: (case_path / name).exists()
        for name in (
            "physics_report.md",
            "execution_report.md",
            "execution_status.json",
            "review_report.md",
            "artifact_contract.json",
            "workflow_evidence.md",
            "workflow_evidence.json",
            "post_processing_report.md",
        )
    }
    artifact_contract = read_json(case_path / "artifact_contract.json")
    execution_status = read_json(case_path / "execution_status.json")
    max_end_time = expected.get("max_end_time")
    end_times = parse_control_end_times(case_path)
    end_time = max(end_times.values()) if end_times else None
    return {
        "case_path": str(case_path),
        "log_path": str(log_path),
        "selected_tutorial": selected_tutorial,
        "reports": reports,
        "configured_end_time": end_time,
        "configured_end_times": end_times,
        "time_dir_count": count_time_dirs(case_path),
        "time_dir_locations": discover_numeric_time_dirs(case_path)[:40],
        "artifact_contract": artifact_contract,
        "execution_status": execution_status,
        "checks": {
            "selected_tutorial_matches_expected": preferred_case_matched(selected_tutorial, expected),
            "end_time_within_expected": (
                end_time is not None and max_end_time is not None and end_time <= float(max_end_time)
            )
            if max_end_time is not None
            else None,
            "artifact_contract_ok": artifact_contract.get("ok") is True if artifact_contract else None,
        },
    }


def result_passed(result: dict[str, Any]) -> bool:
    run = result.get("run") or {}
    checks = (result.get("summary") or {}).get("checks") or {}
    workflow_mode = result.get("workflow_mode")
    if run.get("dry_run"):
        return False
    if run.get("exit_code") != 0 or run.get("timed_out"):
        return False
    if checks.get("selected_tutorial_matches_expected") is False:
        return False
    if workflow_mode == "prepare":
        return True
    if checks.get("end_time_within_expected") is not True:
        return False
    if checks.get("artifact_contract_ok") is False:
        return False
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DeepAgents end-to-end benchmark adapter.")
    parser.add_argument("--cases-file", type=Path, default=DEFAULT_CASES_FILE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--tutorial-path", type=Path, default=DEFAULT_TUTORIAL_PATH)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--workflow-mode", choices=["prepare", "run"], default="run")
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--model-profile", default=None)
    parser.add_argument("--llm-active-profile", default=None)
    parser.add_argument("--retrieval-llm-active-profile", default=None)
    parser.add_argument("--recursion-limit", type=int, default=None)
    parser.add_argument("--agent-timeout", type=int, default=900)
    parser.add_argument("--execution-timeout-seconds", type=int, default=3600)
    parser.add_argument("--enable-execution", action="store_true")
    parser.add_argument(
        "--execution-user",
        default=None,
        help="Run solver subprocesses as this non-root user when --enable-execution is set.",
    )
    parser.add_argument(
        "--no-chown-case",
        action="store_true",
        help="Do not chown generated case directories before non-root solver execution.",
    )
    parser.add_argument("--no-mcp", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-prepare", action="store_true")
    parser.add_argument("--skip-prepare", action="store_true")
    parser.add_argument("--clean-output", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_benchmark_env(args.env_file)
    if not args.model_profile and not args.llm_active_profile:
        args.model_profile = os.getenv("PRINCIPIA_MODEL_PROFILE")
    payload = load_cases(args.cases_file)
    selected = select_cases(payload["cases"], args.limit, args.case_id)
    profile_metadata = model_profile_metadata(args)

    run_id = f"deepagents_{args.workflow_mode}_{utc_timestamp()}"
    output_root = args.output_root / run_id
    if args.clean_output and output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for index, case in enumerate(selected, start=1):
        case_id = str(case["id"])
        case_path = output_root / safe_case_dir_name(case_id)
        log_path = output_root / f"{safe_case_dir_name(case_id)}.log"
        command = command_for_case(args, case_path, case["user_request"])
        print(f"[{index}/{len(selected)}] {case_id}", flush=True)
        print("  " + " ".join(command), flush=True)
        run = run_command(
            command,
            log_path,
            args.timeout,
            dry_run=args.dry_run,
            enable_execution=args.enable_execution,
            execution_user=args.execution_user,
            chown_case=not args.no_chown_case,
        )
        summary = collect_summary(case_path, log_path, case.get("expected") or {})
        result = {
            "case_id": case_id,
            "title": case.get("title"),
            "workflow_mode": args.workflow_mode,
            "model_profile": profile_metadata,
            "command": command,
            "run": run,
            "summary": summary,
        }
        result["passed"] = result_passed(result)
        results.append(result)

    aggregate = {
        "total": len(results),
        "passed": sum(1 for result in results if result["passed"]),
        "failed": sum(1 for result in results if not result["passed"]),
    }
    output = {
        "benchmark": payload.get("name"),
        "benchmark_version": payload.get("version"),
        "run_id": run_id,
        "workflow_mode": args.workflow_mode,
        "model_profile": profile_metadata,
        "output_root": str(output_root),
        "aggregate": aggregate,
        "results": results,
    }
    output_path = output_root / "deepagents_benchmark_results.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"results": str(output_path), **aggregate}, ensure_ascii=False, indent=2))
    return 0 if aggregate["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
