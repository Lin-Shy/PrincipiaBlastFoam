import os
import json
import ast
from typing import Dict, Any, List
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain.tools import StructuredTool

import glob

from principia_ai.graph.graph_state import GraphState
from principia_ai.prompts import PromptManager
from principia_ai.metrics.decorators import track_agent_execution, track_llm_call
from principia_ai.metrics.tracker import MetricsTracker
from ..tools.physics_inspection import read_physics_report_file, get_physics_report_tool
from ..tools.execution_inspection import get_execution_report_tool
from ..tools.review_inspection import get_review_report_tool

# New imports
from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools

class OrchestratorAgent:
    """
    Orchestrator Agent - Refactored to use BaseAgent.
    """

    def __init__(self, llm, use_knowledge_manager=True, use_tutorial_retriever=True):
        self.llm = llm
        self.prompt_manager = PromptManager()
        
        # Initialize Tools - Orchestrator mainly needs to read state/files to plan
        # self.agent_tools = get_read_tools() + get_search_tools() + [get_physics_report_tool()]
        self.agent_tools = [get_physics_report_tool(), get_execution_report_tool(), get_review_report_tool()]

        # Load System Prompt
        self.system_prompt = self.prompt_manager.load_prompt("orchestrator", "react_system")


        # Initialize BaseAgent
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="OrchestratorAgent",
            max_iterations=100
        )

    def _scan_config_state(self, case_path: str) -> Dict[str, str]:
        """
        Scans the case configuration and returns a map of {filepath: signature}.
        Signature = modification_time + file_size.
        """
        state_map = {}
        if not case_path or not os.path.exists(case_path):
            return state_map

        # Monitor core directories
        target_dirs = ['system', 'constant', '0', '0.orig']
        
        for d in target_dirs:
            full_dir = os.path.join(case_path, d)
            if not os.path.exists(full_dir):
                continue
                
            for root, _, files in os.walk(full_dir):
                for file in files:
                    if file.startswith('.'): continue
                    # Exclude large mesh files
                    if "polyMesh" in root and file in ["points", "faces", "owner", "neighbour", "cellZones"]:
                        continue
                        
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, case_path)
                    try:
                        stats = os.stat(abs_path)
                        # Signature: size + mtime
                        state_map[rel_path] = f"{stats.st_size}:{stats.st_mtime}"
                    except OSError:
                        pass
        return state_map

    def create_execution_plan(self, user_query: str, physics_context: str, case_path: str) -> str:
        """
        Generates initial high-level plan.
        """
        planning_prompt = (
            f"You are the Chief Architect for an OpenFOAM simulation.\n"
            f"Goal: {user_query}\n"
            f"Case Path: {case_path}\n"
            f"Context: {physics_context}\n"
            f"Task: Create a high-level step-by-step plan based on the Goal and Context.\n"
            f"IMPORTANT: Compare the Goal with the Context. Only include steps that are strictly necessary to achieve the Goal. Do not include steps for tasks that are already completed or irrelevant.\n"
            f"Return the plan as a numbered list."
        )
        response = self.llm.invoke(planning_prompt)
        
        # Track tokens
        tracker = MetricsTracker()
        usage = response.usage_metadata if hasattr(response, 'usage_metadata') else {}
        tracker.record_llm_call(
            agent_name="orchestrator",
            input_tokens=usage.get('input_tokens', 0),
            output_tokens=usage.get('output_tokens', 0),
            model=self.llm.model_name if hasattr(self.llm, 'model_name') else 'unknown'
        )
        
        return response.content

    @track_agent_execution("orchestrator")
    def route(self, state: GraphState) -> Dict[str, Any]:
        """
        Decides the next step in the workflow using the autonomous agent.
        """
        print("Orchestrator: Reasoning about next step...")
        
        user_query = state.get('user_request', '')
        case_path = state.get("case_path", "")
        plan = state.get('plan', '')
        completed_tasks = state.get('completed_tasks', [])
        physics_report = read_physics_report_file(case_path)
        
        updates = {}

        # === Priority Route: Physics Updater ===
        if state.get('needs_physics_update', False):
            print("Orchestrator: Routing to 'physics_updater' node.")
            return {
                "current_agent": "physics_updater",
                "current_task": {
                    "description": "Update physics report based on file changes.",
                    "assigned_agent": "physics_updater",
                    "status": "pending"
                },
                "needs_physics_update": False # Clear flag
            }
        # === End Priority Route ===
        
        # === Phase 2: Planning Trigger ===
        if physics_report and not plan:
            print("Orchestrator: Physics analysis received. Generating Action Plan...")
            action_plan = self.create_execution_plan(user_query, physics_report, case_path)
            updates["physics_analysis"] = action_plan
            updates["plan"] = action_plan
            print("Orchestrator: Plan generated.")
            # We don't return immediately, we let the reasoning below decide to call case_setup_agent
            plan = action_plan

        # 1. Construct rich execution history as Messages
        chat_history = []
        if completed_tasks:
            for task in completed_tasks:
                # Add task description as Human Message (what was asked)
                chat_history.append(HumanMessage(content=f"Task: {task.get('description')}"))
                
                # Add result as AI Message (what was done)
                result_content = f"Result: {task.get('result_summary')}\nContext: {task.get('context_data')}"
                chat_history.append(AIMessage(content=result_content))

        # 2. Construct Reasoning Prompt
        input_text = (
            f"=== GOAL ===\n{user_query}\n\n"
            f"=== CASE PATH ===\n{case_path}\n\n"
            f"=== ORIGINAL PLAN ===\n{plan}\n\n"
            f"=== DECISION ===\n"
            f"Determine the NEXT immediate step and agent based on the History and Plan.\n"
            f"Note: If 'physics_report.md' exists, assume physics analysis is COMPLETED.\n"
            f"If the goal is achieved, output 'FINISH'.\n"
            f"\nOutput Format JSON: {{'next_agent': '...', 'task_instructions': '...'}}"
        )
        
        result = self.agent.invoke({"chat_history": chat_history, "input": input_text})
        output_content = result.get("output", "")
        
        try:
            # Simple JSON parsing
            clean_json = output_content.replace("```json", "").replace("```", "").strip()
            # Find the first { and last }
            start = clean_json.find("{")
            end = clean_json.rfind("}")
            if start != -1 and end != -1:
                clean_json = clean_json[start:end+1]
                try:
                    decision = json.loads(clean_json)
                except json.JSONDecodeError:
                    # Fallback to ast.literal_eval for single quotes or relaxed syntax
                    try:
                        decision = ast.literal_eval(clean_json)
                    except Exception:
                        # If both fail, raise the original error to be caught by outer except
                        raise
                
                next_agent = decision.get("next_agent", "end")
                updates['current_agent'] = next_agent
                task_instructions = decision.get("task_instructions", "")
                
                if next_agent == "FINISH" or next_agent == "end":
                    return {**updates, "current_agent": "end"}

                print(f"Orchestrator: Routing to {next_agent} with task: {task_instructions[:50]}...")
                
                new_task = {
                    "description": task_instructions,
                    "status": "pending",
                    "assigned_agent": next_agent
                }
                
                return {
                    **updates,
                    "current_agent": next_agent,
                    "current_task": new_task
                }
            else:
                 print(f"Orchestrator: Could not find JSON in output: {output_content}")
                 return {**updates, "current_agent": "end"}

        except Exception as e:
            print(f"Orchestrator: Error parsing decision: {e}. Fallback to manual routing.")
            return {**updates, "current_agent": "end"}

    @track_agent_execution("orchestrator")
    def process_feedback(self, state: GraphState) -> Dict[str, Any]:
        """
        Processes feedback from agents and updates the state.
        """
        print("Orchestrator: Processing feedback and updating context...")
        
        current_task = state.get('current_task', {})
        last_agent = state.get('current_agent')
        case_path = state.get("case_path", "")
        
        result_summary = "Task completed."
        context_data = ""
        
        if last_agent == "physics_analyst_agent":
            context_data = "Physics report contents have been saved to physics_report.md file."
            result_summary = "Physics analysis completed."
        elif last_agent == "execution_agent":
            context_data = state.get("execution_output", "")
            result_summary = state.get("execution_summary", "Simulation run finished.")
            if "run_status" in state:
                current_task['status'] = state["run_status"]
        elif last_agent == "case_setup_agent":
            # Assuming case setup agent might return something or just modify files
            result_summary = "Case setup modifications applied."
        elif last_agent == "reviewer":
             validation_status = state.get('validation_status')
             result_summary = f"Review completed. Status: {validation_status}"
             context_data = state.get('validation_notes', '')

        # Update task status and record detailed history
        if 'status' not in current_task:
            current_task['status'] = 'completed'
            
        current_task['result_summary'] = result_summary
        current_task['context_data'] = str(context_data)[:500] # Truncate to avoid token limit issues
        
        completed_tasks = state.get('completed_tasks', [])
        completed_tasks.append(current_task)
        
        self.save_checkpoint(state)
        
        # === Incremental Detection Logic ===
        updates = {}
        
        # Get old and new state
        old_map = state.get('config_state_map', {})
        new_map = self._scan_config_state(case_path)
        
        # If last agent was not physics_updater or physics_analyst_agent (prevent loops), check for diffs
        if last_agent != 'physics_updater' and last_agent != 'physics_analyst_agent':
            current_changed_files = []
            for f_path, signature in new_map.items():
                if f_path not in old_map or old_map[f_path] != signature:
                    current_changed_files.append(f_path)
            
            # Accumulate changes
            existing_changed_files = state.get('changed_files', [])
            # Use set to avoid duplicates
            all_changed_files = list(set(existing_changed_files + current_changed_files))
            
            if all_changed_files:
                updates['changed_files'] = all_changed_files
                
                # Only trigger update if ExecutionAgent or CaseSetupAgent has finished
                if last_agent == 'execution_agent' or last_agent == 'case_setup_agent':
                    print(f"Orchestrator: Execution finished. Triggering physics update for: {all_changed_files}")
                    updates['needs_physics_update'] = True
                else:
                    print(f"Orchestrator: Changes detected {current_changed_files}, but waiting for ExecutionAgent to trigger update.")
        
        updates['config_state_map'] = new_map
        # === End Incremental Detection ===
        
        return {"completed_tasks": completed_tasks, **updates}

    def save_checkpoint(self, state: GraphState):
        """Saves the current state to a JSON file."""
        try:
            task_id = state.get('task_id', 'default')
            checkpoint_dir = os.path.join("checkpoints", task_id)
            if not os.path.exists(checkpoint_dir):
                os.makedirs(checkpoint_dir)

            iteration = len(glob.glob(os.path.join(checkpoint_dir, "*.json")))
            filename = f"checkpoint_{iteration}.json"
            filepath = os.path.join(checkpoint_dir, filename)

            # Simple dump, avoiding complex serialization for now
            with open(filepath, 'w') as f:
                # Filter out non-serializable objects if any
                serializable_state = {k: v for k, v in state.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}
                json.dump(serializable_state, f, indent=4, default=str)
            print(f"Orchestrator: Saved checkpoint to {filepath}")
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
