import os
from typing import Dict, Any
from langchain.schema import HumanMessage, SystemMessage

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from ..tools.mcp_retrieval_tools import get_mcp_retrieval_tools, set_retrieval_context
from ..tools.context import scoped_tool_context
from ..utils.postprocessing_contracts import validate_post_processing_output

# New imports
from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools, get_execute_tools

class PostProcessingAgent:
    """
    Post-Processing Agent - Refactored to use BaseAgent.
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
        self.agent_tools = get_read_tools() + get_search_tools() + get_execute_tools()
        self.agent_tools.extend(get_mcp_retrieval_tools(use_knowledge_manager, use_tutorial_retriever))
        
        # Load System Prompt
        try:
            self.system_prompt = self.prompt_manager.load_prompt("post_processing_agent", "react_system")
        except Exception as e:
            print(f"Warning: Could not load react_system prompt: {e}. Using default.")
            self.system_prompt = (
                "You are the Post-Processing Agent. Analyze the OpenFOAM simulation results."
            )

        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="PostProcessingAgent",
            max_iterations=int(os.getenv("MAX_ITERATIONS", "50"))
        )

    @track_agent_execution("post_processing_agent")
    def process(self, state: GraphState) -> Dict[str, Any]:
        """
        Processes simulation results using the autonomous agent.
        """
        print("Post-Processing Agent: Starting processing (Autonomous Mode)...")
        
        case_path = state.get('case_path') or ""
        set_retrieval_context(state.get("tutorial_case_path"), state.get("user_request", ""))
        current_task = state.get('current_task', {})
        
        input_text = (
            f"Task: Post-process the simulation in {case_path}.\n"
            f"Task Details: {current_task}\n"
        )
        
        with scoped_tool_context(case_path):
            result = self.agent.invoke({"input": input_text})
        output = result.get("output", "")
        validation = validate_post_processing_output(case_path, output)

        report_path = os.path.join(case_path, "post_processing_report.md")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(output)
                if validation["issues"]:
                    f.write("\n\nPost-processing contract issues:\n")
                    for issue in validation["issues"]:
                        f.write(f"- {issue}\n")
            print(f"Post-Processing Agent: Report saved to {report_path}")
        except Exception as e:
            print(f"Post-Processing Agent: Warning - could not save report file: {e}")
        
        print("Post-Processing Agent: Processing complete.")
        
        # Update current_task status
        if current_task:
            current_task['status'] = 'completed'
            
        return {
            "post_processing_status": "complete" if validation["ok"] else "failed",
            "post_processing_issues": validation["issues"],
            "summary": output,
            "current_task": current_task
        }
