from __future__ import annotations

from principia_deepagents.utils.report_contracts import report_error_reasons


def test_execution_report_timeout_fields_are_not_agent_errors() -> None:
    report = (
        "# Execution Report\n\n"
        "- Command: `./Allrun`\n"
        "- Timed out: `False`\n"
        "- Timeout seconds: `900`\n"
        "- Run status: `completed`\n"
        "- Final status: `success`\n"
    )

    assert report_error_reasons(report) == []


def test_agent_connection_error_is_rejected() -> None:
    report = "# Execution Report\n\nAPI connection error while calling model."

    assert "report contains an agent/tool connection error" in report_error_reasons(report)
