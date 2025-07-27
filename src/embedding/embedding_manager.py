"""
Embedding management for DaCrew - Handles embeddings for codebase, issues, and documents.
"""
from pathlib import Path
from typing import List

from rich.console import Console

from .abstract_embedding_manager import EmbeddingResult
from .codebase_embedding_manager import CodebaseEmbeddingManager
from .documents_embedding_manager import DocumentsEmbeddingManager
from .issues_embedding_manager import IssuesEmbeddingManager

console = Console()

WORKSPACES_DIR = Path.home() / ".dacrew" / "workspaces"


class EmbeddingManager:
    def __init__(self, project_key: str):
        self.project_key = project_key
        self.base_dir = WORKSPACES_DIR / project_key / "embeddings"
        self.codebase_dir = self.base_dir / "codebase"
        self.issues_dir = self.base_dir / "issues"
        self.documents_dir = self.base_dir / "documents"
        self.codebase_manager = CodebaseEmbeddingManager(project_key, self.codebase_dir)
        self.issues_manager = IssuesEmbeddingManager(project_key, self.issues_dir)
        self.documents_manager = DocumentsEmbeddingManager(project_key, self.documents_dir)

        self._ensure_directories()

        # TODO: Initialize vector stores here
        # self.codebase_store = VectorStore(self.codebase_dir)
        # self.issues_store = VectorStore(self.issues_dir)
        # self.documents_store = VectorStore(self.documents_dir)

    def _ensure_directories(self):
        for d in [self.codebase_dir, self.issues_dir, self.documents_dir]:
            d.mkdir(parents=True, exist_ok=True)


    def index_sources(self, sources: list[str], force):
        # Do these in parallel
        if "codebase" in sources:
            self.codebase_manager.index()
        if "issues" in sources:
            self.issues_manager.index()
        if "documents" in sources:
            self.documents_manager.index()


    def query(self, query: str, sources: List[str], top_k: int = 5) -> List[EmbeddingResult]:
        console.print(f"🔍 Querying embeddings for: {query}", style="green")

        results: List[EmbeddingResult] = []

        if "codebase" in sources:
            results.extend(self.codebase_manager.query(query, top_k))

        if "issues" in sources:
            results.extend(self.issues_manager.query(query, top_k))

        if "documents" in sources:
            results.extend(self.documents_manager.query(query, top_k))

        return sorted(results, key=lambda r: r.similarity, reverse=True)[:top_k]


    def clean(self, sources: List[str]):
        if "codebase" in sources:
            self.codebase_manager.clean()
        if "issues" in sources:
            self.issues_manager.clean()
        if "documents" in sources:
            self.documents_manager.clean()


    def get_stats(self, sources: List[str]):
        if "codebase" in sources:
            self.codebase_manager.stats()
        if "issues" in sources:
            self.issues_manager.stats()
        if "documents" in sources:
            self.documents_manager.stats()

