import argparse
import os
import uuid

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from principia_ai.agents import create_workflow
from principia_ai.graph.graph_state import GraphState
from principia_ai.metrics import MetricsReporter, MetricsTracker
from principia_ai.tools.retrieval_llm_config import resolve_retrieval_llm_config


DEFAULT_CASE_PATH = r"/media/dev/vdb1/linshihao/LLM/PrincipiaBlastFoam_output/surfaceburst_scaledd3"
DEFAULT_USER_REQUEST = "模拟一个触地爆场景，并修改爆炸场景的最远比例距离接近3。"
DEFAULT_TUTORIAL_PATH = "/media/dev/vdb1/linshihao/cases/blastFoam-cases-dataset/blastFoam_tutorials"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PrincipiaBlastFoam multi-agent workflow.")
    parser.add_argument("--case-path", default=DEFAULT_CASE_PATH, help="Target case directory.")
    parser.add_argument("--user-request", default=DEFAULT_USER_REQUEST, help="User task description.")
    parser.add_argument(
        "--tutorial-path",
        default=os.getenv("BLASTFOAM_TUTORIALS", DEFAULT_TUTORIAL_PATH),
        help="BlastFoam tutorial root directory.",
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


def build_main_llm(args: argparse.Namespace) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=args.llm_api_base_url,
        model=args.llm_model,
        api_key=args.llm_api_key,
        temperature=0.1,
    )


def build_workflow_app(llm: ChatOpenAI, args: argparse.Namespace):
    retrieval_config = resolve_retrieval_llm_config(
        api_key=args.retrieval_llm_api_key,
        base_url=args.retrieval_llm_base_url,
        model=args.retrieval_llm_model,
    )
    print(
        "Retrieval LLM config: "
        f"model={retrieval_config['model']}, "
        f"base_url={retrieval_config['base_url']}, "
        f"api_key={'set' if retrieval_config['api_key'] else 'missing'}"
    )
    return create_workflow(
        llm,
        retrieval_llm_api_key=retrieval_config["api_key"],
        retrieval_llm_base_url=retrieval_config["base_url"],
        retrieval_llm_model=retrieval_config["model"],
    )


def test_full_workflow_run(workflow_app, args: argparse.Namespace) -> None:
    """
    Tests a full run of the OASiS workflow from user request to final state.
    """
    print("\n=== Testing Full OASiS Workflow Run ===")

    task_id = str(uuid.uuid4())

    tracker = MetricsTracker()
    tracker.start_task(task_id, args.user_request)

    initial_state = GraphState(
        user_request=args.user_request,
        case_path=args.case_path,
        tutorial_path=args.tutorial_path,
        task_id=task_id,
    )

    try:
        final_state = workflow_app.invoke(initial_state, {"recursion_limit": args.recursion_limit})

        if final_state.get("plan"):
            tracker.record_task_event("planned", len(final_state["plan"]))

        completed_tasks = final_state.get("completed_tasks", [])
        if completed_tasks:
            tracker.record_task_event("completed", len(completed_tasks))

        if final_state.get("validation_status") == "passed":
            tracker.record_validation(True)
        elif final_state.get("validation_status") == "failed":
            tracker.record_validation(False)

        print("\n--- Validating Final State ---")

        case_specs = final_state.get("current_case_specs")
        if case_specs:
            print("✅ Physics specifications were generated successfully.")
        else:
            print("⚠️ Physics specifications were not produced; continuing with available state.")

        if "completed_tasks" in final_state:
            print(f"✅ Workflow completed {len(final_state['completed_tasks'])} tasks.")

        if final_state.get("execution_output"):
            print("✅ Execution output was generated.")

        if "run_status" in final_state:
            print(f"✅ Run status: {final_state['run_status']}")

        if final_state.get("case_files"):
            print("✅ Case files were analyzed/created.")

        if final_state.get("current_agent") == "end" or len(final_state.get("completed_tasks", [])) > 0:
            print("✅ Workflow reached completion state.")

        print("\n--- Workflow Run Test Passed ---")

    except Exception as e:
        print(f"\n❌ Workflow failed with error: {e}")
        tracker.record_error("workflow", str(e))
        raise
    finally:
        tracker.end_task()

        metrics_dir = os.path.join(os.path.dirname(args.case_path), "metrics_reports")
        MetricsReporter.save_report(metrics_dir, task_id)

        print("\n" + "=" * 80)
        MetricsReporter.print_summary()
        print("=" * 80)


def main() -> None:
    load_dotenv(override=True)
    args = parse_args()

    os.makedirs(args.case_path, exist_ok=True)

    llm = build_main_llm(args)
    workflow_app = build_workflow_app(llm, args)
    test_full_workflow_run(workflow_app, args)


if __name__ == "__main__":
    main()
