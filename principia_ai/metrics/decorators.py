"""
装饰器 - 用于自动追踪 Agent 执行和 LLM 调用
"""
import time
import functools
from typing import Callable
from .tracker import MetricsTracker


def track_agent_execution(agent_name: str):
    """
    装饰器：追踪 Agent 执行时间和次数
    
    使用方法：
        @track_agent_execution("orchestrator")
        def route(self, state: GraphState):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracker = MetricsTracker()
            tracker.start_agent(agent_name)
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                tracker.record_error(agent_name, str(e))
                raise
            finally:
                tracker.end_agent(agent_name)
        return wrapper
    return decorator


def track_llm_call(agent_name: str):
    """
    装饰器：追踪 LLM 调用的 token 消耗
    
    使用方法：
        @track_llm_call("orchestrator")
        def _call_llm(self, messages):
            return self.llm.invoke(messages)
    
    注意：这个装饰器期望：
    1. 被装饰的方法是类方法（self 作为第一个参数）
    2. 该方法返回 LLM 响应对象
    3. self.llm 有 model_name 属性
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            tracker = MetricsTracker()
            start_time = time.time()
            
            # 执行原函数（LLM 调用）
            response = func(self, *args, **kwargs)
            
            duration = time.time() - start_time
            
            # 提取 token 使用信息（支持多种响应格式）
            input_tokens = 0
            output_tokens = 0
            model = 'unknown'
            
            # 尝试从响应中提取 token 使用信息
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
            
            # 获取模型名称
            if hasattr(self, 'llm') and hasattr(self.llm, 'model_name'):
                model = self.llm.model_name
            
            # 记录 LLM 调用
            tracker.record_llm_call(
                agent_name=agent_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=model,
                duration=duration
            )
            
            return response
        return wrapper
    return decorator
