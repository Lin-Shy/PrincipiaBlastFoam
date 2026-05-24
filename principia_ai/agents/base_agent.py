import os
import traceback
from typing import List, Dict, Any
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel
from langchain.agents import create_tool_calling_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.agents import AgentAction
from langchain_core.messages import HumanMessage
from principia_ai.metrics.callbacks import TokenTrackingCallbackHandler
from principia_ai.utils.redaction import redact_text

try:
    from langgraph.prebuilt import create_react_agent as create_langgraph_react_agent
except Exception:  # pragma: no cover - depends on installed langgraph version
    create_langgraph_react_agent = None

class SelectiveLogCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.last_tool = None

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        self.last_tool = action.tool
        print(redact_text(action.log))

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        if self.last_tool == "read_file":
            print(f"\n<Content of {self.last_tool} omitted>\n")
        else:
            print(f"\n{redact_text(output)}\n")

class BaseAgent:
    """
    Base Agent class implementing the ReAct/tool-calling loop.

    LangGraph's prebuilt ReAct agent is the preferred runtime because it owns
    the model/tool loop as a graph. The older LangChain AgentExecutor path is
    kept as a compatibility fallback for older dependency sets or test doubles.
    """
    def __init__(
        self, 
        llm: BaseChatModel, 
        tools: List[BaseTool], 
        system_prompt: str,
        agent_name: str = "Agent",
        max_iterations: int = 50
    ):
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.agent_name = agent_name
        self.max_iterations = max_iterations
        self.runtime = os.getenv("AGENT_RUNTIME", "langgraph").lower()
        self.agent_executor = self._create_agent_runtime()

    def _create_agent_runtime(self):
        if self.runtime != "langchain" and create_langgraph_react_agent is not None:
            try:
                return create_langgraph_react_agent(
                    model=self.llm,
                    tools=self.tools,
                    prompt=self.system_prompt,
                    name=self.agent_name,
                )
            except Exception as exc:
                print(
                    f"[{self.agent_name}] LangGraph agent initialization failed; "
                    f"falling back to LangChain AgentExecutor: {exc}"
                )

        return self._create_agent_executor()

    def _create_agent_executor(self) -> AgentExecutor:
        """
        Creates the underlying LangChain agent executor.
        Uses OpenAI Tools Agent if supported, otherwise falls back to ReAct (to be implemented if needed).
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Using OpenAI Tools Agent as it's generally more robust for tool calling
        # If the LLM doesn't support bind_tools, we might need a fallback or different agent type.
        # Assuming the provided LLM supports tool binding (like GPT-4, Gemini, etc.)
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        
        return AgentExecutor(
            agent=agent, 
            tools=self.tools, 
            verbose=False, 
            callbacks=[SelectiveLogCallbackHandler(), TokenTrackingCallbackHandler(self.agent_name)],
            handle_parsing_errors=True,
            max_iterations=self.max_iterations # Prevent infinite loops
        )

    def _invoke_langgraph_agent(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        messages = []
        messages.extend(input_data.get("chat_history") or [])
        messages.append(HumanMessage(content=str(input_data.get("input", ""))))

        config = {
            "callbacks": [
                SelectiveLogCallbackHandler(),
                TokenTrackingCallbackHandler(self.agent_name),
            ],
            "recursion_limit": self.max_iterations,
        }
        result = self.agent_executor.invoke({"messages": messages}, config=config)
        output = ""
        result_messages = result.get("messages", []) if isinstance(result, dict) else []
        if result_messages:
            output = getattr(result_messages[-1], "content", "") or ""
        return {"output": output, "raw": result}

    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes the agent with the given input.
        
        Args:
            input_data: Dictionary containing 'input' key with the user query/task description.
            
        Returns:
            Dictionary containing 'output' key with the agent's response.
        """
        try:
            print(f"[{self.agent_name}] Starting execution...")
            if isinstance(self.agent_executor, AgentExecutor):
                result = self.agent_executor.invoke(input_data)
            else:
                result = self._invoke_langgraph_agent(input_data)
            print(f"[{self.agent_name}] Execution finished.")
            return result
        except Exception as e:
            cause = e.__cause__ or e.__context__
            detail = f"{type(e).__module__}.{type(e).__name__}: {e}"
            if cause:
                detail = f"{detail}; cause={type(cause).__module__}.{type(cause).__name__}: {cause}"
            print(traceback.format_exc(limit=8))
            error_msg = f"Error executing agent {self.agent_name}: {redact_text(detail)}"
            print(error_msg)
            return {"output": error_msg}
