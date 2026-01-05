
import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from principia_ai.metrics.tracker import MetricsTracker

# Add project root to path for module imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class CaseContentKnowledgeGraphRetriever:
    """
    A tool for retrieving information from the BlastFoam case content knowledge graph.
    This tool uses LLM-generated search strategies to find relevant tutorial cases, solvers, and concepts.
    """
    def __init__(self, llm_api_key=None, llm_base_url=None):
        """
        Initialize the CaseContentKnowledgeGraphRetriever.
        
        Args:
            llm_api_key: LLM API Key (if None, uses LLM_API_KEY env variable)
            llm_base_url: LLM API base URL (if None, uses LLM_API_BASE_URL env variable)
        """
        # Initialize LLM for search strategy generation
        LLM_API_BASE_URL = llm_base_url or os.getenv("LLM_API_BASE_URL")
        LLM_API_KEY = llm_api_key or os.getenv("LLM_API_KEY")
        LLM_MODEL_NAME = os.getenv("LLM_MODEL", "gpt-4")
        
        self.llm = ChatOpenAI(
            base_url=LLM_API_BASE_URL,
            model=LLM_MODEL_NAME,
            api_key=LLM_API_KEY,
            temperature=0.1,
        )
        
        # Get BLASTFOAM_TUTORIALS path for file reading
        self.foam_tutorials_path = os.getenv("BLASTFOAM_TUTORIALS")
        if not self.foam_tutorials_path:
            print("Warning: BLASTFOAM_TUTORIALS environment variable not set. File content retrieval will be limited.")
        
        # Load knowledge base
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Load the case content knowledge graphs from multiple files."""
        base_dir = Path(__file__).parent.parent.parent
        knowledge_dir = base_dir / "data/knowledge_graph/case_content_knowledge_graph"
        
        self.knowledge_graph = {"nodes": [], "relationships": []}
        self.nodes = []
        self.relationships = []
        self.id_to_node = {}
        
        try:
            json_files = [f for f in os.listdir(knowledge_dir) if f.endswith('.json')]
            
            for file_name in json_files:
                knowledge_path = knowledge_dir / file_name
                with open(knowledge_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 使用文件名（去掉 .json 后缀）作为唯一前缀
                    unique_prefix = file_name.replace('.json', '')
                    
                    # 提取 case_id（第一个 Case 节点的 ID）用于存储
                    case_id = None
                    nodes = data.get("nodes", [])
                    for node in nodes:
                        if node.get('label') == 'Case':
                            case_id = node.get('id')
                            break
                    
                    if not case_id:
                        print(f"Warning: No Case node found in {file_name}, skipping...")
                        continue
                    
                    # 创建 ID 映射表：旧 ID -> 新 ID
                    id_mapping = {}
                    
                    # 处理节点：所有节点都添加唯一前缀以彻底避免冲突
                    for node in nodes:
                        old_id = node['id']
                        
                        # 为所有节点添加文件名前缀
                        new_id = f"{unique_prefix}::{old_id}"
                        node['id'] = new_id
                        id_mapping[old_id] = new_id
                        
                        # 添加元数据属性
                        if 'properties' not in node:
                            node['properties'] = {}
                        node['properties']['source_file'] = file_name
                        node['properties']['case_id'] = case_id
                        node['properties']['original_id'] = old_id  # 保存原始 ID
                    
                    self.nodes.extend(nodes)
                    
                    # 处理关系：更新 source 和 target 引用
                    relationships = data.get("relationships", [])
                    for rel in relationships:
                        old_source = rel.get('source')
                        old_target = rel.get('target')
                        
                        # 更新为新的 ID
                        if old_source in id_mapping:
                            rel['source'] = id_mapping[old_source]
                        else:
                            print(f"Warning: Relationship source '{old_source}' not found in mapping for {file_name}")
                        
                        if old_target in id_mapping:
                            rel['target'] = id_mapping[old_target]
                        else:
                            print(f"Warning: Relationship target '{old_target}' not found in mapping for {file_name}")
                    
                    self.relationships.extend(relationships)

            self.id_to_node = {node['id']: node for node in self.nodes}
            
            # 检查是否有 ID 冲突
            if len(self.id_to_node) < len(self.nodes):
                print(f"Warning: ID conflicts detected! {len(self.nodes)} nodes but only {len(self.id_to_node)} unique IDs.")
            else:
                print(f"✓ All node IDs are unique!")
            
            print(f"Loaded {len(self.nodes)} nodes and {len(self.relationships)} relationships from {len(json_files)} files in the case content knowledge graph.")
        except Exception as e:
            print(f"Error loading case content knowledge graph: {e}")
            import traceback
            traceback.print_exc()
            self.knowledge_graph = {}
            self.nodes = []
            self.relationships = []
            self.id_to_node = {}

    def _get_knowledge_graph_summary(self) -> str:
        """
        Generate a summary of the knowledge graph structure to help LLM understand it.
        
        Returns:
            A summary string describing the knowledge graph structure.
        """
        # Count node types
        node_types = defaultdict(int)
        for node in self.nodes:
            node_types[node.get('label', 'Unknown')] += 1
        
        # Get sample nodes for each type
        samples = defaultdict(list)
        for node in self.nodes[:50]:  # Sample first 50 nodes
            label = node.get('label', 'Unknown')
            if len(samples[label]) < 2:
                samples[label].append(node)
        
        summary = "## Case Content Knowledge Graph Structure\n\n"
        summary += "This knowledge graph contains information extracted from blastFoam tutorial cases.\n\n"
        summary += "### Node Types and Counts:\n"
        for label, count in sorted(node_types.items()):
            summary += f"- **{label}**: {count} nodes\n"
        
        summary += "\n### Node Structure Examples:\n"
        for label, nodes in samples.items():
            summary += f"\n**{label} nodes:**\n"
            for node in nodes:
                summary += f"- ID: {node.get('id')}, Properties: {list(node.get('properties', {}).keys())}\n"
        
        summary += "\n### Search Capabilities:\n"
        summary += "- You can search by node ID (exact match)\n"
        summary += "- You can search by node label (Case, File, Variable, etc.)\n"
        summary += "- You can search by property values (name, path, type, etc.)\n"
        summary += "- You can combine multiple criteria\n"
        
        return summary

    def _execute_search_strategy(self, strategy: dict) -> list:
        """
        Execute the search strategy on the local knowledge graph.
        
        Args:
            strategy: The search strategy dictionary generated by LLM.
            
        Returns:
            List of matching node IDs with their relevance scores.
        """
        search_criteria = strategy.get("search_criteria", {})
        node_labels = search_criteria.get("node_labels", [])
        property_filters = search_criteria.get("property_filters", {})
        
        # Fix: Handle case where property_filters is a list (LLM hallucination)
        if isinstance(property_filters, list):
            print(f"DEBUG: property_filters is a list, converting to dict: {property_filters}")
            new_filters = {}
            for item in property_filters:
                if isinstance(item, dict):
                    new_filters.update(item)
            property_filters = new_filters
        elif not isinstance(property_filters, dict):
            print(f"DEBUG: property_filters is not a dict or list: {type(property_filters)}")
            property_filters = {}

        keyword_search = search_criteria.get("keyword_search", [])
        
        # Dictionary to store node scores
        node_scores = defaultdict(float)
        
        for node in self.nodes:
            node_id = node.get('id')
            label = node.get('label', '')
            properties = node.get('properties', {})
            
            score = 0.0
            
            # Check node label match
            if node_labels and label in node_labels:
                score += 5.0
            
            # Check property filters
            for prop_name, prop_pattern in property_filters.items():
                if prop_name in properties:
                    prop_value = str(properties[prop_name]).lower()
                    pattern = str(prop_pattern).lower()
                    
                    # Handle wildcard matching
                    if '*' in pattern:
                        pattern_regex = pattern.replace('*', '.*')
                        if re.search(pattern_regex, prop_value):
                            score += 3.0
                    elif pattern in prop_value:
                        score += 3.0
            
            # Check keyword search
            for keyword in keyword_search:
                keyword_lower = keyword.lower()
                keyword_lower = keyword_lower.replace('-', '')

                # Search in label
                if keyword_lower in label.lower():
                    score += 2.0
                
                # Search in all properties
                for prop_value in properties.values():
                    if isinstance(prop_value, str) and keyword_lower in prop_value.lower():
                        score += 1.0
            
            if score > 0:
                node_scores[node_id] = score
        
        # Return sorted list of (node_id, score) tuples
        sorted_results = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
        print(f"Search strategy found {len(sorted_results)} matching nodes")
        return sorted_results

    def _retrieve_node_details(self, node_ids: list) -> str:
        """
        Retrieve and format the details for the identified nodes.
        
        Args:
            node_ids: A list of node IDs to retrieve details for.
            
        Returns:
            A formatted string containing the details of the nodes.
        """
        if not node_ids:
            return "No relevant case content information found in the knowledge base."
            
        result = []
        for node_id in node_ids:
            node = self.id_to_node.get(node_id)
            if not node:
                continue
            
            label = node.get('label', 'N/A')
            properties = node.get('properties', {})
            
            content = f"## Type: {label} (ID: {node_id})\n"
            for key, value in properties.items():
                content += f"- **{key.capitalize()}**: {value}\n"
            
            result.append(content)
            
        if not result:
            return "Could not retrieve details for the identified nodes."
            
        return "--- Retrieved Case Content Information ---\n\n" + "\n---\n".join(result)

    def _find_file_for_variable(self, variable_id: str) -> str:
        """
        Find the file that defines a given variable by traversing the knowledge graph relationships.
        
        Args:
            variable_id: The ID of the variable node.
            
        Returns:
            The file path that defines this variable, or None if not found.
        """
        # Look for relationships where this variable is the target and type is DEFINES
        for rel in self.relationships:
            if rel.get('target') == variable_id and rel.get('type') == 'DEFINES':
                file_id = rel.get('source')
                # Check if the source is a File node
                file_node = self.id_to_node.get(file_id)
                if file_node and file_node.get('label') == 'File':
                    return file_node.get('properties', {}).get('path')
        
        return None

    def _get_file_content(self, file_path: str, max_lines: int = 100) -> str:
        """
        Retrieve the actual content of a file from the BLASTFOAM_TUTORIALS directory.
        
        Args:
            file_path: The relative path of the file (e.g., "blastFoam/building3D/system/controlDict")
            max_lines: Maximum number of lines to read (default: 100)
            
        Returns:
            The file content as a string, or an error message if the file cannot be read.
        """
        if not self.foam_tutorials_path:
            return "File content unavailable: BLASTFOAM_TUTORIALS environment variable not set."
        
        full_path = Path(self.foam_tutorials_path) / file_path
        
        if not full_path.exists():
            return f"File not found: {file_path}"
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                if len(lines) > max_lines:
                    content = ''.join(lines[:max_lines])
                    content += f"\n... (truncated, showing first {max_lines} lines of {len(lines)} total lines)"
                else:
                    content = ''.join(lines)
                
                return content
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"

    def _get_case_info_for_nodes(self, node_ids: list) -> dict:
        """
        获取每个节点所属的 Case 信息。
        此方法从 _hierarchical_search 中分离出来，确保所有检索结果都包含 case 上下文信息。
        
        Relationship structure:
        - Case CONTAINS File
        - File DEFINES Variable
        
        Args:
            node_ids: 节点 ID 列表
            
        Returns:
            字典，key 为节点 ID，value 为对应的 Case 节点信息
        """
        node_to_case = {}
        
        for node_id in node_ids:
            node = self.id_to_node.get(node_id)
            if not node:
                continue
            
            case_info = None
            node_label = node.get('label', '')
            
            # 如果节点本身就是 Case
            if node_label == 'Case':
                case_info = node
            
            # 如果是 File 节点，查找包含它的 Case
            elif node_label == 'File':
                for rel in self.relationships:
                    # Case CONTAINS File
                    if (rel.get('type') == 'CONTAINS' and
                        rel.get('target') == node_id):
                        case_id = rel.get('source')
                        case_node = self.id_to_node.get(case_id)
                        if case_node and case_node.get('label') == 'Case':
                            case_info = case_node
                            break
            
            # 如果是 Variable 节点，通过 DEFINES 关系找到 File，再找 Case
            elif node_label == 'Variable':
                for rel in self.relationships:
                    # File DEFINES Variable
                    if (rel.get('type') == 'DEFINES' and
                        rel.get('target') == node_id):
                        file_id = rel.get('source')
                        # 查找 File 所属的 Case
                        for rel2 in self.relationships:
                            # Case CONTAINS File
                            if (rel2.get('type') == 'CONTAINS' and
                                rel2.get('target') == file_id):
                                case_id = rel2.get('source')
                                case_node = self.id_to_node.get(case_id)
                                if case_node and case_node.get('label') == 'Case':
                                    case_info = case_node
                                    break
                        if case_info:
                            break
            
            if case_info:
                node_to_case[node_id] = case_info
        
        return node_to_case

    def _retrieve_node_details_with_content(self, node_ids: list, include_file_content: bool = True, node_to_case: dict = None) -> str:
        """
        Retrieve and format the details for the identified nodes, including file content.
        
        Args:
            node_ids: A list of node IDs to retrieve details for.
            include_file_content: Whether to include actual file content for File nodes.
            node_to_case: Optional dictionary mapping node IDs to their Case node information.
            
        Returns:
            A formatted string containing the details of the nodes with file content.
        """
        if not node_ids:
            return "No relevant case content information found in the knowledge base."
        
        # 如果没有提供 case 信息，自动获取
        if node_to_case is None:
            print("Retrieving case information for nodes...")
            node_to_case = self._get_case_info_for_nodes(node_ids)
            
        result = []
        for node_id in node_ids:
            node = self.id_to_node.get(node_id)
            if not node:
                continue
            
            label = node.get('label', 'N/A')
            properties = node.get('properties', {})
            
            content = f"## Type: {label} (ID: {node_id})\n"
            
            # 添加 Case Context 信息（如果有）
            if node_id in node_to_case:
                case_info = node_to_case[node_id]
                case_props = case_info.get('properties', {})
                content += "\n### Case Context\n"
                content += f"- **Case Name**: {case_props.get('name', 'N/A')}\n"
                content += f"- **Case Path**: {case_props.get('path', 'N/A')}\n"
                content += f"- **Solver**: {case_props.get('solver', 'N/A')}\n"
                
                # Try to fetch README content as description
                case_path = case_props.get('path')
                description = None
                if case_path and self.foam_tutorials_path:
                    for readme_name in ['README.md', 'README']:
                        readme_rel_path = os.path.join(case_path, readme_name)
                        full_readme_path = Path(self.foam_tutorials_path) / readme_rel_path
                        if full_readme_path.exists():
                            description = self._get_file_content(readme_rel_path, max_lines=50)
                            break
                
                if description:
                    content += f"- **Description**: \n{description}\n"
                content += "\n"
            
            # 显示节点自己的属性
            content += "### Node Properties\n"
            for key, value in properties.items():
                content += f"- **{key.capitalize()}**: {value}\n"
            
            # If this is a File node, try to retrieve the actual file content
            if include_file_content and label == 'File':
                file_path = properties.get('path')
                if file_path:
                    if self.foam_tutorials_path:
                        file_path = os.path.join(self.foam_tutorials_path, file_path)

                    content += f"\n### File Content:\n"
                    content += "```\n"
                    file_content = self._get_file_content(file_path)
                    content += file_content
                    content += "\n```\n"
            
            # If this is a Variable node, find the file that defines it and retrieve content
            elif include_file_content and label == 'Variable':
                file_path = self._find_file_for_variable(node_id)
                if file_path:
                    content += f"\n### Defined in File: {file_path}\n"
                    content += "### File Content:\n"
                    content += "```\n"
                    file_content = self._get_file_content(file_path)
                    content += file_content
                    content += "\n```\n"
                else:
                    content += f"\n*Note: Could not find the file that defines this variable*\n"
            
            result.append(content)
            
        if not result:
            return "Could not retrieve details for the identified nodes."
            
        return "--- Retrieved Case Content Information ---\n\n" + "\n---\n".join(result)

    def _react_decide(self, user_query: str, kg_summary: str, history: list) -> dict:
        """
        Use LLM to decide the next action in the ReAct loop.
        """
        history_text = ""
        for item in history:
            role = item['role']
            content = item['content']
            history_text += f"{role.upper()}: {content}\n"
            
        prompt = f"""You are an intelligent agent searching a knowledge graph of OpenFOAM cases.
Your goal is to find information relevant to the user's query.

{kg_summary}

User Query: "{user_query}"

History of your thoughts and actions:
{history_text}

Available Tools:
1. search_nodes: Search for nodes in the knowledge graph.
   Input: A JSON object with search criteria (node_labels, property_filters, keyword_search).
   Example Input: {{ "node_labels": ["Case"], "keyword_search": ["damBreak"] }}
   
2. inspect_nodes: Retrieve details and content of specific nodes.
   Input: A JSON object with a list of node_ids.
   Example Input: {{ "node_ids": ["case::123", "file::456"] }}
   
3. finish: Return the final answer to the user.
   Input: A JSON object with a list of relevant node_ids and an explanation.
   Example Input: {{ "node_ids": ["file::789"], "explanation": "Found the controlDict file." }}

Decide your next step. Return a JSON object with the following structure:
{{
    "thought": "Your reasoning for the next step",
    "action": "search_nodes" or "inspect_nodes" or "finish",
    "action_input": {{ ... }}
}}

Please provide ONLY the JSON object, no additional text.
"""
        
        response = self.llm.invoke(prompt)
        
        # Track tokens
        tracker = MetricsTracker()
        usage = response.usage_metadata if hasattr(response, 'usage_metadata') else {}
        agent_name = tracker.current_agent or "CaseContentTool"
        tracker.record_llm_call(
            agent_name=agent_name,
            input_tokens=usage.get('input_tokens', 0),
            output_tokens=usage.get('output_tokens', 0),
            model=self.llm.model_name if hasattr(self.llm, 'model_name') else 'unknown'
        )
        
        try:
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content.strip())
        except Exception as e:
            print(f"Error parsing ReAct decision: {e}")
            # Fallback or retry logic could go here
            return {
                "thought": "Error parsing response, finishing.",
                "action": "finish",
                "action_input": {"node_ids": [], "explanation": "I encountered an error processing the search."}
            }

    def search(self, user_query: str, top_k: int = 5, include_file_content: bool = True, max_iterations: int = 5) -> str:
        """
        Search the knowledge graph using an LLM-driven ReAct agent.
        
        Args:
            user_query: The user's query string.
            top_k: Number of top results to return in the final answer.
            include_file_content: Whether to include actual file content.
            max_iterations: Maximum number of ReAct iterations.
            
        Returns:
            A string containing the retrieved information.
        """
        print(f"Starting ReAct search for: '{user_query}'")
        
        kg_summary = self._get_knowledge_graph_summary()
        history = []
        
        for i in range(max_iterations):
            print(f"Iteration {i+1}/{max_iterations}")
            
            # 1. Generate Thought and Action
            decision = self._react_decide(user_query, kg_summary, history)
            
            thought = decision.get("thought")
            action = decision.get("action")
            action_input = decision.get("action_input")
            
            print(f"Thought: {thought}")
            print(f"Action: {action}")
            
            history.append({"role": "assistant", "content": f"Thought: {thought}\nAction: {action}\nInput: {json.dumps(action_input)}"})
            
            # 2. Execute Action
            observation = ""
            if action == "search_nodes":
                strategy = {"search_criteria": action_input} # Adapt input to expected strategy format
                # If the agent provided the full strategy structure, use it, otherwise wrap it
                if "search_criteria" in action_input:
                    strategy = action_input
                
                results = self._execute_search_strategy(strategy)
                # Summarize results for the LLM
                top_results = results[:15] 
                observation = f"Found {len(results)} nodes. Top {len(top_results)}:\n"
                for node_id, score in top_results:
                    node = self.id_to_node.get(node_id)
                    if node:
                        props = node.get('properties', {})
                        name = props.get('name', 'N/A')
                        path = props.get('path', 'N/A')
                        label = node.get('label', 'N/A')
                        observation += f"- ID: {node_id}, Label: {label}, Name: {name}, Path: {path}, Score: {score}\n"
                
            elif action == "inspect_nodes":
                node_ids = action_input.get("node_ids", [])
                # Retrieve details without content first to save tokens, or with content if critical?
                # The prompt says "inspect_nodes: Retrieve details and content".
                # Let's include content but maybe truncate if too long? 
                # _retrieve_node_details_with_content already truncates file content to 100 lines.
                content = self._retrieve_node_details_with_content(node_ids, include_file_content=include_file_content)
                observation = f"Node Details:\n{content}"
                
            elif action == "finish":
                final_node_ids = action_input.get("node_ids", [])
                explanation = action_input.get("explanation", "")
                
                if not final_node_ids:
                    return f"No relevant information found. {explanation}"
                
                final_content = self._retrieve_node_details_with_content(final_node_ids, include_file_content=include_file_content)
                return f"{explanation}\n\n{final_content}"
            
            else:
                observation = f"Unknown action: {action}"
            
            print(f"Observation: {observation[:200]}...") 
            history.append({"role": "system", "content": f"Observation: {observation}"})
            
        return "Max iterations reached without a final answer."


# --- Usage Example ---
def main():
    # Load environment variables from .env file at the project root
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / '.env')

    # Initialize the retriever
    retriever = CaseContentKnowledgeGraphRetriever()
    
    # Example 1: Find fvSolution settings from a specific case
    query1 = "Show me the PIMPLE settings from the blastFoam_building3D case."
    results1 = retriever.search(query1, top_k=3)
    print("\n--- Results for Query 1 ---")
    print(results1)

    # Example 2: Find turbulence model information
    query2 = "What turbulence model is used in the blastFoam_axisymmetricCharge case?"
    results2 = retriever.search(query2, top_k=3)
    print("\n--- Results for Query 2 ---")
    print(results2)

    # Example 3: Find equation of state information
    query3 = "example of functions in controlDict for blastFoam overpressure"
    results3 = retriever.search(query3, top_k=3)
    print("\n--- Results for Query 3 ---")
    print(results3)

if __name__ == '__main__':
    main()
