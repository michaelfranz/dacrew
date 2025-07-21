"""Vector database management with flexible configuration"""

import fnmatch
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import chromadb
import numpy as np
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorDBConfig:
    """Configuration for vector database operations"""

    def __init__(self,
                 db_path: Optional[str] = None,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
                 **kwargs):
        self.db_path = db_path
        self.embedding_model = embedding_model
        self.extra_config = kwargs


class VectorManager:
    """
    Flexible vector database manager supporting both Jira issues and codebase chunks

    This manager can be configured with:
    - Custom database paths (for workspace-specific embeddings)
    - Different embedding models
    - Collection-specific operations
    """

    def __init__(self,
                 config: Optional[Union['Config', VectorDBConfig]] = None,
                 db_path: Optional[str] = None,
                 embedding_model: Optional[str] = None):
        """
        Initialize VectorManager with flexible configuration

        Args:
            config: Legacy Config object or VectorDBConfig object
            db_path: Override database path (for workspace-specific embeddings)
            embedding_model: Override embedding model
        """
        self.config = config
        self.client = None
        self.embedding_model = None

        # Determine configuration values
        self._setup_config(config, db_path, embedding_model)

        # Initialize components
        self._initialize_components()

    def _setup_config(self, config, db_path, embedding_model):
        """Setup configuration from various sources"""
        # Handle different config types
        if hasattr(config, 'ai'):  # Legacy Config object
            self.db_path = db_path or config.ai.chroma_persist_directory
            self.embedding_model_name = embedding_model or config.ai.embeddings_model
        elif isinstance(config, VectorDBConfig):  # New config type
            self.db_path = db_path or config.db_path or "data/vectordb"
            self.embedding_model_name = embedding_model or config.embedding_model
        else:  # No config or basic parameters
            self.db_path = db_path or "data/vectordb"
            self.embedding_model_name = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"

    def _initialize_components(self):
        """Initialize ChromaDB client and embedding model"""
        try:
            # Initialize ChromaDB
            persist_dir = Path(self.db_path)
            persist_dir.mkdir(parents=True, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Initialize embedding model
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"VectorManager initialized - DB: {persist_dir}, Model: {self.embedding_model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize vector components: {e}")
            raise

    def get_or_create_collection(self, collection_name: str,
                                 metadata: Optional[Dict[str, Any]] = None) -> 'Collection':
        """Get existing collection or create new one"""
        try:
            collection = self.client.get_collection(collection_name)
            logger.debug(f"Connected to existing collection: {collection_name}")
        except:
            collection_metadata = metadata or {"hnsw:space": "cosine"}
            collection = self.client.create_collection(
                name=collection_name,
                metadata=collection_metadata
            )
            logger.info(f"Created new collection: {collection_name}")

        return collection

    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection"""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            return False

    def list_collections(self) -> List[str]:
        """List all collections in the database"""
        try:
            collections = self.client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = self.embedding_model.encode(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    # ============================================================================
    # Generic Collection Operations
    # ============================================================================

    def add_documents(self, collection_name: str, documents: List[str],
                      metadatas: List[Dict[str, Any]], ids: List[str],
                      embeddings: Optional[List[List[float]]] = None) -> bool:
        """Add documents to a collection"""
        try:
            collection = self.get_or_create_collection(collection_name)

            # Generate embeddings if not provided
            if embeddings is None:
                embeddings = self.generate_embeddings(documents).tolist()

            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.debug(f"Added {len(documents)} documents to collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to add documents to {collection_name}: {e}")
            return False

    def search_collection(self, collection_name: str, query: str,
                          n_results: int = 10,
                          where: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search in a specific collection"""
        try:
            collection = self.get_or_create_collection(collection_name)

            # Generate embedding for query
            query_embedding = self.generate_embeddings([query])[0]

            # Search in collection
            results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    result = {
                        "id": doc_id,
                        "similarity_score": 1 - results['distances'][0][i],
                        "document": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i]
                    }
                    formatted_results.append(result)

            logger.debug(f"Collection {collection_name} search returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to search collection {collection_name}: {e}")
            return []

    def update_documents(self, collection_name: str, ids: List[str],
                         documents: Optional[List[str]] = None,
                         metadatas: Optional[List[Dict[str, Any]]] = None,
                         embeddings: Optional[List[List[float]]] = None) -> bool:
        """Update documents in a collection"""
        try:
            collection = self.get_or_create_collection(collection_name)

            # Generate embeddings if documents provided but embeddings not
            if documents and embeddings is None:
                embeddings = self.generate_embeddings(documents).tolist()

            collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings
            )

            logger.debug(f"Updated {len(ids)} documents in collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update documents in {collection_name}: {e}")
            return False

    def delete_documents(self, collection_name: str, ids: List[str]) -> bool:
        """Delete documents from a collection"""
        try:
            collection = self.get_or_create_collection(collection_name)
            collection.delete(ids=ids)
            logger.debug(f"Deleted {len(ids)} documents from collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete documents from {collection_name}: {e}")
            return False

    def get_collection_count(self, collection_name: str) -> int:
        """Get count of documents in a collection"""
        try:
            collection = self.get_or_create_collection(collection_name)
            return collection.count()
        except Exception as e:
            logger.error(f"Failed to get count for collection {collection_name}: {e}")
            return 0

    # ============================================================================
    # Jira-Specific Operations (for backward compatibility)
    # ============================================================================

    def add_issue_to_vector_db(self, issue: Dict[str, Any],
                               collection_name: str = "jira_issues") -> bool:
        """Add a Jira issue to the vector database"""
        try:
            # Create searchable text from issue
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
                "url": issue["url"],
                "document_type": "jira_issue"
            }

            return self.add_documents(
                collection_name=collection_name,
                documents=[searchable_text],
                metadatas=[metadata],
                ids=[issue["key"]]
            )

        except Exception as e:
            logger.error(f"Failed to add issue {issue.get('key', 'unknown')}: {e}")
            return False

    def add_issues_batch(self, issues: List[Dict[str, Any]],
                         collection_name: str = "jira_issues") -> Dict[str, Any]:
        """Add multiple issues to the vector database in batch"""
        try:
            if not issues:
                return {"success": True, "added": 0, "failed": 0}

            # Prepare batch data
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
                        "url": issue["url"],
                        "document_type": "jira_issue"
                    }

                    documents.append(searchable_text)
                    metadatas.append(metadata)
                    ids.append(issue["key"])

                except Exception as e:
                    logger.error(f"Failed to prepare issue {issue.get('key', 'unknown')}: {e}")
                    continue

            if not documents:
                return {"success": True, "added": 0, "failed": len(issues)}

            # Add to collection
            success = self.add_documents(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            if success:
                logger.info(f"Added {len(documents)} issues to vector database")
                return {
                    "success": True,
                    "added": len(documents),
                    "failed": len(issues) - len(documents)
                }
            else:
                return {"success": False, "error": "Batch add failed", "added": 0, "failed": len(issues)}

        except Exception as e:
            logger.error(f"Failed to add issues batch: {e}")
            return {"success": False, "error": str(e), "added": 0, "failed": len(issues)}

    def semantic_search(self, query: str, n_results: int = 10,
                        filters: Optional[Dict[str, Any]] = None,
                        collection_name: str = "jira_issues") -> List[Dict[str, Any]]:
        """Perform semantic search on Jira issues"""
        try:
            # Build where clause
            where_clause = {"document_type": "jira_issue"}
            if filters:
                for key, value in filters.items():
                    if value:
                        where_clause[key] = value

            results = self.search_collection(
                collection_name=collection_name,
                query=query,
                n_results=n_results,
                where=where_clause
            )

            # Reformat for Jira compatibility
            jira_results = []
            for result in results:
                jira_result = {
                    "issue_key": result["id"],
                    "similarity_score": result["similarity_score"],
                    "document": result["document"],
                    "metadata": result["metadata"]
                }
                jira_results.append(jira_result)

            return jira_results

        except Exception as e:
            logger.error(f"Failed to perform semantic search: {e}")
            return []

    # ============================================================================
    # Codebase Operations
    # ============================================================================

    def index_codebase(self, codebase_path: str, collection_name: str,
                       file_patterns: Optional[List[str]] = None,
                       exclude_patterns: Optional[List[str]] = None,
                       force_rebuild: bool = False,
                       chunk_size: int = 1000,
                       chunk_overlap: int = 200) -> Dict[str, Any]:
        """
        Index codebase files into vector database

        Args:
            codebase_path: Path to the codebase
            collection_name: Name of the collection to store embeddings
            file_patterns: File patterns to include (default: common code files)
            exclude_patterns: Patterns to exclude (default: common ignore patterns)
            force_rebuild: Whether to rebuild the entire collection
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            Statistics about the indexing operation
        """
        if file_patterns is None:
            file_patterns = [
                # Programming languages
                '*.py', '*.java', '*.kt', '*.kts',
                '*.js', '*.ts', '*.jsx', '*.tsx',
                '*.c', '*.cpp', '*.h', '*.hpp',
                '*.cs', '*.php', '*.rb', '*.go',
                '*.rust', '*.scala', '*.clj',

                # Configuration and data files
                '*.xml', '*.json', '*.yaml', '*.yml',
                '*.toml', '*.ini', '*.conf', '*.cfg',
                '*.properties', '*.env',

                # Build files
                '*.gradle', '*.gradle.kts', 'pom.xml',
                'Dockerfile', 'docker-compose.yml',
                'package.json', 'requirements.txt',

                # Web files
                '*.html', '*.css', '*.scss', '*.less',
                '*.vue', '*.svelte',

                # Database
                '*.sql',

                # Documentation
                '*.md', '*.rst', '*.txt'
            ]

        if exclude_patterns is None:
            exclude_patterns = [
                # Build artifacts and dependencies
                '*/node_modules/*', '*/__pycache__/*', '*/venv/*', '*/env/*',
                '*/build/*', '*/dist/*', '*/target/*', '*/out/*',
                '*/bin/*', '*/obj/*', '*/.gradle/*',

                # Version control and IDE
                '*/.git/*', '*/.svn/*', '*/.hg/*',
                '*/.idea/*', '*/.vscode/*', '*/.eclipse/*',
                '*.iml', '*.iws', '*.ipr',

                # Temporary and cache
                '*/tmp/*', '*/temp/*', '*/.cache/*', '*/cache/*',
                '*.log', '*.tmp', '*.swp', '*~',

                # Generated files
                '*/generated/*', '*/gen/*',

                # Binary files
                '*.jar', '*.war', '*.ear', '*.zip', '*.tar.gz',
                '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx',
                '*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg', '*.ico'
            ]

        try:
            start_time = datetime.now()
            codebase_root = Path(codebase_path)

            if not codebase_root.exists():
                raise ValueError(f"Codebase path does not exist: {codebase_path}")

            # Clear collection if force rebuild
            if force_rebuild:
                self.delete_collection(collection_name)

            collection = self.get_or_create_collection(collection_name)

            files_processed = 0
            chunks_created = 0
            file_types = set()
            errors = []

            # Process files
            for file_path in codebase_root.rglob('*'):
                if not file_path.is_file():
                    continue

                # Convert to relative path for pattern matching
                relative_path = str(file_path.relative_to(codebase_root))

                # Check exclude patterns first
                if any(fnmatch.fnmatch(relative_path, pattern) or
                       fnmatch.fnmatch(str(file_path), pattern)
                       for pattern in exclude_patterns):
                    continue

                # Check include patterns
                if not any(fnmatch.fnmatch(file_path.name, pattern)
                           for pattern in file_patterns):
                    continue

                try:
                    # Read file content
                    content = self._read_file_safely(file_path)
                    if not content or len(content.strip()) == 0:
                        continue

                    # Create chunks
                    chunks = self._create_code_chunks(
                        content, file_path, chunk_size, chunk_overlap
                    )

                    if chunks:
                        file_extension = file_path.suffix or 'no_extension'
                        file_types.add(file_extension)

                        # Add chunks to collection
                        documents = [chunk['content'] for chunk in chunks]
                        metadatas = [chunk['metadata'] for chunk in chunks]
                        ids = [chunk['id'] for chunk in chunks]

                        success = self.add_documents(
                            collection_name=collection_name,
                            documents=documents,
                            metadatas=metadatas,
                            ids=ids
                        )

                        if success:
                            files_processed += 1
                            chunks_created += len(chunks)
                        else:
                            errors.append(f"Failed to add chunks for {relative_path}")

                except Exception as e:
                    error_msg = f"Error processing {relative_path}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue

            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()

            # Return statistics
            stats = {
                "total_files": files_processed,
                "total_chunks": chunks_created,
                "file_types": sorted(list(file_types)),
                "duration": duration,
                "errors": errors[:10],  # Limit errors shown
                "collection_name": collection_name,
                "codebase_path": str(codebase_root)
            }

            logger.info(f"Codebase indexing completed: {stats}")
            return stats

        except Exception as e:
            error_msg = f"Failed to index codebase: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "total_files": 0,
                "total_chunks": 0,
                "file_types": [],
                "duration": 0
            }

    def search_codebase(self, query: str, collection_name: str,
                        n_results: int = 10,
                        file_types: Optional[List[str]] = None,
                        file_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search codebase embeddings"""
        try:
            # Build where clause
            where_clause = {"document_type": "code_chunk"}

            if file_types:
                where_clause["file_type"] = {"$in": file_types}

            if file_paths:
                where_clause["file_path"] = {"$in": file_paths}

            results = self.search_collection(
                collection_name=collection_name,
                query=query,
                n_results=n_results,
                where=where_clause
            )

            # Reformat for codebase compatibility
            codebase_results = []
            for result in results:
                codebase_result = {
                    "chunk_id": result["id"],
                    "similarity_score": result["similarity_score"],
                    "content": result["document"],
                    "metadata": result["metadata"]
                }
                codebase_results.append(codebase_result)

            return codebase_results

        except Exception as e:
            logger.error(f"Failed to search codebase: {e}")
            return []

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def _read_file_safely(self, file_path: Path) -> Optional[str]:
        """Safely read file content with encoding detection"""
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # Skip very large files (>1MB)
                    if len(content) > 1_000_000:
                        logger.debug(f"Skipping large file: {file_path}")
                        return None
                    return content
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception:
                break

        logger.warning(f"Could not read file: {file_path}")
        return None

    def _create_code_chunks(self, content: str, file_path: Path,
                            chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """Create chunks from code content"""
        chunks = []

        if len(content) <= chunk_size:
            # Small file - single chunk
            chunk = {
                'id': f"{file_path.name}_chunk_0",
                'content': content,
                'metadata': {
                    'file_path': str(file_path),
                    'file_name': file_path.name,
                    'file_type': file_path.suffix,
                    'chunk_index': 0,
                    'chunk_type': self._determine_chunk_type(file_path),
                    'document_type': 'code_chunk',
                    'size': len(content)
                }
            }
            chunks.append(chunk)
        else:
            # Large file - multiple chunks
            start = 0
            chunk_index = 0

            while start < len(content):
                end = start + chunk_size
                chunk_content = content[start:end]

                # Try to break at line boundaries
                if end < len(content):
                    last_newline = chunk_content.rfind('\n')
                    if last_newline > chunk_size * 0.5:  # Don't break too early
                        chunk_content = chunk_content[:last_newline + 1]
                        end = start + last_newline + 1

                chunk = {
                    'id': f"{file_path.name}_chunk_{chunk_index}",
                    'content': chunk_content,
                    'metadata': {
                        'file_path': str(file_path),
                        'file_name': file_path.name,
                        'file_type': file_path.suffix,
                        'chunk_index': chunk_index,
                        'chunk_type': self._determine_chunk_type(file_path),
                        'document_type': 'code_chunk',
                        'size': len(chunk_content),
                        'start_char': start,
                        'end_char': end
                    }
                }
                chunks.append(chunk)

                # Move start position with overlap
                start = max(start + chunk_size - overlap, end)
                chunk_index += 1

        return chunks

    def _determine_chunk_type(self, file_path: Path) -> str:
        """Determine the type of code chunk based on file extension"""
        extension_map = {
            '.py': 'python',
            '.java': 'java',
            '.kt': 'kotlin',
            '.kts': 'kotlin-script',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'react',
            '.tsx': 'react-typescript',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.xml': 'xml',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sql': 'sql',
            '.sh': 'shell',
            '.dockerfile': 'docker',
            '.gradle': 'gradle',
            '.properties': 'properties'
        }

        return extension_map.get(file_path.suffix.lower(), 'text')

    def _create_searchable_text(self, issue: Dict[str, Any]) -> str:
        """Create searchable text from Jira issue"""
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

    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            collections = self.list_collections()

            stats = {
                "database_path": self.db_path,
                "embedding_model": self.embedding_model_name,
                "total_collections": len(collections),
                "collections": {}
            }

            # Get stats for each collection
            for collection_name in collections:
                try:
                    count = self.get_collection_count(collection_name)
                    stats["collections"][collection_name] = {
                        "document_count": count
                    }
                except:
                    stats["collections"][collection_name] = {
                        "document_count": 0,
                        "error": "Could not get count"
                    }

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}