import os
import re
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..tools.mcp_retrieval_tools import get_mcp_retrieval_tools, set_retrieval_context
from ..tools.context import scoped_tool_context
from ..utils.report_contracts import build_report_repair_prompt, validate_agent_report
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
        output = result.get("output", "")
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
                output = retry_output
            validation = validate_agent_report(output, "review_report", min_chars=120)

        return output, validation

    def _prepare_workflow_evidence(self, case_path: str) -> str:
        if not case_path:
            return ""
        try:
            write_workflow_evidence(case_path)
        except Exception as exc:
            return f"Workflow evidence could not be generated: {exc}"

        evidence_path = os.path.join(case_path, EVIDENCE_MD_FILENAME)
        try:
            with open(evidence_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(12000)
        except OSError as exc:
            return f"Workflow evidence could not be read: {exc}"

    @track_agent_execution("reviewer")
    def review_task(self, state: GraphState) -> Dict[str, Any]:
        """
        Reviews the task result using the autonomous agent.
        """
        print("Reviewer Agent: Starting review (Autonomous Mode)...")
        
        user_request = state.get('user_request', '')
        case_path = state.get('case_path') or ""
        set_retrieval_context(state.get("tutorial_case_path"), user_request)
        workflow_evidence = self._prepare_workflow_evidence(case_path)
        
        input_text = (
            f"User Request: {user_request}\n"
            f"Case Path: {case_path}\n"
            f"Compact Workflow Evidence:\n{workflow_evidence}\n\n"
            f"Task: Review the simulation in {case_path}. \n"
            f"1. Verify if the simulation ran successfully.\n"
            f"2. Extract specific requirements from the 'User Request' and verify if the case configuration matches them.\n"
            f"3. Report back with a checklist and status."
            f"\nUse the Compact Workflow Evidence first. Avoid reading full solver logs, numeric time-directory field files, "
            f"or binary OpenFOAM fields unless a checklist item remains unresolved. Prefer targeted text_search "
            f"or small line ranges when extra evidence is required."
        )
        
        output, report_status = self._run_review_task(case_path, input_text)
        
        # Save the report to a file for other agents to use
        report_path = os.path.join(case_path, "review_report.md")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Reviewer Agent: Report saved to {report_path}")
        except Exception as e:
            print(f"Reviewer Agent: Warning - could not save report file: {e}")
        
        status = self._parse_validation_status(output) if report_status["valid"] else "failed"
            
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
