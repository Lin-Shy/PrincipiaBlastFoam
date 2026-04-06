import argparse
import json
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from principia_ai.agents import create_workflow
from principia_ai.graph.graph_state import GraphState
from principia_ai.metrics import MetricsReporter, MetricsTracker
from principia_ai.tools.retrieval_llm_config import resolve_retrieval_llm_config


DEFAULT_MODE = "basic"
DEFAULT_TUTORIAL_PATH = "/media/dev/vdb1/linshihao/cases/blastFoam-cases-dataset/blastFoam_tutorials"


def default_modifications_file(mode: str) -> str:
    return f"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam/dataset/modification/blastfoam_{mode}_modifications.json"


def default_output_base_dir(mode: str) -> str:
    return f"/media/dev/vdb1/linshihao/LLM/LLM-output-cases/agent-batch_runs/blastfoam_{mode}_modifications"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PrincipiaBlastFoam batch workflow.")
    parser.add_argument(
        "--mode",
        default=DEFAULT_MODE,
        help="Modification dataset mode, typically 'basic' or 'senior'.",
    )
    parser.add_argument(
        "--tutorial-path",
        default=os.getenv("BLASTFOAM_TUTORIALS", DEFAULT_TUTORIAL_PATH),
        help="BlastFoam tutorial root directory.",
    )
    parser.add_argument(
        "--modifications-file",
        default=None,
        help="Path to the batch modifications JSON file. Defaults to the path derived from --mode.",
    )
    parser.add_argument(
        "--output-base-dir",
        default=None,
        help="Base output directory for generated cases. Defaults to the path derived from --mode.",
    )
    parser.add_argument(
        "--results-file",
        default=None,
        help="Batch results JSON path. Defaults to <output-base-dir>/batch_execution_results.json.",
    )
    parser.add_argument(
        "--llm-api-base-url",
        default=os.getenv("LLM_API_BASE_URL"),
        help="Main agent LLM base URL. Defaults to LLM_API_BASE_URL.",
    )
    parser.add_argument(
        "--llm-api-key",
        default=os.getenv("LLM_API_KEY"),
        help="Main agent LLM API key. Defaults to LLM_API_KEY.",
    )
    parser.add_argument(
        "--llm-model",
        default=os.getenv("LLM_MODEL"),
        help="Main agent LLM model. Defaults to LLM_MODEL.",
    )
    parser.add_argument(
        "--retrieval-llm-api-key",
        default=os.getenv("RETRIEVAL_LLM_API_KEY"),
        help="Retrieval-only LLM API key. Falls back to RETRIEVAL_LLM_API_KEY/LLM_API_KEY.",
    )
    parser.add_argument(
        "--retrieval-llm-base-url",
        default=os.getenv("RETRIEVAL_LLM_API_BASE_URL"),
        help="Retrieval-only LLM base URL. Falls back to RETRIEVAL_LLM_API_BASE_URL/LLM_API_BASE_URL.",
    )
    parser.add_argument(
        "--retrieval-llm-model",
        default=os.getenv("RETRIEVAL_LLM_MODEL"),
        help="Retrieval-only LLM model. Falls back to RETRIEVAL_LLM_MODEL/LLM_MODEL.",
    )
    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=200,
        help="LangGraph recursion limit.",
    )
    return parser.parse_args()


def build_runtime_config(args: argparse.Namespace) -> argparse.Namespace:
    args.modifications_file = args.modifications_file or default_modifications_file(args.mode)
    args.output_base_dir = args.output_base_dir or default_output_base_dir(args.mode)
    args.results_file = args.results_file or os.path.join(args.output_base_dir, "batch_execution_results.json")
    return args


def build_main_llm(args: argparse.Namespace) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=args.llm_api_base_url,
        model=args.llm_model,
        api_key=args.llm_api_key,
        temperature=0.1,
    )


def load_modifications(modifications_file: str):
    with open(modifications_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_batch_results(results, results_file: str):
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if "current_summary" in results:
        summary = results["current_summary"]
        print(
            f"   ✅ Success: {summary['success']} | ❌ Failed: {summary['failed']} | "
            f"⚠️  Incomplete: {summary['incomplete']} | 📊 Results saved to: {results_file}"
        )


def execute_single_case(modification, llm_instance, args: argparse.Namespace, retrieval_config, index: int, total: int):
    """
    Execute workflow for a single case modification.
    """
    case_name = modification["case_name"]
    case_path = os.path.join(args.output_base_dir, case_name)
    user_request = f"{modification['description']} {modification['modification']}"

    print("\n" + "=" * 80)
    print(f"🚀 Processing Case [{index}/{total}]: {case_name}")
    print("=" * 80)
    print(f"📝 User Request: {user_request}")
    print(f"📁 Output Path: {case_path}")
    print(f"📄 Modified Files: {', '.join(modification['modified_files'])}")

    task_id = str(uuid.uuid4())

    tracker = MetricsTracker()
    tracker.start_task(task_id, user_request)

    result = {
        "case_name": case_name,
        "case_path": case_path,
        "base_case": modification["case_path"],
        "user_request": user_request,
        "modified_files": modification["modified_files"],
        "task_id": task_id,
        "start_time": datetime.now().isoformat(),
        "status": "pending",
        "error": None,
        "metrics": {},
    }

    try:
        os.makedirs(case_path, exist_ok=True)
        os.environ["BLASTFOAM_TUTORIALS"] = args.tutorial_path

        workflow_app = create_workflow(
            llm_instance,
            retrieval_llm_api_key=retrieval_config["api_key"],
            retrieval_llm_base_url=retrieval_config["base_url"],
            retrieval_llm_model=retrieval_config["model"],
        )

        initial_state = GraphState(
            user_request=user_request,
            case_path=case_path,
            tutorial_path=args.tutorial_path,
            task_id=task_id,
        )

        print("\n⚙️  Starting workflow execution...")
        final_state = workflow_app.invoke(initial_state, {"recursion_limit": args.recursion_limit})

        if final_state.get("plan"):
            tracker.record_task_event("planned", len(final_state["plan"]))
            result["planned_tasks"] = len(final_state["plan"])

        completed_tasks = final_state.get("completed_tasks", [])
        if completed_tasks:
            tracker.record_task_event("completed", len(completed_tasks))
            result["completed_tasks"] = len(completed_tasks)

        if final_state.get("validation_status") == "passed":
            tracker.record_validation(True)
            result["validation_status"] = "passed"
        elif final_state.get("validation_status") == "failed":
            tracker.record_validation(False)
            result["validation_status"] = "failed"
        else:
            result["validation_status"] = "unknown"

        if final_state.get("current_agent") == "end" or len(final_state.get("completed_tasks", [])) > 0:
            result["status"] = "success"
            print(f"✅ Case {case_name} completed successfully!")
        else:
            result["status"] = "incomplete"
            print(f"⚠️  Case {case_name} completed with warnings.")

        result["run_status"] = final_state.get("run_status", "unknown")
        result["has_execution_output"] = "execution_output" in final_state
        result["case_specs_generated"] = "current_case_specs" in final_state

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ Case {case_name} failed with error: {error_msg}")
        tracker.record_error("workflow", error_msg)
        result["status"] = "failed"
        result["error"] = error_msg

    finally:
        tracker.end_task()
        result["end_time"] = datetime.now().isoformat()

        metrics_summary = tracker.get_metrics()
        if metrics_summary:
            result["metrics"] = metrics_summary

        metrics_dir = os.path.join(args.output_base_dir, "metrics_reports")
        MetricsReporter.save_report(metrics_dir, task_id)

        print(f"\n📊 Metrics saved for task: {task_id}")

    return result


def run_batch_workflow(args: argparse.Namespace):
    print("\n" + "=" * 80)
    print("🎯 BATCH WORKFLOW EXECUTION")
    print("=" * 80)

    os.makedirs(args.output_base_dir, exist_ok=True)
    os.environ["BLASTFOAM_TUTORIALS"] = args.tutorial_path

    print(f"\n📂 Loading modifications from: {args.modifications_file}")
    modifications = load_modifications(args.modifications_file)
    total_cases = len(modifications)
    print(f"✅ Found {total_cases} cases to process")

    print(f"\n🤖 Initializing LLM: {args.llm_model}")
    llm_instance = build_main_llm(args)

    retrieval_config = resolve_retrieval_llm_config(
        api_key=args.retrieval_llm_api_key,
        base_url=args.retrieval_llm_base_url,
        model=args.retrieval_llm_model,
    )
    print(
        "🔎 Retrieval LLM config: "
        f"model={retrieval_config['model']}, "
        f"base_url={retrieval_config['base_url']}, "
        f"api_key={'set' if retrieval_config['api_key'] else 'missing'}"
    )

    batch_results = {
        "batch_start_time": datetime.now().isoformat(),
        "total_cases": total_cases,
        "mode": args.mode,
        "modifications_file": args.modifications_file,
        "output_directory": args.output_base_dir,
        "tutorial_path": args.tutorial_path,
        "llm_model": args.llm_model,
        "llm_api_base_url": args.llm_api_base_url,
        "retrieval_llm_model": retrieval_config["model"],
        "retrieval_llm_base_url": retrieval_config["base_url"],
        "results": [],
    }

    success_count = 0
    failed_count = 0

    for index, modification in enumerate(modifications, start=1):
        result = execute_single_case(modification, llm_instance, args, retrieval_config, index, total_cases)
        batch_results["results"].append(result)

        if result["status"] == "success":
            success_count += 1
        elif result["status"] == "failed":
            failed_count += 1

        batch_results["current_summary"] = {
            "processed": index,
            "remaining": total_cases - index,
            "success": success_count,
            "failed": failed_count,
            "incomplete": index - success_count - failed_count,
        }

        print(f"\n💾 Saving progress: {index}/{total_cases} cases processed...")
        save_batch_results(batch_results, args.results_file)

    batch_results["batch_end_time"] = datetime.now().isoformat()
    batch_results["summary"] = {
        "success": success_count,
        "failed": failed_count,
        "incomplete": total_cases - success_count - failed_count,
    }

    save_batch_results(batch_results, args.results_file)

    print("\n" + "=" * 80)
    print("📊 BATCH EXECUTION SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully completed: {success_count}/{total_cases}")
    print(f"❌ Failed: {failed_count}/{total_cases}")
    print(f"⚠️  Incomplete: {total_cases - success_count - failed_count}/{total_cases}")
    print(f"\n📁 Results saved to: {args.results_file}")
    print(f"📁 Cases output to: {args.output_base_dir}")
    print("=" * 80 + "\n")


def main() -> None:
    load_dotenv(override=True)
    args = build_runtime_config(parse_args())
    run_batch_workflow(args)


if __name__ == "__main__":
    main()
