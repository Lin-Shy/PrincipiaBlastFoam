import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import List, Optional

import requests

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*_args, **_kwargs):  # type: ignore[no-redef]
        return False

from langchain.docstore.document import Document
from langchain.embeddings.base import Embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
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


class EmbeddingIndexBuilder:
    """
    Build and cache FAISS indexes for retrieval benchmarks.
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
            if self.embedding_level not in {"case", "file"}:
                raise ValueError("case_content benchmark supports only embedding_level='case' or 'file'.")
            source_identity = str(self.case_base_dir.resolve())
            source_name = self.case_base_dir.name
        elif self.benchmark == "user_guide":
            if self.embedding_level != "node":
                raise ValueError("user_guide benchmark supports only embedding_level='node'.")
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
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = cache_path_for(
            benchmark=self.benchmark,
            embedding_level=self.embedding_level,
            source_identity=source_identity,
            source_name=source_name,
            cache_dir=self.cache_dir,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    def _is_case_directory(self, directory: Path) -> bool:
        return (directory / "Allrun").exists()

    def _find_case_directories(self, base_dir: Path) -> List[Path]:
        case_dirs: List[Path] = []

        def recursive_search(current_dir: Path) -> None:
            if not current_dir.is_dir():
                return
            if self._is_case_directory(current_dir):
                case_dirs.append(current_dir)
                return
            try:
                for subdir in current_dir.iterdir():
                    if subdir.is_dir():
                        recursive_search(subdir)
            except PermissionError:
                pass

        recursive_search(base_dir)
        return case_dirs

    def _load_case_content_documents(self) -> List[Document]:
        docs: List[Document] = []
        assert self.case_base_dir is not None

        print(f"Searching for case directories (containing Allrun) in {self.case_base_dir}...")
        case_dirs = self._find_case_directories(self.case_base_dir)
        print(f"Found {len(case_dirs)} case directories.")

        for case_dir in case_dirs:
            if self.embedding_level == "case":
                readme_path = case_dir / "README.md"
                if not readme_path.exists():
                    continue
                try:
                    content = readme_path.read_text(encoding="utf-8").strip()
                except Exception:
                    continue
                if not content:
                    continue
                docs.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": str(readme_path),
                            "case_dir": str(case_dir),
                            "case_name": case_dir.name,
                            "benchmark": self.benchmark,
                            "embedding_level": self.embedding_level,
                        },
                    )
                )
            elif self.embedding_level == "file":
                for file_path in case_dir.rglob("*"):
                    if not file_path.is_file():
                        continue
                    try:
                        content = file_path.read_text(encoding="utf-8").strip()
                    except Exception:
                        continue
                    if not content:
                        continue
                    docs.append(
                        Document(
                            page_content=content,
                            metadata={
                                "source": str(file_path),
                                "case_dir": str(case_dir),
                                "case_name": case_dir.name,
                                "file_name": file_path.name,
                                "benchmark": self.benchmark,
                                "embedding_level": self.embedding_level,
                            },
                        )
                    )

        return docs

    def _user_guide_node_to_text(self, node: dict) -> str:
        parts = [
            f"Node ID: {node.get('id')}",
            f"Section Number: {node.get('number')}",
            f"Title: {node.get('title')}",
            f"Semantic Type: {node.get('semantic_type')}",
        ]

        summary = str(node.get("content_summary") or "").strip()
        if summary:
            parts.append(f"Summary:\n{summary}")

        content = str(node.get("content") or "").strip()
        if content:
            parts.append(f"Content:\n{content}")

        table = node.get("table")
        if table and table != "[]":
            if isinstance(table, str):
                try:
                    table = json.loads(table)
                except Exception:
                    pass
            parts.append(f"Table:\n{json.dumps(table, ensure_ascii=False, indent=2)}")

        return "\n\n".join(parts).strip()

    def _load_user_guide_documents(self) -> List[Document]:
        docs: List[Document] = []
        nodes = json.loads(USER_GUIDE_GRAPH_PATH.read_text(encoding="utf-8"))

        for node in nodes:
            node_id = node.get("id")
            if not node_id:
                continue

            content = self._user_guide_node_to_text(node)
            if not content:
                continue

            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": str(node_id),
                        "node_id": str(node_id),
                        "number": str(node.get("number") or ""),
                        "title": str(node.get("title") or ""),
                        "semantic_type": str(node.get("semantic_type") or ""),
                        "parent_id": str(node.get("parentId") or ""),
                        "benchmark": self.benchmark,
                        "embedding_level": self.embedding_level,
                    },
                )
            )

        print(f"Loaded {len(docs)} user-guide nodes from {USER_GUIDE_GRAPH_PATH}")
        return docs

    def _load_documents(self) -> List[Document]:
        if self.benchmark == "case_content":
            return self._load_case_content_documents()
        if self.benchmark == "user_guide":
            return self._load_user_guide_documents()
        raise ValueError(f"Unsupported benchmark: {self.benchmark}")

    def build_and_save_index(self, force_rebuild: bool = False) -> bool:
        if self.cache_path.exists() and not force_rebuild:
            print(f"Index already exists at {self.cache_path}")
            print("Use force_rebuild=True to rebuild.")
            return True

        print(
            f"Building new FAISS index for benchmark '{self.benchmark}' "
            f"at embedding level '{self.embedding_level}'..."
        )
        documents = self._load_documents()
        if not documents:
            print(f"No documents found for benchmark '{self.benchmark}' and level '{self.embedding_level}'.")
            return False

        print(f"Loaded {len(documents)} documents.")
        texts: List[Document] = []
        for doc in documents:
            max_chars = 8000 * 4
            if len(doc.page_content) > max_chars:
                texts.extend(self.text_splitter.split_documents([doc]))
            else:
                texts.append(doc)

        valid_texts = [doc for doc in texts if isinstance(doc.page_content, str) and doc.page_content.strip()]
        if not valid_texts:
            print("No valid documents after filtering.")
            return False

        print(f"Processing {len(valid_texts)} document chunks for indexing...")
        batch_size = 100
        vector_store = None

        for i in range(0, len(valid_texts), batch_size):
            batch = valid_texts[i:i + batch_size]
            print(f"Processing batch {i // batch_size + 1}/{(len(valid_texts) - 1) // batch_size + 1} ({len(batch)} documents)...")
            try:
                if vector_store is None:
                    vector_store = FAISS.from_documents(batch, self.embeddings)
                else:
                    batch_store = FAISS.from_documents(batch, self.embeddings)
                    vector_store.merge_from(batch_store)
            except Exception as batch_error:
                print(f"Error processing batch {i // batch_size + 1}: {batch_error}")
                print("Retrying this batch one document at a time to isolate bad inputs...")
                recovered_docs = 0
                for doc in batch:
                    source = doc.metadata.get("source", "unknown")
                    try:
                        if vector_store is None:
                            vector_store = FAISS.from_documents([doc], self.embeddings)
                        else:
                            single_store = FAISS.from_documents([doc], self.embeddings)
                            vector_store.merge_from(single_store)
                        recovered_docs += 1
                    except Exception as single_error:
                        print(f"Skipping document after single-document retry failed: {source}")
                        print(f"  Error: {single_error}")
                print(f"Recovered {recovered_docs}/{len(batch)} documents from batch {i // batch_size + 1} after fallback retry.")

        if vector_store is None:
            print("Failed to create vector store from any batch.")
            return False

        print(
            f"Successfully built FAISS index for benchmark '{self.benchmark}' "
            f"at embedding level '{self.embedding_level}'."
        )
        try:
            print(f"Saving FAISS index to {self.cache_path}")
            vector_store.save_local(str(self.cache_path))
            print("Successfully saved index to cache.")
            return True
        except Exception as exc:
            print(f"Error saving index to cache: {exc}")
            return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FAISS embedding indexes for retrieval benchmarks.")
    parser.add_argument("--benchmark", default="case_content", choices=["case_content", "user_guide"])
    parser.add_argument("--embedding-level", default=None, help="Embedding level. case_content: case|file, user_guide: node")
    parser.add_argument("--tutorials-dir", default=os.getenv("BLASTFOAM_TUTORIALS"), help="Tutorials root for case_content.")
    parser.add_argument("--force-rebuild", action="store_true", help="Rebuild even if a cache already exists.")
    return parser.parse_args()


def main() -> None:
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
    args = parse_args()

    if args.benchmark == "case_content":
        if not args.tutorials_dir:
            raise SystemExit("BLASTFOAM_TUTORIALS environment variable not set.")
        embedding_level = args.embedding_level or "file"
        print(f"Using BLASTFOAM_TUTORIALS path: {args.tutorials_dir}")
        builder = EmbeddingIndexBuilder(
            case_base_dir=args.tutorials_dir,
            embedding_level=embedding_level,
            benchmark=args.benchmark,
        )
    else:
        embedding_level = args.embedding_level or "node"
        builder = EmbeddingIndexBuilder(
            case_base_dir=None,
            embedding_level=embedding_level,
            benchmark=args.benchmark,
        )

    success = builder.build_and_save_index(force_rebuild=args.force_rebuild)
    if success:
        print("\n✓ Index built successfully!")
    else:
        print("\n✗ Failed to build index.")


if __name__ == "__main__":
    main()
