import os
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..tools.mcp_retrieval_tools import get_mcp_retrieval_tools, set_retrieval_context

# New imports
from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools, get_edit_tools
from ..tools.physics_inspection import get_physics_report_tool

class CaseSetupAgent:
    """
    Case Setup Agent - Refactored to use BaseAgent.
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
        self.agent_tools = get_edit_tools() + get_read_tools() + get_search_tools()
        self.agent_tools.append(get_physics_report_tool())
        self.agent_tools.extend(get_mcp_retrieval_tools(use_knowledge_manager, use_tutorial_retriever))
        
        # Load System Prompt
        try:
            self.system_prompt = self.prompt_manager.load_prompt("case_setup_agent", "react_system")
        except Exception as e:
            print(f"Warning: Could not load react_system prompt: {e}. Using default.")
            self.system_prompt = (
                "You are the Case Setup Agent. Modify OpenFOAM case files based on instructions. "
                "Use 'read_file' to check content and 'write_file' or 'replace_in_file' to edit."
            )

        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="CaseSetupAgent",
            max_iterations=int(os.getenv("MAX_ITERATIONS"))
        )

    @track_agent_execution("case_setup_agent")
    def run_setup(self, state: GraphState) -> Dict[str, Any]:
        """
        Executes case setup tasks using the autonomous agent.
        """
        print("Case Setup Agent: Starting setup (Autonomous Mode)...")
        
        case_path = state.get('case_path')
        user_request = state.get('user_request', '')
        set_retrieval_context(state.get("tutorial_case_path"), user_request)
        physics_analysis = state.get('physics_analysis', '')
        current_task = state.get('current_task', {})
        
        input_text = (
            f"Task: Configure the OpenFOAM case in {case_path}.\n"
            f"User Request: {user_request}\n"
            f"Physics Analysis/Plan: {physics_analysis}\n"
            f"Current Task Details: {current_task}\n"
        )
        
        result = self.agent.invoke({"input": input_text})
        output = result.get("output", "")
        
        print("Case Setup Agent: Setup complete.")
        
        return {
            "case_setup_output": output,
            # We assume the agent has modified the files directly.
            # We can return the output as a log of what was done.
        }
