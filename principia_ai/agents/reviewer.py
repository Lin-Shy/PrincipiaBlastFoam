import os
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage
from langchain.tools import StructuredTool

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..tools.user_guide_knowledge_graph_tool import UserGuideKnowledgeGraphRetriever
from ..tools.case_content_knowledge_graph_tool import CaseContentKnowledgeGraphRetriever

from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools, get_edit_tools, get_execute_tools

class ReviewerAgent:
    """
    Reviewer Agent - Refactored to use BaseAgent.
    """

    def __init__(self, llm, use_knowledge_manager=True, use_tutorial_retriever=True):
        self.llm = llm
        self.prompt_manager = PromptManager()
        
        # Initialize Tools
        self.agent_tools = get_read_tools() + get_search_tools() + get_edit_tools() + get_execute_tools()
        
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
        self.system_prompt = self.prompt_manager.load_prompt("reviewer", "react_system")

        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="ReviewerAgent",
            max_iterations=100
        )

    @track_agent_execution("reviewer")
    def review_task(self, state: GraphState) -> Dict[str, Any]:
        """
        Reviews the task result using the autonomous agent.
        """
        print("Reviewer Agent: Starting review (Autonomous Mode)...")
        
        user_request = state.get('user_request', '')
        case_path = state.get('case_path')
        
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
