from __future__ import annotations

import re
from typing import Dict, List


AGENT_ERROR_RE = re.compile(
    r"(error executing agent|connection error|api connection error|timeout|no output generated)",
    flags=re.IGNORECASE,
)
PLACEHOLDER_RESPONSE_RE = re.compile(
    r"^\s*(?:sorry[,\s]*)?(?:i\s+)?(?:need|require|would need)\s+"
    r"(?:more|additional)\s+(?:steps|time|information|context)\b"
    r"|^\s*(?:sorry[,\s]*)?(?:i\s+)?(?:cannot|can't|can not)\s+"
    r"(?:complete|process|finish)\s+this\s+request\b"
    r"|^\s*(?:please\s+)?(?:continue|provide more context)\b",
    flags=re.IGNORECASE,
)
RAW_TOOL_OUTPUT_RE = re.compile(
    r"^\s*(?:---\s*)?Retrieved Documentation Information(?:\s*---)?"
    r"|^\s*Observation:\s*"
    r"|^\s*Tool output:\s*",
    flags=re.IGNORECASE,
)


def _single_line(text: str, limit: int = 220) -> str:
    return " ".join((text or "").strip().split())[:limit]


def report_error_reasons(text: str) -> List[str]:
    content = text or ""
    stripped = content.strip()
    reasons: List[str] = []
    if not stripped:
        reasons.append("report is empty")
    if AGENT_ERROR_RE.search(content):
        reasons.append("report contains an agent/tool connection error")
    if PLACEHOLDER_RESPONSE_RE.search(stripped):
        reasons.append("report is a placeholder continuation response")
    if RAW_TOOL_OUTPUT_RE.search(stripped):
        reasons.append("report appears to be raw tool/retrieval output instead of an analysis report")
    return reasons


def validate_agent_report(text: str, report_name: str, min_chars: int = 80) -> Dict[str, object]:
    reasons = report_error_reasons(text)
    if len((text or "").strip()) < min_chars:
        reasons.append(f"{report_name} is shorter than the minimum content contract")
    return {
        "valid": not reasons,
        "reason": "; ".join(reasons),
        "reasons": reasons,
        "excerpt": _single_line(text),
    }


def build_report_repair_prompt(
    *,
    report_name: str,
    original_task: str,
    invalid_report: str,
    validation: Dict[str, object],
) -> str:
    reasons = validation.get("reasons") or []
    reason_text = "\n".join(f"- {reason}" for reason in reasons) or "- report failed validation"
    excerpt = _single_line(invalid_report, limit=600)
    return (
        f"The previous {report_name} did not satisfy the workflow report contract.\n"
        f"Validation issues:\n{reason_text}\n\n"
        f"Previous output excerpt:\n{excerpt}\n\n"
        f"Original task:\n{original_task}\n\n"
        "Produce a complete, self-contained Markdown report now. "
        "Do not ask for more steps, do not output raw tool results, and do not use placeholder text. "
        "If execution or validation failed, still write a concrete failure report with the command/log evidence "
        "available in the case directory."
    )
