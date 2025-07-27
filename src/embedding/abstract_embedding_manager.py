from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    content: str
    source: str  # e.g., "codebase", "issues", "documents"
    reference: str  # e.g., file path, issue key, document name
    similarity: float


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

