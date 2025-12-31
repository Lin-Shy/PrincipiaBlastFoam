from typing import List, Dict, Any, Optional
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models import BaseChatModel
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.agents import create_tool_calling_agent
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.agents import AgentAction

class SelectiveLogCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.last_tool = None

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        self.last_tool = action.tool
        print(action.log)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        if self.last_tool == "read_file":
            print(f"\n<Content of {self.last_tool} omitted>\n")
        else:
            print(f"\n{output}\n")

class BaseAgent:
    """
    Base Agent class implementing the ReAct pattern or Tool-calling agent.
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
        self.agent_executor = self._create_agent_executor()

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
            callbacks=[SelectiveLogCallbackHandler()],
            handle_parsing_errors=True,
            max_iterations=self.max_iterations # Prevent infinite loops
        )

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
            result = self.agent_executor.invoke(input_data)
            print(f"[{self.agent_name}] Execution finished.")
            return result
        except Exception as e:
            error_msg = f"Error executing agent {self.agent_name}: {str(e)}"
            print(error_msg)
            return {"output": error_msg}
