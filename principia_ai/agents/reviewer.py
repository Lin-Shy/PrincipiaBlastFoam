import os
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..tools.mcp_retrieval_tools import get_mcp_retrieval_tools, set_retrieval_context

from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools, get_edit_tools, get_execute_tools

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
        self.agent_tools = get_read_tools() + get_search_tools() + get_edit_tools() + get_execute_tools()
        self.agent_tools.extend(get_mcp_retrieval_tools(use_knowledge_manager, use_tutorial_retriever))
        
        # Load System Prompt
        self.system_prompt = self.prompt_manager.load_prompt("reviewer", "react_system")

        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="ReviewerAgent",
            max_iterations=int(os.getenv("MAX_ITERATIONS"))
        )

    @track_agent_execution("reviewer")
    def review_task(self, state: GraphState) -> Dict[str, Any]:
        """
        Reviews the task result using the autonomous agent.
        """
        print("Reviewer Agent: Starting review (Autonomous Mode)...")
        
        user_request = state.get('user_request', '')
        case_path = state.get('case_path')
        set_retrieval_context(state.get("tutorial_case_path"), user_request)
        
        input_text = (
            f"User Request: {user_request}\n"
            f"Case Path: {case_path}\n"
            f"Task: Review the simulation in {case_path}. \n"
            f"1. Verify if the simulation ran successfully.\n"
            f"2. Extract specific requirements from the 'User Request' and verify if the case configuration matches them.\n"
            f"3. Report back with a checklist and status."
        )
        
        result = self.agent.invoke({"input": input_text})
        output = result.get("output", "")
        
        # Save the report to a file for other agents to use
        report_path = os.path.join(case_path, "review_report.md")
        try:
            with open(report_path, "w") as f:
                f.write(output)
            print(f"Reviewer Agent: Report saved to {report_path}")
        except Exception as e:
            print(f"Reviewer Agent: Warning - could not save report file: {e}")
        
        # Parse status from output (heuristic)
        status = "passed"
        if "fail" in output.lower() or "error" in output.lower() or "not satisfied" in output.lower():
             status = "failed"
            
        print(f"Reviewer Agent: Review complete. Status: {status}")
        
        return {
            "validation_status": status,
            "validation_notes": output,
            # "issue_details": {} # Could be parsed if we structured the output
        }
