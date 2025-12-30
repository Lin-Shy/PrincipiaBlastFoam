import json
from neo4j import GraphDatabase
import argparse
import os


def import_json_to_neo4j(json_path, uri, user, password):
    """
    将特定结构的JSON文件导入Neo4j数据库。
    JSON文件应为一个列表，其中每个对象代表一个节点。
    节点间的层级关系由 'parentId' 字段定义。
    """
    if not os.path.isfile(json_path):
        print(f"错误: JSON文件不存在于路径 {json_path}")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            # 我们的JSON文件是一个节点列表
            node_data_list = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: 解析JSON文件失败: {e}")
        return
    except Exception as e:
        print(f"错误: 读取文件时发生未知错误: {e}")
        return

    if not isinstance(node_data_list, list):
        print("错误: JSON文件的顶层结构应为一个列表 [...]。")
        return

    print(f"从JSON文件加载了 {len(node_data_list)} 个节点定义。")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # 1. 清空数据库 (可选，但在脚本重复运行时很有用)
        print("正在清空数据库...")
        session.run("MATCH (n) DETACH DELETE n")
        print("数据库已清空。")

        # 2. 创建唯一性约束 (极大地提升性能并保证数据一致性)
        print("正在创建唯一性约束...")
        # 获取所有唯一的节点类型
        labels = {node.get('semantic_type', 'Node') for node in node_data_list}
        for label in labels:
            if label and label.isalnum():  # 确保标签是合法的
                print(f"  - 为标签 :{label} 的 id 属性创建约束")
                session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE")
        print("约束创建完成。")

        # 3. 导入所有节点
        print("正在导入节点...")
        for node_props in node_data_list:
            # 节点的标签由 semantic_type 决定
            label = node_props.get('semantic_type', 'Node')  # 提供一个默认标签
            if not label or not label.isalnum():
                print(f"警告: 跳过一个拥有不合法标签的节点: {node_props.get('id')}")
                continue

            # 复制属性字典以进行修改，避免改变原始数据
            params = node_props.copy()

            # Neo4j本身不支持直接存储列表/字典，最佳实践是将其转为JSON字符串
            if 'table' in params and isinstance(params['table'], list):
                params['table'] = json.dumps(params['table'])

            # 使用 SET n = $props 一次性设置所有属性
            query = f"CREATE (n:{label}) SET n = $params"
            session.run(query, params=params)
        print(f"{len(node_data_list)} 个节点导入完成。")

        # 4. 创建关系
        print("正在创建层级关系 (HAS_SUBSECTION)...")
        relationship_count = 0
        for node_props in node_data_list:
            # 如果节点有 parentId，就创建一条从父节点指向该节点的关系
            if node_props.get("parentId"):
                child_id = node_props['id']
                parent_id = node_props['parentId']

                # 匹配父子节点并创建关系
                # 由于我们创建了约束，这里的MATCH会非常快
                query = (
                    "MATCH (parent {id: $parent_id}), (child {id: $child_id}) "
                    "CREATE (parent)-[:HAS_SUBSECTION]->(child)"
                )
                session.run(query, parent_id=parent_id, child_id=child_id)
                relationship_count += 1
        print(f"{relationship_count} 条关系创建完成。")

    driver.close()
    print("导入过程成功完成！")


def main():
    parser = argparse.ArgumentParser(description='将blastFoam知识图谱JSON导入Neo4j数据库')
    # 请确保这里的默认路径是正确的，或者通过命令行参数传入
    parser.add_argument('-json', type=str,
                        default='data/knowledge_graph/user_guide_knowledge_graph/user_guide_knowledge_graph.json',
                        help='知识图谱JSON文件路径')
    parser.add_argument('-uri', type=str, default='bolt://localhost:7687', help='Neo4j数据库URI')
    parser.add_argument('-user', type=str, default='neo4j', help='Neo4j用户名')
    parser.add_argument('-password', type=str, default='12345678', help='Neo4j密码')
    args = parser.parse_args()

    import_json_to_neo4j(args.json, args.uri, args.user, args.password)


if __name__ == '__main__':
    main()
