import os
import json
import re
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..tools.mcp_retrieval_tools import get_mcp_retrieval_tools, set_retrieval_context
from ..utils.execution_status import build_execution_status, write_execution_status

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
            max_iterations=int(os.getenv("MAX_ITERATIONS"))
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

    @track_agent_execution("execution_agent")
    def execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Executes OpenFOAM simulation workflow using the autonomous agent.
        """
        print("Execution Agent: Starting execution (Autonomous Mode)...")
        
        case_path = state.get('case_path')
        set_retrieval_context(state.get("tutorial_case_path"), state.get("user_request", ""))
        current_task = state.get('current_task', {'id': 'execution', 'name': 'Execute simulation'})
        
        input_text = (
            f"Task: Execute the simulation in {case_path}.\n"
            f"Follow your defined workflow to manage scripts, run the simulation, and handle errors.\n"
            f"Report the final status and a summary of the execution."
        )
        
        result = self.agent.invoke({"input": input_text})
        output = result.get("output", "")
        
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
        
        return {
            'current_task': current_task,
            "run_status": status,
            "execution_status": execution_status,
            "execution_status_path": str(status_path) if status_path else None,
            "execution_output": output,
            "execution_summary": summary,
            "completed_tasks": state.get('completed_tasks', []) + [current_task]
        }
