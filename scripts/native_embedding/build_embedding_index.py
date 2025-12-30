import os
import hashlib
import requests
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
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


class EmbeddingIndexBuilder:
    """
    A tool for building and saving FAISS vector store indexes.
    Supports both case-level (READMEs) and file-level (all files) embeddings.
    """
    def __init__(self, case_base_dir: str, embedding_level: str = 'case'):
        """
        Initializes the EmbeddingIndexBuilder.

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
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a descriptive name for the cache file
        # Format: embedding_{level}_{dirname_hash}
        # This makes it easier to identify which index corresponds to which directory
        base_dir_name = self.case_base_dir.name
        base_dir_hash = hashlib.md5(str(self.case_base_dir).encode('utf-8')).hexdigest()[:8]
        self.cache_path = self.cache_dir / f"embedding_{self.embedding_level}_{base_dir_name}_{base_dir_hash}"
        
        # Text splitter for large documents
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    def _is_case_directory(self, directory: Path) -> bool:
        """
        Check if a directory is a valid OpenFOAM case directory.
        A directory is considered a case if it contains an Allrun file.
        
        Args:
            directory (Path): The directory to check.
            
        Returns:
            bool: True if the directory contains an Allrun file.
        """
        allrun_file = directory / 'Allrun'
        return allrun_file.exists() and allrun_file.is_file()
    
    def _find_case_directories(self, base_dir: Path) -> list:
        """
        Recursively find all case directories under base_dir.
        
        Args:
            base_dir (Path): The base directory to search.
            
        Returns:
            list: A list of Path objects representing case directories.
        """
        case_dirs = []
        
        def recursive_search(current_dir: Path):
            """Recursively search for case directories."""
            if not current_dir.is_dir():
                return
            
            # Check if current directory is a case directory
            if self._is_case_directory(current_dir):
                case_dirs.append(current_dir)
                # Don't search subdirectories of a case directory
                return
            
            # Recursively search subdirectories
            try:
                for subdir in current_dir.iterdir():
                    if subdir.is_dir():
                        recursive_search(subdir)
            except PermissionError:
                # Skip directories we don't have permission to read
                pass
        
        recursive_search(base_dir)
        return case_dirs
    
    def _load_documents(self):
        """
        Loads documents based on the embedding level.
        - 'case': Each README.md is a document.
        - 'file': Each file in a case is a document.
        
        Recursively searches for case directories (identified by Allrun file).
        """
        docs = []
        
        # Find all case directories
        print(f"Searching for case directories (containing Allrun) in {self.case_base_dir}...")
        case_dirs = self._find_case_directories(self.case_base_dir)
        print(f"Found {len(case_dirs)} case directories.")
        
        for case_dir in case_dirs:
            if self.embedding_level == 'case':
                # Load only README.md from each case
                readme_path = case_dir / 'README.md'
                if readme_path.exists():
                    try:
                        content = readme_path.read_text(encoding='utf-8')
                        if content and content.strip():
                            content_str = str(content).strip()
                            if content_str:
                                docs.append(Document(
                                    page_content=content_str, 
                                    metadata={
                                        "source": str(readme_path),
                                        "case_dir": str(case_dir),
                                        "case_name": case_dir.name
                                    }
                                ))
                    except Exception as e:
                        print(f"Error reading {readme_path}: {e}")
                        
            elif self.embedding_level == 'file':
                # Load all files from each case
                for file_path in case_dir.rglob('*'):
                    if file_path.is_file():
                        try:
                            content = file_path.read_text(encoding='utf-8')
                            if content and content.strip():
                                content_str = str(content).strip()
                                if content_str:
                                    docs.append(Document(
                                        page_content=content_str, 
                                        metadata={
                                            "source": str(file_path),
                                            "case_dir": str(case_dir),
                                            "case_name": case_dir.name,
                                            "file_name": file_path.name
                                        }
                                    ))
                        except Exception as e:
                            # Ignore binary files or files with encoding issues
                            pass
        
        return docs

    def build_and_save_index(self, force_rebuild: bool = False):
        """
        Builds the FAISS vector store and saves it to disk.
        
        Args:
            force_rebuild (bool): If True, rebuild even if cache exists.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        # Check if a cached index exists
        if self.cache_path.exists() and not force_rebuild:
            print(f"Index already exists at {self.cache_path}")
            print("Use force_rebuild=True to rebuild.")
            return True

        # Build a new index
        print(f"Building new FAISS index for embedding level '{self.embedding_level}'...")
        documents = self._load_documents()
        
        if not documents:
            print(f"No documents found for embedding level '{self.embedding_level}' in '{self.case_base_dir}'")
            return False
        
        print(f"Loaded {len(documents)} documents.")
        
        # Split documents into chunks to avoid token limit issues
        texts = []
        for doc in documents:
            max_chars = 8000 * 4  # Conservative limit (1 token ≈ 4 chars)
            if len(doc.page_content) > max_chars:
                chunks = self.text_splitter.split_documents([doc])
                texts.extend(chunks)
            else:
                texts.append(doc)

        if not texts:
            print("No documents to index.")
            return False

        print(f"Processing {len(texts)} document chunks for indexing...")

        try:
            # Validate all documents have valid content
            valid_texts = []
            for doc in texts:
                if isinstance(doc.page_content, str) and doc.page_content.strip():
                    valid_texts.append(doc)
                else:
                    print(f"Skipping invalid document: {doc.metadata.get('source', 'unknown')}")
            
            if not valid_texts:
                print("No valid documents after filtering.")
                return False
            
            print(f"Valid documents after filtering: {len(valid_texts)}")
            
            # Process documents in batches
            batch_size = 100
            vector_store = None
            
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i:i + batch_size]
                print(f"Processing batch {i//batch_size + 1}/{(len(valid_texts)-1)//batch_size + 1} ({len(batch)} documents)...")
                
                try:
                    if vector_store is None:
                        vector_store = FAISS.from_documents(batch, self.embeddings)
                    else:
                        batch_store = FAISS.from_documents(batch, self.embeddings)
                        vector_store.merge_from(batch_store)
                except Exception as batch_error:
                    print(f"Error processing batch {i//batch_size + 1}: {batch_error}")
                    continue
            
            if vector_store is None:
                print("Failed to create vector store from any batch.")
                return False
            
            print(f"Successfully built FAISS index for embedding level '{self.embedding_level}'.")
            
            # Save the index to cache
            try:
                print(f"Saving FAISS index to {self.cache_path}")
                vector_store.save_local(str(self.cache_path))
                print("Successfully saved index to cache.")
                return True
            except Exception as e:
                print(f"Error saving index to cache: {e}")
                return False

        except Exception as e:
            print(f"Error building FAISS index: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main function to build indexes."""
    # Load environment variables
    project_root = Path(__file__).parent.parent.parent
    dotenv_path = project_root / '.env'
    load_dotenv(dotenv_path=dotenv_path)
    
    foam_tutorials_path = os.getenv("BLASTFOAM_TUTORIALS")
    
    if not foam_tutorials_path:
        print("BLASTFOAM_TUTORIALS environment variable not set.")
        return

    print(f"Using BLASTFOAM_TUTORIALS path: {foam_tutorials_path}")
    
    # Build case-level index
    print("\n" + "="*60)
    print("Building Case-Level Index (README files only)")
    print("="*60)
    case_builder = EmbeddingIndexBuilder(
        case_base_dir=foam_tutorials_path, 
        embedding_level='case'
    )
    case_success = case_builder.build_and_save_index(force_rebuild=False)
    
    if case_success:
        print("\n✓ Case-level index built successfully!")
    else:
        print("\n✗ Failed to build case-level index.")
    
    # Build file-level index
    print("\n" + "="*60)
    print("Building File-Level Index (all files)")
    print("="*60)
    print("WARNING: This may take a very long time for large repositories!")
    
    # Ask for confirmation
    response = input("Do you want to build file-level index? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        file_builder = EmbeddingIndexBuilder(
            case_base_dir=foam_tutorials_path, 
            embedding_level='file'
        )
        file_success = file_builder.build_and_save_index(force_rebuild=False)
        
        if file_success:
            print("\n✓ File-level index built successfully!")
        else:
            print("\n✗ Failed to build file-level index.")
    else:
        print("Skipping file-level index build.")


if __name__ == '__main__':
    main()
