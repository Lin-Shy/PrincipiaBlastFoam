"""
Run a small end-to-end benchmark against the existing agent workflow.

This runner intentionally treats the agent system as a black box. It invokes
run_workflow.py with realistic short-runtime prompts, records basic performance
and effect signals, and periodically removes heavy OpenFOAM output directories.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import shlex

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:  # type: ignore[no-redef]
        return False


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from principia_ai.utils.solver_logs import solver_log_has_clean_end
from principia_ai.utils.execution_status import read_execution_status, status_run_completed

DEFAULT_CASES_FILE = PROJECT_ROOT / "experiments" / "end2end" / "agent_benchmark_cases.json"
DEFAULT_OUTPUT_ROOT = Path("/data/PrincipiaBlastFoam_output/e2e_agent_benchmark")
DEFAULT_TUTORIAL_PATH = Path(os.getenv("BLASTFOAM_TUTORIALS", "/data/graduation-projects/blastFoam_tutorials"))
NUMERIC_TIME_RE = re.compile(r"^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")


def load_cases(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("cases"), list):
        raise ValueError(f"Benchmark file has no cases list: {path}")
    return payload


def select_cases(cases: List[Dict[str, Any]], limit: Optional[int], case_ids: Iterable[str]) -> List[Dict[str, Any]]:
    requested = set(case_ids)
    selected = [case for case in cases if not requested or case.get("id") in requested]
    if requested:
        found = {case.get("id") for case in selected}
        missing = sorted(requested - found)
        if missing:
            raise ValueError(f"Unknown benchmark case id(s): {', '.join(missing)}")
    if limit is not None and limit > 0:
        selected = selected[:limit]
    return selected


def shell_join(parts: List[object]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def user_exists(username: str) -> bool:
    try:
        pwd.getpwnam(username)
    except KeyError:
        return False
    return True


def current_username() -> Optional[str]:
    try:
        return pwd.getpwuid(os.geteuid()).pw_name
    except KeyError:
        return None


def resolve_run_as_user(args: argparse.Namespace) -> Optional[str]:
    requested = (args.run_as_user or "").strip()
    if requested:
        if not user_exists(requested):
            raise SystemExit(f"OpenFOAM run user does not exist: {requested}")
        if requested == "root" and not args.allow_root_openfoam:
            raise SystemExit("--run-as-user root is disabled. Use a non-root user or pass --allow-root-openfoam.")
        if os.geteuid() != 0 and requested != current_username():
            raise SystemExit("--run-as-user can only switch users when the benchmark runner is started as root.")
        return requested if requested != current_username() else None

    if os.geteuid() != 0 or args.allow_root_openfoam:
        return None

    for candidate in ("openfoam", "foam", "ofuser"):
        if user_exists(candidate):
            print(f"Running OpenFOAM workflow as non-root user: {candidate}")
            return candidate

    raise SystemExit(
        "Benchmark runner is running as root. OpenFOAM cases with #calc/#codeStream should run as a "
        "non-root user. Pass --run-as-user USER, set OPENFOAM_RUN_AS_USER, or pass --allow-root-openfoam "
        "only when you explicitly accept root execution."
    )


def chown_tree(path: Path, username: Optional[str]) -> None:
    if not username or os.geteuid() != 0:
        return
    user = pwd.getpwnam(username)
    if not path.exists():
        return
    for root, dirs, files in os.walk(path):
        os.chown(root, user.pw_uid, user.pw_gid)
        for name in dirs:
            os.chown(os.path.join(root, name), user.pw_uid, user.pw_gid)
        for name in files:
            os.chown(os.path.join(root, name), user.pw_uid, user.pw_gid)


def wrap_command_for_user(command: str, run_as_user: Optional[str]) -> str:
    if not run_as_user or os.geteuid() != 0:
        return command
    return f"runuser -u {shlex.quote(run_as_user)} -- bash -lc {shlex.quote(command)}"


def build_workflow_command(args: argparse.Namespace, case_path: Path, user_request: str) -> str:
    workflow_args = [
        sys.executable,
        PROJECT_ROOT / "run_workflow.py",
        "--case-path",
        case_path,
        "--user-request",
        user_request,
        "--tutorial-path",
        args.tutorial_path,
        "--recursion-limit",
        args.recursion_limit,
    ]

    setup_parts: List[str] = []
    if not args.skip_openfoam_source:
        openfoam_bashrc = Path(args.openfoam_bashrc)
        blastfoam_bashrc = Path(args.blastfoam_bashrc)
        if openfoam_bashrc.exists():
            setup_parts.append(f"source {shlex.quote(str(openfoam_bashrc))} >/dev/null 2>&1")
        if blastfoam_bashrc.exists():
            setup_parts.append(
                f"MAKE=True source {shlex.quote(str(blastfoam_bashrc))} >/dev/null 2>&1"
            )

    setup_parts.append(f"ENABLE_EXECUTION=1 REQUIRE_EXECUTION=1 PYTHONUNBUFFERED=1 {shell_join(workflow_args)}")
    return wrap_command_for_user("; ".join(setup_parts), args.run_as_user)


def run_subprocess(command: str, log_path: Path, timeout: int) -> Dict[str, Any]:
    started = time.time()
    timed_out = False
    with log_path.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            ["bash", "-lc", command],
            cwd=PROJECT_ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
            preexec_fn=os.setsid,
            text=True,
        )
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                return_code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                return_code = process.wait()

    elapsed = time.time() - started
    return {
        "exit_code": return_code,
        "elapsed_seconds": elapsed,
        "timed_out": timed_out,
    }


def parse_control_end_time(case_path: Path) -> Optional[float]:
    control_dict = case_path / "system" / "controlDict"
    if not control_dict.exists():
        return None
    text = control_dict.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"\bendTime\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*;", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def count_time_dirs(case_path: Path) -> int:
    if not case_path.exists():
        return 0
    return sum(1 for child in case_path.iterdir() if child.is_dir() and NUMERIC_TIME_RE.match(child.name))


def newest_metrics_file(
    search_roots: Iterable[Path],
    started_at: float,
    user_request: Optional[str] = None,
) -> Optional[Path]:
    candidates: List[Path] = []
    for root in search_roots:
        metrics_dir = root / "metrics_reports"
        if not metrics_dir.exists():
            continue
        candidates.extend(
            path for path in metrics_dir.glob("metrics_*.json")
            if path.stat().st_mtime >= started_at - 2
        )
    if not candidates:
        return None
    if user_request:
        matching_candidates = []
        for path in candidates:
            payload = load_json(path)
            if payload and payload.get("user_request") == user_request:
                matching_candidates.append(path)
        candidates = matching_candidates
        if not candidates:
            return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_log_tail(log_path: Path, max_chars: int = 4000) -> str:
    if not log_path.exists():
        return ""
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    return text[-max_chars:]


def read_log(log_path: Path) -> str:
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8", errors="ignore")


def parse_selected_tutorial(log_text: str) -> Optional[str]:
    matches = re.findall(r"Successfully initialized case from tutorial:\s*(.+)", log_text)
    if not matches:
        return None
    return matches[-1].strip()


def solver_log_has_end(case_path: Path) -> bool:
    return solver_log_has_clean_end(case_path)


def preferred_case_matched(selected_tutorial: Optional[str], expected: Dict[str, Any]) -> Optional[bool]:
    keywords = expected.get("preferred_case_keywords")
    if not keywords:
        return None
    if not selected_tutorial:
        return False
    lowered = selected_tutorial.lower()
    return any(str(keyword).lower() in lowered for keyword in keywords)


def collect_case_summary(
    case_path: Path,
    log_path: Path,
    output_root: Path,
    started_at: float,
    expected: Dict[str, Any],
    user_request: Optional[str] = None,
) -> Dict[str, Any]:
    log_text = read_log(log_path)
    selected_tutorial = parse_selected_tutorial(log_text)
    report_files = {
        name: (case_path / name).exists()
        for name in (
            "physics_report.md",
            "execution_report.md",
            "execution_status.json",
            "review_report.md",
            "scaledDistance_modification.md",
        )
    }
    end_time = parse_control_end_time(case_path)
    metrics_path = newest_metrics_file((case_path.parent, output_root), started_at, user_request)
    metrics = load_json(metrics_path)
    max_end_time = expected.get("max_end_time")
    execution_status = read_execution_status(case_path)

    checks = {
        "physics_report_present": report_files["physics_report.md"],
        "execution_report_present": report_files["execution_report.md"],
        "execution_status_present": report_files["execution_status.json"],
        "execution_status_completed": status_run_completed(execution_status),
        "solver_log_has_end": solver_log_has_end(case_path),
        "end_time_within_expected": (
            end_time is not None and max_end_time is not None and end_time <= float(max_end_time)
        ) if max_end_time is not None else None,
        "workflow_log_has_completion_marker": "Workflow reached completion state" in log_text,
        "workflow_failure_absent": "Workflow Run Test Failed" not in log_text,
        "selected_tutorial_matches_expected": preferred_case_matched(selected_tutorial, expected),
        "case_selection_error_absent": "Error in LLM case selection" not in log_text,
        "orchestrator_empty_output_absent": "Orchestrator: Could not find JSON in output" not in log_text,
    }

    return {
        "case_path": str(case_path),
        "log_path": str(log_path),
        "selected_tutorial": selected_tutorial,
        "reports": report_files,
        "configured_end_time": end_time,
        "time_dir_count": count_time_dirs(case_path),
        "post_processing_present": (case_path / "postProcessing").exists(),
        "metrics_report": str(metrics_path) if metrics_path else None,
        "metrics_summary": summarize_metrics(metrics),
        "execution_status": execution_status,
        "checks": checks,
    }


def summarize_metrics(metrics: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not metrics:
        return None
    llm_calls = metrics.get("llm_calls")
    if isinstance(llm_calls, list):
        llm_call_count = len(llm_calls)
    elif isinstance(llm_calls, dict):
        llm_call_count = llm_calls.get("total_calls")
    else:
        llm_call_count = None

    total_tokens = metrics.get("total_tokens")
    if isinstance(total_tokens, dict):
        total_token_count = total_tokens.get("total")
    elif isinstance(llm_calls, dict):
        total_token_count = llm_calls.get("total_tokens")
    else:
        total_token_count = None

    return {
        "task_id": metrics.get("task_id"),
        "total_duration": metrics.get("total_duration"),
        "llm_calls": llm_call_count,
        "total_tokens": total_token_count,
        "agent_stats": metrics.get("agent_stats") or metrics.get("agent_executions"),
        "validation_results": metrics.get("validation_results"),
    }


def result_passed(result: Dict[str, Any]) -> bool:
    if result.get("dry_run"):
        return False
    run = result.get("run", {})
    summary = result.get("summary", {})
    checks = summary.get("checks", {})
    end_time_check = checks.get("end_time_within_expected")
    return bool(
        run.get("exit_code") == 0
        and not run.get("timed_out")
        and checks.get("physics_report_present")
        and checks.get("execution_report_present")
        and checks.get("execution_status_present")
        and checks.get("execution_status_completed")
        and checks.get("solver_log_has_end")
        and checks.get("workflow_log_has_completion_marker")
        and checks.get("workflow_failure_absent")
        and checks.get("case_selection_error_absent")
        and checks.get("orchestrator_empty_output_absent")
        and end_time_check is not False
        and checks.get("selected_tutorial_matches_expected") is not False
    )


def cleanup_simulation_outputs(case_path: Path, cleanup_logs: bool = False) -> Dict[str, Any]:
    removed: List[str] = []
    if not case_path.exists():
        return {"removed": removed, "bytes_freed": 0}

    before_size = directory_size(case_path)
    for child in list(case_path.iterdir()):
        should_remove = False
        if child.is_dir() and NUMERIC_TIME_RE.match(child.name) and child.name != "0":
            should_remove = True
        elif child.is_dir() and (child.name == "postProcessing" or child.name.startswith("processor")):
            should_remove = True
        elif child.is_file() and child.suffix == ".foam":
            should_remove = True
        elif cleanup_logs and child.is_file() and child.name.startswith("log."):
            should_remove = True

        if should_remove:
            removed.append(child.name)
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)

    after_size = directory_size(case_path)
    return {
        "removed": sorted(removed),
        "bytes_freed": max(0, before_size - after_size),
    }


def directory_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return total
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return total


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description="Run small end-to-end benchmarks for the Principia agent workflow.")
    parser.add_argument("--cases-file", type=Path, default=DEFAULT_CASES_FILE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--tutorial-path", type=Path, default=DEFAULT_TUTORIAL_PATH)
    parser.add_argument("--case-id", action="append", default=[], help="Run only this case id. Can be repeated.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workflow-timeout", type=int, default=900)
    parser.add_argument("--recursion-limit", type=int, default=80)
    parser.add_argument("--cleanup-interval", type=int, default=2, help="Clean heavy outputs after every N completed cases.")
    parser.add_argument("--cleanup-final", action="store_true", help="Clean heavy outputs for any remaining cases at the end.")
    parser.add_argument("--cleanup-logs", action="store_true", help="Also remove log.* files during cleanup.")
    parser.add_argument("--dry-run", action="store_true", help="Only print the selected cases and commands.")
    parser.add_argument("--skip-openfoam-source", action="store_true")
    parser.add_argument("--openfoam-bashrc", default="/data/OpenFOAM/OpenFOAM-9/etc/bashrc")
    parser.add_argument("--blastfoam-bashrc", default="/data/OpenFOAM/blastfoam/etc/bashrc")
    parser.add_argument(
        "--run-as-user",
        default=os.getenv("OPENFOAM_RUN_AS_USER") or os.getenv("PRINCIPIA_OPENFOAM_USER") or "",
        help="Run each workflow/OpenFOAM subprocess as this non-root user. Defaults to OPENFOAM_RUN_AS_USER.",
    )
    parser.add_argument(
        "--allow-root-openfoam",
        action="store_true",
        help="Allow running OpenFOAM as root. Not recommended for tutorials using #calc/#codeStream.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.run_as_user = resolve_run_as_user(args)
    benchmark = load_cases(args.cases_file)
    selected_cases = select_cases(benchmark["cases"], args.limit, args.case_id)
    if not selected_cases:
        raise SystemExit("No benchmark cases selected.")

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_root = args.output_root.resolve()
    run_root = output_root / f"run_{run_id}"
    run_root.mkdir(parents=True, exist_ok=True)
    chown_tree(run_root, args.run_as_user)

    print(f"Benchmark: {benchmark.get('name')} ({len(selected_cases)} case(s))")
    print(f"Output root: {output_root}")
    print(f"Run root: {run_root}")

    results: List[Dict[str, Any]] = []
    pending_cleanup: List[Path] = []

    for index, case in enumerate(selected_cases, start=1):
        case_id = str(case["id"])
        case_path = run_root / "cases" / case_id
        log_path = run_root / "logs" / f"{case_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        case_path.parent.mkdir(parents=True, exist_ok=True)
        chown_tree(run_root, args.run_as_user)

        command = build_workflow_command(args, case_path, str(case["user_request"]))
        print(f"\n[{index}/{len(selected_cases)}] {case_id}: {case.get('title', '')}")
        print(f"Case path: {case_path}")
        print(f"Log path: {log_path}")

        if args.dry_run:
            print(f"Command: {command}")
            results.append({"case_id": case_id, "dry_run": True, "case_path": str(case_path), "log_path": str(log_path)})
            continue

        started_at = time.time()
        run_result = run_subprocess(command, log_path, timeout=args.workflow_timeout)
        summary = collect_case_summary(
            case_path,
            log_path,
            output_root,
            started_at,
            case.get("expected", {}),
            case.get("prompt"),
        )
        result = {
            "case_id": case_id,
            "title": case.get("title"),
            "tags": case.get("tags", []),
            "difficulty": case.get("difficulty"),
            "run": run_result,
            "summary": summary,
        }
        result["benchmark_passed"] = result_passed(result)
        results.append(result)
        pending_cleanup.append(case_path)

        print(
            f"Result: exit={run_result['exit_code']} timeout={run_result['timed_out']} "
            f"elapsed={run_result['elapsed_seconds']:.1f}s endTime={summary['configured_end_time']} "
            f"timeDirs={summary['time_dir_count']}"
        )

        if args.cleanup_interval > 0 and len(pending_cleanup) >= args.cleanup_interval:
            for path in pending_cleanup:
                cleanup = cleanup_simulation_outputs(path, cleanup_logs=args.cleanup_logs)
                result_for_path = next(item for item in results if item.get("summary", {}).get("case_path") == str(path))
                result_for_path["cleanup"] = cleanup
                print(f"Cleaned {path.name}: removed={len(cleanup['removed'])} freed={cleanup['bytes_freed']} bytes")
            pending_cleanup = []

        write_json(run_root / "benchmark_partial.json", build_report(benchmark, results, run_id, args))

    if args.cleanup_final and pending_cleanup:
        for path in pending_cleanup:
            cleanup = cleanup_simulation_outputs(path, cleanup_logs=args.cleanup_logs)
            result_for_path = next(item for item in results if item.get("summary", {}).get("case_path") == str(path))
            result_for_path["cleanup"] = cleanup
            print(f"Cleaned {path.name}: removed={len(cleanup['removed'])} freed={cleanup['bytes_freed']} bytes")

    report = build_report(benchmark, results, run_id, args)
    report_path = run_root / "benchmark_report.json"
    write_json(report_path, report)
    print(f"\nBenchmark report: {report_path}")


def build_report(benchmark: Dict[str, Any], results: List[Dict[str, Any]], run_id: str, args: argparse.Namespace) -> Dict[str, Any]:
    completed = [item for item in results if not item.get("dry_run")]
    passed = sum(1 for item in completed if result_passed(item))
    return {
        "run_id": run_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "benchmark": {
            "name": benchmark.get("name"),
            "version": benchmark.get("version"),
            "sources": benchmark.get("sources", []),
        },
        "settings": {
            "workflow_timeout": args.workflow_timeout,
            "recursion_limit": args.recursion_limit,
            "cleanup_interval": args.cleanup_interval,
            "cleanup_final": args.cleanup_final,
            "cleanup_logs": args.cleanup_logs,
            "tutorial_path": str(args.tutorial_path),
            "run_as_user": args.run_as_user,
            "allow_root_openfoam": args.allow_root_openfoam,
        },
        "aggregate": {
            "cases_total": len(results),
            "cases_executed": len(completed),
            "exit_code_zero": sum(1 for item in completed if item["run"]["exit_code"] == 0),
            "timed_out": sum(1 for item in completed if item["run"]["timed_out"]),
            "physics_reports": sum(1 for item in completed if item["summary"]["reports"].get("physics_report.md")),
            "execution_reports": sum(1 for item in completed if item["summary"]["reports"].get("execution_report.md")),
            "execution_status_files": sum(1 for item in completed if item["summary"]["reports"].get("execution_status.json")),
            "benchmark_passed": passed,
            "benchmark_pass_rate": (passed / len(completed)) if completed else 0.0,
        },
        "results": results,
    }


if __name__ == "__main__":
    main()
