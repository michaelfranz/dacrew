"""Vector Database Manager for JIRA AI Assistant"""

import logging
import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings

# Suppress specific warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")

from sentence_transformers import SentenceTransformer
import numpy as np

from ..config import Config
from ..jira_client import JIRAClient

logger = logging.getLogger(__name__)


class VectorManager:
    """Manages vector embeddings and semantic search for JIRA issues"""

    def __init__(self, config: Config):
        self.config = config
        self.client = None
        self.collection = None
        self.embedding_model = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize ChromaDB and embedding model"""
        try:
            # Initialize ChromaDB
            persist_dir = Path(self.config.ai.chroma_persist_directory)
            persist_dir.mkdir(parents=True, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Initialize or get collection
            collection_name = "jira_issues"
            try:
                self.collection = self.client.get_collection(collection_name)
                logger.info(f"Connected to existing collection: {collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {collection_name}")

            # Initialize embedding model
            self.embedding_model = SentenceTransformer(self.config.ai.embeddings_model)
            logger.info(f"Loaded embedding model: {self.config.ai.embeddings_model}")

        except Exception as e:
            logger.error(f"Failed to initialize vector components: {e}")
            raise

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = self.embedding_model.encode(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def add_issue_to_vector_db(self, issue: Dict[str, Any]) -> bool:
        """Add a JIRA issue to the vector database"""
        try:
            # Create searchable text from issue
            searchable_text = self._create_searchable_text(issue)

            # Generate embedding
            embedding = self.generate_embeddings([searchable_text])[0]

            # Prepare metadata
            metadata = {
                "issue_key": issue["key"],
                "summary": issue["summary"],
                "status": issue["status"],
                "priority": issue["priority"],
                "assignee": issue["assignee"],
                "project": issue["project"],
                "issue_type": issue["issue_type"],
                "created": issue["created"],
                "updated": issue["updated"],
                "url": issue["url"]
            }

            # Add to collection
            self.collection.add(
                embeddings=[embedding.tolist()],
                documents=[searchable_text],
                metadatas=[metadata],
                ids=[issue["key"]]
            )

            logger.debug(f"Added issue {issue['key']} to vector database")
            return True

        except Exception as e:
            logger.error(f"Failed to add issue {issue.get('key', 'unknown')} to vector database: {e}")
            return False

    def add_issues_batch(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add multiple issues to the vector database in batch"""
        try:
            if not issues:
                return {"success": True, "added": 0, "failed": 0}

            # Prepare batch data
            embeddings = []
            documents = []
            metadatas = []
            ids = []

            for issue in issues:
                try:
                    # Create searchable text
                    searchable_text = self._create_searchable_text(issue)

                    # Prepare metadata
                    metadata = {
                        "issue_key": issue["key"],
                        "summary": issue["summary"],
                        "status": issue["status"],
                        "priority": issue["priority"],
                        "assignee": issue["assignee"],
                        "project": issue["project"],
                        "issue_type": issue["issue_type"],
                        "created": issue["created"],
                        "updated": issue["updated"],
                        "url": issue["url"]
                    }

                    documents.append(searchable_text)
                    metadatas.append(metadata)
                    ids.append(issue["key"])

                except Exception as e:
                    logger.error(f"Failed to prepare issue {issue.get('key', 'unknown')}: {e}")
                    continue

            if not documents:
                return {"success": True, "added": 0, "failed": len(issues)}

            # Generate embeddings for all documents
            embeddings = self.generate_embeddings(documents)

            # Add to collection
            self.collection.add(
                embeddings=embeddings.tolist(),
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(documents)} issues to vector database")
            return {
                "success": True,
                "added": len(documents),
                "failed": len(issues) - len(documents)
            }

        except Exception as e:
            logger.error(f"Failed to add issues batch: {e}")
            return {"success": False, "error": str(e), "added": 0, "failed": len(issues)}

    def semantic_search(self, query: str, n_results: int = 10,
                        filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Perform semantic search on JIRA issues"""
        try:
            # Generate embedding for query
            query_embedding = self.generate_embeddings([query])[0]

            # Prepare where clause for filtering
            where_clause = {}
            if filters:
                for key, value in filters.items():
                    if value:
                        where_clause[key] = value

            # Search in collection
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, issue_id in enumerate(results['ids'][0]):
                    result = {
                        "issue_key": issue_id,
                        "similarity_score": 1 - results['distances'][0][i],  # Convert distance to similarity
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i]
                    }
                    formatted_results.append(result)

            logger.info(f"Semantic search returned {len(formatted_results)} results for query: {query}")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to perform semantic search: {e}")
            return []

    def update_issue_in_vector_db(self, issue: Dict[str, Any]) -> bool:
        """Update an issue in the vector database"""
        try:
            # First, try to delete the existing entry
            try:
                self.collection.delete(ids=[issue["key"]])
            except:
                pass  # Issue might not exist in vector DB

            # Add the updated issue
            return self.add_issue_to_vector_db(issue)

        except Exception as e:
            logger.error(f"Failed to update issue {issue.get('key', 'unknown')} in vector database: {e}")
            return False

    def delete_issue_from_vector_db(self, issue_key: str) -> bool:
        """Delete an issue from the vector database"""
        try:
            self.collection.delete(ids=[issue_key])
            logger.info(f"Deleted issue {issue_key} from vector database")
            return True

        except Exception as e:
            logger.error(f"Failed to delete issue {issue_key} from vector database: {e}")
            return False

    def sync_with_jira(self, jira_client: JIRAClient, project_key: str = None,
                       force_refresh: bool = False) -> Dict[str, Any]:
        """Sync vector database with JIRA issues"""
        try:
            logger.info("Starting JIRA sync with vector database")

            # Build JQL for syncing
            if project_key:
                jql = f"project = {project_key}"
            else:
                jql = "ORDER BY updated DESC"

            # If not force refresh, only sync recent updates
            if not force_refresh:
                # Get last sync time from collection metadata
                last_sync = self._get_last_sync_time()
                if last_sync:
                    jql += f" AND updated >= '{last_sync}'"

            # Get issues from JIRA
            issues = jira_client.search_issues(jql, max_results=1000)

            if not issues:
                logger.info("No issues to sync")
                return {"success": True, "synced": 0}

            # Add/update issues in vector database
            result = self.add_issues_batch(issues)

            # Update last sync time
            self._update_last_sync_time()

            logger.info(f"Sync completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to sync with JIRA: {e}")
            return {"success": False, "error": str(e)}

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database collection"""
        try:
            count = self.collection.count()

            return {
                "total_issues": count,
                "collection_name": self.collection.name,
                "embedding_model": self.config.ai.embeddings_model
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}

    def _create_searchable_text(self, issue: Dict[str, Any]) -> str:
        """Create searchable text from JIRA issue"""
        text_parts = [
            f"Summary: {issue['summary']}",
            f"Key: {issue['key']}",
            f"Status: {issue['status']}",
            f"Priority: {issue['priority']}",
            f"Type: {issue['issue_type']}",
            f"Project: {issue['project']}",
            f"Assignee: {issue['assignee']}",
            f"Reporter: {issue['reporter']}"
        ]

        # Add description if available
        if issue.get('description'):
            text_parts.append(f"Description: {issue['description']}")

        # Add labels if available
        if issue.get('labels'):
            text_parts.append(f"Labels: {', '.join(issue['labels'])}")

        # Add components if available
        if issue.get('components'):
            text_parts.append(f"Components: {', '.join(issue['components'])}")

        return "\n".join(text_parts)

    def _get_last_sync_time(self) -> Optional[str]:
        """Get the last sync time from collection metadata"""
        try:
            # This is a simplified approach - in a real implementation,
            # you might want to store this in a separate metadata collection
            return None
        except:
            return None

    def _update_last_sync_time(self):
        """Update the last sync time"""
        try:
            # This is a simplified approach - in a real implementation,
            # you might want to store this in a separate metadata collection
            pass
        except:
            pass