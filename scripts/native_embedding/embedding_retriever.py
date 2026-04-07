import hashlib
import os
from pathlib import Path
from typing import List, Optional

import requests

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args, **_kwargs):  # type: ignore[no-redef]
        return False

from langchain.embeddings.base import Embeddings
from langchain_community.vectorstores import FAISS


PROJECT_ROOT = Path(__file__).parent.parent.parent
USER_GUIDE_GRAPH_PATH = (
    PROJECT_ROOT
    / "data"
    / "knowledge_graph"
    / "user_guide_knowledge_graph"
    / "user_guide_knowledge_graph.json"
)


def cache_path_for(benchmark: str, embedding_level: str, source_identity: str, source_name: str, cache_dir: Path) -> Path:
    source_hash = hashlib.md5(source_identity.encode("utf-8")).hexdigest()[:8]
    if benchmark == "case_content":
        return cache_dir / f"embedding_{embedding_level}_{source_name}_{source_hash}"
    return cache_dir / f"embedding_{benchmark}_{embedding_level}_{source_name}_{source_hash}"


class CustomOpenAIEmbeddings(Embeddings):
    """
    Custom embeddings class that uses standard OpenAI API format.
    Compatible with DashScope and other OpenAI-compatible APIs.
    """

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings.extend(self._get_embeddings(batch))
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        return self._get_embeddings([text])[0]

    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        url = f"{self.base_url}/embeddings"
        payload = {
            "model": self.model,
            "input": texts if len(texts) > 1 else texts[0],
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            if isinstance(data.get("data"), list):
                sorted_data = sorted(data["data"], key=lambda x: x.get("index", 0))
                return [item["embedding"] for item in sorted_data]
            raise ValueError(f"Unexpected response format: {data}")
        except requests.exceptions.RequestException as exc:
            raise Exception(f"Embedding API request failed: {exc}")


class EmbeddingRetriever:
    """
    Load a pre-built FAISS index and perform similarity search.
    """

    def __init__(
        self,
        case_base_dir: Optional[str] = None,
        embedding_level: str = "case",
        benchmark: str = "case_content",
    ):
        load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

        self.benchmark = benchmark
        self.embedding_level = embedding_level
        self.case_base_dir = Path(case_base_dir) if case_base_dir else None

        if self.benchmark == "case_content":
            if not self.case_base_dir or not self.case_base_dir.is_dir():
                raise ValueError(f"Provided case_base_dir is not a valid directory: {case_base_dir}")
            source_identity = str(self.case_base_dir.resolve())
            source_name = self.case_base_dir.name
        elif self.benchmark == "user_guide":
            source_identity = str(USER_GUIDE_GRAPH_PATH.resolve())
            source_name = USER_GUIDE_GRAPH_PATH.stem
        else:
            raise ValueError(f"Unsupported benchmark: {self.benchmark}")

        self.embeddings = CustomOpenAIEmbeddings(
            api_key=os.getenv("EMBEDDING_API_KEY"),
            base_url=os.getenv("EMBEDDING_API_BASE_URL"),
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-v3"),
        )
        self.cache_dir = PROJECT_ROOT / "data" / "vector_store_cache"
        self.cache_path = cache_path_for(
            benchmark=self.benchmark,
            embedding_level=self.embedding_level,
            source_identity=source_identity,
            source_name=source_name,
            cache_dir=self.cache_dir,
        )
        self.vector_store = self._load_index()

    def _load_index(self):
        if not self.cache_path.exists():
            print(f"No index found at {self.cache_path}")
            print("Please build the index first using build_embedding_index.py")
            return None
        try:
            print(f"Loading FAISS index from {self.cache_path}")
            vector_store = FAISS.load_local(
                str(self.cache_path),
                self.embeddings,
                allow_dangerous_deserialization=True,
            )
            print(
                f"Successfully loaded FAISS index for benchmark '{self.benchmark}' "
                f"at embedding level '{self.embedding_level}'."
            )
            return vector_store
        except Exception as exc:
            print(f"Error loading index from cache: {exc}")
            return None

    def search(self, query: str, k: int = 3) -> str:
        if not self.vector_store:
            return (
                f"No vector store available for benchmark '{self.benchmark}' "
                f"at embedding level '{self.embedding_level}'. Please build the index first."
            )
        try:
            results = self.vector_store.similarity_search(query, k=k)
            if not results:
                return "No relevant documents found."

            formatted_results = []
            for doc in results:
                source = doc.metadata.get("source", "unknown")
                title = doc.metadata.get("title")
                number = doc.metadata.get("number")
                header = f"### Result from {source}"
                if self.benchmark == "user_guide" and title:
                    header = f"### Result from {number or source}: {title}"

                formatted_results.append(
                    f"{header}\n"
                    f"**Source:** {source}\n"
                    f"**Content Snippet:**\n{doc.page_content}\n"
                )

            return (
                f"--- Retrieved Results from Embedding Search "
                f"({self.benchmark}/{self.embedding_level}) ---\n\n"
                + "\n---\n".join(formatted_results)
            )
        except Exception as exc:
            return f"An error occurred during embedding search: {exc}"

    def search_with_scores(self, query: str, k: int = 3) -> list:
        if not self.vector_store:
            print(
                f"No vector store available for benchmark '{self.benchmark}' "
                f"at embedding level '{self.embedding_level}'."
            )
            return []

        try:
            return self.vector_store.similarity_search_with_score(query, k=k)
        except Exception as exc:
            print(f"An error occurred during embedding search: {exc}")
            return []


def main() -> None:
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    foam_tutorials_path = os.getenv("BLASTFOAM_TUTORIALS")

    if foam_tutorials_path:
        print("\n" + "=" * 60)
        print("Testing Case-Content File-Level Retriever")
        print("=" * 60)
        file_retriever = EmbeddingRetriever(
            case_base_dir=foam_tutorials_path,
            embedding_level="file",
            benchmark="case_content",
        )
        if file_retriever.vector_store:
            query = "PIMPLE algorithm settings"
            print(file_retriever.search(query, k=3))

    print("\n" + "=" * 60)
    print("Testing User-Guide Node-Level Retriever")
    print("=" * 60)
    guide_retriever = EmbeddingRetriever(
        case_base_dir=None,
        embedding_level="node",
        benchmark="user_guide",
    )
    if guide_retriever.vector_store:
        query = "Where is the RK4 time integration method described?"
        print(guide_retriever.search(query, k=3))


if __name__ == "__main__":
    main()
