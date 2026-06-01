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
from ..utils.report_contracts import build_report_repair_prompt, validate_agent_report
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
        output = result.get("output", "")
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
                output = retry_output
            validation = validate_agent_report(output, "execution_report", min_chars=120)

        return output, validation

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
            output = format_preflight_report(preflight)
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
            f"Report the final status and a summary of the execution."
        )
        
        output, report_status = self._run_report_task(case_path, input_text)
        
        # Save the report to a file for other agents to use
        report_path = os.path.join(case_path, "execution_report.md")
        try:
            with open(report_path, "w") as f:
                f.write(output)
            print(f"Execution Agent: Report saved to {report_path}")
        except Exception as e:
            print(f"Execution Agent: Warning - could not save report file: {e}")
        
        parsed_report_status = self._parse_execution_status(output)
        execution_status = build_execution_status(case_path, output, parsed_report_status)
        execution_status["report_contract"] = report_status
        status = execution_status["run_status"]
        status_path = None
        try:
            status_path = write_execution_status(case_path, execution_status)
            print(f"Execution Agent: Status saved to {status_path}")
        except Exception as e:
            print(f"Execution Agent: Warning - could not save execution status file: {e}")

        try:
            write_workflow_evidence(case_path)
            print("Execution Agent: Workflow evidence saved.")
        except Exception as e:
            print(f"Execution Agent: Warning - could not save workflow evidence: {e}")

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
