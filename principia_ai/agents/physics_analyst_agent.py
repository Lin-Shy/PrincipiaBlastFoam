import os
import json
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from ..graph.graph_state import GraphState
from ..prompts import PromptManager
from ..tools.mcp_retrieval_tools import get_mcp_retrieval_tools, set_retrieval_context
from ..tools.context import scoped_tool_context
from ..utils.report_contracts import (
    build_report_repair_prompt,
    compact_agent_report,
    report_length_instruction,
    validate_agent_report,
)
from ..utils.case_digest import build_physics_case_digest
from ..metrics.decorators import track_agent_execution, track_llm_call

# New imports for Refactoring
from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools, get_edit_tools, get_execute_tools

class PhysicsAnalystAgent:
    """
    Physics Analyst Agent - 物理问题专家 (Physics Problem Expert).
    Refactored to use BaseAgent (ReAct/Tool-use pattern).
    
    - Analyzes physical phenomena from user requirements.
    - Uses tools to inspect existing case files.
    - Searches knowledge base for appropriate models.
    - Outputs physical specifications.
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
        self.agent_tools = get_read_tools() + get_search_tools() + get_edit_tools() + get_execute_tools()
        self.agent_tools.extend(get_mcp_retrieval_tools(use_knowledge_manager, use_tutorial_retriever))

        # Load System Prompt
        self.system_prompt = self.prompt_manager.load_prompt("physics_analyst_agent", "react_system")


        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="physics_analyst_agent",
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50"))
        )

    def _run_report_task(self, case_path: str, input_text: str) -> tuple[str, Dict[str, Any]]:
        with scoped_tool_context(case_path):
            result = self.agent.invoke({"input": input_text})
        output = compact_agent_report(result.get("output", "No output generated."), "physics_report")
        validation = validate_agent_report(output, "physics_report", min_chars=120)

        max_repairs = int(os.getenv("REPORT_REPAIR_ATTEMPTS", "1"))
        for _attempt in range(max_repairs):
            if validation["valid"]:
                break
            print(f"Physics Analyst: physics_report contract failed; retrying once: {validation['reason']}")
            repair_prompt = build_report_repair_prompt(
                report_name="physics_report.md",
                original_task=input_text,
                invalid_report=output,
                validation=validation,
            )
            with scoped_tool_context(case_path):
                retry_result = self.agent.invoke({"input": repair_prompt})
            retry_output = retry_result.get("output", "")
            if retry_output.strip():
                output = compact_agent_report(retry_output, "physics_report")
            validation = validate_agent_report(output, "physics_report", min_chars=120)

        return output, validation

    @track_agent_execution("physics_analyst_agent")
    def analyze(self, state: GraphState) -> Dict[str, Any]:
        """
        Phase 1: Reconnaissance
        Analyzes the current case state and retrieves necessary knowledge.
        Does NOT generate a modification plan.
        """
        print("Physics Analyst Agent: Starting Reconnaissance Phase...")
        
        user_query = state.get("user_request", "")
        case_path = state.get("case_path", "")
        set_retrieval_context(state.get("tutorial_case_path"), user_query)
        current_task = state.get("current_task", {})
        task_description = current_task.get("description", "Analyze the current case configuration against the User Query.")

        digest_context = ""
        if os.getenv("PHYSICS_ANALYST_CASE_DIGEST", "true").lower() in {"1", "true", "yes", "on"}:
            digest = build_physics_case_digest(
                case_path,
                user_request=user_query,
                tutorial_case_path=state.get("tutorial_case_path"),
                tutorial_source_path=state.get("tutorial_source_path"),
            )
            digest_context = (
                "=== PROGRAMMATIC CASE DIGEST ===\n"
                f"{digest['markdown']}\n\n"
                "Digest guidance: This digest is precomputed evidence from the current case files. "
                "Use it as your starting context. Stay in the ReAct workflow and call tools only for "
                "targeted follow-up questions, missing files, or ambiguity that the digest cannot resolve. "
                "Do not repeat broad directory scans or full-file reads for files already summarized here.\n\n"
            )

        # Construct input for the agent
        input_text = (
            f"User Query: {user_query}\n"
            f"Case Path: {case_path}\n"
            f"Task: {task_description}\n"
            f"{digest_context}"
            f"Output a comprehensive 'Physics Report' detailing the current configuration and discrepancies.\n"
            f"Focus on analyzing the CURRENT state. Do NOT generate a fix plan yet."
            f"\n{report_length_instruction('physics_report')}"
        )
        
        output, report_status = self._run_report_task(case_path, input_text)
        
        # Save the report to a file for other agents to use
        report_path = os.path.join(case_path, "physics_report.md")
        try:
            with open(report_path, "w") as f:
                f.write(output)
            print(f"Physics Analyst: Report saved to {report_path}")
        except Exception as e:
            print(f"Physics Analyst: Warning - could not save report file: {e}")
        
        print("Physics Analyst Agent: Reconnaissance complete.")
        
        # Return minimal state update; report is persisted to filesystem for downstream agents.
        if not report_status["valid"]:
            return {
                "physics_report_status": "failed",
                "workflow_error": report_status["reason"],
            }
        return {"physics_report_status": "completed"}

    @track_agent_execution("physics_updater")
    def update_report(self, state: GraphState) -> Dict[str, Any]:
        """
        Incremental update node. Reads changed files and patches the report.
        """
        print("Physics Updater: Starting incremental report update...")

        # Check environment variable to see if we should update the report
        if os.getenv("UPDATE_PHYSICS_REPORT", "false").lower() != "true":
            print("Physics Updater: UPDATE_PHYSICS_REPORT is not set to true. Skipping update.")
            return {}
        
        case_path = state.get("case_path", "")
        set_retrieval_context(state.get("tutorial_case_path"), state.get("user_request", ""))
        changed_files = state.get("changed_files", [])
        report_path = os.path.join(case_path, "physics_report.md")
        
        if not os.path.exists(report_path):
            print("Physics Updater: No existing report found. Falling back to full analysis.")
            return self.analyze(state)
            
        if not changed_files:
            print("Physics Updater: No changed files detected. Skipping.")
            return {}

        max_chars_per_file = int(os.getenv("PHYSICS_UPDATE_FILE_CONTEXT_CHARS", "4000"))

        # Read only the relevant changed files selected by the orchestrator.
        file_contents = ""
        for rel_path in changed_files:
            abs_path = os.path.join(case_path, rel_path)
            try:
                with open(abs_path, 'r') as f:
                    content = f.read()
                    if len(content) > max_chars_per_file:
                        content = content[:max_chars_per_file] + "\n... [truncated]\n"
                    file_contents += f"\n=== FILE: {rel_path} ===\n{content}\n"
            except Exception as e:
                file_contents += f"\n=== FILE: {rel_path} (Error: {e}) ===\n"

        prompt = (
            f"You are a CFD Physics Analyst. A configuration change has occurred.\n"
            f"=== TASK ===\n"
            f"Update the existing Physics Report ({report_path}) to reflect the changes in the modified files.\n"
            f"Only use the relevant changed configuration files below; do not run the solver or inspect runtime output.\n"
            f"Prefer patching affected sections or adding a concise incremental update note over rewriting unrelated content.\n"
            f"Use the tools to overwrite the report with the updated content.\n"
            f"Do NOT output the report content in your response. Just confirm the update.\n\n"
            f"=== MODIFIED FILES ===\n{file_contents}\n"
        )

        # 4. Invoke LLM
        with scoped_tool_context(case_path):
            result = self.agent.invoke({"input": prompt})
        
        print(f"Physics Updater: Agent invoked for update on {len(changed_files)} files.")
        
        # Clear changed files list
        return {"changed_files": []}
