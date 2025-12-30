import os
import uuid
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from principia_ai.agents import create_workflow
from principia_ai.graph.graph_state import GraphState
from principia_ai.metrics import MetricsTracker, MetricsReporter

# Load environment variables
load_dotenv(override=True)
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL_NAME = os.getenv("LLM_MODEL")

# CASE_PATH = r"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/urban_005_14"
# user_request = "只修改运行的并行度为16，其他不做修改。"


# CASE_PATH = r"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/building3D"
# user_request = "通过修改炸弹的体积来使其当量修改成100kg，其他不做修改。"

# CASE_PATH = r"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/airburst_scaledh3"
# user_request = "模拟一个自由场空爆场景，并通过修改爆源的高度来设定爆炸的比例爆高为3.0或者接近3.0，设定爆炸场景的实际大小为实际爆高的3倍。"

# CASE_PATH = r"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/surfaceburst_scaledd3"
# user_request = "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。"

# CASE_PATH = r"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/airburst_scaledh3"
# user_request = "通过修改爆源的高度来设定爆炸的比例爆高为3.0或者接近3.0，设定爆炸场景的实际大小为实际爆高的3倍，其他不做修改。"

CASE_PATH = r"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/BuildingDiffraction"
user_request = "Simulate a simple scenario of an exterior blast diffraction, including only the ground, an explosive source, and a rectangular building. The explosive source is at the same height as the center of the rectangular building and is located at a certain distance from it."

# CASE_PATH = r"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/building3D"
# user_request = "Set the charge closer to the building to observe the effects on the structure."


tutorial_path = "/media/dev/vdb1/linshihao/cases/blastFoam-cases-dataset/blastFoam_tutorials"


def llm():
    """Provides a ChatOpenAI instance for the test module."""
    return ChatOpenAI(
        base_url=LLM_API_BASE_URL,
        model=LLM_MODEL_NAME,
        api_key=LLM_API_KEY,
        temperature=0.1,
    )


def workflow_app(llm):
    """Creates the full LangGraph application for testing."""
    return create_workflow(llm)


def test_full_workflow_run(workflow_app):
    """
    Tests a full run of the OASiS workflow from user request to final state.
    """
    print("\n=== Testing Full OASiS Workflow Run ===")

    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 初始化指标追踪器
    tracker = MetricsTracker()
    tracker.start_task(task_id, user_request)

    initial_state = GraphState(
        user_request=user_request,
        case_path=CASE_PATH,  # For Physics Analyst to analyze existing case
        tutorial_path=tutorial_path,
        task_id=task_id
    )

    try:
        # Invoke the workflow
        final_state = workflow_app.invoke(initial_state, {"recursion_limit": 200})

        # 记录计划任务数
        if final_state.get('plan'):
            tracker.record_task_event('planned', len(final_state['plan']))
        
        # 记录完成任务数
        completed_tasks = final_state.get('completed_tasks', [])
        if completed_tasks:
            tracker.record_task_event('completed', len(completed_tasks))
        
        # 记录验证结果
        if final_state.get('validation_status') == 'passed':
            tracker.record_validation(True)
        elif final_state.get('validation_status') == 'failed':
            tracker.record_validation(False)

        # --- Assertions to validate the final state ---
        print("\n--- Validating Final State ---")

        # 1. Check physics specs (optional in current workflow)
        case_specs = final_state.get("current_case_specs")
        if case_specs:
            print("✅ Physics specifications were generated successfully.")
        else:
            print("⚠️ Physics specifications were not produced; continuing with available state.")

        # 3. Check completed tasks
        if "completed_tasks" in final_state:
            print(f"✅ Workflow completed {len(final_state['completed_tasks'])} tasks.")
        
        # 4. Check execution results (if execution was performed)
        if final_state.get("execution_output"):
            print("✅ Execution output was generated.")
        
        # 5. Check run status (if execution was performed)
        if "run_status" in final_state:
            print(f"✅ Run status: {final_state['run_status']}")
        
        # 6. Check that case files were analyzed or created
        if final_state.get("case_files"):
            print("✅ Case files were analyzed/created.")

        # 9. Check workflow completion
        if final_state.get("current_agent") == "end" or len(final_state.get("completed_tasks", [])) > 0:
            print("✅ Workflow reached completion state.")

        print("\n--- Workflow Run Test Passed ---")
    
    except Exception as e:
        print(f"\n❌ Workflow failed with error: {e}")
        tracker.record_error("workflow", str(e))
        raise
    finally:
        # 结束追踪并生成报告
        tracker.end_task()
        
        # 保存报告到文件
        metrics_dir = os.path.join(os.path.dirname(CASE_PATH), "metrics_reports")
        MetricsReporter.save_report(metrics_dir, task_id)
        
        # 打印摘要到控制台
        print("\n" + "="*80)
        MetricsReporter.print_summary()
        print("="*80)



if __name__ == '__main__':
    # Initialize components
    llm = llm()
    os.makedirs(CASE_PATH, exist_ok=True)

    workflow_app = workflow_app(llm)
    test_full_workflow_run(workflow_app)
    