"""Vector Database Manager for JIRA AI Assistant"""
import fnmatch
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
        self.codebase_collection = None
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

            # Initialize or get JIRA issues collection
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

            # Initialize or get codebase collection
            codebase_collection_name = "codebase"
            try:
                self.codebase_collection = self.client.get_collection(codebase_collection_name)
                logger.info(f"Connected to existing codebase collection: {codebase_collection_name}")

            except:
                self.codebase_collection = self.client.create_collection(
                    name=codebase_collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new codebase collection: {codebase_collection_name}")

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

    def search_codebase(self, query: str, n_results: int = 10,
                       file_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Perform semantic search on codebase"""
        try:
            # Generate embedding for query
            query_embedding = self.generate_embeddings([query])[0]

            # Prepare where clause for filtering by file types
            where_clause = {}
            if file_types:
                where_clause["chunk_type"] = {"$in": file_types}

            # Search in codebase collection
            results = self.codebase_collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, chunk_id in enumerate(results['ids'][0]):
                    result = {
                        "chunk_id": chunk_id,
                        "similarity_score": 1 - results['distances'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i]
                    }
                    formatted_results.append(result)

            logger.info(f"Codebase search returned {len(formatted_results)} results for query: {query}")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to perform codebase search: {e}")
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
        """Get statistics about the vector database collections"""
        try:
            jira_count = self.collection.count()
            codebase_count = self.codebase_collection.count()

            return {
                "jira_issues": jira_count,
                "codebase_chunks": codebase_count,
                "collection_names": {
                    "jira": self.collection.name,
                    "codebase": self.codebase_collection.name
                },
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

    def index_codebase(self, codebase_path: str,
                      file_patterns: List[str] = None,
                      exclude_patterns: List[str] = None) -> Dict[str, Any]:
        """Index codebase files into vector database"""
        if file_patterns is None:
            file_patterns = [
                # Programming languages
                '*.py', '*.java', '*.kt', '*.kts',  # Python, Java, Kotlin
                '*.js', '*.ts', '*.jsx', '*.tsx',   # JavaScript/TypeScript

                # Configuration files
                '*.xml', '*.json', '*.yaml', '*.yml',  # Config formats
                'requirements.txt', # Python library dependencies
                '*.toml', '*.ini', '*.conf', '*.cfg',  # More config formats
                '*.properties', '*.env',  # Properties and environment files

                # Build and project files
                '*.gradle', '*.gradle.kts',  # Gradle files
                '*.pom.xml', 'build.gradle*',  # Maven and Gradle
                'CMakeLists.txt', 'Makefile', 'makefile',  # Build systems
                'Dockerfile', 'docker-compose.yml',  # Docker

                # Web technologies
                '*.html', '*.css', '*.scss', '*.less',  # Web frontend
                '*.vue', '*.svelte', '*.angular.ts',  # Frontend frameworks

                # Database and ORM
                '*.sql', '*.hbm.xml',  # SQL and Hibernate mapping files

                # Documentation that might contain code
                '*.md', '*.rst',  # Markdown and reStructuredText with code blocks
            ]

        if exclude_patterns is None:
            exclude_patterns = [
                # Dependencies and build artifacts
                '*/node_modules/*', '*/__pycache__/*', '*/venv/*', '*/env/*',
                '*/.git/*', '*/.svn/*', '*/.hg/*',  # Version control
                '*/build/*', '*/dist/*', '*/target/*', '*/out/*',  # Build outputs
                '*/bin/*', '*/obj/*', '*/.gradle/*',  # More build artifacts

                # IDE and editor files
                '*/.idea/*', '*/.vscode/*', '*/.eclipse/*',
                '*.iml', '*.iws', '*.ipr',  # IntelliJ files

                # Temporary and cache files
                '*/tmp/*', '*/temp/*', '*/.cache/*', '*/cache/*',
                '*.log', '*.tmp', '*.swp', '*~',  # Temporary files

                # Generated files
                '*/generated/*', '*/gen/*', '**/generated/**',

                # Large data files that shouldn't be indexed
                '*.jar', '*.war', '*.ear', '*.zip', '*.tar.gz',  # Archives
                '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx',  # Binary docs
                '*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg', '*.ico',  # Images
            ]

        try:
            codebase_root = Path(codebase_path)
            if not codebase_root.exists():
                raise ValueError(f"Codebase path does not exist: {codebase_path}")

            files_processed = 0
            chunks_created = 0

            # Clear existing codebase data
            try:
                self.codebase_collection.delete()
                self.codebase_collection = self.client.create_collection(
                    name="codebase",
                    metadata={"hnsw:space": "cosine"}
                )
            except:
                pass

            # Walk through codebase
            for file_path in codebase_root.rglob('*'):
                if not file_path.is_file():
                    continue

                # Check if file matches include patterns
                if not any(fnmatch.fnmatch(str(file_path), pattern) for pattern in file_patterns):
                    continue

                # Check if file matches exclude patterns
                if any(fnmatch.fnmatch(str(file_path), pattern) for pattern in exclude_patterns):
                    continue

                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    if not content.strip():
                        continue

                    # Create chunks from file content with file type awareness
                    chunks = self._create_code_chunks(content, str(file_path))

                    # Add chunks to vector database
                    if chunks:
                        self._add_code_chunks(chunks)
                        chunks_created += len(chunks)

                    files_processed += 1

                    if files_processed % 10 == 0:
                        logger.info(f"Processed {files_processed} files, created {chunks_created} chunks")

                except Exception as e:
                    logger.warning(f"Failed to process file {file_path}: {e}")
                    continue

            logger.info(f"Codebase indexing completed: {files_processed} files, {chunks_created} chunks")
            return {
                "success": True,
                "files_processed": files_processed,
                "chunks_created": chunks_created
            }

        except Exception as e:
            logger.error(f"Failed to index codebase: {e}")
            return {"success": False, "error": str(e)}

    def _create_code_chunks(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Create semantic chunks from code content with file type awareness"""
        chunks = []
        lines = content.split('\n')
        file_extension = Path(file_path).suffix.lower()

        # File type specific chunking strategies
        current_chunk = []
        current_line_start = 1
        chunk_size_limit = 50  # Default chunk size

        # Adjust chunking based on file type
        if file_extension in ['.xml', '.html']:
            chunk_size_limit = 30  # Smaller chunks for XML/HTML due to verbosity
        elif file_extension in ['.json', '.yaml', '.yml']:
            chunk_size_limit = 20  # Even smaller for config files
        elif file_extension in ['.md', '.rst']:
            chunk_size_limit = 100  # Larger chunks for documentation

        for i, line in enumerate(lines):
            current_chunk.append(line)

            # Create chunk based on file type and content structure
            should_chunk = False

            if file_extension in ['.py']:
                # Python-specific chunking
                should_chunk = (len(current_chunk) >= chunk_size_limit or
                                line.strip().startswith('def ') or
                                line.strip().startswith('class ') or
                                line.strip().startswith('async def '))

            elif file_extension in ['.java', '.kt', '.kts']:
                # Java/Kotlin-specific chunking
                should_chunk = (len(current_chunk) >= chunk_size_limit or
                                line.strip().startswith('public class ') or
                                line.strip().startswith('class ') or
                                line.strip().startswith('interface ') or
                                line.strip().startswith('fun ') or  # Kotlin functions
                                line.strip().startswith('private fun ') or
                                line.strip().startswith('public fun '))

            elif file_extension in ['.js', '.ts']:
                # JavaScript/TypeScript-specific chunking
                should_chunk = (len(current_chunk) >= chunk_size_limit or
                                line.strip().startswith('function ') or
                                line.strip().startswith('class ') or
                                line.strip().startswith('const ') and '= (' in line or
                                line.strip().startswith('export '))

            elif file_extension in ['.xml']:
                # XML-specific chunking (by major elements)
                should_chunk = (len(current_chunk) >= chunk_size_limit or
                                ('<hibernate-mapping' in line) or
                                ('<entity' in line) or
                                ('<configuration' in line) or
                                ('</hibernate-mapping>' in line) or
                                ('</configuration>' in line))

            elif file_extension in ['.gradle', '.gradle.kts']:
                # Gradle-specific chunking
                should_chunk = (len(current_chunk) >= chunk_size_limit or
                                line.strip().startswith('dependencies ') or
                                line.strip().startswith('plugins ') or
                                line.strip().startswith('android ') or
                                line.strip().startswith('task '))

            else:
                # Generic chunking for other file types
                should_chunk = (len(current_chunk) >= chunk_size_limit)

            # Also chunk at end of file
            if i == len(lines) - 1:
                should_chunk = True

            if should_chunk and current_chunk:
                chunk_content = '\n'.join(current_chunk)
                if chunk_content.strip():  # Only add non-empty chunks
                    # Determine chunk type based on file extension
                    chunk_type = self._determine_chunk_type(file_extension)

                    chunks.append({
                        'content': chunk_content,
                        'metadata': {
                            'file_path': file_path,
                            'chunk_type': chunk_type,
                            'file_extension': file_extension,
                            'line_start': current_line_start,
                            'line_end': i + 1
                        }
                    })

                current_chunk = []
                current_line_start = i + 2

        return chunks

    def _determine_chunk_type(self, file_extension: str) -> str:
        """Determine the type of code chunk based on file extension"""
        type_mapping = {
            '.py': 'python',
            '.java': 'java',
            '.kt': 'kotlin',
            '.kts': 'kotlin-script',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.xml': 'xml-config',
            '.json': 'json-config',
            '.yaml': 'yaml-config',
            '.yml': 'yaml-config',
            '.gradle': 'gradle-build',
            '.gradle.kts': 'gradle-kotlin',
            '.properties': 'properties-config',
            '.sql': 'sql-query',
            '.md': 'documentation',
            '.rst': 'documentation'
        }

        return type_mapping.get(file_extension, 'code')

    def _add_code_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Add code chunks to the codebase collection"""
        try:
            if not chunks:
                return

            # Prepare data for batch insertion
            documents = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                documents.append(chunk['content'])
                metadatas.append(chunk['metadata'])
                # Create unique ID for chunk
                chunk_id = f"{chunk['metadata']['file_path']}:{chunk['metadata']['line_start']}-{chunk['metadata']['line_end']}"
                ids.append(chunk_id)

            # Generate embeddings for all chunks
            embeddings = self.generate_embeddings(documents)

            # Add to codebase collection
            self.codebase_collection.add(
                embeddings=embeddings.tolist(),
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

            logger.debug(f"Added {len(chunks)} code chunks to vector database")

        except Exception as e:
            logger.error(f"Failed to add code chunks: {e}")
            raise