import os
from typing import Dict, Any

from principia_ai.graph.graph_state import GraphState
from principia_ai.tools.tutorial_initializer import TutorialInitializer
from principia_ai.agents.base_agent import BaseAgent
from principia_ai.tools.standard_tools import get_read_tools
from principia_ai.tools.search.list_directory import list_directory
from principia_ai.prompts.prompt_manager import PromptManager


class CaseInitializationStep:
    """
    Standalone workflow step that initializes an empty case directory using the
    most relevant tutorial case. Runs before any agent logic.
    """

    def __init__(self, llm):
        self.llm = llm
        try:
            self.tutorial_initializer = TutorialInitializer(llm)
        except Exception as exc:
            self.tutorial_initializer = None
            print(f"Warning: Could not initialize TutorialInitializer: {exc}")

        # Initialize Agent
        self.prompt_manager = PromptManager()
        try:
            self.system_prompt = self.prompt_manager.load_prompt("case_initializer", "react_system")
        except Exception as e:
            print(f"Warning: Could not load case_initializer prompt: {e}. Using default.")
            self.system_prompt = (
                "You are the Case Initializer Agent. Check if the case directory needs initialization. "
                "If empty or irrelevant to user request, decide INITIALIZE. Otherwise SKIP. "
                "End with DECISION: INITIALIZE or DECISION: SKIP."
            )
            
        self.agent_tools = get_read_tools() + [list_directory]
        self.agent = BaseAgent(
            llm=self.llm,
            tools=self.agent_tools,
            system_prompt=self.system_prompt,
            agent_name="CaseInitializerAgent",
            max_iterations=10
        )

    def _is_directory_empty(self, directory: str) -> bool:
        """Checks whether directory has visible files."""
        try:
            entries = [name for name in os.listdir(directory) if not name.startswith('.')]
        except FileNotFoundError:
            return True
        except NotADirectoryError:
            return False
        return len(entries) == 0

    def _scan_config_state(self, case_path: str) -> Dict[str, str]:
        """Returns a signature map for core configuration files."""
        signatures: Dict[str, str] = {}
        if not case_path or not os.path.exists(case_path):
            return signatures

        watched_dirs = ['system', 'constant', '0', '0.orig']
        for directory in watched_dirs:
            full_dir = os.path.join(case_path, directory)
            if not os.path.exists(full_dir):
                continue

            for root, _dirs, files in os.walk(full_dir):
                for file_name in files:
                    if file_name.startswith('.'):  # ignore hidden files
                        continue
                    if "polyMesh" in root and file_name in ["points", "faces", "owner", "neighbour", "cellZones"]:
                        continue

                    abs_path = os.path.join(root, file_name)
                    rel_path = os.path.relpath(abs_path, case_path)
                    try:
                        stats = os.stat(abs_path)
                        signatures[rel_path] = f"{stats.st_size}:{stats.st_mtime}"
                    except OSError:
                        continue
        return signatures

    def run(self, state: GraphState) -> Dict[str, Any]:
        """Initializes the case directory if it is empty."""
        case_path = state.get("case_path", "")
        if not case_path:
            return {}

        os.makedirs(case_path, exist_ok=True)
        
        user_request = state.get("user_request", "")
        
        # Invoke Agent to decide
        input_text = (
            f"User Request: {user_request}\n"
            f"Case Directory: {case_path}\n"
            "Please check the directory and decide if we need to initialize the case."
        )
        
        print("Case Initializer Agent: Checking if initialization is needed...")
        result = self.agent.invoke({"input": input_text})
        output = result.get("output", "")
        
        should_initialize = False
        if "DECISION: INITIALIZE" in output:
            should_initialize = True
        elif "DECISION: SKIP" in output:
            should_initialize = False
        else:
            # Fallback if agent fails to decide clearly, use old logic (empty check)
            print("Case Initializer Agent: Ambiguous decision, falling back to empty check.")
            should_initialize = self._is_directory_empty(case_path)

        if not should_initialize:
            print("Case Initializer Agent: Skipping initialization.")
            return {}

        print("Case Initializer Agent: Proceeding with initialization.")

        if not self.tutorial_initializer:
            return {"initialization_message": "Tutorial initializer unavailable."}

        tutorial_root = state.get("tutorial_path") or os.getenv(
            "BLASTFOAM_TUTORIALS",
            "/media/dev/vdb1/linshihao/cases/blastFoam-cases-dataset/blastFoam_tutorials",
        )

        if not tutorial_root or not os.path.exists(tutorial_root):
            return {"initialization_message": f"Tutorial path unavailable: {tutorial_root}"}

        cases = self.tutorial_initializer.find_complete_cases(tutorial_root)
        if not cases:
            return {"initialization_message": "Error: No tutorial cases found."}

        relevant_cases = self.tutorial_initializer.find_relevant_tutorial_cases(user_request, cases, top_k=1)
        if not relevant_cases:
            return {"initialization_message": "Error: Could not find relevant tutorial case."}

        selected_case = relevant_cases[0]
        source_case_path = selected_case.get("path")
        if not source_case_path or not os.path.exists(source_case_path):
            return {"initialization_message": "Selected tutorial case path invalid."}

        success = self.tutorial_initializer.copy_case_files(source_case_path, case_path)
        if not success:
            return {"initialization_message": "Failed to initialize case from tutorial."}

        message = (
            "Successfully initialized case from "
            f"{selected_case.get('relative_path', os.path.basename(source_case_path))}."
        )

        return {
            "tutorial_initialized": True,
            "initialization_message": message,
            "config_state_map": self._scan_config_state(case_path),
        }