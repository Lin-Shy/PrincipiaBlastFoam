import os
import json
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
from ..tools.standard_tools import get_execute_tools, get_read_tools, get_edit_tools, get_search_tools

class ExecutionAgent:
    """
    Execution Agent - Refactored to use BaseAgent.
    """

    def __init__(self, llm, use_knowledge_manager=True, use_tutorial_retriever=True):
        self.llm = llm
        self.prompt_manager = PromptManager()
        
        # Initialize Tools
        self.agent_tools = get_execute_tools() + get_read_tools() + get_edit_tools() + get_search_tools()

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
            max_iterations=50
        )

    @track_agent_execution("execution_agent")
    def execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Executes OpenFOAM simulation workflow using the autonomous agent.
        """
        print("Execution Agent: Starting execution (Autonomous Mode)...")
        
        case_path = state.get('case_path')
        current_task = state.get('current_task', {'id': 'execution', 'name': 'Execute simulation'})
        
        input_text = (
            f"Task: Execute the simulation in {case_path}.\n"
            f"Follow your defined workflow to manage scripts, run the simulation, and handle errors.\n"
            f"IMPORTANT: Return the final result as a JSON string:\n"
            f"```json\n"
            f"{{\n"
            f"  \"status\": \"completed\" or \"failed\",\n"
            f"  \"summary\": \"Brief summary of what happened and any errors found.\"\n"
            f"}}\n"
            f"```"
        )
        
        result = self.agent.invoke({"input": input_text})
        output = result.get("output", "")
        
        # Parse JSON output
        status = "completed"
        summary = "Execution finished."
        
        try:
            # Extract JSON from output
            json_str = output
            if "```json" in output:
                json_str = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                # Try to find the block that looks like JSON
                parts = output.split("```")
                for part in parts:
                    if "{" in part and "}" in part:
                        json_str = part.strip()
                        break
            
            start = json_str.find("{")
            end = json_str.rfind("}")
            if start != -1 and end != -1:
                json_data = json.loads(json_str[start:end+1])
                status = json_data.get("status", "completed")
                summary = json_data.get("summary", summary)
            else:
                 # Fallback heuristic
                 if "fail" in output.lower() or "error" in output.lower():
                     status = "failed"
                     summary = "Execution failed (JSON parsing failed, heuristic used)."

        except Exception as e:
            print(f"ExecutionAgent: Error parsing JSON output: {e}")
            if "fail" in output.lower() or "error" in output.lower():
                status = "failed"
                summary = "Execution failed (Exception during parsing)."

        current_task['status'] = status
        current_task['result_summary'] = summary
        
        return {
            'current_task': current_task,
            "run_status": status,
            "execution_output": output,
            "execution_summary": summary,
            "completed_tasks": state.get('completed_tasks', []) + [current_task]
        }
