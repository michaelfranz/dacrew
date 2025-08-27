from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import faiss
import numpy as np
import requests
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from .config import AppConfig, CodebaseConfig, DocumentsConfig, EmbeddingConfig, ProjectConfig


class EmbeddingManager:
    """Manages embedding generation, storage, and retrieval for projects."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.model = SentenceTransformer(config.embedding.model)
        self.workspace_path = Path(config.embedding.workspace_path)
        self.workspace_path.mkdir(exist_ok=True)

    def get_project_workspace(self, project_id: str) -> Path:
        """Get the workspace path for a specific project."""
        return self.workspace_path / project_id

    def get_embedding_file(self, project_id: str, source_type: str) -> Path:
        """Get the embedding file path for a project and source type."""
        workspace = self.get_project_workspace(project_id)
        return workspace / f"{source_type}_embeddings.npz"

    def get_metadata_file(self, project_id: str, source_type: str) -> Path:
        """Get the metadata file path for a project and source type."""
        workspace = self.get_project_workspace(project_id)
        return workspace / f"{source_type}_metadata.json"

    def should_update_embeddings(self, project_id: str, source_type: str, 
                               update_frequency_hours: int) -> bool:
        """Check if embeddings need to be updated based on frequency."""
        metadata_file = self.get_metadata_file(project_id, source_type)
        if not metadata_file.exists():
            return True
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            last_update = datetime.fromisoformat(metadata.get('last_update', '1970-01-01'))
            return datetime.now() - last_update > timedelta(hours=update_frequency_hours)
        except (json.JSONDecodeError, KeyError):
            return True

    async def update_project_embeddings(self, project_id: str) -> None:
        """Update embeddings for a project's codebase and documents."""
        project = self.config.get_project(project_id)
        if not project:
            return

        workspace = self.get_project_workspace(project_id)
        workspace.mkdir(exist_ok=True)

        # Update codebase embeddings
        if project.codebase:
            if self.should_update_embeddings(project_id, "codebase", 
                                           project.codebase.update_frequency_hours):
                await self._update_codebase_embeddings(project_id, project.codebase)

        # Update document embeddings
        if project.documents:
            if self.should_update_embeddings(project_id, "documents", 
                                           project.documents.update_frequency_hours):
                await self._update_document_embeddings(project_id, project.documents)

    async def _update_codebase_embeddings(self, project_id: str, codebase_config: CodebaseConfig) -> None:
        """Update embeddings for a codebase repository."""
        print(f"Updating codebase embeddings for project {project_id}")
        
        # Clone or update repository
        repo_path = await self._get_repository(codebase_config.repo, codebase_config.branch)
        
        # Extract and process files
        files = self._get_codebase_files(repo_path, codebase_config.include_patterns, 
                                       codebase_config.exclude_patterns)
        
        # Generate embeddings
        texts, metadata = await self._process_codebase_files(files)
        if texts:
            embeddings = self.model.encode(texts, show_progress_bar=True)
            self._save_embeddings(project_id, "codebase", embeddings, metadata)

    async def _update_document_embeddings(self, project_id: str, documents_config: DocumentsConfig) -> None:
        """Update embeddings for documents."""
        print(f"Updating document embeddings for project {project_id}")
        
        texts = []
        metadata = []
        
        # Process local files
        for path in documents_config.paths:
            if os.path.exists(path):
                file_texts, file_metadata = await self._process_document_file(path)
                texts.extend(file_texts)
                metadata.extend(file_metadata)
        
        # Process URLs
        for url in documents_config.urls:
            url_texts, url_metadata = await self._process_document_url(url)
            texts.extend(url_texts)
            metadata.extend(url_metadata)
        
        if texts:
            embeddings = self.model.encode(texts, show_progress_bar=True)
            self._save_embeddings(project_id, "documents", embeddings, metadata)

    async def _get_repository(self, repo_url: str, branch: str) -> Path:
        """Clone or update a git repository."""
        repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
        repo_path = Path(tempfile.gettempdir()) / f"dacrew_repo_{repo_hash}"
        
        if repo_path.exists():
            # Update existing repository
            subprocess.run(["git", "-C", str(repo_path), "fetch"], check=True)
            subprocess.run(["git", "-C", str(repo_path), "checkout", branch], check=True)
            subprocess.run(["git", "-C", str(repo_path), "pull"], check=True)
        else:
            # Clone new repository
            subprocess.run(["git", "clone", "-b", branch, repo_url, str(repo_path)], check=True)
        
        return repo_path

    def _get_codebase_files(self, repo_path: Path, include_patterns: List[str], 
                           exclude_patterns: List[str]) -> List[Path]:
        """Get list of files to process from codebase."""
        files = []
        
        for pattern in include_patterns:
            for file_path in repo_path.rglob(pattern.replace("**/*", "*")):
                if file_path.is_file():
                    # Check if file should be excluded
                    relative_path = file_path.relative_to(repo_path)
                    excluded = any(Path(pattern.replace("**", "*")).match(str(relative_path)) 
                                 for pattern in exclude_patterns)
                    if not excluded:
                        files.append(file_path)
        
        return files

    async def _process_codebase_files(self, files: List[Path]) -> Tuple[List[str], List[Dict]]:
        """Process codebase files and extract text chunks."""
        texts = []
        metadata = []
        
        for file_path in tqdm(files, desc="Processing codebase files"):
            try:
                # Read file content
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Split into chunks
                chunks = self._split_text(content, self.config.embedding.chunk_size, 
                                       self.config.embedding.chunk_overlap)
                
                for i, chunk in enumerate(chunks):
                    texts.append(chunk)
                    metadata.append({
                        'source': 'codebase',
                        'file': str(file_path),
                        'chunk_index': i,
                        'chunk_size': len(chunk)
                    })
                    
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        return texts, metadata

    async def _process_document_file(self, file_path: str) -> Tuple[List[str], List[Dict]]:
        """Process a local document file."""
        texts = []
        metadata = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            chunks = self._split_text(content, self.config.embedding.chunk_size, 
                                   self.config.embedding.chunk_overlap)
            
            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                metadata.append({
                    'source': 'document',
                    'file': file_path,
                    'chunk_index': i,
                    'chunk_size': len(chunk)
                })
                
        except Exception as e:
            print(f"Error processing document file {file_path}: {e}")
        
        return texts, metadata

    async def _process_document_url(self, url: str) -> Tuple[List[str], List[Dict]]:
        """Process a document URL."""
        texts = []
        metadata = []
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.text
            
            chunks = self._split_text(content, self.config.embedding.chunk_size, 
                                   self.config.embedding.chunk_overlap)
            
            for i, chunk in enumerate(chunks):
                texts.append(chunk)
                metadata.append({
                    'source': 'document',
                    'url': url,
                    'chunk_index': i,
                    'chunk_size': len(chunk)
                })
                
        except Exception as e:
            print(f"Error processing document URL {url}: {e}")
        
        return texts, metadata

    def _split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - chunk_overlap
        
        return chunks

    def _save_embeddings(self, project_id: str, source_type: str, 
                        embeddings: np.ndarray, metadata: List[Dict]) -> None:
        """Save embeddings and metadata to disk."""
        embedding_file = self.get_embedding_file(project_id, source_type)
        metadata_file = self.get_metadata_file(project_id, source_type)
        
        # Save embeddings
        np.savez_compressed(embedding_file, embeddings=embeddings)
        
        # Save metadata
        metadata_with_timestamp = {
            'last_update': datetime.now().isoformat(),
            'embedding_count': len(embeddings),
            'chunks': metadata
        }
        with open(metadata_file, 'w') as f:
            json.dump(metadata_with_timestamp, f, indent=2)

    def get_relevant_context(self, project_id: str, query: str, 
                           source_types: List[str] = None, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant context for a query from project embeddings."""
        if source_types is None:
            source_types = ["codebase", "documents"]
        
        results = []
        
        for source_type in source_types:
            embedding_file = self.get_embedding_file(project_id, source_type)
            metadata_file = self.get_metadata_file(project_id, source_type)
            
            if not embedding_file.exists() or not metadata_file.exists():
                continue
            
            # Load embeddings and metadata
            embeddings_data = np.load(embedding_file)
            embeddings = embeddings_data['embeddings']
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Encode query
            query_embedding = self.model.encode([query])
            
            # Calculate similarities
            similarities = np.dot(embeddings, query_embedding.T).flatten()
            
            # Get top-k results
            top_indices = np.argsort(similarities)[-top_k:][::-1]
            
            for idx in top_indices:
                chunk_metadata = metadata['chunks'][idx]
                results.append({
                    'source_type': source_type,
                    'similarity': float(similarities[idx]),
                    'content': chunk_metadata.get('content', ''),
                    'metadata': chunk_metadata
                })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
