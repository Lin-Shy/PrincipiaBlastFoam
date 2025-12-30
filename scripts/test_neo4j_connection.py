import os
from neo4j import GraphDatabase

# 获取环境变量或使用默认值
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "12345678")

def test_neo4j_connection():
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            value = result.single()["test"]
            print(f"Neo4j connection successful! Test value: {value}")
        driver.close()
    except Exception as e:
        print(f"Neo4j connection failed: {e}")

if __name__ == "__main__":
    test_neo4j_connection()
