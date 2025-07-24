"""Repository-Embedding coordination layer - orchestrates between codebase and vector operations"""

import json
import logging
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from .exceptions import EmbeddingError

logger = logging.getLogger(__name__)


class EmbeddingMetadata:
    """Manages embedding metadata for repositories"""

    def __init__(self, embeddings_dir: Path):
        self.embeddings_dir = embeddings_dir
        self.embeddings_dir.mkdir(exist_ok=True)

    def get_metadata_path(self, repo_id: str) -> Path:
        """Get the metadata file path for a repository"""
        return self.embeddings_dir / repo_id / "metadata.json"

    def get_embedding_dir(self, repo_id: str) -> Path:
        """Get the embedding directory for a repository"""
        return self.embeddings_dir / repo_id

    def exists(self, repo_id: str) -> bool:
        """Check if embedding metadata exists for repository"""
        metadata_path = self.get_metadata_path(repo_id)
        return metadata_path.exists() and metadata_path.parent.exists()

    def load(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Load embedding metadata for a repository"""
        metadata_path = self.get_metadata_path(repo_id)

        try:
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load metadata for {repo_id}: {e}")

        return None

    def save(self, repo_id: str, metadata: Dict[str, Any]) -> bool:
        """Save embedding metadata for a repository"""
        try:
            embedding_dir = self.get_embedding_dir(repo_id)
            embedding_dir.mkdir(parents=True, exist_ok=True)

            metadata_path = self.get_metadata_path(repo_id)
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            return True
        except Exception as e:
            logger.error(f"Failed to save metadata for {repo_id}: {e}")
            return False

    def delete(self, repo_id: str) -> bool:
        """Delete embedding metadata and directory for a repository"""
        try:
            embedding_dir = self.get_embedding_dir(repo_id)
            if embedding_dir.exists():
                import shutil
                shutil.rmtree(embedding_dir)
                return True
        except Exception as e:
            logger.error(f"Failed to delete metadata for {repo_id}: {e}")

        return False

    def list_all(self) -> List[str]:
        """List all repository IDs with embeddings"""
        try:
            if not self.embeddings_dir.exists():
                return []

            repo_ids = []
            for item in self.embeddings_dir.iterdir():
                if item.is_dir() and self.exists(item.name):
                    repo_ids.append(item.name)

            return sorted(repo_ids)
        except Exception:
            return []


class EmbeddingManager:
    """
    Coordination layer for repository-embedding operations

    This manager orchestrates between:
    - CodebaseManager (repository operations)
    - VectorManager (embedding operations)
    - EmbeddingMetadata (metadata persistence)

    It maintains the relationship between repositories and their embeddings
    without being tightly coupled to either implementation.
    """

    def __init__(self,
                 workspace_root: Optional[Path] = None,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize EmbeddingManager

        Args:
            workspace_root: Root directory for workspace (default: ./workspace)
            embedding_model: Model to use for embeddings
        """
        self.workspace_root = workspace_root or Path.cwd() / "workspace"
        self.embeddings_dir = self.workspace_root / "embeddings"
        self.embedding_model = embedding_model

        # Initialize metadata manager
        self.metadata = EmbeddingMetadata(self.embeddings_dir)

        # Initialize managers (imported locally to avoid circular dependencies)
        self._codebase_manager = None
        self._vector_managers = {}  # Cache for repo-specific vector managers

    def _get_codebase_manager(self):
        """Lazy initialization of codebase manager"""
        if self._codebase_manager is None:
            from ..codebase import SimpleCodebaseManager
            self._codebase_manager = SimpleCodebaseManager()
        return self._codebase_manager

    def _get_vector_manager(self, repo_id: str):
        """Get or create vector manager for specific repository"""
        if repo_id not in self._vector_managers:
            from ..vector_db import VectorManager

            # Create repository-specific vector database
            embedding_dir = self.metadata.get_embedding_dir(repo_id)
            vector_db_path = embedding_dir / "chromadb"

            self._vector_managers[repo_id] = VectorManager(
                db_path=str(vector_db_path),
                embedding_model=self.embedding_model
            )

        return self._vector_managers[repo_id]

    # ============================================================================
    # Main Coordination Operations
    # ============================================================================

    def create_embedding_for_current_repo(self,
                                          progress_callback: Optional[callable] = None,
                                          **indexing_options) -> Dict[str, Any]:
        """Create embeddings for the current active repository"""
        codebase_manager = self._get_codebase_manager()

        # Get current repository info
        repo_info = codebase_manager.get_current_repository_info()
        if not repo_info:
            raise EmbeddingError("No active repository found. Add a codebase first.")

        repo_path = codebase_manager.get_codebase_path()
        if not repo_path:
            raise EmbeddingError("Current repository path not accessible")

        return self.create_embedding(
            repo_info['repo_id'],
            repo_path,
            repo_info,
            progress_callback=progress_callback,
            **indexing_options
        )

    def create_embedding(self,
                         repo_id: str,
                         repo_path: Path,
                         repo_info: Dict[str, Any],
                         progress_callback: Optional[callable] = None,
                         file_patterns: Optional[List[str]] = None,
                         exclude_patterns: Optional[List[str]] = None,
                         chunk_size: int = 1000,
                         chunk_overlap: int = 200,
                         force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Create embeddings for a repository

        Args:
            repo_id: Repository identifier
            repo_path: Path to the repository
            repo_info: Repository information
            progress_callback: Optional callback for progress updates
            file_patterns: File patterns to include
            exclude_patterns: Patterns to exclude
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            force_rebuild: Whether to rebuild existing embeddings

        Returns:
            Embedding metadata
        """
        if not repo_path.exists():
            raise EmbeddingError(f"Repository path does not exist: {repo_path}")

        # Check if embeddings already exist
        if not force_rebuild and self.has_embedding(repo_id):
            existing_metadata = self.get_embedding_metadata(repo_id)
            if existing_metadata and existing_metadata.get("indexing_status") == "complete":
                if progress_callback:
                    progress_callback("Embeddings already exist. Use force_rebuild=True to recreate.")
                return existing_metadata

        try:
            # Initialize metadata
            if progress_callback:
                progress_callback("Initializing embedding metadata...")

            metadata = self._create_initial_metadata(repo_id, repo_path, repo_info)
            self.metadata.save(repo_id, metadata)

            # Get vector manager for this repository
            if progress_callback:
                progress_callback("Initializing vector database...")

            vector_manager = self._get_vector_manager(repo_id)
            collection_name = f"codebase_{repo_id}"

            # Index the codebase
            if progress_callback:
                progress_callback("Indexing codebase...")

            indexing_stats = vector_manager.index_codebase(
                codebase_path=str(repo_path),
                collection_name=collection_name,
                file_patterns=file_patterns,
                exclude_patterns=exclude_patterns,
                force_rebuild=force_rebuild,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            # Update metadata with results
            metadata.update({
                "indexing_status": "complete",
                "last_updated": datetime.now().isoformat(),
                "total_chunks": indexing_stats.get("total_chunks", 0),
                "total_files": indexing_stats.get("total_files", 0),
                "file_types": indexing_stats.get("file_types", []),
                "indexing_duration_seconds": indexing_stats.get("duration", 0),
                "collection_name": collection_name,
                "indexing_options": {
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "file_patterns": file_patterns,
                    "exclude_patterns": exclude_patterns
                }
            })

            # Save final metadata
            self.metadata.save(repo_id, metadata)

            if progress_callback:
                progress_callback(f"Embedding creation complete! Created {metadata['total_chunks']} chunks from {metadata['total_files']} files.")

            return metadata

        except Exception as e:
            # Update metadata with error status
            error_metadata = {
                **metadata,
                "indexing_status": "failed",
                "error_message": str(e),
                "failed_at": datetime.now().isoformat()
            }
            self.metadata.save(repo_id, error_metadata)

            raise EmbeddingError(f"Failed to create embeddings for {repo_id}: {str(e)}")

    def update_embedding(self,
                         repo_id: str,
                         progress_callback: Optional[callable] = None,
                         **indexing_options) -> Dict[str, Any]:
        """Update embeddings for a repository"""
        if not self.has_embedding(repo_id):
            raise EmbeddingError(f"No existing embeddings found for repository: {repo_id}")

        # Get repository info from codebase manager
        codebase_manager = self._get_codebase_manager()
        repo_info = codebase_manager.get_repository_info(repo_id)
        if not repo_info:
            raise EmbeddingError(f"Repository {repo_id} not found in codebase manager")

        repo_path = Path(repo_info['actual_path'])
        if not repo_path.exists():
            raise EmbeddingError(f"Repository path does not exist: {repo_path}")

        # Force rebuild for updates
        indexing_options['force_rebuild'] = True

        return self.create_embedding(
            repo_id=repo_id,
            repo_path=repo_path,
            repo_info=repo_info,
            progress_callback=progress_callback,
            **indexing_options
        )

    def update_current_embedding(self,
                                 progress_callback: Optional[callable] = None,
                                 **indexing_options) -> Dict[str, Any]:
        """Update embeddings for the current active repository"""
        codebase_manager = self._get_codebase_manager()

        repo_info = codebase_manager.get_current_repository_info()
        if not repo_info:
            raise EmbeddingError("No active repository found")

        return self.update_embedding(
            repo_info['repo_id'],
            progress_callback=progress_callback,
            **indexing_options
        )

    def search_current_codebase(self,
                                query: str,
                                n_results: int = 10,
                                file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search embeddings for the current repository"""
        codebase_manager = self._get_codebase_manager()

        repo_info = codebase_manager.get_current_repository_info()
        if not repo_info:
            raise EmbeddingError("No active repository found")

        return self.search_codebase(repo_info['repo_id'], query, n_results, file_types)

    def search_codebase(self,
                        repo_id: str,
                        query: str,
                        n_results: int = 10,
                        file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search embeddings for a specific repository"""
        if not self.has_embedding(repo_id):
            raise EmbeddingError(f"No embeddings found for repository: {repo_id}")

        metadata = self.get_embedding_metadata(repo_id)
        if not metadata or metadata.get("indexing_status") != "complete":
            raise EmbeddingError(f"Embeddings not ready for repository: {repo_id}")

        # Get vector manager and search
        vector_manager = self._get_vector_manager(repo_id)
        collection_name = metadata.get("collection_name", f"codebase_{repo_id}")

        return vector_manager.search_codebase(
            query=query,
            collection_name=collection_name,
            n_results=n_results,
            file_types=file_types
        )

    def delete_embedding(self, repo_id: str) -> bool:
        """Delete embeddings for a repository"""
        try:
            # Remove vector manager from cache
            if repo_id in self._vector_managers:
                del self._vector_managers[repo_id]

            # Delete metadata and files
            return self.metadata.delete(repo_id)

        except Exception as e:
            logger.error(f"Failed to delete embedding for {repo_id}: {e}")
            return False

    # ============================================================================
    # Information and Status Methods
    # ============================================================================

    def has_embedding(self, repo_id: str) -> bool:
        """Check if embeddings exist for a repository"""
        if not self.metadata.exists(repo_id):
            return False

        # Check if vector database exists
        embedding_dir = self.metadata.get_embedding_dir(repo_id)
        vector_db_path = embedding_dir / "chromadb"

        return vector_db_path.exists() and any(vector_db_path.iterdir())

    def get_embedding_metadata(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get embedding metadata for a repository"""
        return self.metadata.load(repo_id)

    def list_embeddings(self) -> List[Dict[str, Any]]:
        """List all embeddings with their metadata"""
        embeddings = []

        for repo_id in self.metadata.list_all():
            metadata = self.get_embedding_metadata(repo_id)
            if metadata:
                # Add status information
                metadata = metadata.copy()
                metadata["has_vector_db"] = self.has_embedding(repo_id)
                embeddings.append(metadata)

        return embeddings

    def get_embedding_status(self, repo_id: str) -> Dict[str, Any]:
        """Get comprehensive status of embeddings for a repository"""
        metadata = self.get_embedding_metadata(repo_id)
        if not metadata:
            return {"exists": False}

        # Get vector database information
        has_vector_db = self.has_embedding(repo_id)
        vector_db_stats = {}

        if has_vector_db:
            try:
                vector_manager = self._get_vector_manager(repo_id)
                collection_name = metadata.get("collection_name", f"codebase_{repo_id}")
                doc_count = vector_manager.get_collection_count(collection_name)
                vector_db_stats = {
                    "collection_name": collection_name,
                    "document_count": doc_count
                }
            except Exception as e:
                vector_db_stats = {"error": str(e)}

        return {
            "exists": True,
            "metadata": metadata,
            "has_vector_db": has_vector_db,
            "vector_db_stats": vector_db_stats
        }

    def get_current_embedding_status(self) -> Dict[str, Any]:
        """Get embedding status for the current repository"""
        codebase_manager = self._get_codebase_manager()

        repo_info = codebase_manager.get_current_repository_info()
        if not repo_info:
            return {"has_current_repo": False}

        status = self.get_embedding_status(repo_info['repo_id'])
        status["current_repo"] = {
            "repo_id": repo_info['repo_id'],
            "repo_name": repo_info['repo_name'],
            "repo_url": repo_info['repo_url']
        }
        status["has_current_repo"] = True

        return status

    # ============================================================================
    # Batch Operations
    # ============================================================================

    def sync_embeddings_with_repositories(self,
                                          progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Sync embeddings with available repositories"""
        codebase_manager = self._get_codebase_manager()
        repositories = codebase_manager.list_repositories()

        stats = {
            "repositories_found": len(repositories),
            "embeddings_created": 0,
            "embeddings_updated": 0,
            "embeddings_failed": 0,
            "embeddings_removed": 0
        }

        # Create/update embeddings for existing repositories
        for repo in repositories:
            if not repo["exists"]:  # Skip non-existent repositories
                continue

            repo_id = repo["repo_id"]

            try:
                if self.has_embedding(repo_id):
                    # Check if update is needed
                    metadata = self.get_embedding_metadata(repo_id)
                    repo_updated = datetime.fromisoformat(repo.get("last_updated", repo.get("cloned_at")))
                    embedding_updated = datetime.fromisoformat(metadata.get("last_updated", "1970-01-01T00:00:00"))

                    if repo_updated > embedding_updated:
                        if progress_callback:
                            progress_callback(f"Updating embeddings for {repo['repo_name']}...")
                        self.update_embedding(repo_id)
                        stats["embeddings_updated"] += 1
                else:
                    if progress_callback:
                        progress_callback(f"Creating embeddings for {repo['repo_name']}...")
                    self.create_embedding(
                        repo_id=repo_id,
                        repo_path=Path(repo["actual_path"]),
                        repo_info=repo
                    )
                    stats["embeddings_created"] += 1

            except Exception as e:
                logger.error(f"Failed to sync embeddings for {repo_id}: {e}")
                stats["embeddings_failed"] += 1

        # Remove embeddings for repositories that no longer exist
        existing_repo_ids = {repo["repo_id"] for repo in repositories if repo["exists"]}
        embedding_repo_ids = set(self.metadata.list_all())

        orphaned_embeddings = embedding_repo_ids - existing_repo_ids
        for repo_id in orphaned_embeddings:
            if progress_callback:
                progress_callback(f"Removing orphaned embeddings for {repo_id}...")
            self.delete_embedding(repo_id)
            stats["embeddings_removed"] += 1

        return stats

    # ============================================================================
    # Issue embeddings
    # ============================================================================

    def create_issue_embeddings(
        self,
        issues: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None,
        force_rebuild: bool = False) -> Dict[str, Any]:
            """
            Create embeddings for JIRA issues in the current workspace.
            """
            repo_id = "issues"
            embedding_dir = self.metadata.get_embedding_dir(repo_id)
            embedding_dir.mkdir(parents=True, exist_ok=True)

            if not force_rebuild and self.has_embedding(repo_id):
                existing_metadata = self.get_embedding_metadata(repo_id)
                if existing_metadata and existing_metadata.get("indexing_status") == "complete":
                    if progress_callback:
                        progress_callback("Issue embeddings already exist. Use --force to rebuild.")
                    return existing_metadata

            if progress_callback:
                progress_callback(f"Indexing {len(issues)} JIRA issues...")

            documents = []
            for issue in issues:
                issue_text = f"{issue.get('summary', '')}\n\n{issue.get('description', '')}"
                documents.append({
                    "id": issue["key"],
                    "text": issue_text,
                    "metadata": {
                        "key": issue["key"],
                        "status": issue.get("status"),
                        "labels": issue.get("labels", [])
                    }
                })

            vector_manager = self._get_vector_manager(repo_id)
            collection_name = "issues_collection"

            indexing_stats = vector_manager.index_documents(
                documents=documents,
                collection_name=collection_name,
                force_rebuild=force_rebuild
            )

            metadata = {
                "repo_id": repo_id,
                "total_issues": len(issues),
                "indexing_status": "complete",
                "last_updated": datetime.now().isoformat(),
                "collection_name": collection_name,
                "indexing_duration_seconds": indexing_stats.get("duration", 0),
            }
            self.metadata.save(repo_id, metadata)

            return metadata


    def update_issue_embeddings(
            self,
            issues: List[Dict[str, Any]],
            progress_callback: Optional[callable] = None
        ) -> Dict[str, Any]:
        """
        Update the issue embeddings by rebuilding them.
        """
        return self.create_issue_embeddings(
            issues,
            progress_callback=progress_callback,
            force_rebuild=True
        )

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def _create_initial_metadata(self, repo_id: str, repo_path: Path, repo_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create initial embedding metadata"""
        return {
            "repo_id": repo_id,
            "repo_name": repo_info.get("repo_name", "unknown"),
            "repo_url": repo_info.get("repo_url", ""),
            "repo_branch": repo_info.get("branch", "main"),
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "embedding_model": self.embedding_model,
            "vector_db": "chromadb",
            "total_chunks": 0,
            "total_files": 0,
            "file_types": [],
            "indexing_status": "in_progress",
            "platform": platform.system(),
            "repo_size_mb": self._calculate_repo_size(repo_path),
            "embedding_version": "2.0"
        }

    def _calculate_repo_size(self, repo_path: Path) -> float:
        """Calculate repository size in MB"""
        try:
            if not repo_path.exists():
                return 0.0

            size_bytes = sum(
                f.stat().st_size
                for f in repo_path.rglob('*')
                if f.is_file()
            )
            return round(size_bytes / (1024 * 1024), 1)
        except:
            return 0.0


    def cleanup(self):
        """Clean up resources"""
        # Clear vector manager cache
        self._vector_managers.clear()
        self._codebase_manager = None