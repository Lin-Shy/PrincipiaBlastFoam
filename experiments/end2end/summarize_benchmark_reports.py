#!/usr/bin/env python3
"""Summarize end-to-end benchmark reports into tables and lightweight SVG charts."""

from __future__ import annotations

import argparse
import csv
import html
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_REPORT_GLOB = "/data/PrincipiaBlastFoam_output/e2e_agent_benchmark/run_*/benchmark_report.json"
DEFAULT_OUTPUT_ROOT = Path("/data/PrincipiaBlastFoam_output/e2e_agent_benchmark_analysis")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bool_score(value: Any) -> Optional[float]:
    if value is None:
        return None
    return 1.0 if bool(value) else 0.0


def partial_score(result: Dict[str, Any]) -> Optional[float]:
    if result.get("dry_run"):
        return None
    run = result.get("run") or {}
    summary = result.get("summary") or {}
    checks = summary.get("checks") or {}

    values: List[Optional[float]] = [
        bool_score(run.get("exit_code") == 0),
        bool_score(not run.get("timed_out")),
        bool_score(checks.get("physics_report_present")),
        bool_score(checks.get("execution_report_present")),
        bool_score(checks.get("execution_status_present")),
        bool_score(checks.get("execution_status_completed")),
        bool_score(checks.get("solver_log_has_end")),
        bool_score(checks.get("end_time_within_expected")),
        bool_score(checks.get("workflow_log_has_completion_marker")),
        bool_score(checks.get("workflow_failure_absent")),
        bool_score(checks.get("case_selection_error_absent")),
        bool_score(checks.get("orchestrator_empty_output_absent")),
    ]

    tutorial_match = checks.get("selected_tutorial_matches_expected")
    if tutorial_match is not None:
        values.append(bool_score(tutorial_match))

    scored = [value for value in values if value is not None]
    return round(sum(scored) / len(scored), 4) if scored else None


def result_to_row(report_path: Path, report: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    run = result.get("run") or {}
    summary = result.get("summary") or {}
    checks = summary.get("checks") or {}
    metrics = summary.get("metrics_summary") or {}
    row: Dict[str, Any] = {
        "report_path": str(report_path),
        "run_id": report.get("run_id"),
        "created_at": report.get("created_at"),
        "benchmark_name": (report.get("benchmark") or {}).get("name"),
        "case_id": result.get("case_id"),
        "title": result.get("title"),
        "difficulty": result.get("difficulty"),
        "dry_run": bool(result.get("dry_run")),
        "benchmark_passed": result.get("benchmark_passed"),
        "partial_score": partial_score(result),
        "exit_code": run.get("exit_code"),
        "timed_out": run.get("timed_out"),
        "elapsed_seconds": run.get("elapsed_seconds"),
        "selected_tutorial": summary.get("selected_tutorial"),
        "configured_end_time": summary.get("configured_end_time"),
        "time_dir_count": summary.get("time_dir_count"),
        "post_processing_present": summary.get("post_processing_present"),
        "metrics_report": summary.get("metrics_report"),
        "metrics_total_duration": metrics.get("total_duration"),
        "metrics_llm_calls": metrics.get("llm_calls"),
        "metrics_total_tokens": metrics.get("total_tokens"),
    }
    for key, value in checks.items():
        row[f"check_{key}"] = value
    return row


def flatten_reports(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in sorted(paths):
        report = load_json(path)
        for result in report.get("results", []):
            rows.append(result_to_row(path, report, result))
    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    keys = sorted({key for row in rows for key in row.keys()})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def failure_reasons(rows: List[Dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        if row.get("dry_run") or row.get("benchmark_passed") is True:
            continue
        if row.get("exit_code") not in (0, None, ""):
            counter["exit_code_nonzero"] += 1
        if row.get("timed_out") is True:
            counter["timed_out"] += 1
        for key, value in row.items():
            if key.startswith("check_") and value is False:
                counter[key.removeprefix("check_")] += 1
    return counter


def summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    executed = [row for row in rows if not row.get("dry_run")]
    strict_passed = [row for row in executed if row.get("benchmark_passed") is True]
    partial_scores = [row["partial_score"] for row in executed if row.get("partial_score") is not None]

    by_case: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_run: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in executed:
        by_case[str(row.get("case_id"))].append(row)
        by_run[str(row.get("run_id"))].append(row)

    return {
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rows_total": len(rows),
        "executed_total": len(executed),
        "strict_passed": len(strict_passed),
        "strict_pass_rate": round(len(strict_passed) / len(executed), 4) if executed else 0.0,
        "mean_partial_score": round(mean(partial_scores), 4) if partial_scores else None,
        "cases": {
            case_id: {
                "runs": len(case_rows),
                "strict_pass_rate": round(
                    sum(1 for row in case_rows if row.get("benchmark_passed") is True) / len(case_rows),
                    4,
                ),
                "mean_partial_score": round(
                    mean(row["partial_score"] for row in case_rows if row.get("partial_score") is not None),
                    4,
                )
                if any(row.get("partial_score") is not None for row in case_rows)
                else None,
            }
            for case_id, case_rows in sorted(by_case.items())
        },
        "runs": {
            run_id: {
                "cases": len(run_rows),
                "strict_pass_rate": round(
                    sum(1 for row in run_rows if row.get("benchmark_passed") is True) / len(run_rows),
                    4,
                ),
                "mean_partial_score": round(
                    mean(row["partial_score"] for row in run_rows if row.get("partial_score") is not None),
                    4,
                )
                if any(row.get("partial_score") is not None for row in run_rows)
                else None,
            }
            for run_id, run_rows in sorted(by_run.items())
        },
        "failure_reasons": dict(failure_reasons(executed).most_common()),
    }


def bar_svg(title: str, data: Dict[str, float], path: Path, x_label_rotate: bool = False) -> None:
    width = 920
    height = 460
    margin_left = 70
    margin_right = 30
    margin_top = 60
    margin_bottom = 140 if x_label_rotate else 90
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    items = list(data.items())
    max_value = max([value for _, value in items] + [1.0])
    bar_gap = 10
    bar_width = max(10, (plot_width - bar_gap * max(0, len(items) - 1)) / max(1, len(items)))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{width / 2}" y="32" text-anchor="middle" font-family="Arial" font-size="20" font-weight="700">{html.escape(title)}</text>',
        f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" stroke="#333"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#333"/>',
    ]

    for tick in range(0, 6):
        value = max_value * tick / 5
        y = margin_top + plot_height - (value / max_value) * plot_height
        parts.append(f'<line x1="{margin_left - 5}" y1="{y:.1f}" x2="{margin_left + plot_width}" y2="{y:.1f}" stroke="#e6e6e6"/>')
        parts.append(f'<text x="{margin_left - 10}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{value:.2f}</text>')

    for index, (label, value) in enumerate(items):
        x = margin_left + index * (bar_width + bar_gap)
        bar_height = (value / max_value) * plot_height if max_value else 0
        y = margin_top + plot_height - bar_height
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="#3973b7"/>')
        parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-family="Arial" font-size="11">{value:.2f}</text>')
        escaped = html.escape(label)
        if x_label_rotate:
            tx = x + bar_width / 2
            ty = margin_top + plot_height + 18
            parts.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="end" font-family="Arial" font-size="11" transform="rotate(-35 {tx:.1f} {ty:.1f})">{escaped}</text>')
        else:
            parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{margin_top + plot_height + 22}" text-anchor="middle" font-family="Arial" font-size="11">{escaped}</text>')

    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: Dict[str, Any], output_files: List[str]) -> None:
    lines = [
        "# Benchmark结果汇总",
        "",
        f"- 生成时间: {summary['created_at']}",
        f"- 逐案例记录数: {summary['rows_total']}",
        f"- 已执行记录数: {summary['executed_total']}",
        f"- 严格通过数: {summary['strict_passed']}",
        f"- 严格通过率: {summary['strict_pass_rate']:.4f}",
        f"- 平均部分得分: {summary['mean_partial_score']}",
        "",
        "## 按案例统计",
        "",
        "| case | runs | strict_pass_rate | mean_partial_score |",
        "| --- | ---: | ---: | ---: |",
    ]
    for case_id, item in summary["cases"].items():
        lines.append(
            f"| `{case_id}` | {item['runs']} | {item['strict_pass_rate']:.4f} | {item['mean_partial_score']} |"
        )

    lines.extend(["", "## 失败原因计数", "", "| reason | count |", "| --- | ---: |"])
    for reason, count in summary["failure_reasons"].items():
        lines.append(f"| `{reason}` | {count} |")

    lines.extend(["", "## 输出文件", ""])
    for name in output_files:
        lines.append(f"- `{name}`")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize PrincipiaBlastFoam end-to-end benchmark reports.")
    parser.add_argument("--reports-glob", default=DEFAULT_REPORT_GLOB)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = sorted(Path("/").glob(args.reports_glob.removeprefix("/"))) if args.reports_glob.startswith("/") else sorted(Path().glob(args.reports_glob))
    if not paths:
        raise SystemExit(f"No benchmark reports matched: {args.reports_glob}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_root / f"run_{run_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = flatten_reports(paths)
    summary = summarize_rows(rows)

    csv_path = output_dir / "benchmark_case_rows.csv"
    rows_json_path = output_dir / "benchmark_case_rows.json"
    summary_json_path = output_dir / "summary.json"
    markdown_path = output_dir / "summary.md"

    write_csv(csv_path, rows)
    write_json(rows_json_path, rows)
    write_json(summary_json_path, summary)

    run_rates = {run_id: item["strict_pass_rate"] for run_id, item in summary["runs"].items()}
    case_scores = {
        case_id: item["mean_partial_score"]
        for case_id, item in summary["cases"].items()
        if item["mean_partial_score"] is not None
    }
    failures = {reason: float(count) for reason, count in summary["failure_reasons"].items()}

    pass_svg = output_dir / "pass_rate_by_run.svg"
    score_svg = output_dir / "partial_score_by_case.svg"
    failure_svg = output_dir / "failure_reason_counts.svg"
    bar_svg("Strict pass rate by run", run_rates, pass_svg, x_label_rotate=True)
    bar_svg("Mean partial score by case", case_scores, score_svg, x_label_rotate=True)
    bar_svg("Failure reason counts", failures, failure_svg, x_label_rotate=True)

    output_files = [
        csv_path.name,
        rows_json_path.name,
        summary_json_path.name,
        markdown_path.name,
        pass_svg.name,
        score_svg.name,
        failure_svg.name,
    ]
    write_markdown(markdown_path, summary, output_files)

    print(f"Wrote benchmark analysis to {output_dir}")


if __name__ == "__main__":
    main()
