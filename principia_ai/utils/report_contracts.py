from __future__ import annotations

import re
from typing import Dict, List


AGENT_ERROR_RE = re.compile(
    r"(error executing agent|connection error|api connection error|timeout|no output generated)",
    flags=re.IGNORECASE,
)


def report_error_reasons(text: str) -> List[str]:
    content = text or ""
    reasons: List[str] = []
    if not content.strip():
        reasons.append("report is empty")
    if AGENT_ERROR_RE.search(content):
        reasons.append("report contains an agent/tool connection error")
    return reasons


def validate_agent_report(text: str, report_name: str, min_chars: int = 80) -> Dict[str, object]:
    reasons = report_error_reasons(text)
    if len((text or "").strip()) < min_chars:
        reasons.append(f"{report_name} is shorter than the minimum content contract")
    return {
        "valid": not reasons,
        "reason": "; ".join(reasons),
        "reasons": reasons,
    }
