"""
Prompt management system for FoamFlowAI agents.

This module provides centralized prompt management with:
- Template-based prompt system
- BlastFoam-specific usage rules injection
- Organized prompt structure by agent
"""

from .prompt_manager import PromptManager, load_prompt

__all__ = [
    "PromptManager",
    "load_prompt", 
]
