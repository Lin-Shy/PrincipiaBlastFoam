import os
import hashlib
import requests
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.embeddings.base import Embeddings


class CustomOpenAIEmbeddings(Embeddings):
    """
    Custom embeddings class that uses standard OpenAI API format.
    Compatible with DashScope and other OpenAI-compatible APIs.
    """
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        embeddings = []
        # DashScope has a batch size limit of 10
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._get_embeddings(batch)
            embeddings.extend(batch_embeddings)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        return self._get_embeddings([text])[0]
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Call the embedding API."""
        url = f"{self.base_url}/embeddings"
        
        # Use standard OpenAI format
        payload = {
            "model": self.model,
            "input": texts if len(texts) > 1 else texts[0]
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            # Extract embeddings from response
            if isinstance(data.get('data'), list):
                # Sort by index to ensure correct order
                sorted_data = sorted(data['data'], key=lambda x: x.get('index', 0))
                return [item['embedding'] for item in sorted_data]
            else:
                raise ValueError(f"Unexpected response format: {data}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Embedding API request failed: {e}")


class EmbeddingRetriever:
    """
    A retriever that loads a pre-built FAISS index and performs similarity search.
    """
    def __init__(self, case_base_dir: str, embedding_level: str = 'case'):
        """
        Initializes the EmbeddingRetriever.

        Args:
            case_base_dir (str): The base directory where the cases are stored.
            embedding_level (str): 'case' for READMEs, 'file' for all files.
        """
        if not case_base_dir or not os.path.isdir(case_base_dir):
            raise ValueError(f"Provided case_base_dir is not a valid directory: {case_base_dir}")

        # Load environment variables from the project root
        project_root = Path(__file__).parent.parent.parent
        dotenv_path = project_root / '.env'
        load_dotenv(dotenv_path=dotenv_path)

        self.case_base_dir = Path(case_base_dir)
        self.embedding_level = embedding_level
        
        # Use custom embeddings that work with DashScope API
        self.embeddings = CustomOpenAIEmbeddings(
            api_key=os.getenv("EMBEDDING_API_KEY"),
            base_url=os.getenv("EMBEDDING_API_BASE_URL"),
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
        )
        
        # Setup cache directory
        self.cache_dir = project_root / "data" / "vector_store_cache"
        
        # Create a descriptive name for the cache file (same as in build_embedding_index.py)
        # Format: embedding_{level}_{dirname_hash}
        base_dir_name = self.case_base_dir.name
        base_dir_hash = hashlib.md5(str(self.case_base_dir).encode('utf-8')).hexdigest()[:8]
        self.cache_path = self.cache_dir / f"embedding_{self.embedding_level}_{base_dir_name}_{base_dir_hash}"
        
        # Load the vector store
        self.vector_store = self._load_index()

    def _load_index(self):
        """
        Loads the FAISS vector store from cache.
        """
        if not self.cache_path.exists():
            print(f"No index found at {self.cache_path}")
            print(f"Please build the index first using build_embedding_index.py")
            return None
        
        try:
            print(f"Loading FAISS index from {self.cache_path}")
            vector_store = FAISS.load_local(
                str(self.cache_path), 
                self.embeddings, 
                allow_dangerous_deserialization=True
            )
            print(f"Successfully loaded FAISS index for embedding level '{self.embedding_level}'.")
            return vector_store
        except Exception as e:
            print(f"Error loading index from cache: {e}")
            return None

    def search(self, query: str, k: int = 3) -> str:
        """
        Searches the vector store for similar documents.

        Args:
            query (str): The search query.
            k (int): The number of results to return.

        Returns:
            A formatted string of search results.
        """
        if not self.vector_store:
            return f"No vector store available for embedding level '{self.embedding_level}'. Please build the index first."

        try:
            results = self.vector_store.similarity_search(query, k=k)
            
            if not results:
                return "No relevant documents found."

            formatted_results = [
                f"### Result from {os.path.basename(doc.metadata['source'])}\n"
                f"**Source:** {doc.metadata['source']}\n"
                f"**Content Snippet:**\n{doc.page_content}\n"
                for doc in results
            ]
            
            return f"--- Retrieved Results from Embedding Search ({self.embedding_level} level) ---\n\n" + "\n---\n".join(formatted_results)

        except Exception as e:
            return f"An error occurred during embedding search: {e}"

    def search_with_scores(self, query: str, k: int = 3) -> list:
        """
        Searches the vector store and returns results with similarity scores.

        Args:
            query (str): The search query.
            k (int): The number of results to return.

        Returns:
            A list of tuples (document, score).
        """
        if not self.vector_store:
            print(f"No vector store available for embedding level '{self.embedding_level}'.")
            return []

        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            print(f"An error occurred during embedding search: {e}")
            return []


def main():
    """Main function to demonstrate the retriever."""
    # Load environment variables
    project_root = Path(__file__).parent.parent.parent
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path=dotenv_path)
    
    foam_tutorials_path = os.getenv("BLASTFOAM_TUTORIALS")
    
    if not foam_tutorials_path:
        print("BLASTFOAM_TUTORIALS environment variable not set.")
        return

    print(f"Using BLASTFOAM_TUTORIALS path: {foam_tutorials_path}")
    
    # Test case-level retriever
    print("\n" + "="*60)
    print("Testing Case-Level Retriever")
    print("="*60)
    case_retriever = EmbeddingRetriever(
        case_base_dir=foam_tutorials_path, 
        embedding_level='case'
    )
    
    if case_retriever.vector_store:
        query = "settings for a 3D building blast case"
        print(f"\nQuery: {query}")
        results = case_retriever.search(query, k=3)
        print(results)
    
    # Test file-level retriever
    print("\n" + "="*60)
    print("Testing File-Level Retriever")
    print("="*60)
    file_retriever = EmbeddingRetriever(
        case_base_dir=foam_tutorials_path, 
        embedding_level='file'
    )
    
    if file_retriever.vector_store:
        query = "PIMPLE algorithm settings"
        print(f"\nQuery: {query}")
        results = file_retriever.search(query, k=3)
        print(results)
        
        # Test with scores
        print("\n--- Results with Similarity Scores ---")
        results_with_scores = file_retriever.search_with_scores(query, k=3)
        for doc, score in results_with_scores:
            print(f"\nScore: {score:.4f}")
            print(f"Source: {doc.metadata['source']}")
            print(f"Content: {doc.page_content[:200]}...")


if __name__ == '__main__':
    main()
