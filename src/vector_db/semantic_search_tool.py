"""Semantic Search Tool for Jira issues"""

import logging

from crewai.tools import BaseTool

logger = logging.getLogger(__name__)


class SemanticSearchTool(BaseTool):
    """Tool for performing semantic search on Jira issues"""
    name: str = "semantic_search"
    description: str = "Perform semantic search on Jira issues using natural language. Parameters: query (str), max_results (int, default=10), project_filter (str, optional), status_filter (str, optional)"

    def _run(self, query: str, max_results: int = 10,
             project_filter: str = None, status_filter: str = None) -> str:
        """Perform semantic search on Jira issues"""
        vector_manager = getattr(self, '_vector_manager', None)
        if not vector_manager:
            return "Error: Vector manager not available"

        try:
            # Prepare filters
            filters = {}
            if project_filter:
                filters['project'] = project_filter
            if status_filter:
                filters['status'] = status_filter

            # Perform semantic search
            results = vector_manager.semantic_search(
                query=query,
                n_results=max_results,
                filters=filters
            )

            if not results:
                return f"No similar issues found for query: {query}"

            # Format results
            response = f"Found {len(results)} semantically similar issues:\n\n"

            for i, result in enumerate(results, 1):
                metadata = result['metadata']
                similarity = result['similarity_score']

                response += f"{i}. [{metadata['issue_key']}] {metadata['summary']}\n"
                response += f"   Similarity: {similarity:.2f} | Status: {metadata['status']}\n"
                response += f"   Assignee: {metadata['assignee']} | Priority: {metadata['priority']}\n"
                response += f"   URL: {metadata['url']}\n\n"

            return response

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return f"Error performing semantic search: {str(e)}"


class VectorSyncTool(BaseTool):
    """Tool for syncing Jira issues with vector database"""
    name: str = "sync_vector_db"
    description: str = "Sync Jira issues with vector database for semantic search. Parameters: project_key (str, optional), force_refresh (bool, default=False)"

    def _run(self, project_key: str = None, force_refresh: bool = False) -> str:
        """Sync Jira issues with vector database"""
        vector_manager = getattr(self, '_vector_manager', None)
        jira_client = getattr(self, '_jira_client', None)

        if not vector_manager:
            return "Error: Vector manager not available"
        if not jira_client:
            return "Error: Jira client not available"

        try:
            result = vector_manager.sync_with_jira(
                jira_client=jira_client,
                project_key=project_key,
                force_refresh=force_refresh
            )

            if result['success']:
                return f"✅ Successfully synced {result.get('added', 0)} issues with vector database"
            else:
                return f"❌ Failed to sync with vector database: {result.get('error', 'Unknown error')}"

        except Exception as e:
            logger.error(f"Error syncing vector database: {e}")
            return f"Error syncing vector database: {str(e)}"


class VectorStatsTool(BaseTool):
    """Tool for getting vector database statistics"""
    name: str = "vector_db_stats"
    description: str = "Get statistics about the vector database. No parameters required."

    def _run(self) -> str:
        """Get vector database statistics"""
        vector_manager = getattr(self, '_vector_manager', None)
        if not vector_manager:
            return "Error: Vector manager not available"

        try:
            stats = vector_manager.get_collection_stats()

            if 'error' in stats:
                return f"Error getting stats: {stats['error']}"

            response = "📊 Vector Database Statistics:\n"
            response += f"Total Issues: {stats['total_issues']}\n"
            response += f"Collection: {stats['collection_name']}\n"
            response += f"Embedding Model: {stats['embedding_model']}\n"

            return response

        except Exception as e:
            logger.error(f"Error getting vector database stats: {e}")
            return f"Error getting stats: {str(e)}"