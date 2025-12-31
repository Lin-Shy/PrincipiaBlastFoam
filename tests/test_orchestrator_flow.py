import os
import sys
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from principia_ai.agents.orchestrator import OrchestratorAgent
from principia_ai.graph.graph_state import GraphState

# Load environment variables
load_dotenv()

def get_llm():
    # Try to get from env, otherwise use defaults or fail gracefully
    base_url = os.getenv("LLM_API_BASE_URL")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    
    if not api_key:
        print("Warning: LLM_API_KEY not found. Tests might fail if they hit the real LLM.")
    
    return ChatOpenAI(
        base_url=base_url,
        model=model,
        api_key=api_key,
        temperature=0.1
    )

def test_orchestrator_flow():
    print("=== Testing Orchestrator Flow ===")
    
    # 1. Initialize LLM and Orchestrator
    try:
        llm = get_llm()
        orchestrator = OrchestratorAgent(llm)
        print("Orchestrator initialized.")
    except Exception as e:
        print(f"Failed to initialize Orchestrator: {e}")
        return

    # 2. Load Physics Analyst Output
    physics_output_path = "/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/agents_output/physics_analyst_agent.md"
    physics_context = ""
    case_path = "/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/agents_output"
    
    if os.path.exists(physics_output_path):
        with open(physics_output_path, 'r') as f:
            physics_context = f.read()
        print(f"Loaded physics context from {physics_output_path}")
    else:
        print(f"Warning: Physics output file not found at {physics_output_path}")
        # Create a dummy context if file is missing, to ensure test runs
        physics_context = """
        ### Analysis
        The case is a blastFoam simulation.
        Current status:
        - Mesh: snappyHexMesh used.
        - Solver: blastFoam.
        - Issues: None critical, but check refinement.
        """
        print("Using dummy physics context.")

    # Persist the context to the case directory so orchestrator reads from filesystem
    os.makedirs(case_path, exist_ok=True)
    report_path = os.path.join(case_path, "physics_report.md")
    with open(report_path, "w") as f:
        f.write(physics_context)
    print(f"Physics report written to {report_path}")

    # 3. Construct Initial State
    # Scenario: User wants to modify the case to increase refinement.
    # user_request = "Please check the refinement levels and increase them if necessary to ensure shock capturing."
    
    user_request = "通过修改炸弹的体积来使其当量修改成100kg，其他不做修改。"
    # Initialize state as a dict (GraphState is a TypedDict)
    state = {
        "user_request": user_request,
        "case_path": case_path,
        "current_agent": "physics_analyst_agent",
        "completed_tasks": [],
        "plan": None,
        "current_task": {}
    }

    print("\n--- Step 1: Initial Routing (Should generate Plan) ---")
    # This call should trigger plan generation AND the first step decision
    result1 = orchestrator.route(state)
    
    # Print result for inspection
    print("Result 1 keys:", result1.keys())
    if "plan" in result1:
        print("Plan generated successfully.")
        print(f"Plan preview: {result1['plan'][:100]}...")
    else:
        print("Test Failed: Plan was not generated.")
        return

    next_agent = result1.get("current_agent")
    print(f"Next Agent selected: {next_agent}")
    
    if next_agent == "end":
        print("Orchestrator decided to end immediately.")
        return

    # 4. Simulate Execution of First Step
    # Assume the orchestrator routed to 'case_setup_agent'
    
    task_instruction = result1.get("current_task", {}).get("description", "No instruction")
    print(f"Task Instruction: {task_instruction}")

    # Simulate that the agent ran successfully
    print(f"\n--- Simulating {next_agent} execution ---")
    
    completed_task = {
        "description": task_instruction,
        "status": "completed",
        "assigned_agent": next_agent,
        "result_summary": "Modified snappyHexMeshDict to increase refinement level to 3.",
        "context_data": "Updated system/snappyHexMeshDict. Refinement levels set to (3 3)."
    }
    
    # Update state manually (simulating the graph update)
    state["completed_tasks"].append(completed_task)
    state["current_agent"] = next_agent
    state["plan"] = result1["plan"] # Persist the plan
    
    # 5. Step 2: Routing after First Step
    print("\n--- Step 2: Routing after First Step ---")
    result2 = orchestrator.route(state)
    
    next_agent_2 = result2.get("current_agent")
    print(f"Next Agent selected: {next_agent_2}")
    
    if "current_task" in result2:
        print(f"Next Task Instruction: {result2['current_task'].get('description')}")

if __name__ == "__main__":
    test_orchestrator_flow()
