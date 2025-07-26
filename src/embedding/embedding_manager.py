"""
Embedding management for DaCrew - Handles embeddings for codebase, issues, and documents.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List

from rich.console import Console

from .codebase_embedding_manager import CodebaseEmbeddingManager
from .embedding_utils import _clean_directory

console = Console()

WORKSPACES_DIR = Path.home() / ".dacrew" / "workspaces"


@dataclass
class EmbeddingResult:
    content: str
    source: str  # e.g., "codebase", "issues", "documents"
    reference: str  # e.g., file path, issue key, document name
    similarity: float


class EmbeddingManager:
    def __init__(self, project_key: str):
        self.project_key = project_key
        self.base_dir = WORKSPACES_DIR / project_key / "embeddings"
        self.codebase_dir = self.base_dir / "codebase"
        self.issues_dir = self.base_dir / "issues"
        self.documents_dir = self.base_dir / "documents"
        self.codebase_manager = CodebaseEmbeddingManager(project_key, self.codebase_dir)

        self._ensure_directories()

        # TODO: Initialize vector stores here
        # self.codebase_store = VectorStore(self.codebase_dir)
        # self.issues_store = VectorStore(self.issues_dir)
        # self.documents_store = VectorStore(self.documents_dir)

    def _ensure_directories(self):
        for d in [self.codebase_dir, self.issues_dir, self.documents_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------
    # INDEXING
    # ------------------------
    def index_codebase(self):
        self.codebase_manager.index()

    def index_issues(self):
        """
        Index Jira issues into vector embeddings.
        """
        issues = []
        console.print(f"📝 Indexing {len(issues)} Jira issues...", style="cyan")
        # TODO: Convert issues to text and embed.

    def index_documents(self):
        """
        Index documents (local + web).
        """
        paths = []
        urls = []
        console.print(f"📚 Indexing documents: {len(paths)} local files, {len(urls)} URLs.", style="cyan")
        # TODO: Extract text (PDF, Word, etc.), embed, and store.

    def index_sources(self, sources: list[str], force):
        # Do these in parallel
        if "codebase" in sources:
            self.index_codebase()
        if "issues" in sources:
            self.index_issues()
        if "documents" in sources:
            self.index_documents()

    # ------------------------
    # QUERY
    # ------------------------
    def query(self, query: str, sources: List[str], top_k: int = 5) -> List[EmbeddingResult]:
        """
        Query across all embedding stores (codebase, issues, documents) and return a unified result set.
        """
        console.print(f"🔍 Querying embeddings for: {query}", style="green")

        # TODO: Perform vector search in each store
        # codebase_hits = self.codebase_store.search(query, top_k=top_k)
        # issues_hits = self.issues_store.search(query, top_k=top_k)
        # documents_hits = self.documents_store.search(query, top_k=top_k)

        # For now, return dummy results

        results: List[EmbeddingResult] = [
            EmbeddingResult(content="Example code snippet", source="codebase", reference="src/example.py",
                            similarity=0.92),
            EmbeddingResult(content="Example Jira issue description", source="issues", reference="BTS-123",
                            similarity=0.89),
            EmbeddingResult(content="Example document excerpt", source="documents", reference="architecture.md",
                            similarity=0.85)]

        return sorted(results, key=lambda r: r.similarity, reverse=True)

    # ------------------------
    # CLEANING
    # ------------------------

    def clean_codebase(self):
        self.codebase_manager.clean()

    def clean_issues(self):
        _clean_directory(self.issues_dir, "issues")

    def clean_documents(self):
        _clean_directory(self.documents_dir, "documents")

    def clean(self, sources: List[str]):
        if "codebase" in sources:
            self.clean_codebase()
        elif "issues" in sources:
            self.clean_issues()
        elif "documents" in sources:
            self.clean_documents()

    def get_stats(self):
        pass

