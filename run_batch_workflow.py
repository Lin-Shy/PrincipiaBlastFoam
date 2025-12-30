import os
import json
import uuid
from datetime import datetime
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

# Configuration
BLASTFOAM_TUTORIALS="/media/dev/vdb1/linshihao/cases/blastFoam-cases-dataset/blastFoam_tutorials"
TUTORIAL_PATH = "/media/dev/vdb1/linshihao/cases/blastFoam-cases-dataset/blastFoam_tutorials/"
mode = "basic"  # Change to desired mode: "senior" or "basic"
MODIFICATIONS_FILE = f"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/dataset/modification/blastfoam_{mode}_modifications.json"
OUTPUT_BASE_DIR = f"/media/dev/vdb1/linshihao/LLM/LLM-output-cases/agent-batch_runs/blastfoam_{mode}_modifications"
RESULTS_FILE = os.path.join(OUTPUT_BASE_DIR, "batch_execution_results.json")


def llm():
    """Provides a ChatOpenAI instance."""
    return ChatOpenAI(
        base_url=LLM_API_BASE_URL,
        model=LLM_MODEL_NAME,
        api_key=LLM_API_KEY,
        temperature=0.1,
    )


def load_modifications():
    """Load modifications from JSON file."""
    with open(MODIFICATIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_batch_results(results):
    """Save batch execution results to JSON file (incremental save after each case)."""
    os.makedirs(os.path.dirname(RESULTS_FILE), exist_ok=True)
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Show current progress if available
    if "current_summary" in results:
        summary = results["current_summary"]
        print(f"   ✅ Success: {summary['success']} | ❌ Failed: {summary['failed']} | "
              f"⚠️  Incomplete: {summary['incomplete']} | 📊 Results saved to: {RESULTS_FILE}")


def execute_single_case(modification, llm_instance, index, total):
    """
    Execute workflow for a single case modification.
    
    Args:
        modification: Dictionary containing case modification details
        llm_instance: ChatOpenAI instance
        index: Current case index (1-based)
        total: Total number of cases
        
    Returns:
        Dictionary containing execution results
    """
    case_name = modification['case_name']
    case_path = os.path.join(OUTPUT_BASE_DIR, case_name)
    
    # Construct full user request from description and modification
    user_request = f"{modification['description']} {modification['modification']}"
    
    print("\n" + "="*80)
    print(f"🚀 Processing Case [{index}/{total}]: {case_name}")
    print("="*80)
    print(f"📝 User Request: {user_request}")
    print(f"📁 Output Path: {case_path}")
    print(f"📄 Modified Files: {', '.join(modification['modified_files'])}")
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    
    # Initialize metrics tracker
    tracker = MetricsTracker()
    tracker.start_task(task_id, user_request)
    
    # Initialize result record
    result = {
        "case_name": case_name,
        "case_path": case_path,
        "base_case": modification['case_path'],
        "user_request": user_request,
        "modified_files": modification['modified_files'],
        "task_id": task_id,
        "start_time": datetime.now().isoformat(),
        "status": "pending",
        "error": None,
        "metrics": {}
    }
    
    try:
        # Ensure case directory exists
        os.makedirs(case_path, exist_ok=True)
        
        # Create workflow app
        workflow_app = create_workflow(llm_instance)
        
        initial_state = GraphState(
            user_request=user_request,
            case_path=case_path,
            tutorial_path=TUTORIAL_PATH,
            task_id=task_id
        )
        
        # Invoke the workflow
        print(f"\n⚙️  Starting workflow execution...")
        final_state = workflow_app.invoke(initial_state, {"recursion_limit": 200})
        
        # Record planned tasks
        if final_state.get('plan'):
            tracker.record_task_event('planned', len(final_state['plan']))
            result['planned_tasks'] = len(final_state['plan'])
        
        # Record completed tasks
        completed_tasks = final_state.get('completed_tasks', [])
        if completed_tasks:
            tracker.record_task_event('completed', len(completed_tasks))
            result['completed_tasks'] = len(completed_tasks)
        
        # Record validation results
        if final_state.get('validation_status') == 'passed':
            tracker.record_validation(True)
            result['validation_status'] = 'passed'
        elif final_state.get('validation_status') == 'failed':
            tracker.record_validation(False)
            result['validation_status'] = 'failed'
        else:
            result['validation_status'] = 'unknown'
        
        # Check if workflow completed successfully
        if final_state.get("current_agent") == "end" or len(final_state.get("completed_tasks", [])) > 0:
            result['status'] = 'success'
            print(f"✅ Case {case_name} completed successfully!")
        else:
            result['status'] = 'incomplete'
            print(f"⚠️  Case {case_name} completed with warnings.")
        
        # Store additional information
        result['run_status'] = final_state.get('run_status', 'unknown')
        result['has_execution_output'] = 'execution_output' in final_state
        result['case_specs_generated'] = 'current_case_specs' in final_state
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Case {case_name} failed with error: {error_msg}")
        tracker.record_error("workflow", error_msg)
        result['status'] = 'failed'
        result['error'] = error_msg
    
    finally:
        # End tracking and save metrics
        tracker.end_task()
        result['end_time'] = datetime.now().isoformat()
        
        # Get metrics summary from tracker
        metrics_summary = tracker.get_metrics()
        if metrics_summary:
            result['metrics'] = metrics_summary
        
        # Save metrics report
        metrics_dir = os.path.join(OUTPUT_BASE_DIR, "metrics_reports")
        MetricsReporter.save_report(metrics_dir, task_id)
        
        print(f"\n📊 Metrics saved for task: {task_id}")
    
    return result


def run_batch_workflow():
    """
    Main function to run batch workflow for all modifications.
    """
    print("\n" + "="*80)
    print("🎯 BATCH WORKFLOW EXECUTION")
    print("="*80)
    
    # Create output directory
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    
    # Load modifications
    print(f"\n📂 Loading modifications from: {MODIFICATIONS_FILE}")
    modifications = load_modifications()
    total_cases = len(modifications)
    print(f"✅ Found {total_cases} cases to process")
    
    # Initialize LLM (reuse for all cases)
    print(f"\n🤖 Initializing LLM: {LLM_MODEL_NAME}")
    llm_instance = llm()
    
    # Track overall results
    batch_results = {
        "batch_start_time": datetime.now().isoformat(),
        "total_cases": total_cases,
        "modifications_file": MODIFICATIONS_FILE,
        "output_directory": OUTPUT_BASE_DIR,
        "tutorial_path": TUTORIAL_PATH,
        "results": []
    }
    
    # Process each modification
    success_count = 0
    failed_count = 0
    
    for index, modification in enumerate(modifications, start=1):
        result = execute_single_case(modification, llm_instance, index, total_cases)
        batch_results["results"].append(result)
        
        if result['status'] == 'success':
            success_count += 1
        elif result['status'] == 'failed':
            failed_count += 1
        
        # Update current summary after each case
        batch_results["current_summary"] = {
            "processed": index,
            "remaining": total_cases - index,
            "success": success_count,
            "failed": failed_count,
            "incomplete": index - success_count - failed_count
        }
        
        # Save intermediate results after each case (incremental save)
        print(f"\n💾 Saving progress: {index}/{total_cases} cases processed...")
        save_batch_results(batch_results)
    
    # Finalize batch results
    batch_results["batch_end_time"] = datetime.now().isoformat()
    batch_results["summary"] = {
        "success": success_count,
        "failed": failed_count,
        "incomplete": total_cases - success_count - failed_count
    }
    
    # Save final results
    save_batch_results(batch_results)
    
    # Print final summary
    print("\n" + "="*80)
    print("📊 BATCH EXECUTION SUMMARY")
    print("="*80)
    print(f"✅ Successfully completed: {success_count}/{total_cases}")
    print(f"❌ Failed: {failed_count}/{total_cases}")
    print(f"⚠️  Incomplete: {total_cases - success_count - failed_count}/{total_cases}")
    print(f"\n📁 Results saved to: {RESULTS_FILE}")
    print(f"📁 Cases output to: {OUTPUT_BASE_DIR}")
    print("="*80 + "\n")


if __name__ == '__main__':
    run_batch_workflow()
