import json
import os
from pathlib import Path
from langchain_openai import ChatOpenAI


class UserGuideKnowledgeGraphRetriever:
    """
    A hierarchical approach to knowledge retrieval from the BlastFoam documentation.
    This class uses a two-step process:
    1. First, it identifies relevant chapters using a simplified knowledge graph
    2. Then, it retrieves more specific sections within those chapters
    3. Finally, it returns the full content of the identified target nodes
    """
    def __init__(self, llm_api_key=None, llm_base_url=None):
        """
        Initialize the KnowledgeGraphRetriever.
        
        Args:
            llm_api_key: LLM API Key (if None, uses LLM_API_KEY env variable)
            llm_base_url: LLM API base URL (if None, uses LLM_API_BASE_URL env variable)
        """
        # Initialize LLM
        LLM_API_BASE_URL = llm_base_url or os.getenv("LLM_API_BASE_URL")
        LLM_API_KEY = llm_api_key or os.getenv("LLM_API_KEY")
        LLM_MODEL_NAME = os.getenv("LLM_MODEL", "gpt-4")
        
        self.llm = ChatOpenAI(
            base_url=LLM_API_BASE_URL,
            model=LLM_MODEL_NAME,
            api_key=LLM_API_KEY,
            temperature=0.1,
        )
        
        # Load knowledge bases
        self._load_knowledge_bases()

    def _load_knowledge_bases(self):
        """Load both simplified and complete knowledge bases"""
        # Determine the paths to the knowledge files
        base_dir = Path(__file__).parent.parent.parent
        simplified_path = base_dir / "data/knowledge_graph/user_guide_knowledge_graph/simplified_user_guide_knowledge_graph.json"
        complete_path = base_dir / "data/knowledge_graph/user_guide_knowledge_graph/user_guide_knowledge_graph.json"
        
        # Load simplified knowledge (used for initial retrieval)
        try:
            with open(simplified_path, 'r', encoding='utf-8') as f:
                self.simplified_knowledge = json.load(f)
            print(f"Loaded {len(self.simplified_knowledge)} simplified knowledge nodes")
        except Exception as e:
            print(f"Error loading simplified knowledge: {e}")
            self.simplified_knowledge = []
        
        # Load complete knowledge (used for final content retrieval)
        try:
            with open(complete_path, 'r', encoding='utf-8') as f:
                self.complete_knowledge = json.load(f)
            print(f"Loaded {len(self.complete_knowledge)} complete knowledge nodes")
        except Exception as e:
            print(f"Error loading complete knowledge: {e}")
            self.complete_knowledge = []
        
        # Build a mapping from ID to node for faster lookups
        self.id_to_node = {node.get('id'): node for node in self.complete_knowledge if node.get('id')}
    
    def _identify_relevant_chapters(self, query):
        """
        First level of retrieval: identify relevant chapters
        
        Args:
            query: User's query string
            
        Returns:
            List of chapter node IDs deemed relevant
        """
        # Filter to just get chapter-level nodes
        chapter_nodes = [node for node in self.simplified_knowledge 
                        if node.get('id') and 
                        node.get('id').startswith('ch')]
        
        # Create a prompt to identify relevant chapters
        chapters_info = "\n".join([
            f"Chapter {node.get('number', 'unknown')}: {node.get('title', 'untitled')}"
            for node in chapter_nodes
        ])
        example_output = {'chapters': ['ch2', 'ch3', 'ch19']}
        prompt = f"""You are an expert in computational fluid dynamics and the BlastFoam software.
Given a user query about BlastFoam and a list of available documentation chapters, 
identify which chapters would contain relevant information to answer the query.

User Query: "{query}"

Available Chapters:
{chapters_info}

Output only the IDs of the relevant chapters in a JSON array format. 
If no chapters seem relevant, return an empty array.
Example: 
{json.dumps(example_output, indent=2)}
"""
        
        # Call LLM to identify relevant chapters
        try:
            response = self.llm.invoke(
                [{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.content)
            relevant_chapters = result.get("chapters", [])
            if not isinstance(relevant_chapters, list):
                relevant_chapters = [relevant_chapters]
                
            print(f"Identified {len(relevant_chapters)} relevant chapters: {relevant_chapters}")
            return relevant_chapters
            
        except Exception as e:
            print(f"Error identifying relevant chapters: {e}")
            # If error, return empty list
            return []
    
    def _identify_relevant_sections(self, query, chapter_ids):
        """
        Second level of retrieval: within identified chapters, find relevant sections
        
        Args:
            query: User's query string
            chapter_ids: List of relevant chapter IDs
            
        Returns:
            List of section node IDs deemed relevant
        """
        if not chapter_ids:
            return []
            
        # Get all sections that belong to the identified chapters
        sections = []
        for node in self.simplified_knowledge:
            if (node.get('parentId') in chapter_ids or 
                any(node.get('id', '').startswith(ch_id + '.') for ch_id in chapter_ids)):
                sections.append(node)
        
        if not sections:
            # If no sections found, return the chapter IDs themselves
            return chapter_ids
        
        # Create a prompt to identify relevant sections
        sections_info = "\n".join([
            f"Sec {node.get('number', 'unknown')}: {node.get('title', 'untitled')} - {node.get('content_summary', 'No summary')}"
            for node in sections
        ])
        example_output = {'sections': ['sec2.1', 'sec2.3', 'sec5.2']}
        prompt = f"""You are an expert in computational fluid dynamics and the BlastFoam software.
Given a user query and a list of documentation sections, identify which sections would 
contain information most relevant to answering the query.

User Query: "{query}"

Available Sections:
{sections_info}

Output only the IDs of the relevant sections in a JSON array format. 
Choose the most specific sections (using sec) that would answer the query.
Example: 
{json.dumps(example_output, indent=2)}
"""
        
        # Call LLM to identify relevant sections
        try:
            response = self.llm.invoke(
                [{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.content)
            relevant_sections = result.get("sections", [])
            if not isinstance(relevant_sections, list):
                relevant_sections = [relevant_sections]
                
            print(f"Identified {len(relevant_sections)} relevant sections: {relevant_sections}")
            
            # If no sections identified, fall back to the chapters
            if not relevant_sections:
                return chapter_ids
                
            return relevant_sections
            
        except Exception as e:
            print(f"Error identifying relevant sections: {e}")
            # If error, return chapter IDs as fallback
            return chapter_ids
            
    def _identify_relevant_subsections(self, query, section_ids):
        """
        Third level of retrieval: within identified sections, find relevant subsections at all levels
        
        This function recursively retrieves all levels of subsections under the provided section IDs
        and includes the section IDs themselves in the search scope. It then identifies the most
        relevant subsections for the user's query using section numbers rather than IDs.
        
        Args:
            query: User's query string
            section_ids: List of relevant section IDs
            
        Returns:
            List of subsection node IDs deemed relevant
        """
        if not section_ids:
            return []
        
        # Get the original section nodes to include in the search
        section_nodes = []
        for section_id in section_ids:
            node = self.id_to_node.get(section_id)
            if node:
                section_nodes.append(node)
            
        # Get all subsections recursively under the identified sections
        subsections = []
        
        # Add the sections themselves to the search scope
        subsections.extend(section_nodes)
        
        # Function to recursively find all children of a node
        def get_all_children(parent_id):
            children = []
            for node in self.complete_knowledge:
                if node.get('parentId') == parent_id:
                    children.append(node)
                    # Recursively get children of this node
                    children.extend(get_all_children(node.get('id')))
            return children
        
        # Get all subsections for each section
        for section_id in section_ids:
            subsections.extend(get_all_children(section_id))
        
        if not subsections:
            # If no subsections found, return the section IDs themselves
            return section_ids
        
        # Create mapping from section number to node ID for retrieval later
        number_to_id_map = {}
        for node in subsections:
            number = node.get('number')
            if number:
                number_to_id_map[number] = node.get('id')
        
        # Create a prompt to identify relevant subsections using section numbers
        subsections_info = "\n".join([
            f"Section {node.get('number', 'unknown')}: {node.get('title', 'untitled')} - {node.get('content_summary', 'No summary')}"
            for node in subsections
        ])
        example_output = {'section_numbers': ['2.2.1', '3.2', '5.4.2']}
        prompt = f"""You are an expert in computational fluid dynamics and the BlastFoam software.
Given a user query and a list of sections and subsections, identify which ones would 
contain information most relevant to answering the query.

User Query: "{query}"

Available Sections/Subsections:
{subsections_info}

Output only the section numbers of the relevant subsections in a JSON array format. 
Choose the most specific subsections that would answer the query.
Example: 
{json.dumps(example_output, indent=2)}
"""
        
        # Call LLM to identify relevant subsections
        try:
            response = self.llm.invoke(
                [{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = json.loads(response.content)
            relevant_section_numbers = result.get("section_numbers", [])
            if not isinstance(relevant_section_numbers, list):
                relevant_section_numbers = [relevant_section_numbers]
                
            print(f"Identified {len(relevant_section_numbers)} relevant section numbers: {relevant_section_numbers}")
            
            # Convert section numbers back to node IDs
            relevant_subsection_ids = []
            for section_number in relevant_section_numbers:
                # Check if this number exists in our map
                if section_number in number_to_id_map:
                    relevant_subsection_ids.append(number_to_id_map[section_number])
                else:
                    # Try to find a node with this number directly
                    for node in subsections:
                        if node.get('number') == section_number:
                            relevant_subsection_ids.append(node.get('id'))
                            break
            
            print(f"Mapped to {len(relevant_subsection_ids)} subsection IDs: {relevant_subsection_ids}")
            
            # If no subsections identified or mapping failed, fall back to the sections
            if not relevant_subsection_ids:
                return section_ids
                
            return relevant_subsection_ids
            
        except Exception as e:
            print(f"Error identifying relevant subsections: {e}")
            # If error, return section IDs as fallback
            return section_ids
    
    def _normalize_node_id(self, node_id):
        """
        Normalize a node ID by removing spaces and converting 'section' to 'sec'
        
        Args:
            node_id: The node ID string to normalize
            
        Returns:
            Normalized node ID string
        """
        # Remove spaces
        node_id = node_id.strip().replace(" ", "")
        # Convert 'section' to 'sec' case-insensitively
        node_id = node_id.lower().replace("section", "sec")
        if node_id.startswith("sec"):
            # Restore the original case for the 'sec' prefix
            node_id = "sec" + node_id[3:]
        return node_id
        
    def _retrieve_full_content(self, node_ids):
        """
        Retrieve the full content for the identified nodes
        
        Args:
            node_ids: List of node IDs to retrieve full content for
            
        Returns:
            String containing the full formatted content
        """
        if not node_ids:
            return "No relevant information found in the knowledge base."
        
        result = []
        valid_node_ids = set()
        
        for node_id in node_ids:
            normalized_node_id = self._normalize_node_id(node_id)
            node = self.id_to_node.get(normalized_node_id)
            if not node:
                continue
            valid_node_ids.add(normalized_node_id)
            # Format the node content
            section_content = f"## Section {node.get('number', 'unknown')}: {node.get('title', 'untitled')}\n\n"
            
            if node.get('content_summary'):
                section_content += f"**Summary:** {node.get('content_summary')}\n\n"
                
            if node.get('content'):
                section_content += f"**Content:**\n{node.get('content')}\n\n"
                
            # Add table information if available
            table = node.get('table')
            if table and table != '[]':
                try:
                    if isinstance(table, str):
                        table = json.loads(table)
                    section_content += f"**Parameters Table:**\n{json.dumps(table, indent=2)}\n\n"
                except:
                    pass
                    
            result.append(section_content)
        print(f"Identified {len(result)} relevant contents: {', '.join(valid_node_ids)}")
        if not result:
            return "No content found for the identified sections."
            
        return "--- Retrieved Documentation Information ---\n\n" + "\n---\n".join(result)

    def search(self, user_query: str) -> str:
        """
        Main search method that implements the hierarchical retrieval process
        
        Args:
            user_query: The user's query string
            
        Returns:
            String containing the retrieved knowledge content
        """
        print(f"Searching knowledge base for: '{user_query}'")
        
        # Step 1: Identify relevant chapters
        chapter_ids = self._identify_relevant_chapters(user_query)
        
        # Step 2: Within those chapters, identify relevant sections
        section_ids = self._identify_relevant_sections(user_query, chapter_ids)
        
        # Step 3: Within those sections, identify relevant subsections at all levels
        subsection_ids = self._identify_relevant_subsections(user_query, section_ids)
        
        # Step 4: Retrieve full content for the identified subsections
        results = self._retrieve_full_content(subsection_ids)
        
        return results

# --- 使用示例 ---
def main():
    # 初始化工具 - 使用环境变量作为默认值
    knowledge_retriever = UserGuideKnowledgeGraphRetriever()
    
    # 示例1：检索时间积分方案
    query1 = "How do I use the RK4 time integration scheme?"
    results1 = knowledge_retriever.search(query1)
    print("\n--- Results for Query 1 ---")
    print(results1)

    # 示例2：检索摩擦模型
    query2 = "List all the Frictional stress models and their titles"
    results2 = knowledge_retriever.search(query2)
    print("\n--- Results for Query 2 ---")
    print(results2)

    # 示例3：检索特定参数
    query3 = "What are the parameters for the JohnsonJackson model?"
    results3 = knowledge_retriever.search(query3)
    print("\n--- Results for Query 3 ---")
    print(results3)
    
    # 示例4：复杂实体查询
    query4 = "I need to set up a simulation for a mine buried charge. Can you find the relevant example section?"
    results4 = knowledge_retriever.search(query4)
    print("\n--- Results for Query 4 ---")
    print(results4)


if __name__ == '__main__':
    main()
