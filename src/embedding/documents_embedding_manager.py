import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from langchain_community.document_loaders import TextLoader, WebBaseLoader, PyPDFLoader, Docx2txtLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console

from .abstract_embedding_manager import AbstractEmbeddingManager, EmbeddingResult, _load_faiss_vector_store
from .embedding_utils import _clean_directory
from .hybrid_query_mixin import HybridQueryMixin
from config import Config

console = Console()
config = Config.load()

import hashlib

def _hash_file(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute a SHA-1 hash for the given file.
    Uses a chunked approach for large files to avoid loading into memory.
    """
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha1.update(chunk)
    return sha1.hexdigest()


def _load_document(path: Path):
    """
    Load a file (text, PDF, or Word) and return a list of Document objects.
    """
    ext = path.suffix.lower()
    if ext == ".pdf":
        loader = PyPDFLoader(str(path))
    elif ext in [".doc", ".docx"]:
        loader = Docx2txtLoader(str(path))
    else:
        loader = TextLoader(str(path), encoding="utf-8")

    return loader.load()  # Always returns a List[Document]

class DocumentsEmbeddingManager(AbstractEmbeddingManager, HybridQueryMixin):
    BATCH_SIZE = 20  # Number of documents to embed in one batch

    def __init__(self, project_key: str, documents_dir: Path):
        self.project_key = project_key
        self.documents_dir = documents_dir
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_fn = OpenAIEmbeddings(model="text-embedding-3-small", api_key=config.ai.openai_api_key)

    # ---------------------------------------------------------
    # Public Methods
    # ---------------------------------------------------------
    def index(self, force: bool = False):
        """
        Index documents from paths and URLs.
        """
        documents_cfg = config.embedding.documents
        manifest_path = self.documents_dir / "manifest.json"
        old_hashes = _load_manifest(manifest_path, force)

        changed_docs, all_hashes = self._collect_documents(
            paths=[Path(p).resolve() for p in getattr(documents_cfg, "paths", [])],
            urls=getattr(documents_cfg, "urls", []),
            old_hashes=old_hashes,
            force=force
        )

        # Embed changed/new documents
        if changed_docs:
            console.print(f"📄 Indexing {len(changed_docs)} changed/new documents...", style="cyan")
            self._embed_changed_documents(changed_docs)
        else:
            console.print("✅ No changes detected.", style="green")

        # Save new manifest
        _save_manifest(manifest_path, all_hashes)
        console.print(f"Manifest updated at: {manifest_path}", style="cyan")

    def clean(self):
        _clean_directory(self.documents_dir, "documents")

    def stats(self):
        """
        Return statistics for the documents embeddings.
        """
        manifest_path = self.documents_dir / "manifest.json"
        if not manifest_path.exists():
            return {"documents_indexed": 0}
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        return {"documents_indexed": len(manifest.get("doc-hashes", {}))}

    def query(self, query: str, top_k: int = 5, debug: bool = False) -> List[EmbeddingResult]:
        store = _load_faiss_vector_store(self.documents_dir, self.embedding_fn)
        hits = store.similarity_search_with_score(query, k=top_k * 2)

        results = [
            EmbeddingResult(
                content=doc.page_content,
                source="documents",
                reference=doc.metadata.get("source", ""),
                similarity=-score  # Convert distance to similarity
            )
            for doc, score in hits
        ]

        # Hybrid keyword boosting
        results = self._rerank_by_keyword(query, results)
        final_results = results[:top_k]

        if debug:
            self._debug_print_results(query, final_results)

        return final_results

    # ---------------------------------------------------------
    # Private Helpers
    # ---------------------------------------------------------
    def _collect_documents(
            self, paths: List[Path], urls: List[str], old_hashes: Dict[str, str], force: bool
    ) -> Tuple[List[Dict], Dict[str, str]]:
        """
        Collects and hashes all documents (files and URLs).
        """
        changed_docs = []
        all_hashes = {}

        # Process local files
        for path in paths:
            if not path.is_file():
                continue
            file_hash = _hash_file(path)
            rel_path = str(path)
            all_hashes[rel_path] = file_hash
            if force or old_hashes.get(rel_path) != file_hash:
                changed_docs.append({"type": "file", "source": path})

        # Process URLs
        for url in urls:
            try:
                content_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()  # URL-based hash
                all_hashes[url] = content_hash
                if force or old_hashes.get(url) != content_hash:
                    changed_docs.append({"type": "url", "source": url})
            except Exception as e:
                console.print(f"[yellow]Warning:[/] Could not process URL {url}: {e}")

        return changed_docs, all_hashes

    def _embed_changed_documents(self, changed_docs: List[Dict]):
        """
        Embed changed documents (files and URLs).
        """
        try:
            db = FAISS.load_local(str(self.documents_dir), self.embedding_fn)
        except Exception:
            db = None

        for i in range(0, len(changed_docs), self.BATCH_SIZE):
            batch = changed_docs[i:i + self.BATCH_SIZE]
            documents = []
            for doc_info in batch:
                if doc_info["type"] == "file":
                    try:
                        docs = _load_document(Path(doc_info["source"]))
                        for d in docs:
                            d.metadata["source"] = str(doc_info["source"])
                        documents.extend(docs)
                    except Exception as e:
                        console.print(f"[yellow]Warning:[/] Could not load file {doc_info['source']}: {e}")
                elif doc_info["type"] == "url":
                    try:
                        loader = WebBaseLoader(doc_info["source"])
                        docs = loader.load()
                        for d in docs:
                            d.metadata["source"] = doc_info["source"]
                        documents.extend(docs)
                    except Exception as e:
                        console.print(f"[yellow]Warning:[/] Could not load URL {doc_info['source']}: {e}")

            if not documents:
                continue

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " ", ""]
            )
            chunks = splitter.split_documents(documents)

            if db:
                db.add_documents(chunks)
            else:
                db = FAISS.from_documents(chunks, self.embedding_fn)

        if db:
            db.save_local(str(self.documents_dir))


def _load_manifest(manifest_path: Path, force: bool) -> Dict[str, str]:
    """
    Loads the manifest file and returns a mapping of document -> hash.
    """
    if manifest_path.exists() and not force:
        with open(manifest_path, "r", encoding="utf-8") as f:
            old_manifest = json.load(f)
        console.print(f"🔄 Found existing manifest: {manifest_path}", style="cyan")
        return old_manifest.get("doc-hashes", {})
    else:
        console.print("🆕 No manifest found or forced indexing. Full re-indexing.", style="cyan")
        return {}


def _save_manifest(manifest_path: Path, hashes: Dict[str, str]):
    """
    Saves the manifest file.
    """
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "doc-hashes": hashes,
            "modified": datetime.now().isoformat()
        }, f, indent=2)