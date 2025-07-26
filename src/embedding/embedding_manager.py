"""
Embedding management for DaCrew - Handles embeddings for codebase, issues, and documents.
"""

import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

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
    def index_codebase(self, path: str, include_patterns: List[str] = None, exclude_patterns: List[str] = None):
        """
        Index source code into vector embeddings.
        """
        console.print(f"📦 Indexing codebase at: {path}", style="cyan")
        # TODO: Walk files, chunk code, embed, and store in codebase vector DB.

    def index_issues(self, issues: List[Dict[str, Any]]):
        """
        Index Jira issues into vector embeddings.
        """
        console.print(f"📝 Indexing {len(issues)} Jira issues...", style="cyan")
        # TODO: Convert issues to text and embed.

    def index_documents(self, paths: List[str], urls: List[str]):
        """
        Index documents (local + web).
        """
        console.print(f"📚 Indexing documents: {len(paths)} local files, {len(urls)} URLs.", style="cyan")
        # TODO: Extract text (PDF, Word, etc.), embed, and store.

    def index_sources(self, sources, force):
        pass


    # ------------------------
    # QUERY
    # ------------------------
    def query_embeddings(self, query: str, top_k: int = 5) -> List[EmbeddingResult]:
        """
        Query across all embedding stores (codebase, issues, documents) and return a unified result set.
        """
        console.print(f"🔍 Querying embeddings for: {query}", style="green")

        results: List[EmbeddingResult] = [
            EmbeddingResult(content="Example code snippet", source="codebase", reference="src/example.py",
                            similarity=0.92),
            EmbeddingResult(content="Example Jira issue description", source="issues", reference="BTS-123",
                            similarity=0.89),
            EmbeddingResult(content="Example document excerpt", source="documents", reference="architecture.md",
                            similarity=0.85)]

        # TODO: Perform vector search in each store
        # codebase_hits = self.codebase_store.search(query, top_k=top_k)
        # issues_hits = self.issues_store.search(query, top_k=top_k)
        # documents_hits = self.documents_store.search(query, top_k=top_k)

        # For now, return dummy results

        return sorted(results, key=lambda r: r.similarity, reverse=True)


    def clean_codebase(self):
        print(f"Error: clean_codebase not implemented.")
        pass

    def clean_issues(self):
        print(f"Error: clean_issues not implemented.")
        pass

    def clean_docs(self):
        print(f"Error: clean_docs not implemented.")
        pass

    def clean(self, source: str):
        if source == "codebase":
            self.clean_codebase()
        elif source == "issues":
            self.clean_issues()
        elif source == "docs":
            self.clean_docs()
        else:
            print(f"Error: '{source}' is not a valid source.")

    def get_stats(self):
        pass

