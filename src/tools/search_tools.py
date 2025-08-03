"""
CrewAI tools for embedding-based searching functionality.
"""
from typing import List, Dict, Any
from crewai.tools import tool
from pydantic import BaseModel, Field
from embedding.embedding_manager import EmbeddingManager

class SearchEmbeddingsInput(BaseModel):
    """Input schema for the search embeddings tool."""
    query: str = Field(description="The search query to use")
    sources: List[str] = Field(description="List of sources to search in (codebase, issues, documents)")
    top_k: int = Field(default=5, description="Number of results to return")

@tool("SearchEmbedding")
def search_embeddings(project_key: str, query: str, sources: List[str], top_k: int = 5) -> Dict[str, Any]:
    """
    Search across codebase, issues, and documents using embeddings.

    Args:
        project_key: The project key for the embedding manager
        query: The search query to use
        sources: List of sources to search in (codebase, issues, documents)
        top_k: Number of results to return

    Returns:
        Dictionary containing search results and count
    """
    try:
        # Initialize the embedding manager
        embedding_manager = EmbeddingManager(project_key)

        # Perform the search
        results = embedding_manager.query(query, sources, top_k)

        # Format results for CrewAI
        formatted_results = []
        for result in results:
            formatted_results.append({
                "content": result.content,
                "source": result.source,
                "similarity": result.similarity,
                "reference": result.reference
            })

        return {
            "results": formatted_results,
            "count": len(formatted_results)
        }
    except Exception as e:
        return {"error": str(e)}