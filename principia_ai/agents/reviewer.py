import os
import re
import json
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..utils.execution_status import read_execution_status, status_run_completed
from ..tools.mcp_retrieval_tools import get_mcp_retrieval_tools, set_retrieval_context
from ..tools.context import scoped_tool_context
from ..utils.report_contracts import (
    build_report_repair_prompt,
    compact_agent_report,
    report_length_instruction,
    validate_agent_report,
)
from ..utils.workflow_artifacts import validate_workflow_artifacts
from ..utils.workflow_evidence import EVIDENCE_MD_FILENAME, write_workflow_evidence

from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools

class ReviewerAgent:
    """
    Reviewer Agent - Refactored to use BaseAgent.
    """

    def __init__(
        self,
        llm,
        use_knowledge_manager=True,
        use_tutorial_retriever=True,
        retrieval_llm_api_key=None,
        retrieval_llm_base_url=None,
        retrieval_llm_model=None,
    ):
        self.llm = llm
        self.prompt_manager = PromptManager()
        
        # Initialize Tools
        self.agent_tools = get_read_tools() + get_search_tools()
        self.agent_tools.extend(get_mcp_retrieval_tools(use_knowledge_manager, use_tutorial_retriever))
        
        # Load System Prompt
        self.system_prompt = self.prompt_manager.load_prompt("reviewer", "react_system")

        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="ReviewerAgent",
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50"))
        )

    def _parse_validation_status(self, output: str) -> str:
        """Parse the required status line before falling back to coarse heuristics."""
        text = output or ""
        for line in text.splitlines()[:80]:
            normalized = re.sub(r"[*_`>#\[\]()]|\s+", " ", line).strip().lower()
            match = re.search(
                r"\b(?:validation\s+status|status)\s*[:：-]?\s*(passed|pass|failed|fail|partial)\b",
                normalized,
            )
            if match:
                status = match.group(1)
                return "passed" if status in {"passed", "pass"} else "failed"

        lowered = text.lower()
        explicit_failure_patterns = (
            r"\bvalidation\s+(?:status\s*[:：-]\s*)?failed\b",
            r"\brequirements?\s+(?:are\s+)?not\s+satisfied\b",
            r"\bchecklist\s+(?:is\s+)?not\s+satisfied\b",
            r"\bblocking\s+(?:issue|failure|error)s?\b",
        )
        if any(re.search(pattern, lowered) for pattern in explicit_failure_patterns):
            return "failed"
        return "passed"

    def _run_review_task(self, case_path: str, input_text: str) -> tuple[str, Dict[str, Any]]:
        with scoped_tool_context(case_path):
            result = self.agent.invoke({"input": input_text})
        output = compact_agent_report(result.get("output", ""), "review_report")
        validation = validate_agent_report(output, "review_report", min_chars=120)

        max_repairs = int(os.getenv("REPORT_REPAIR_ATTEMPTS", "1"))
        for _attempt in range(max_repairs):
            if validation["valid"]:
                break
            print(f"Reviewer Agent: review_report contract failed; retrying once: {validation['reason']}")
            repair_prompt = build_report_repair_prompt(
                report_name="review_report.md",
                original_task=input_text,
                invalid_report=output,
                validation=validation,
            )
            with scoped_tool_context(case_path):
                retry_result = self.agent.invoke({"input": repair_prompt})
            retry_output = retry_result.get("output", "")
            if retry_output.strip():
                output = compact_agent_report(retry_output, "review_report")
            validation = validate_agent_report(output, "review_report", min_chars=120)

        return output, validation

    def _prepare_workflow_evidence(self, case_path: str) -> tuple[Dict[str, Any], str]:
        if not case_path:
            return {}, ""
        try:
            evidence = write_workflow_evidence(case_path)
        except Exception as exc:
            return {}, f"Workflow evidence could not be generated: {exc}"

        evidence_path = os.path.join(case_path, EVIDENCE_MD_FILENAME)
        try:
            with open(evidence_path, "r", encoding="utf-8", errors="ignore") as f:
                max_chars = int(os.getenv("REVIEW_EVIDENCE_MAX_CHARS", "6000"))
                return evidence, f.read(max(1000, min(max_chars, 12000)))
        except OSError as exc:
            return evidence, f"Workflow evidence could not be read: {exc}"

    def _build_deterministic_review(
        self,
        state: GraphState,
        evidence: Dict[str, Any],
    ) -> Dict[str, Any]:
        case_path = state.get("case_path") or ""
        execution_status = state.get("execution_status")
        if not isinstance(execution_status, dict):
            execution_status = evidence.get("execution_status")
        if not isinstance(execution_status, dict) and case_path:
            execution_status = read_execution_status(case_path)

        contract = validate_workflow_artifacts(
            case_path,
            {**state, "execution_status": execution_status},
            require_execution=True,
            require_review=False,
        )
        checks = contract.get("checks") or {}
        diagnostics_summary = contract.get("openfoam_diagnostics_summary") or {}
        solver = evidence.get("solver") or {}

        checklist = [
            {
                "name": "physics_report.md valid",
                "passed": bool(checks.get("physics_report_valid")),
                "evidence": "artifact contract",
            },
            {
                "name": "execution_report.md valid",
                "passed": bool(checks.get("execution_report_valid")),
                "evidence": "artifact contract",
            },
            {
                "name": "execution_status.json present",
                "passed": bool(checks.get("execution_status_present")),
                "evidence": "execution_status.json",
            },
            {
                "name": "execution status completed",
                "passed": status_run_completed(execution_status),
                "evidence": (execution_status or {}).get("status_reason"),
            },
            {
                "name": "solver log has clean End marker",
                "passed": bool(solver.get("clean_end")),
                "evidence": ", ".join(solver.get("logs") or []),
            },
            {
                "name": "OpenFOAM blocking diagnostics absent",
                "passed": diagnostics_summary.get("blocking", 0) == 0,
                "evidence": diagnostics_summary,
            },
        ]
        failed = [item for item in checklist if not item["passed"]]
        status = "passed" if not failed and contract.get("ok") else "failed"
        return {
            "validation_status": status,
            "user_request": state.get("user_request", ""),
            "case_path": case_path,
            "checklist": checklist,
            "artifact_contract_ok": bool(contract.get("ok")),
            "artifact_contract_issues": contract.get("issues") or [],
            "execution_status": {
                "run_status": (execution_status or {}).get("run_status"),
                "final_status": (execution_status or {}).get("final_status"),
                "status_source": (execution_status or {}).get("status_source"),
                "status_reason": (execution_status or {}).get("status_reason"),
            },
            "control": evidence.get("control") or {},
            "time_dir_count": evidence.get("time_dir_count"),
            "post_processing": evidence.get("post_processing") or {},
        }

    def _format_deterministic_review_report(self, review_data: Dict[str, Any]) -> str:
        status = review_data.get("validation_status", "failed")
        lines = [
            "# Review Report",
            "",
            f"Validation Status: {'Passed' if status == 'passed' else 'Failed'}",
            "",
            "## Deterministic Checklist",
        ]
        for item in review_data.get("checklist") or []:
            mark = "PASS" if item.get("passed") else "FAIL"
            evidence = item.get("evidence")
            lines.append(f"- {mark}: {item.get('name')} ({evidence})")

        issues = review_data.get("artifact_contract_issues") or []
        lines.extend(["", "## Artifact Issues"])
        if issues:
            lines.extend(f"- {issue}" for issue in issues)
        else:
            lines.append("- None detected by deterministic artifact checks.")

        lines.extend(
            [
                "",
                "## Summary",
                (
                    "The deterministic checks passed; the case has the required execution artifacts."
                    if status == "passed"
                    else "One or more deterministic checks failed; inspect execution_status.json and workflow_evidence.md."
                ),
            ]
        )
        return compact_agent_report("\n".join(lines).rstrip() + "\n", "review_report")

    def _response_text(self, response: Any) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    text = block.get("text") or block.get("content")
                    if text:
                        parts.append(str(text))
            return "\n".join(parts)
        return str(content)

    @track_llm_call("ReviewerAgent")
    def _invoke_review_summary_llm(self, input_text: str):
        return self.llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You write concise CFD workflow review summaries from deterministic check data. "
                        "Do not call tools, do not request more steps, and do not override the supplied validation status."
                    )
                ),
                HumanMessage(content=input_text),
            ]
        )

    def _run_programmatic_review_summary(
        self,
        case_path: str,
        input_text: str,
        review_data: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        if getattr(self, "llm", None) is not None:
            try:
                response = self._invoke_review_summary_llm(input_text)
                output = compact_agent_report(self._response_text(response), "review_report")
            except Exception:
                fallback = self._format_deterministic_review_report(review_data)
                return fallback, validate_agent_report(fallback, "review_report", min_chars=120)
        else:
            output, validation = self._run_review_task(case_path, input_text)
            if validation["valid"]:
                return output, validation

        validation = validate_agent_report(output, "review_report", min_chars=120)
        if validation["valid"]:
            return output, validation

        fallback = self._format_deterministic_review_report(review_data)
        return fallback, validate_agent_report(fallback, "review_report", min_chars=120)

    @track_agent_execution("reviewer")
    def review_task(self, state: GraphState) -> Dict[str, Any]:
        """
        Reviews the task result using the autonomous agent.
        """
        print("Reviewer Agent: Starting review (Autonomous Mode)...")
        
        user_request = state.get('user_request', '')
        case_path = state.get('case_path') or ""
        set_retrieval_context(state.get("tutorial_case_path"), user_request)
        evidence, workflow_evidence = self._prepare_workflow_evidence(case_path)
        review_data = self._build_deterministic_review(state, evidence)
        review_json = json.dumps(review_data, ensure_ascii=False, indent=2)[:6000]
        
        input_text = (
            f"User Request: {user_request}\n"
            f"Case Path: {case_path}\n"
            f"Deterministic Review Data:\n{review_json}\n\n"
            f"Compact Workflow Evidence:\n{workflow_evidence}\n\n"
            f"Task: Write a concise review_report.md summary using only the deterministic review data above. "
            f"The validation status is already decided as {review_data['validation_status']}; do not change it. "
            f"Report a short checklist and the main evidence files."
            f"\nUse the Compact Workflow Evidence first. Avoid reading full solver logs, numeric time-directory field files, "
            f"or binary OpenFOAM fields unless a checklist item remains unresolved. Prefer targeted text_search "
            f"or small line ranges when extra evidence is required. {report_length_instruction('review_report')}"
        )
        
        output, report_status = self._run_programmatic_review_summary(case_path, input_text, review_data)
        
        # Save the report to a file for other agents to use
        report_path = os.path.join(case_path, "review_report.md")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Reviewer Agent: Report saved to {report_path}")
        except Exception as e:
            print(f"Reviewer Agent: Warning - could not save report file: {e}")
        
        status = review_data["validation_status"] if report_status["valid"] else "failed"
            
        print(f"Reviewer Agent: Review complete. Status: {status}")
        
        state_update = {
            "validation_status": status,
            "validation_notes": output,
            "review_report_status": "completed" if report_status["valid"] else "failed",
            # "issue_details": {} # Could be parsed if we structured the output
        }
        if not report_status["valid"]:
            state_update["workflow_error"] = f"review_report.md failed artifact contract: {report_status['reason']}"
        return state_update
