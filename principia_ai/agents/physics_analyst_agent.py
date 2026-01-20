import os
import json
from typing import Dict, Any, List, Optional
from langchain.schema import HumanMessage, SystemMessage
from langchain.tools import StructuredTool

from ..graph.graph_state import GraphState
from ..prompts import PromptManager
from ..tools.user_guide_knowledge_graph_tool import UserGuideKnowledgeGraphRetriever
from ..tools.case_content_knowledge_graph_tool import CaseContentKnowledgeGraphRetriever
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
        self.system_prompt = self.prompt_manager.load_prompt("physics_analyst_agent", "react_system")


        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="physics_analyst_agent",
            max_iterations=int(os.getenv("MAX_ITERATIONS"))
        )

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
        current_task = state.get("current_task", {})
        task_description = current_task.get("description", "Analyze the current case configuration against the User Query.")


        # Construct input for the agent
        input_text = (
            f"User Query: {user_query}\n"
            f"Case Path: {case_path}\n"
            f"Task: {task_description}\n"
            f"Output a comprehensive 'Physics Report' detailing the current configuration and discrepancies.\n"
            f"Focus on analyzing the CURRENT state. Do NOT generate a fix plan yet."
        )
        
        # Run the agent
        result = self.agent.invoke({"input": input_text})
        output = result.get("output", "No output generated.")
        
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
        return {}

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
        changed_files = state.get("changed_files", [])
        report_path = os.path.join(case_path, "physics_report.md")
        
        if not os.path.exists(report_path):
            print("Physics Updater: No existing report found. Falling back to full analysis.")
            return self.analyze(state)
            
        if not changed_files:
            print("Physics Updater: No changed files detected. Skipping.")
            return {}

        # 1. Read old report
        with open(report_path, 'r') as f:
            old_report = f.read()
            
        # 2. Read changed files content
        file_contents = ""
        for rel_path in changed_files:
            abs_path = os.path.join(case_path, rel_path)
            try:
                with open(abs_path, 'r') as f:
                    content = f.read()
                    file_contents += f"\n=== FILE: {rel_path} ===\n{content}\n"
            except Exception as e:
                file_contents += f"\n=== FILE: {rel_path} (Error: {e}) ===\n"

        # 3. Construct incremental update prompt
        prompt = (
            f"You are a CFD Physics Analyst. A configuration change has occurred.\n"
            f"=== TASK ===\n"
            f"Update the existing Physics Report ({report_path}) to reflect the changes in the modified files.\n"
            f"Use the tools to overwrite the report with the updated content.\n"
            f"Do NOT output the report content in your response. Just confirm the update.\n\n"
            f"=== MODIFIED FILES ===\n{file_contents}\n"
        )

        # 4. Invoke LLM
        result = self.agent.invoke({"input": prompt})
        
        print(f"Physics Updater: Agent invoked for update on {len(changed_files)} files.")
        
        # Clear changed files list
        return {"changed_files": []}
