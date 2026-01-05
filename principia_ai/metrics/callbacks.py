from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from .tracker import MetricsTracker

class TokenTrackingCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler to track token usage and report to MetricsTracker.
    """
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.tracker = MetricsTracker()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        if not response.llm_output:
            return

        # Try to extract token usage from llm_output
        # Different providers have different structures
        token_usage = response.llm_output.get("token_usage")
        model_name = response.llm_output.get("model_name", "unknown")
        
        if not token_usage:
            # Fallback for some providers that might put it elsewhere or if it's missing
            # For example, some might put it in generations info
            # But standard OpenAI/LangChain usually puts it in llm_output['token_usage']
            return

        input_tokens = token_usage.get("prompt_tokens", 0)
        output_tokens = token_usage.get("completion_tokens", 0)
        
        # If total_tokens is present but others are missing, try to infer? 
        # Usually prompt_tokens and completion_tokens are present.
        
        self.tracker.record_llm_call(
            agent_name=self.agent_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model_name
        )
