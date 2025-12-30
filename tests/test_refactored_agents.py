import os
import sys
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from principia_ai.agents.workflow import create_workflow
from principia_ai.tools.standard_tools import get_read_tools, get_search_tools, get_edit_tools, get_execute_tools

def test_workflow_compilation():
    print("Testing workflow compilation...")
    
    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm # Mock bind_tools for OpenAI tools agent
    
    try:
        app = create_workflow(mock_llm)
        print("Workflow compiled successfully.")
    except Exception as e:
        print(f"Workflow compilation failed: {e}")
        raise

if __name__ == "__main__":
    test_workflow_compilation()
