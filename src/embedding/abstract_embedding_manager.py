from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings

from rich.console import Console
console = Console()

@dataclass
class EmbeddingResult:
    content: str
    source: str  # e.g., "codebase", "issues", "documents"
    reference: str  # e.g., file path, issue key, document name
    similarity: float


def _load_faiss_vector_store(store_dir: Path, embedding_fn: Embeddings) -> None | FAISS:
    try:
        return FAISS.load_local(
            store_dir.as_posix(),
            embedding_fn,
            allow_dangerous_deserialization=True
        )
    except RuntimeError as e:
        if "could not open" in str(e) and "index.faiss" in str(e):
            console.print("[yellow]No index found. Please run indexing first.[/]")
            return None
        console.print(f"[red]Error loading index: {e}[/]")
        return None
    except Exception as e:
        console.print(f"[red]Error loading index: {e}[/]")
        return None


class AbstractEmbeddingManager(ABC):

    @abstractmethod
    def index(self):
        pass

    @abstractmethod
    def clean(self):
        pass

    @abstractmethod
    def stats(self):
        pass

    @abstractmethod
    def query(self, query: str, top_k: int = 5):
        pass


