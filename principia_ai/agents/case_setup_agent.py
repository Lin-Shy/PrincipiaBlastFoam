import os
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage
from langchain.tools import StructuredTool

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..tools.user_guide_knowledge_graph_tool import UserGuideKnowledgeGraphRetriever
from ..tools.case_content_knowledge_graph_tool import CaseContentKnowledgeGraphRetriever

# New imports
from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools, get_edit_tools, get_execute_tools
from ..tools.physics_inspection import get_physics_report_tool

class CaseSetupAgent:
    """
    Case Setup Agent - Refactored to use BaseAgent.
    """

    def __init__(self, llm, use_knowledge_manager=True, use_tutorial_retriever=True):
        self.llm = llm
        self.prompt_manager = PromptManager()
        
        # Initialize Tools
        self.agent_tools = get_edit_tools() + get_read_tools() + get_search_tools() + get_execute_tools()
        self.agent_tools.append(get_physics_report_tool())

        # Add Knowledge Tools if enabled
        if use_knowledge_manager:
            try:
                self.user_guide_retriever = UserGuideKnowledgeGraphRetriever()
                # Wrap knowledge search as a tool
                self.agent_tools.append(
                    StructuredTool.from_function(
                        func=self.user_guide_retriever.search,
                        name="search_user_guide",
                        description="Search the BlastFoam user guide for interfacial models, granular models, fluid and solid thermodynamic models, burst patches, region models, diameter models and solver settings."
                    )
                )
            except Exception as e:
                print(f"Warning: Could not initialize UserGuideKnowledgeGraphRetriever: {e}")
            
        if use_tutorial_retriever:
            try:
                self.case_content_retriever = CaseContentKnowledgeGraphRetriever()
                 # Wrap tutorial search as a tool
                self.agent_tools.append(
                    StructuredTool.from_function(
                        func=self.case_content_retriever.search,
                        name="search_case_content",
                        description="Search for blastFoam tutorial cases setting, files contents, and variable definitions as reference content when encountering uncertain problems. "
                    )
                )
            except Exception as e:
                print(f"Warning: Could not initialize CaseContentKnowledgeGraphRetriever: {e}")
        
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
