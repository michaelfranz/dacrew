"""
Internal manager for codebase embeddings.
Not intended to be used directly outside the embedding package.
"""

import json
from pathlib import Path
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from rich.console import Console

from .abstract_embedding_manager import AbstractEmbeddingManager, EmbeddingResult
from .embedding_utils import _clean_directory
from ..config import Config

console = Console()
config = Config.load()

class DocumentsEmbeddingManager(AbstractEmbeddingManager):
    def __init__(self, project_key: str, documents_dir: Path):
        self.project_key = project_key
        self.documents_dir = documents_dir
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        # TODO make this configurable:
        self.embedding_fn = OpenAIEmbeddings(model="text-embedding-3-small", api_key=config.ai.openai_api_key)

    def index(self, force: bool = False):
        """
        Index the project documents using configuration include/exclude patterns.
        """
        config = Config.load()
        documents_cfg = config.embedding.documents
        base_paths = [Path(p).resolve() for p in documents_cfg.paths]

        manifest_path = self.documents_dir / "manifest.json"
        old_hashes = {}

        # Load existing manifest for incremental indexing
        if manifest_path.exists() and not force:
            with open(manifest_path, "r", encoding="utf-8") as f:
                old_manifest = json.load(f)
                old_hashes = {f["path"]: f["hash"] for f in old_manifest.get("files", [])}
            console.print(f"🔄 Found existing manifest: {manifest_path}", style="cyan")
        else:
            console.print("🆕 No manifest found or forced indexing. Full re-indexing.", style="cyan")

        files = []
        changed_files = []

        pass


    def clean(self):
        _clean_directory(self.documents_dir, "documents")

    def stats(self):
        """
        Return statistics for the documents embeddings.
        """
        manifest_path = self.documents_dir / "manifest.json"
        if not manifest_path.exists():
            return {"files_indexed": 0}
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        return {"files_indexed": len(manifest.get("files", []))}

    def query(self, query: str, top_k: int = 5) -> List[EmbeddingResult]:
        store = self._load_vector_store()
        hits = store.similarity_search_with_score(query, k=top_k)
        return [
            EmbeddingResult(
                content=doc.page_content,
                source="codebase",  # or "issues", "documents"
                reference=doc.metadata.get("reference", ""),
                similarity=1 - score  # if using distance, convert to similarity
            )
            for doc, score in hits
        ]

    def _load_vector_store(self) -> FAISS:
        return FAISS.load_local(
            self.codebase_dir.as_posix(),
            self.embedding_fn,
            allow_dangerous_deserialization=True
        )