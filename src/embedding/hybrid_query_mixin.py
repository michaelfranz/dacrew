import re
from typing import List

import numpy as np
from rank_bm25 import BM25Okapi
from rich.console import Console

from .abstract_embedding_manager import EmbeddingResult

console = Console()


class HybridQueryMixin:
    """
    A mixin providing hybrid keyword-based re-ranking for embedding query results.
    """
    @staticmethod
    def _rerank_by_keyword(
            query: str, results: List[EmbeddingResult], alpha: float = 0.6
    ) -> List[EmbeddingResult]:
        """
        Re-rank results using BM25 and embedding similarity.

        alpha: weight for BM25 vs. embedding similarity.
               1.0 = BM25 only, 0.0 = embedding similarity only.
        """
        if not results:
            return results

        # Tokenize query and documents
        query_terms = re.findall(r"\w+", query.lower())
        tokenized_docs = [re.findall(r"\w+", r.content.lower()) for r in results]

        # Initialize BM25
        bm25 = BM25Okapi(tokenized_docs)
        bm25_scores = np.array(bm25.get_scores(query_terms))

        # Normalize BM25 scores
        if bm25_scores.max() > 0:
            bm25_scores = bm25_scores / bm25_scores.max()

        # Extract embedding similarities (already in results)
        embed_scores = np.array([r.similarity for r in results])
        if embed_scores.max() > 0:
            embed_scores = embed_scores / embed_scores.max()

        # Combine scores
        hybrid_scores = alpha * bm25_scores + (1 - alpha) * embed_scores

        # Update results with new similarity scores
        for idx, r in enumerate(results):
            r.similarity = float(hybrid_scores[idx])

        return sorted(results, key=lambda x: x.similarity, reverse=True)


    @staticmethod
    def _debug_print_results(query: str, results: List[EmbeddingResult]):
        """
        Prints a debug-friendly view of query results.
        """
        console.print(f"[DEBUG] Query: {query}", style="cyan")
        for r in results:
            console.print(
                f"[{r.similarity:.3f}] {r.reference} -> {r.content[:120]}...", style="dim"
            )