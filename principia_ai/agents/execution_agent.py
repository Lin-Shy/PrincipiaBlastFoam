import os
import json
import re
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..tools.mcp_retrieval_tools import get_mcp_retrieval_tools, set_retrieval_context
from ..tools.context import scoped_tool_context
from ..utils.execution_preflight import format_preflight_report, run_execution_preflight
from ..utils.execution_status import build_execution_status, write_execution_status
from ..utils.openfoam_diagnostics import summarize_diagnostics
from ..utils.report_contracts import (
    build_report_repair_prompt,
    compact_agent_report,
    report_length_instruction,
    validate_agent_report,
)
from ..utils.workflow_evidence import write_workflow_evidence

# New imports
from .base_agent import BaseAgent
from ..tools.standard_tools import get_execute_tools, get_read_tools, get_edit_tools, get_search_tools

class ExecutionAgent:
    """
    Execution Agent - Refactored to use BaseAgent.
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
        self.agent_tools = get_execute_tools() + get_read_tools() + get_edit_tools() + get_search_tools()
        self.agent_tools.extend(get_mcp_retrieval_tools(use_knowledge_manager, use_tutorial_retriever))
        
        # Load System Prompt
        try:
            self.system_prompt = self.prompt_manager.load_prompt("execution_agent", "react_system")
        except Exception as e:
            print(f"Warning: Could not load react_system prompt: {e}. Using default.")
            self.system_prompt = (
                "You are the Execution Agent. Responsible for writing Allrun/Allclean scripts, executing them, "
                "and analyzing logs. If Allrun fails due to script errors, fix it. "
                "If it fails due to basic case config errors, fix them. "
                "Only report to Orchestrator if the config error is complex or unfixable."
            )

        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="ExecutionAgent",
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50"))
        )

    def _parse_execution_status(self, output: str) -> str:
        """Prefer explicit execution status over incidental words like 'errors'."""
        text = output or ""
        lowered = text.lower()
        first_lines = "\n".join(text.splitlines()[:8]).lower()

        if re.search(r"execution\s+failed|final status:\s*\n?\s*-\s*execution failed", lowered):
            return "failed"
        if re.search(
            r"execution completed successfully|execution\s+succeeded|final status:\s*\n?\s*-\s*execution (completed|succeeded|successful)",
            lowered,
        ):
            return "completed"
        if "completed successfully" in first_lines:
            return "completed"

        if "foam fatal" in lowered or "traceback" in lowered:
            return "failed"
        if "failed" in first_lines:
            return "failed"

        return "completed"

    def _run_report_task(self, case_path: str, input_text: str) -> tuple[str, Dict[str, Any]]:
        with scoped_tool_context(case_path):
            result = self.agent.invoke({"input": input_text})
        output = compact_agent_report(result.get("output", ""), "execution_report")
        validation = validate_agent_report(output, "execution_report", min_chars=120)

        max_repairs = int(os.getenv("REPORT_REPAIR_ATTEMPTS", "1"))
        for _attempt in range(max_repairs):
            if validation["valid"]:
                break
            print(f"Execution Agent: execution_report contract failed; retrying once: {validation['reason']}")
            repair_prompt = build_report_repair_prompt(
                report_name="execution_report.md",
                original_task=input_text,
                invalid_report=output,
                validation=validation,
            )
            with scoped_tool_context(case_path):
                retry_result = self.agent.invoke({"input": repair_prompt})
            retry_output = retry_result.get("output", "")
            if retry_output.strip():
                output = compact_agent_report(retry_output, "execution_report")
            validation = validate_agent_report(output, "execution_report", min_chars=120)

        return output, validation

    def _run_execution_actions(self, case_path: str, input_text: str) -> str:
        """Run the autonomous action loop once; status is determined separately."""
        with scoped_tool_context(case_path):
            result = self.agent.invoke({"input": input_text})
        return result.get("output", "")

    def _agent_excerpt(self, agent_output: str, limit: int = 900) -> str:
        text = " ".join((agent_output or "").strip().split())
        if not text:
            return "The execution action loop did not return a textual summary."
        if "error executing agent" in text.lower():
            return "The execution action loop returned an agent-level error; deterministic solver-log checks were used for final status."
        if len(text) > limit:
            return text[:limit] + f"... [truncated after {limit} characters]"
        return text

    def _format_deterministic_execution_report(
        self,
        case_path: str,
        execution_status: Dict[str, Any],
        agent_output: str,
        evidence: Dict[str, Any] | None = None,
    ) -> str:
        evidence = evidence or {}
        control = evidence.get("control") or {}
        solver = evidence.get("solver") or {}
        diagnostics_summary = evidence.get("openfoam_diagnostic_summary") or summarize_diagnostics([])
        solver_logs = execution_status.get("solver_logs") or solver.get("logs") or []

        lines = [
            "# Execution Report",
            "",
            "## Final Status",
            f"- Final status: `{execution_status.get('final_status')}`",
            f"- Run status: `{execution_status.get('run_status')}`",
            f"- Status source: `{execution_status.get('status_source')}`",
            f"- Status reason: {execution_status.get('status_reason')}",
            "",
            "## Deterministic Checks",
            f"- Solver clean End marker: `{execution_status.get('solver_log_has_clean_end')}`",
            f"- Solver logs checked: `{', '.join(solver_logs) if solver_logs else 'none'}`",
            f"- OpenFOAM blocking diagnostics: `{diagnostics_summary.get('blocking', 0)}`",
            f"- OpenFOAM fatal diagnostics: `{diagnostics_summary.get('fatal', 0)}`",
            f"- Application: `{control.get('application')}`",
            f"- endTime: `{control.get('endTime')}`",
            f"- Time directory count: `{evidence.get('time_dir_count')}`",
            "",
            "## Agent Action Summary",
            self._agent_excerpt(agent_output),
            "",
            "## Evidence Files",
            "- `execution_status.json` contains the authoritative run status.",
            "- `workflow_evidence.md` contains compact solver-log tails and artifact summaries.",
        ]
        return compact_agent_report("\n".join(lines).rstrip() + "\n", "execution_report")

    @track_agent_execution("execution_agent")
    def execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Executes OpenFOAM simulation workflow using the autonomous agent.
        """
        print("Execution Agent: Starting execution (Autonomous Mode)...")
        
        case_path = state.get('case_path') or ""
        set_retrieval_context(state.get("tutorial_case_path"), state.get("user_request", ""))
        current_task = state.get('current_task', {'id': 'execution', 'name': 'Execute simulation'})

        preflight = run_execution_preflight(case_path)
        if not preflight["ok"]:
            output = compact_agent_report(format_preflight_report(preflight), "execution_report")
            report_path = os.path.join(case_path, "execution_report.md")
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"Execution Agent: Preflight report saved to {report_path}")
            except Exception as e:
                print(f"Execution Agent: Warning - could not save preflight report file: {e}")

            execution_status = build_execution_status(case_path, output, "failed")
            execution_status.update(
                {
                    "status_source": "environment_preflight",
                    "status_reason": "; ".join(preflight["blockers"]),
                    "environment_status": "blocked",
                    "environment_blockers": preflight["blockers"],
                    "environment_warnings": preflight["warnings"],
                }
            )
            status_path = None
            try:
                status_path = write_execution_status(case_path, execution_status)
                print(f"Execution Agent: Preflight status saved to {status_path}")
            except Exception as e:
                print(f"Execution Agent: Warning - could not save execution status file: {e}")
            try:
                write_workflow_evidence(case_path)
                print("Execution Agent: Preflight workflow evidence saved.")
            except Exception as e:
                print(f"Execution Agent: Warning - could not save workflow evidence: {e}")

            current_task['status'] = "failed"
            current_task['result_summary'] = output
            return {
                'current_task': current_task,
                "run_status": "failed",
                "execution_status": execution_status,
                "execution_status_path": str(status_path) if status_path else None,
                "execution_output": output,
                "execution_summary": output,
                "environment_status": "blocked",
                "environment_blockers": preflight["blockers"],
                "completed_tasks": state.get('completed_tasks', []) + [current_task],
            }
        
        input_text = (
            f"Task: Execute the simulation in {case_path}.\n"
            f"Follow your defined workflow to manage scripts, run the simulation, and handle errors.\n"
            f"Keep command output targeted; read only compact log tails when diagnostics are needed.\n"
            f"Do not produce a long final report; the workflow will generate deterministic status from solver logs.\n"
            f"{report_length_instruction('execution_report')}"
        )

        agent_output = self._run_execution_actions(case_path, input_text)
        provisional_status = build_execution_status(case_path, "", None)
        try:
            evidence = write_workflow_evidence(case_path)
            print("Execution Agent: Workflow evidence saved.")
        except Exception as e:
            print(f"Execution Agent: Warning - could not save workflow evidence: {e}")
            evidence = {}

        output = self._format_deterministic_execution_report(
            case_path,
            provisional_status,
            agent_output,
            evidence,
        )
        report_status = validate_agent_report(output, "execution_report", min_chars=120)

        # Save the report to a file for other agents to use
        report_path = os.path.join(case_path, "execution_report.md")
        try:
            with open(report_path, "w") as f:
                f.write(output)
            print(f"Execution Agent: Report saved to {report_path}")
        except Exception as e:
            print(f"Execution Agent: Warning - could not save report file: {e}")
        
        execution_status = build_execution_status(case_path, output, None)
        execution_status["report_contract"] = report_status
        status = execution_status["run_status"]
        status_path = None
        try:
            status_path = write_execution_status(case_path, execution_status)
            print(f"Execution Agent: Status saved to {status_path}")
        except Exception as e:
            print(f"Execution Agent: Warning - could not save execution status file: {e}")

        summary = output

        current_task['status'] = status
        current_task['result_summary'] = summary
        
        state_update = {
            'current_task': current_task,
            "run_status": status,
            "execution_status": execution_status,
            "execution_status_path": str(status_path) if status_path else None,
            "execution_output": output,
            "execution_summary": summary,
            "execution_report_status": "completed" if report_status["valid"] else "failed",
            "completed_tasks": state.get('completed_tasks', []) + [current_task],
        }
        if not report_status["valid"]:
            state_update["workflow_error"] = f"execution_report.md failed artifact contract: {report_status['reason']}"
        return state_update
