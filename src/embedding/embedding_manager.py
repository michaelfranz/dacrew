"""
Embedding management for DaCrew - Handles embeddings for codebase, issues, and documents.
"""

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

from rich.console import Console

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
        """
        Index source code into vector embeddings.
        """
        path = ""
        console.print(f"📦 Indexing codebase at: {path}", style="cyan")
        # TODO: Walk files, chunk code, embed, and store in codebase vector DB.

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
        if "codebase" in sources:
            self.index_codebase()
        elif "issues" in sources:
            self.index_issues()
        elif "documents" in sources:
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
    @staticmethod
    def _clean_directory(directory: Path, name: str):
        if not directory.exists() or not any(directory.iterdir()):
            console.print(f"⚠️ No {name} embeddings found to clean.", style="yellow")
            return

        try:
            shutil.rmtree(directory)
            directory.mkdir(parents=True, exist_ok=True)  # Recreate the empty directory
            console.print(f"✅ {name.capitalize()} embeddings cleaned successfully.", style="green")
        except Exception as e:
            console.print(f"❌ Failed to clean {name} embeddings: {e}", style="red")

    def clean_codebase(self):
        self._clean_directory(self.codebase_dir, "codebase")

    def clean_issues(self):
        self._clean_directory(self.issues_dir, "issues")

    def clean_documents(self):
        self._clean_directory(self.documents_dir, "documents")

    def clean(self, sources: List[str]):
        if "codebase" in sources:
            self.clean_codebase()
        elif "issues" in sources:
            self.clean_issues()
        elif "documents" in sources:
            self.clean_documents()

    def get_stats(self):
        pass

