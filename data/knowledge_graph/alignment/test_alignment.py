#!/usr/bin/env python3
"""
知识图谱对齐工具测试脚本

快速验证对齐工具的基本功能
"""

import json
import os
from pathlib import Path


def test_alignment_results():
    """测试对齐结果"""
    print("="*60)
    print("对齐结果验证测试")
    print("="*60)
    
    # 定义路径
    project_base = Path(__file__).parent.parent.parent
    aligned_user_guide_path = project_base / "data/knowledge_graph/user_guide_knowledge_graph/aligned_user_guide_knowledge_graph.json"
    aligned_case_dir = project_base / "data/knowledge_graph/case_content_knowledge_graph_aligned"
    
    results = {
        'tests_passed': 0,
        'tests_failed': 0,
        'errors': []
    }
    
    # 测试 1: 检查文件是否存在
    print("\n【测试 1】检查对齐后的文件是否存在")
    print("-" * 60)
    
    files_to_check = [
        ("User Guide", aligned_user_guide_path),
        ("Case Content Dir", aligned_case_dir)
    ]
    
    for name, path in files_to_check:
        if path.exists():
            print(f"  ✓ {name}: {path}")
            results['tests_passed'] += 1
        else:
            print(f"  ✗ {name} 不存在: {path}")
            results['tests_failed'] += 1
            results['errors'].append(f"{name} 文件不存在")
    
    # 测试 2: 验证 User Guide 中的对齐字段
    print("\n【测试 2】验证 User Guide 对齐字段")
    print("-" * 60)
    
    try:
        if aligned_user_guide_path.exists():
            with open(aligned_user_guide_path, 'r', encoding='utf-8') as f:
                user_guide_nodes = json.load(f)
            
            nodes_with_examples = [n for n in user_guide_nodes if 'tutorial_examples' in n]
            
            if nodes_with_examples:
                print(f"  ✓ 找到 {len(nodes_with_examples)} 个节点有 tutorial_examples")
                results['tests_passed'] += 1
                
                # 显示示例
                sample = nodes_with_examples[0]
                print(f"\n  示例节点:")
                print(f"    ID: {sample.get('id')}")
                print(f"    Title: {sample.get('title')}")
                print(f"    Examples Count: {sample.get('tutorial_examples_count', 0)}")
                
                if sample.get('tutorial_examples'):
                    print(f"    第一个示例:")
                    ex = sample['tutorial_examples'][0]
                    print(f"      - Source: {ex.get('source')}")
                    print(f"      - Case: {ex.get('case_name', 'N/A')}")
                    print(f"      - Node ID: {ex.get('node_id')}")
            else:
                print(f"  ✗ 没有找到包含 tutorial_examples 的节点")
                results['tests_failed'] += 1
                results['errors'].append("User Guide 没有对齐数据")
        else:
            print(f"  ⚠ 跳过测试（文件不存在）")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        results['tests_failed'] += 1
        results['errors'].append(f"User Guide 测试错误: {e}")
    
    # 测试 3: 验证 Case Content 中的对齐字段
    print("\n【测试 3】验证 Case Content 对齐字段")
    print("-" * 60)
    
    try:
        if aligned_case_dir.exists():
            case_files = list(aligned_case_dir.glob("*.json"))
            
            if case_files:
                print(f"  ✓ 找到 {len(case_files)} 个对齐后的案例文件")
                results['tests_passed'] += 1
                
                # 随机检查一个文件
                sample_file = case_files[0]
                with open(sample_file, 'r', encoding='utf-8') as f:
                    case_graph = json.load(f)
                
                nodes = case_graph.get('nodes', [])
                variable_nodes_with_concept = [
                    n for n in nodes 
                    if n.get('label') == 'Variable' and 'concept_id' in n.get('properties', {})
                ]
                
                if variable_nodes_with_concept:
                    print(f"  ✓ 案例 {sample_file.name} 中有 {len(variable_nodes_with_concept)} 个变量节点对齐")
                    results['tests_passed'] += 1
                    
                    # 显示示例
                    sample = variable_nodes_with_concept[0]
                    props = sample.get('properties', {})
                    print(f"\n  示例节点:")
                    print(f"    Case: {sample_file.stem}")
                    print(f"    Node ID: {sample.get('id')}")
                    print(f"    Name: {props.get('name')}")
                    print(f"    Type: {props.get('type')}")
                    print(f"    Concept ID: {props.get('concept_id')}")
                    print(f"    Concept Title: {props.get('concept_title')}")
                else:
                    print(f"  ✗ 案例中没有对齐的变量节点")
                    results['tests_failed'] += 1
                    results['errors'].append("Case Content 没有对齐数据")
            else:
                print(f"  ✗ 没有找到对齐后的案例文件")
                results['tests_failed'] += 1
                results['errors'].append("Case Content 文件不存在")
        else:
            print(f"  ⚠ 跳过测试（目录不存在）")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        results['tests_failed'] += 1
        results['errors'].append(f"Case Content 测试错误: {e}")
    
    # 测试 4: 验证双向对齐的一致性
    print("\n【测试 4】验证双向对齐一致性")
    print("-" * 60)
    
    try:
        if aligned_user_guide_path.exists() and aligned_case_dir.exists():
            with open(aligned_user_guide_path, 'r', encoding='utf-8') as f:
                user_guide_nodes = json.load(f)
            
            # 找一个有双向对齐的例子
            ug_with_examples = [n for n in user_guide_nodes if 'tutorial_examples' in n]
            
            if ug_with_examples:
                sample_ug = ug_with_examples[0]
                sample_example = sample_ug['tutorial_examples'][0]
                case_name = sample_example.get('case_name')
                
                if case_name:
                    # 在 case 文件中找这个节点
                    case_file = aligned_case_dir / f"{case_name}.json"
                    
                    if case_file.exists():
                        with open(case_file, 'r', encoding='utf-8') as f:
                            case_graph = json.load(f)
                        
                        # 查找对应的节点
                        case_nodes = case_graph.get('nodes', [])
                        var_name = sample_example.get('properties', {}).get('name')
                        
                        matching_nodes = [
                            n for n in case_nodes
                            if n.get('properties', {}).get('name') == var_name
                            and 'concept_id' in n.get('properties', {})
                        ]
                        
                        if matching_nodes:
                            concept_id = matching_nodes[0]['properties']['concept_id']
                            
                            if concept_id == sample_ug['id']:
                                print(f"  ✓ 双向对齐一致性验证通过")
                                print(f"    User Guide ID: {sample_ug['id']} ↔ Case Concept ID: {concept_id}")
                                print(f"    Variable: {var_name} in {case_name}")
                                results['tests_passed'] += 1
                            else:
                                print(f"  ✗ 对齐不一致")
                                print(f"    User Guide ID: {sample_ug['id']}")
                                print(f"    Case Concept ID: {concept_id}")
                                results['tests_failed'] += 1
                                results['errors'].append("双向对齐不一致")
                        else:
                            print(f"  ⚠ 无法找到匹配的 Case 节点")
                    else:
                        print(f"  ⚠ Case 文件不存在: {case_file}")
                else:
                    print(f"  ⚠ 示例中没有 case_name")
            else:
                print(f"  ⚠ 没有可用的示例进行验证")
        else:
            print(f"  ⚠ 跳过测试（文件不存在）")
    except Exception as e:
        print(f"  ✗ 测试失败: {e}")
        results['tests_failed'] += 1
        results['errors'].append(f"一致性测试错误: {e}")
    
    # 测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"  ✓ 通过: {results['tests_passed']}")
    print(f"  ✗ 失败: {results['tests_failed']}")
    
    if results['errors']:
        print(f"\n错误详情:")
        for i, error in enumerate(results['errors'], 1):
            print(f"  {i}. {error}")
    
    if results['tests_failed'] == 0:
        print(f"\n🎉 所有测试通过！对齐工具运行正常。")
        return 0
    else:
        print(f"\n⚠️  部分测试失败，请检查对齐工具是否正确运行。")
        return 1


def show_alignment_examples():
    """显示一些有趣的对齐示例"""
    print("\n" + "="*60)
    print("对齐示例展示")
    print("="*60)
    
    project_base = Path(__file__).parent.parent.parent
    aligned_user_guide_path = project_base / "data/knowledge_graph/user_guide_knowledge_graph/aligned_user_guide_knowledge_graph.json"
    
    if not aligned_user_guide_path.exists():
        print("对齐后的 User Guide 文件不存在，请先运行对齐工具")
        return
    
    with open(aligned_user_guide_path, 'r', encoding='utf-8') as f:
        user_guide_nodes = json.load(f)
    
    # 找出被引用最多的节点
    nodes_with_examples = [
        (n, n.get('tutorial_examples_count', 0)) 
        for n in user_guide_nodes 
        if 'tutorial_examples' in n
    ]
    
    nodes_with_examples.sort(key=lambda x: x[1], reverse=True)
    
    print("\n【最受欢迎的物理模型】（被最多案例使用）")
    print("-" * 60)
    
    for i, (node, count) in enumerate(nodes_with_examples[:5], 1):
        print(f"\n{i}. {node['title']} ({node.get('semantic_type', 'Unknown')})")
        print(f"   被 {count} 个案例/节点使用")
        print(f"   ID: {node['id']}")
        
        # 显示使用它的案例
        examples = node.get('tutorial_examples', [])
        case_names = set(ex.get('case_name', 'Unknown') for ex in examples if 'case_name' in ex)
        if case_names:
            print(f"   案例: {', '.join(list(case_names)[:3])}")
            if len(case_names) > 3:
                print(f"        ... 等 {len(case_names)} 个案例")


def query_examples():
    """演示如何使用对齐后的数据进行查询"""
    print("\n" + "="*60)
    print("查询示例演示")
    print("="*60)
    
    project_base = Path(__file__).parent.parent.parent
    aligned_user_guide_path = project_base / "data/knowledge_graph/user_guide_knowledge_graph/aligned_user_guide_knowledge_graph.json"
    
    if not aligned_user_guide_path.exists():
        print("对齐后的 User Guide 文件不存在，请先运行对齐工具")
        return
    
    with open(aligned_user_guide_path, 'r', encoding='utf-8') as f:
        user_guide_nodes = json.load(f)
    
    # 查询 1: 找出使用 JWL 的所有案例
    print("\n【查询 1】哪些案例使用了 JWL 状态方程？")
    print("-" * 60)
    
    jwl_node = next((n for n in user_guide_nodes if n.get('title', '').lower() == 'jwl'), None)
    
    if jwl_node and 'tutorial_examples' in jwl_node:
        examples = jwl_node['tutorial_examples']
        case_names = set(ex.get('case_name', 'Unknown') for ex in examples if 'case_name' in ex)
        
        print(f"找到 {len(case_names)} 个案例使用 JWL:")
        for case_name in sorted(case_names):
            print(f"  - {case_name}")
    else:
        print("未找到 JWL 或没有对应的案例")
    
    # 查询 2: 统计各类型节点的对齐情况
    print("\n【查询 2】各类型节点的对齐情况")
    print("-" * 60)
    
    from collections import defaultdict
    type_stats = defaultdict(lambda: {'total': 0, 'aligned': 0})
    
    for node in user_guide_nodes:
        sem_type = node.get('semantic_type', 'Unknown')
        type_stats[sem_type]['total'] += 1
        if 'tutorial_examples' in node:
            type_stats[sem_type]['aligned'] += 1
    
    for sem_type, stats in sorted(type_stats.items()):
        total = stats['total']
        aligned = stats['aligned']
        rate = (aligned / total * 100) if total > 0 else 0
        print(f"  {sem_type:20s}: {aligned:3d}/{total:3d} ({rate:5.1f}%)")


if __name__ == '__main__':
    import sys
    
    print("\n" + "🔍 知识图谱对齐验证工具")
    
    # 运行测试
    exit_code = test_alignment_results()
    
    if exit_code == 0:
        # 如果测试通过，显示额外的示例
        show_alignment_examples()
        query_examples()
    
    sys.exit(exit_code)
