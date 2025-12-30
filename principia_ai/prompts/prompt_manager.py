import os
from typing import Dict, Any, Optional
from string import Template


class PromptManager:
    """统一管理所有智能体的prompt模板"""
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = os.path.join(os.path.dirname(__file__))
        self.prompts_dir = prompts_dir
        self._ensure_prompts_dir()
    
    def _ensure_prompts_dir(self):
        """确保prompt目录存在"""
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)
    
    def load_prompt(self, agent_name: str, prompt_name: str, **kwargs) -> str:
        """
        加载并填充指定智能体的prompt模板
        
        Args:
            agent_name: 智能体名称 (如: orchestrator, physics_analyst_agent)
            prompt_name: prompt文件名 (如: base, analyze_request)
            **kwargs: 模板变量
        
        Returns:
            填充后的prompt字符串
        """
        prompt_file = os.path.join(self.prompts_dir, agent_name, f"{prompt_name}.txt")
        
        if not os.path.exists(prompt_file):
            raise FileNotFoundError(f"Prompt file {prompt_file} not found")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        template = Template(template_content)
        return template.safe_substitute(**kwargs)
    
# 全局prompt管理器实例
_prompt_manager = PromptManager()


def load_prompt(agent_name: str, prompt_name: str, **kwargs) -> str:
    """便捷函数：加载prompt模板"""
    return _prompt_manager.load_prompt(agent_name, prompt_name, **kwargs)
