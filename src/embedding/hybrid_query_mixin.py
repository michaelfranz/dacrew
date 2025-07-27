import re
from typing import List

from rich.console import Console

from .abstract_embedding_manager import EmbeddingResult

console = Console()


class HybridQueryMixin:
    """
    A mixin providing hybrid keyword-based re-ranking for embedding query results.
    """

    def _rerank_by_keyword(
            self, query: str, results: List[EmbeddingResult], boost: float = 0.2
    ) -> List[EmbeddingResult]:
        """
        Re-rank results by keyword overlap with the query.
        boost: How much to increase the similarity score per keyword match.
        """
        query_terms = re.findall(r"\w+", query.lower())
        for r in results:
            content_lower = r.content.lower()
            keyword_matches = sum(1 for term in query_terms if term in content_lower)
            r.similarity += keyword_matches * boost
        return sorted(results, key=lambda x: x.similarity, reverse=True)

    def _debug_print_results(self, query: str, results: List[EmbeddingResult]):
        """
        Prints a debug-friendly view of query results.
        """
        console.print(f"[DEBUG] Query: {query}", style="cyan")
        for r in results:
            console.print(
                f"[{r.similarity:.3f}] {r.reference} -> {r.content[:120]}...", style="dim"
            )