#!/usr/bin/env python3
"""
知识图谱对齐工具 - 方案一：轻量级标签对齐

功能：
1. 在 Tutorial 知识图谱的节点中添加 concept_id 字段，指向 User Guide 中匹配的节点
2. 在 User Guide 知识图谱的节点中添加 tutorial_examples 字段，指向 Tutorial 中匹配的节点
3. 使用不区分大小写的 title 匹配方法

Author: AI Assistant
Date: 2025-10-24
"""

import json
import os
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict


class KnowledgeGraphAligner:
    """知识图谱对齐器"""
    
    def __init__(self, project_base_dir: str = None):
        """
        初始化对齐器
        
        Args:
            project_base_dir: 项目根目录路径，如果为 None 则自动检测
        """
        if project_base_dir is None:
            # 自动检测项目根目录（假设脚本在 data/knowledge_graph/ 下）
            project_base_dir = Path(__file__).parent.parent.parent
        
        self.project_base_dir = Path(project_base_dir)
        
        # 定义路径
        self.user_guide_path = self.project_base_dir / "data/knowledge_graph/user_guide_knowledge_graph/user_guide_knowledge_graph.json"
        self.case_content_dir = self.project_base_dir / "data/knowledge_graph/case_content_knowledge_graph"
        
        # 输出路径
        self.aligned_user_guide_path = self.project_base_dir / "data/knowledge_graph/user_guide_knowledge_graph/aligned_user_guide_knowledge_graph.json"
        self.aligned_case_content_dir = self.project_base_dir / "data/knowledge_graph/case_content_knowledge_graph_aligned"
        
        # 数据容器
        self.user_guide_nodes = []
        self.case_graphs = {}
        
        # 索引映射
        self.title_to_user_guide_nodes = defaultdict(list)  # title(lowercase) -> [node_ids]
        self.name_to_case_nodes = defaultdict(list)         # name(lowercase) -> [node_info]
        
        # 统计信息
        self.stats = {
            'user_guide_nodes_count': 0,
            'case_nodes_count': 0,
            'aligned_case_to_guide': 0,
            'aligned_guide_to_case': 0,
            'user_guide_with_examples': 0
        }
        
    def load_user_guide(self):
        """加载 User Guide 知识图谱"""
        print(f"\n{'='*60}")
        print("Step 1: 加载 User Guide 知识图谱")
        print(f"{'='*60}")
        
        try:
            with open(self.user_guide_path, 'r', encoding='utf-8') as f:
                self.user_guide_nodes = json.load(f)
            
            self.stats['user_guide_nodes_count'] = len(self.user_guide_nodes)
            print(f"✓ 成功加载 {len(self.user_guide_nodes)} 个 User Guide 节点")
            
            # 构建 title 索引（不区分大小写）
            for node in self.user_guide_nodes:
                title = node.get('title', '').strip()
                if title:
                    title_lower = title.lower()
                    self.title_to_user_guide_nodes[title_lower].append(node)
            
            print(f"✓ 构建了 {len(self.title_to_user_guide_nodes)} 个唯一标题的索引")
            
        except Exception as e:
            print(f"✗ 加载 User Guide 失败: {e}")
            raise
    
    def load_case_content_graphs(self):
        """加载所有 Case Content 知识图谱"""
        print(f"\n{'='*60}")
        print("Step 2: 加载 Case Content 知识图谱")
        print(f"{'='*60}")
        
        case_files = glob.glob(str(self.case_content_dir / "*.json"))
        print(f"找到 {len(case_files)} 个案例文件")
        
        total_nodes = 0
        for case_file in case_files:
            try:
                case_name = Path(case_file).stem
                with open(case_file, 'r', encoding='utf-8') as f:
                    case_graph = json.load(f)
                
                self.case_graphs[case_name] = case_graph
                
                nodes = case_graph.get('nodes', [])
                total_nodes += len(nodes)
                
                # 构建索引
                for node in nodes:
                    properties = node.get('properties', {})
                    name = properties.get('name', '').strip()
                    if name:
                        name_lower = name.lower()
                        self.name_to_case_nodes[name_lower].append({
                            'node': node,
                            'source': 'case_content',
                            'case_name': case_name
                        })
                
            except Exception as e:
                print(f"  ✗ 加载 {case_name} 失败: {e}")
        
        self.stats['case_nodes_count'] = total_nodes
        print(f"✓ 成功加载 {len(self.case_graphs)} 个案例，共 {total_nodes} 个节点")
        print(f"✓ Case Content 总索引: {len(self.name_to_case_nodes)} 个唯一名称")
    
    def align_case_content_to_user_guide(self):
        """
        将 Case Content 图谱对齐到 User Guide
        
        对于 Case 中的每个变量节点，尝试找到 User Guide 中匹配的概念节点
        """
        print("\n" + "="*50)
        print("步骤 3: 对齐 Case Content → User Guide")
        print("="*50)
        
        # ------ 对齐 Case Content 图谱 ------
        
        # 4.2 对齐 Case Content 图谱
        print("\n4.2 对齐 Case Content 图谱...")
        case_aligned_count = 0
        
        for case_name, case_graph in self.case_graphs.items():
            case_count = 0
            for node in case_graph.get('nodes', []):
                label = node.get('label', '')
                
                # 只对齐 Variable 节点
                if label != 'Variable':
                    continue
                
                properties = node.get('properties', {})
                name = properties.get('name', '').strip()
                
                if not name:
                    continue
                
                # 不区分大小写匹配
                name_lower = name.lower()
                if name_lower in self.title_to_user_guide_nodes:
                    matched_nodes = self.title_to_user_guide_nodes[name_lower]
                    
                    # 选择最佳匹配
                    best_match = None
                    for matched_node in matched_nodes:
                        if best_match is None:
                            best_match = matched_node
                        elif matched_node.get('semantic_type') == 'PhysicalModel':
                            best_match = matched_node
                            break
                    
                    if best_match:
                        # 添加对齐信息
                        properties['concept_id'] = best_match['id']
                        properties['concept_title'] = best_match['title']
                        properties['concept_type'] = best_match.get('semantic_type', 'Unknown')
                        properties['concept_chapter'] = self._get_chapter_id(best_match)
                        case_count += 1
            
            case_aligned_count += case_count
            if case_count > 0:
                print(f"  ✓ {case_name}: {case_count} 个节点对齐")
        
        print(f"\n  ✓ 所有案例对齐总计: {case_aligned_count} 个节点")
        
        self.stats['aligned_case_to_guide'] = case_aligned_count
        print(f"\n{'='*40}")
        print(f"总计对齐 Case Content -> User Guide: {self.stats['aligned_case_to_guide']} 个节点")
        print(f"{'='*40}")
    
    def align_user_guide_to_case_content(self):
        """
        对齐方向二：User Guide 节点 -> Case Content 节点
        为 User Guide 节点添加 tutorial_examples 字段
        """
        print(f"\n{'='*60}")
        print("Step 4: 对齐 User Guide -> Case Content")
        print(f"{'='*60}")
        
        aligned_count = 0
        total_examples = 0
        
        for node in self.user_guide_nodes:
            title = node.get('title', '').strip()
            
            if not title:
                continue
            
            # 不区分大小写匹配
            title_lower = title.lower()
            if title_lower in self.name_to_case_nodes:
                matched_infos = self.name_to_case_nodes[title_lower]
                
                # 收集所有匹配的 Tutorial 节点信息
                tutorial_examples = []
                
                for info in matched_infos:
                    tutorial_node = info['node']
                    source = info['source']
                    
                    example_info = {
                        'node_id': tutorial_node.get('id'),
                        'node_label': tutorial_node.get('label'),
                        'source': source
                    }
                    
                    # 添加额外的上下文信息
                    if source == 'case_content':
                        example_info['case_name'] = info.get('case_name')
                        # 提取案例路径
                        props = tutorial_node.get('properties', {})
                        if 'path' in props:
                            example_info['case_path'] = props['path']
                    
                    # 添加节点属性
                    props = tutorial_node.get('properties', {})
                    if props:
                        example_info['properties'] = {
                            'name': props.get('name'),
                            'type': props.get('type'),
                            'path': props.get('path')
                        }
                    
                    tutorial_examples.append(example_info)
                
                # 为 User Guide 节点添加示例引用
                if tutorial_examples:
                    node['tutorial_examples'] = tutorial_examples
                    node['tutorial_examples_count'] = len(tutorial_examples)
                    aligned_count += 1
                    total_examples += len(tutorial_examples)
        
        self.stats['aligned_guide_to_case'] = aligned_count
        self.stats['user_guide_with_examples'] = aligned_count
        
        print(f"✓ 对齐完成:")
        print(f"  - {aligned_count} 个 User Guide 节点找到了对应的 Case 示例")
        print(f"  - 总共关联了 {total_examples} 个 Case 节点")
        print(f"  - 平均每个 User Guide 节点: {total_examples/aligned_count:.1f} 个示例" if aligned_count > 0 else "")
    
    def _get_chapter_id(self, node: dict) -> str:
        """获取节点所属的章节 ID"""
        node_id = node.get('id', '')
        
        # 如果是章节本身
        if node_id.startswith('ch'):
            return node_id.split('.')[0]  # ch2.1 -> ch2
        
        # 如果有 parentId，递归查找
        parent_id = node.get('parentId')
        if parent_id:
            # 简单处理：提取 ch 开头的部分
            if parent_id.startswith('ch'):
                return parent_id.split('.')[0]
            # 从 id 中提取
            if 'ch' in node_id:
                return node_id.split('.')[0]
        
        return 'unknown'
    
    def generate_alignment_report(self):
        """生成对齐报告"""
        print(f"\n{'='*60}")
        print("对齐报告")
        print(f"{'='*60}")
        
        print("\n【数据统计】")
        print(f"  User Guide 节点总数: {self.stats['user_guide_nodes_count']}")
        print(f"  Case Content 节点数: {self.stats['case_nodes_count']}")
        
        print("\n【对齐结果】")
        print(f"  Case Content -> User Guide: {self.stats['aligned_case_to_guide']} 个节点")
        if self.stats['case_nodes_count'] > 0:
            coverage = self.stats['aligned_case_to_guide'] / self.stats['case_nodes_count'] * 100
            print(f"    覆盖率: {coverage:.2f}%")
        
        print(f"\n  User Guide -> Case Content: {self.stats['aligned_guide_to_case']} 个节点")
        if self.stats['user_guide_nodes_count'] > 0:
            coverage = self.stats['aligned_guide_to_case'] / self.stats['user_guide_nodes_count'] * 100
            print(f"    覆盖率: {coverage:.2f}%")
        
        # 分析高频匹配
        print("\n【高频匹配分析】")
        user_guide_with_most_examples = []
        for node in self.user_guide_nodes:
            if 'tutorial_examples' in node:
                count = node.get('tutorial_examples_count', 0)
                user_guide_with_most_examples.append((node['title'], count, node.get('semantic_type', 'Unknown')))
        
        user_guide_with_most_examples.sort(key=lambda x: x[1], reverse=True)
        
        print("  User Guide 节点被引用最多的前 10 个:")
        for i, (title, count, sem_type) in enumerate(user_guide_with_most_examples[:10], 1):
            print(f"    {i}. {title} ({sem_type}): {count} 个示例")
        
        # 分析未匹配的节点
        print("\n【未匹配分析】")
        unmatched_types = defaultdict(int)
        for node in self.user_guide_nodes:
            if 'tutorial_examples' not in node:
                sem_type = node.get('semantic_type', 'Unknown')
                unmatched_types[sem_type] += 1
        
        print("  未找到示例的 User Guide 节点（按类型）:")
        for sem_type, count in sorted(unmatched_types.items(), key=lambda x: x[1], reverse=True):
            print(f"    {sem_type}: {count} 个")
    
    def save_aligned_graphs(self):
        """保存对齐后的知识图谱"""
        print(f"\n{'='*60}")
        print("Step 6: 保存对齐后的知识图谱")
        print(f"{'='*60}")
        
        # 6.1 保存对齐后的 User Guide
        print("\n6.1 保存 User Guide...")
        try:
            os.makedirs(self.aligned_user_guide_path.parent, exist_ok=True)
            with open(self.aligned_user_guide_path, 'w', encoding='utf-8') as f:
                json.dump(self.user_guide_nodes, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 已保存到: {self.aligned_user_guide_path}")
        except Exception as e:
            print(f"  ✗ 保存失败: {e}")
        
        # 6.2 保存对齐后的 Case Content 图谱
        print("\n6.2 保存 Case Content 图谱...")
        try:
            os.makedirs(self.aligned_case_content_dir, exist_ok=True)
            
            saved_count = 0
            for case_name, case_graph in self.case_graphs.items():
                output_path = self.aligned_case_content_dir / f"{case_name}.json"
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(case_graph, f, ensure_ascii=False, indent=2)
                saved_count += 1
            
            print(f"  ✓ 已保存 {saved_count} 个案例到: {self.aligned_case_content_dir}")
        except Exception as e:
            print(f"  ✗ 保存失败: {e}")
    
    def run(self):
        """执行完整的对齐流程"""
        print("\n" + "="*60)
        print("知识图谱对齐工具 - 方案一")
        print("="*60)
        
        try:
            # 步骤 1: 加载 User Guide
            self.load_user_guide()
            
            # 步骤 2: 加载 Case Content 图谱
            self.load_case_content_graphs()
            
            # 步骤 3: 对齐 Case Content -> User Guide
            self.align_case_content_to_user_guide()
            
            # 步骤 4: 对齐 User Guide -> Case Content
            self.align_user_guide_to_case_content()
            
            # 步骤 5: 生成报告
            self.generate_alignment_report()
            
            # 步骤 6: 保存结果
            self.save_aligned_graphs()
            
            print("\n" + "="*60)
            print("✓ 对齐完成！")
            print("="*60)
            
        except Exception as e:
            print(f"\n✗ 对齐过程出错: {e}")
            import traceback
            traceback.print_exc()
            raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='知识图谱对齐工具 - 方案一')
    parser.add_argument('--project-dir', type=str, default=None,
                       help='项目根目录路径（默认自动检测）')
    
    args = parser.parse_args()
    
    # 创建对齐器并运行
    aligner = KnowledgeGraphAligner(project_base_dir=args.project_dir)
    aligner.run()


if __name__ == '__main__':
    main()
