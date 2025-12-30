"""
Defines the shared state object for the langgraph workflow.
"""
import uuid
from typing import List, Dict, TypedDict, Optional, Any


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        user_request: The initial user request.
        case_path: The path to the OpenFOAM case directory.
        tutorial_path: The path to the OpenFOAM tutorial directory for initialization.
        task_id: Unique identifier for this workflow task.
        plan: A list of tasks to be executed.
        completed_tasks: A list of completed tasks.
        current_task: The currently executing task.
        current_case_specs: Specifications derived from physics analysis.
        case_files: A dictionary of file paths and their content.
        execution_output: Output from the execution agent.
        validation_status: The status of the validation ('passed' or 'failed').
        validation_notes: Notes from the validation process.
        issue_details: Detailed information about any issues found.
        iteration_count: The number of iterations the graph has run.
    """
    user_request: str
    case_path: str
    tutorial_path: Optional[str]
    task_id: Optional[str]
    plan: Optional[List[dict]]
    completed_tasks: List[dict]
    current_task: Optional[dict]
    current_case_specs: Optional[Dict[str, Any]]
    relevant_tutorial_cases: Optional[List[Dict[str, Any]]]
    case_files: Dict[str, str]
    execution_output: Optional[str]
    validation_status: Optional[str]
    validation_notes: Optional[str]
    issue_details: Optional[dict]
    iteration_count: int
    current_agent: Optional[str]
    physics_analysis: Optional[str]
    run_status: Optional[str]
    execution_summary: Optional[str]
    config_state_map: Optional[Dict[str, str]]
    needs_physics_update: Optional[bool]
    changed_files: Optional[List[str]]
