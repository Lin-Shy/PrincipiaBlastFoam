"""
MetricsReporter - 生成和保存指标报告
"""
import os
import json
from datetime import datetime
from typing import Dict, Any
from .tracker import MetricsTracker


class MetricsReporter:
    """生成指标报告"""
    
    @staticmethod
    def generate_summary(metrics: Dict[str, Any]) -> str:
        """
        生成文本格式的指标摘要
        
        Args:
            metrics: 从 MetricsTracker.get_metrics() 获取的指标字典
            
        Returns:
            格式化的文本报告
        """
        lines = []
        lines.append("=" * 80)
        lines.append("  🔧 PrincipiaBlastFoam 工作流执行报告")
        lines.append("=" * 80)
        lines.append(f"任务ID: {metrics.get('task_id', 'N/A')}")
        lines.append(f"用户请求: {metrics.get('user_request', 'N/A')}")
        lines.append(f"开始时间: {metrics.get('start_time', 'N/A')}")
        lines.append(f"结束时间: {metrics.get('end_time', 'N/A')}")
        
        # 计算总时间
        if metrics.get('start_time') and metrics.get('end_time'):
            try:
                start = datetime.fromisoformat(metrics['start_time'])
                end = datetime.fromisoformat(metrics['end_time'])
                duration = (end - start).total_seconds()
                minutes = int(duration // 60)
                seconds = duration % 60
                if minutes > 0:
                    lines.append(f"总执行时间: {minutes}分{seconds:.1f}秒 ({duration:.2f}秒)")
                else:
                    lines.append(f"总执行时间: {duration:.2f}秒")
            except:
                lines.append("总执行时间: 无法计算")
        
        # Token 消耗统计
        lines.append("\n" + "-" * 80)
        lines.append("  💰 Token 消耗统计")
        lines.append("-" * 80)
        tokens = metrics.get('total_tokens', {})
        lines.append(f"输入 Tokens:  {tokens.get('input', 0):>10,}")
        lines.append(f"输出 Tokens:  {tokens.get('output', 0):>10,}")
        lines.append(f"总计 Tokens:  {tokens.get('total', 0):>10,}")
        lines.append(f"LLM 调用次数: {len(metrics.get('llm_calls', [])):>10}")
        
        # 按 Agent 分布
        tokens_by_agent = metrics.get('tokens_by_agent', {})
        if tokens_by_agent:
            lines.append("\n📊 按 Agent 分布:")
            # 按总 token 数排序
            sorted_agents = sorted(tokens_by_agent.items(), 
                                  key=lambda x: x[1].get('total', 0), 
                                  reverse=True)
            for agent, usage in sorted_agents:
                percentage = (usage.get('total', 0) / tokens.get('total', 1)) * 100
                lines.append(f"\n  {agent}:")
                lines.append(f"    输入:  {usage.get('input', 0):>10,}")
                lines.append(f"    输出:  {usage.get('output', 0):>10,}")
                lines.append(f"    总计:  {usage.get('total', 0):>10,} ({percentage:.1f}%)")
        
        # Agent 执行统计
        lines.append("\n" + "-" * 80)
        lines.append("  🤖 Agent 执行统计")
        lines.append("-" * 80)
        agent_executions = metrics.get('agent_executions', {})
        agent_timings = metrics.get('agent_timings', {})
        agent_errors = metrics.get('agent_errors', {})
        
        if agent_executions:
            # 按执行次数排序
            sorted_agents = sorted(agent_executions.items(), 
                                  key=lambda x: x[1], 
                                  reverse=True)
            for agent, count in sorted_agents:
                timings = agent_timings.get(agent, [])
                errors = agent_errors.get(agent, 0)
                
                lines.append(f"\n{agent}:")
                lines.append(f"  执行次数: {count}")
                
                if timings:
                    avg_time = sum(timings) / len(timings)
                    min_time = min(timings)
                    max_time = max(timings)
                    total_time = sum(timings)
                    lines.append(f"  执行时间:")
                    lines.append(f"    平均: {avg_time:>8.2f}秒")
                    lines.append(f"    最小: {min_time:>8.2f}秒")
                    lines.append(f"    最大: {max_time:>8.2f}秒")
                    lines.append(f"    总计: {total_time:>8.2f}秒")
                
                if errors > 0:
                    lines.append(f"  ⚠️ 错误次数: {errors}")
        
        # 任务统计
        lines.append("\n" + "-" * 80)
        lines.append("  📋 任务统计")
        lines.append("-" * 80)
        tasks = metrics.get('tasks', {})
        lines.append(f"计划任务数: {tasks.get('planned', 0)}")
        lines.append(f"完成任务数: {tasks.get('completed', 0)}")
        lines.append(f"失败任务数: {tasks.get('failed', 0)}")
        lines.append(f"重试次数:   {tasks.get('retried', 0)}")
        
        if tasks.get('planned', 0) > 0:
            success_rate = (tasks.get('completed', 0) / tasks['planned']) * 100
            lines.append(f"成功率:     {success_rate:.1f}%")
        
        # 验证统计
        lines.append("\n" + "-" * 80)
        lines.append("  ✅ 验证统计")
        lines.append("-" * 80)
        validation = metrics.get('validation_results', {})
        passed = validation.get('passed', 0)
        failed = validation.get('failed', 0)
        total_validations = passed + failed
        
        lines.append(f"验证通过: {passed}")
        lines.append(f"验证失败: {failed}")
        lines.append(f"验证总数: {total_validations}")
        
        if total_validations > 0:
            pass_rate = (passed / total_validations) * 100
            lines.append(f"通过率:   {pass_rate:.1f}%")
        
        # 错误记录
        errors = metrics.get('errors', [])
        if errors:
            lines.append("\n" + "-" * 80)
            lines.append("  ⚠️ 错误记录")
            lines.append("-" * 80)
            for i, error in enumerate(errors, 1):
                lines.append(f"\n{i}. [{error.get('agent', 'unknown')}] {error.get('timestamp', 'N/A')}")
                error_msg = error.get('error', 'No message')
                # 限制错误消息长度
                if len(error_msg) > 200:
                    error_msg = error_msg[:200] + "..."
                lines.append(f"   {error_msg}")
        
        # LLM 调用详情（可选，如果需要详细分析）
        llm_calls = metrics.get('llm_calls', [])
        if llm_calls and len(llm_calls) <= 20:  # 只在调用次数不多时显示
            lines.append("\n" + "-" * 80)
            lines.append("  🔍 LLM 调用详情")
            lines.append("-" * 80)
            for i, call in enumerate(llm_calls, 1):
                lines.append(f"\n{i}. [{call.get('agent', 'unknown')}] {call.get('model', 'unknown')}")
                lines.append(f"   时间: {call.get('timestamp', 'N/A')}")
                lines.append(f"   Tokens: {call.get('input_tokens', 0)} + {call.get('output_tokens', 0)} = {call.get('total_tokens', 0)}")
                if call.get('duration'):
                    lines.append(f"   耗时: {call['duration']:.2f}秒")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def save_report(output_dir: str, task_id: str = None):
        """
        保存报告到文件
        
        Args:
            output_dir: 输出目录
            task_id: 任务ID（如果不提供，从 tracker 获取）
            
        Returns:
            (json_path, txt_path) 保存的文件路径
        """
        tracker = MetricsTracker()
        metrics = tracker.get_metrics()
        
        # 使用提供的 task_id 或从 metrics 获取
        if task_id is None:
            task_id = metrics.get('task_id', 'unknown')
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名（带时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{task_id}_{timestamp}"
        
        # 保存 JSON 格式
        json_path = os.path.join(output_dir, f"metrics_{base_filename}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        # 保存文本报告
        txt_path = os.path.join(output_dir, f"report_{base_filename}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(MetricsReporter.generate_summary(metrics))
        
        print(f"\n📊 指标报告已保存:")
        print(f"  📄 JSON: {json_path}")
        print(f"  📄 文本: {txt_path}")
        
        return json_path, txt_path
    
    @staticmethod
    def print_summary():
        """打印当前指标摘要到控制台"""
        tracker = MetricsTracker()
        metrics = tracker.get_metrics()
        print("\n" + MetricsReporter.generate_summary(metrics))
