"""
MetricsTracker - 核心指标追踪器（单例模式）
"""
import time
from typing import Dict, Any, List
from collections import defaultdict
import json
from datetime import datetime


class MetricsTracker:
    """单例模式的指标追踪器"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化指标数据结构"""
        self.metrics = {
            'task_id': None,
            'user_request': None,
            'start_time': None,
            'end_time': None,
            'llm_calls': [],  # 每次 LLM 调用的详细信息
            'agent_executions': defaultdict(int),  # 各 agent 执行次数
            'agent_timings': defaultdict(list),  # 各 agent 执行时间列表
            'agent_errors': defaultdict(int),  # 各 agent 错误次数
            'total_tokens': {'input': 0, 'output': 0, 'total': 0},
            'tokens_by_agent': defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0}),
            'tasks': {
                'planned': 0,
                'completed': 0,
                'failed': 0,
                'retried': 0
            },
            'validation_results': {
                'passed': 0,
                'failed': 0
            },
            'errors': []
        }
        self.current_agent = None
        self.current_start_time = None
    
    def start_task(self, task_id: str, user_request: str = None):
        """开始新任务"""
        self.metrics['task_id'] = task_id
        self.metrics['user_request'] = user_request
        self.metrics['start_time'] = datetime.now().isoformat()
        print(f"📊 MetricsTracker: Started tracking task {task_id}")
    
    def end_task(self):
        """结束任务"""
        self.metrics['end_time'] = datetime.now().isoformat()
        print(f"📊 MetricsTracker: Ended tracking task {self.metrics['task_id']}")
    
    def start_agent(self, agent_name: str):
        """记录 Agent 开始执行"""
        self.current_agent = agent_name
        self.current_start_time = time.time()
        self.metrics['agent_executions'][agent_name] += 1
        # print(f"  ├─ Agent '{agent_name}' started (execution #{self.metrics['agent_executions'][agent_name]})")
    
    def end_agent(self, agent_name: str):
        """记录 Agent 结束执行"""
        if self.current_start_time:
            duration = time.time() - self.current_start_time
            self.metrics['agent_timings'][agent_name].append(duration)
            # print(f"  └─ Agent '{agent_name}' completed in {duration:.2f}s")
        self.current_agent = None
        self.current_start_time = None
    
    def record_llm_call(self, agent_name: str, 
                       input_tokens: int, 
                       output_tokens: int,
                       model: str,
                       duration: float = None):
        """记录 LLM 调用"""
        total = input_tokens + output_tokens
        
        call_info = {
            'agent': agent_name,
            'timestamp': datetime.now().isoformat(),
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': total,
            'model': model,
            'duration': duration
        }
        self.metrics['llm_calls'].append(call_info)
        
        # 更新总计
        self.metrics['total_tokens']['input'] += input_tokens
        self.metrics['total_tokens']['output'] += output_tokens
        self.metrics['total_tokens']['total'] += total
        
        # 按 Agent 统计
        self.metrics['tokens_by_agent'][agent_name]['input'] += input_tokens
        self.metrics['tokens_by_agent'][agent_name]['output'] += output_tokens
        self.metrics['tokens_by_agent'][agent_name]['total'] += total
        
        print(f"    🤖 LLM Call [{agent_name}]: {input_tokens} + {output_tokens} = {total} tokens")
    
    def record_task_event(self, event_type: str, count: int = 1):
        """记录任务事件"""
        if event_type in self.metrics['tasks']:
            self.metrics['tasks'][event_type] += count
            # print(f"  📝 Task event: {event_type} (+{count}, total: {self.metrics['tasks'][event_type]})")
    
    def record_validation(self, passed: bool):
        """记录验证结果"""
        if passed:
            self.metrics['validation_results']['passed'] += 1
            # print(f"  ✅ Validation passed (total: {self.metrics['validation_results']['passed']})")
        else:
            self.metrics['validation_results']['failed'] += 1
            # print(f"  ❌ Validation failed (total: {self.metrics['validation_results']['failed']})")
    
    def record_error(self, agent_name: str, error_msg: str):
        """记录错误"""
        self.metrics['errors'].append({
            'agent': agent_name,
            'timestamp': datetime.now().isoformat(),
            'error': error_msg
        })
        self.metrics['agent_errors'][agent_name] += 1
        print(f"  ⚠️ Error in '{agent_name}': {error_msg[:100]}...")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取当前指标（转换为普通 dict）"""
        # 将 defaultdict 转换为普通 dict 以便 JSON 序列化
        metrics_copy = dict(self.metrics)
        metrics_copy['agent_executions'] = dict(self.metrics['agent_executions'])
        metrics_copy['agent_timings'] = dict(self.metrics['agent_timings'])
        metrics_copy['agent_errors'] = dict(self.metrics['agent_errors'])
        metrics_copy['tokens_by_agent'] = dict(self.metrics['tokens_by_agent'])
        return metrics_copy
    
    def reset(self):
        """重置指标"""
        self._initialize()
        print("📊 MetricsTracker: Reset all metrics")
