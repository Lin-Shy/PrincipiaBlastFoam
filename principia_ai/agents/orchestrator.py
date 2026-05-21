import os
import json
import ast
import re
import threading
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
from ..utils.execution_status import read_execution_status, status_run_completed

# New imports
from .base_agent import BaseAgent
from ..tools.standard_tools import get_read_tools, get_search_tools


NUMERIC_TIME_DIR_RE = re.compile(r"^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$")


def re_fullmatch_numeric_time(value: str) -> bool:
    return bool(NUMERIC_TIME_DIR_RE.fullmatch(value))

class OrchestratorAgent:
    """
    Orchestrator Agent - Refactored to use BaseAgent.
    """

    def __init__(self, llm, use_knowledge_manager=True, use_tutorial_retriever=True):
        self.llm = llm
        self.prompt_manager = PromptManager()
        self._async_physics_update_runner = None
        self._active_async_physics_updates: set[str] = set()
        
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
            max_iterations=int(os.getenv("MAX_ITERATIONS"))
        )

    def set_async_physics_update_runner(self, runner) -> None:
        self._async_physics_update_runner = runner

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
                    if self._is_runtime_output_path(rel_path):
                        continue
                    try:
                        stats = os.stat(abs_path)
                        # Signature: size + mtime
                        state_map[rel_path] = f"{stats.st_size}:{stats.st_mtime}"
                    except OSError:
                        pass
        return state_map

    def _execution_enabled(self) -> bool:
        return os.getenv("ENABLE_EXECUTION", "false").lower() in {"1", "true", "yes", "on"}

    def _physics_update_enabled(self) -> bool:
        mode = os.getenv("PHYSICS_UPDATE_MODE", "config_only").lower()
        if mode in {"off", "false", "disabled", "none"}:
            return False
        return os.getenv("UPDATE_PHYSICS_REPORT", "false").lower() in {"1", "true", "yes", "on"}

    def _async_physics_update_with_execution_enabled(self) -> bool:
        return os.getenv("ASYNC_PHYSICS_UPDATE_WITH_EXECUTION", "true").lower() in {"1", "true", "yes", "on"}

    def _auto_repair_execution_failures_enabled(self) -> bool:
        return os.getenv("AUTO_REPAIR_EXECUTION_FAILURES", "false").lower() in {"1", "true", "yes", "on"}

    def _normalize_case_rel_path(self, rel_path: str) -> str:
        return rel_path.replace(os.sep, "/")

    def _is_runtime_output_path(self, rel_path: str) -> bool:
        normalized = self._normalize_case_rel_path(rel_path)
        first_part = normalized.split("/", 1)[0]
        if first_part != "0" and re_fullmatch_numeric_time(first_part):
            return True
        if normalized.startswith("postProcessing/") or normalized.startswith("processor"):
            return True
        if normalized.startswith("constant/polyMesh/"):
            return True
        if normalized.startswith("log."):
            return True
        return False

    def _is_physics_relevant_config_path(self, rel_path: str) -> bool:
        normalized = self._normalize_case_rel_path(rel_path)
        if self._is_runtime_output_path(normalized):
            return False
        return normalized.startswith(("system/", "constant/", "0/", "0.orig/"))

    def _filter_physics_relevant_changes(self, changed_files: List[str]) -> tuple[List[str], List[str]]:
        relevant: List[str] = []
        ignored: List[str] = []
        for rel_path in changed_files:
            normalized = self._normalize_case_rel_path(rel_path)
            if self._is_physics_relevant_config_path(normalized):
                relevant.append(normalized)
            else:
                ignored.append(normalized)
        return sorted(set(relevant)), sorted(set(ignored))

    def _start_async_physics_update(self, state: GraphState, changed_files: List[str]) -> bool:
        runner = getattr(self, "_async_physics_update_runner", None)
        active_updates = getattr(self, "_active_async_physics_updates", None)
        case_path = state.get("case_path", "")
        if not runner or active_updates is None or not case_path:
            return False
        if case_path in active_updates:
            print(f"Orchestrator: Async physics update already running for {case_path}.")
            return True
        active_updates.add(case_path)

        update_state = dict(state)
        update_state.update(
            {
                "changed_files": changed_files,
                "needs_physics_update": False,
                "current_agent": "physics_updater",
                "current_task": {
                    "description": "Update physics report asynchronously from relevant configuration changes.",
                    "assigned_agent": "physics_updater",
                    "status": "pending",
                },
            }
        )

        def run_update() -> None:
            try:
                runner(update_state)
                print(f"Orchestrator: Async physics update completed for {case_path}.")
            except Exception as exc:
                print(f"Orchestrator: Async physics update failed for {case_path}: {exc}")
            finally:
                active_updates.discard(case_path)

        thread = threading.Thread(
            target=run_update,
            name=f"physics-update-{os.path.basename(case_path) or 'case'}",
            daemon=True,
        )
        thread.start()
        return True

    def _fail_workflow(self, reason: str, updates: Dict[str, Any] | None = None) -> Dict[str, Any]:
        print(f"Orchestrator: Failing workflow: {reason}")
        return {
            **(updates or {}),
            "current_agent": "end",
            "run_status": "failed",
            "validation_status": "failed",
            "workflow_error": reason,
        }

    def _current_execution_status(self, state: GraphState, case_path: str) -> Dict[str, Any] | None:
        status = state.get("execution_status")
        if isinstance(status, dict):
            return status
        if case_path:
            return read_execution_status(case_path)
        return None

    def _execution_run_status(self, state: GraphState, case_path: str) -> str | None:
        status = self._current_execution_status(state, case_path)
        if status:
            return status.get("run_status")
        return state.get("run_status")

    def _can_finish(self, state: GraphState, case_path: str, physics_report: str) -> tuple[bool, str]:
        if not physics_report:
            return False, "orchestrator attempted to finish before physics_report.md was produced"

        if self._execution_enabled():
            execution_report_path = os.path.join(case_path, "execution_report.md")
            execution_status = self._current_execution_status(state, case_path)
            has_execution_report = os.path.exists(execution_report_path)
            if not has_execution_report:
                return False, "orchestrator attempted to finish before execution_report.md was produced"
            if not execution_status:
                return False, "orchestrator attempted to finish before execution_status.json was produced"
            if not status_run_completed(execution_status):
                return False, "orchestrator attempted to finish before execution_status.json marked execution successful"

        if state.get("validation_status") == "failed":
            return False, "reviewer marked validation as failed"

        return True, ""

    def _last_agent_index(self, completed_tasks: List[dict], agent_name: str) -> int:
        for index in range(len(completed_tasks or []) - 1, -1, -1):
            if completed_tasks[index].get("assigned_agent") == agent_name:
                return index
        return -1

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
        usage = getattr(response, 'usage_metadata', None) or {}
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
        execution_run_status = self._execution_run_status(state, case_path)

        if state.get("workflow_error"):
            return self._fail_workflow(str(state["workflow_error"]))
        
        updates = {}

        last_case_setup_index = self._last_agent_index(completed_tasks, "case_setup_agent")
        last_execution_index = self._last_agent_index(completed_tasks, "execution_agent")
        last_reviewer_index = self._last_agent_index(completed_tasks, "reviewer")
        should_run_initial_execution = last_case_setup_index != -1 and last_execution_index == -1
        should_rerun_after_fix = (
            last_case_setup_index != -1
            and last_execution_index != -1
            and last_case_setup_index > last_execution_index
            and execution_run_status != "completed"
        )

        # If execution is enabled, a pending physics report update should not
        # block the actual solver run. The report can be updated in blocking
        # mode by setting ASYNC_PHYSICS_UPDATE_WITH_EXECUTION=false.
        if state.get('needs_physics_update', False):
            if (
                self._execution_enabled()
                and self._async_physics_update_with_execution_enabled()
                and (should_run_initial_execution or should_rerun_after_fix)
            ):
                async_started = self._start_async_physics_update(state, state.get("changed_files", []))
                print("Orchestrator: Physics update is pending, but execution is allowed to proceed first.")
                return {
                    "current_agent": "execution_agent",
                    "current_task": {
                        "description": "Run the prepared OpenFOAM case while physics report update is deferred.",
                        "assigned_agent": "execution_agent",
                        "status": "pending",
                    },
                    "needs_physics_update": False,
                    "physics_update_pending": True,
                    "physics_update_status": "async_started" if async_started else "deferred_for_execution",
                }

            print("Orchestrator: Routing to 'physics_updater' node.")
            return {
                "current_agent": "physics_updater",
                "current_task": {
                    "description": "Update physics report based on relevant configuration file changes.",
                    "assigned_agent": "physics_updater",
                    "status": "pending"
                },
                "needs_physics_update": False,
                "physics_update_pending": True,
                "physics_update_status": "running",
            }
        if self._execution_enabled() and physics_report and (should_run_initial_execution or should_rerun_after_fix):
            print("Orchestrator: ENABLE_EXECUTION=true and case setup is complete; routing to execution_agent.")
            return {
                "current_agent": "execution_agent",
                "current_task": {
                    "description": "Run the prepared OpenFOAM/blastFoam case and report solver logs/results.",
                    "assigned_agent": "execution_agent",
                    "status": "pending",
                },
            }

        if (
            self._execution_enabled()
            and last_execution_index != -1
            and execution_run_status == "failed"
            and not self._auto_repair_execution_failures_enabled()
        ):
            return self._fail_workflow("execution_status.json marked execution failed; see execution_report.md")

        if self._execution_enabled() and last_execution_index != -1 and execution_run_status == "completed":
            if last_reviewer_index == -1 or last_reviewer_index < last_execution_index:
                print("Orchestrator: Execution completed; routing to reviewer for final validation.")
                return {
                    "current_agent": "reviewer",
                    "current_task": {
                        "description": "Review the completed simulation against the user request and generated reports.",
                        "assigned_agent": "reviewer",
                        "status": "pending",
                    },
                }
            if state.get("validation_status") == "passed":
                print("Orchestrator: Execution and review completed successfully.")
                return {"current_agent": "end"}
            if state.get("validation_status") == "failed":
                return self._fail_workflow("reviewer marked validation as failed")
        
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
        if not str(output_content).strip():
            print("Orchestrator: Empty decision output; retrying once.")
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
                    can_finish, reason = self._can_finish(state, case_path, physics_report)
                    if not can_finish:
                        return self._fail_workflow(reason, updates)
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
                 return self._fail_workflow("orchestrator produced no parseable JSON decision", updates)

        except Exception as e:
            print(f"Orchestrator: Error parsing decision: {e}.")
            return self._fail_workflow(f"orchestrator decision parsing failed: {e}", updates)

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
        elif last_agent == "physics_updater":
            result_summary = "Physics report update completed."
            context_data = "Physics report was updated from relevant configuration changes."
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
        
        if last_agent == "physics_updater":
            updates["physics_update_pending"] = False
            updates["physics_update_status"] = "completed"

        # If last agent was not physics_updater or physics_analyst_agent (prevent loops), check for diffs
        if last_agent != 'physics_updater' and last_agent != 'physics_analyst_agent':
            current_changed_files = []
            for f_path, signature in new_map.items():
                if f_path not in old_map or old_map[f_path] != signature:
                    current_changed_files.append(f_path)
            relevant_changed_files, ignored_changed_files = self._filter_physics_relevant_changes(current_changed_files)
            
            # Accumulate changes
            existing_changed_files = state.get('changed_files', [])
            existing_changed_files, _ = self._filter_physics_relevant_changes(existing_changed_files)
            # Use set to avoid duplicates
            all_changed_files = sorted(set(existing_changed_files + relevant_changed_files))
            
            if all_changed_files:
                updates['changed_files'] = all_changed_files
                
                if last_agent == 'case_setup_agent':
                    if self._physics_update_enabled():
                        if self._execution_enabled() and self._async_physics_update_with_execution_enabled():
                            async_started = self._start_async_physics_update(state, all_changed_files)
                            print(
                                "Orchestrator: Relevant config changes detected; "
                                "deferring physics update so execution can start."
                            )
                            updates['needs_physics_update'] = False
                            updates['physics_update_pending'] = True
                            updates['physics_update_status'] = "async_started" if async_started else "deferred_for_execution"
                        else:
                            print(f"Orchestrator: Relevant config changes detected. Triggering physics update for: {all_changed_files}")
                            updates['needs_physics_update'] = True
                            updates['physics_update_pending'] = True
                            updates['physics_update_status'] = "pending"
                    else:
                        print(f"Orchestrator: Relevant config changes detected, physics update disabled: {all_changed_files}")
                        updates['needs_physics_update'] = False
                        updates['physics_update_pending'] = False
                        updates['physics_update_status'] = "disabled"
                elif last_agent == 'execution_agent':
                    print("Orchestrator: Execution completed; runtime output will not trigger physics report update.")
                    updates['needs_physics_update'] = False
                else:
                    print(f"Orchestrator: Relevant config changes detected {all_changed_files}, but no update trigger for {last_agent}.")
            elif ignored_changed_files:
                print(f"Orchestrator: Ignoring runtime/non-config changes for physics update: {ignored_changed_files}")
        
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
