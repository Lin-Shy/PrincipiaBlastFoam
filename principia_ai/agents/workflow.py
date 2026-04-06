import os
from langgraph.graph import StateGraph, END
from principia_ai.graph.graph_state import GraphState
from principia_ai.agents import (OrchestratorAgent, PhysicsAnalystAgent,
                              CaseSetupAgent, ExecutionAgent, PostProcessingAgent, ReviewerAgent)
from principia_ai.workflow.case_initializer_step import CaseInitializationStep


def create_workflow(
    llm,
    retrieval_llm_api_key=None,
    retrieval_llm_base_url=None,
    retrieval_llm_model=None,
):
    """
    创建并配置基于OASiS模型的多智能体协作工作流。
    (Creates and configures the multi-agent collaboration workflow based on the OASiS model.)
    """
    
    # 1. 初始化所有智能体 (Initialize all agents)
    # 获取知识检索工具配置
    use_user_guide_retriever = os.getenv("USE_USER_GUIDE_RETRIEVER", "true").lower() == "true"
    use_tutorial_retriever = os.getenv("USE_TUTORIAL_RETRIEVER", "true").lower() == "true"
    use_knowledge_manager = os.getenv("USE_KNOWLEDGE_MANAGER", "true").lower() == "true"

    retrieval_kwargs = {
        "retrieval_llm_api_key": retrieval_llm_api_key,
        "retrieval_llm_base_url": retrieval_llm_base_url,
        "retrieval_llm_model": retrieval_llm_model,
    }
    
    case_initializer = CaseInitializationStep(llm)
    orchestrator = OrchestratorAgent(llm, use_knowledge_manager, use_tutorial_retriever)
    physics_analyst_agent = PhysicsAnalystAgent(
        llm,
        use_knowledge_manager,
        use_tutorial_retriever,
        **retrieval_kwargs,
    )
    case_setup_agent = CaseSetupAgent(
        llm,
        use_knowledge_manager,
        use_tutorial_retriever,
        **retrieval_kwargs,
    )
    execution_agent = ExecutionAgent(
        llm,
        use_knowledge_manager,
        use_tutorial_retriever,
        **retrieval_kwargs,
    )
    post_processing_agent = PostProcessingAgent(
        llm,
        use_knowledge_manager,
        use_tutorial_retriever,
        **retrieval_kwargs,
    )
    reviewer_agent = ReviewerAgent(
        llm,
        use_knowledge_manager=use_knowledge_manager,
        use_tutorial_retriever=use_tutorial_retriever,
        **retrieval_kwargs,
    )

    # 2. 定义工作流图 (Define the workflow graph)
    workflow = StateGraph(GraphState)

    # 3. 添加节点 (Add nodes for each agent)
    workflow.add_node("case_initializer", case_initializer.run)
    workflow.add_node("orchestrator", orchestrator.route)
    workflow.add_node("feedback_processor", orchestrator.process_feedback)
    workflow.add_node("physics_analyst_agent", physics_analyst_agent.analyze)
    workflow.add_node("physics_updater", physics_analyst_agent.update_report)
    
    # 只使用case_setup_agent处理所有文件生成任务
    workflow.add_node("case_setup_agent", case_setup_agent.run_setup)
    workflow.add_node("execution_agent", execution_agent.execute)
    workflow.add_node("post_processing_agent", post_processing_agent.process)
    workflow.add_node("reviewer", reviewer_agent.review_task) # Add reviewer node

    # 4. 定义路由逻辑 (Define the routing logic)
    workflow.set_entry_point("case_initializer")

    # 5. Agents route to feedback_processor to allow Orchestrator to decide next step
    workflow.add_edge("case_initializer", "orchestrator")
    workflow.add_edge("physics_analyst_agent", "feedback_processor")
    workflow.add_edge("physics_updater", "feedback_processor")
    workflow.add_edge("case_setup_agent", "feedback_processor")
    workflow.add_edge("execution_agent", "feedback_processor")
    workflow.add_edge("post_processing_agent", "feedback_processor")
    workflow.add_edge("reviewer", "feedback_processor")

    # 6. 反馈处理器返回到协调器进行下一轮路由
    workflow.add_edge("feedback_processor", "orchestrator")

    # 添加结束条件
    workflow.add_conditional_edges(
        "orchestrator",
        lambda state: state.get('current_agent'),
        {
            "orchestrator": "orchestrator",
            "physics_analyst_agent": "physics_analyst_agent",
            "physics_updater": "physics_updater",
            "case_setup_agent": "case_setup_agent",
            "post_processing_agent": "post_processing_agent",
            "execution_agent": "execution_agent",
            "reviewer": "reviewer",
            "end": END,
        }
    )
    
    # 6. 编译工作流
    app = workflow.compile()
    
    print("OASiS workflow created successfully.")
    return app
