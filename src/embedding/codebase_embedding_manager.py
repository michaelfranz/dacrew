"""
Internal manager for codebase embeddings.
Not intended to be used directly outside the embedding package.
"""

import fnmatch
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console

from .abstract_embedding_manager import AbstractEmbeddingManager, EmbeddingResult, _load_vector_store
from .embedding_utils import _clean_directory, _hash_file
from .hybrid_query_mixin import HybridQueryMixin
from config import Config

console = Console()
config = Config.load()

class CodebaseEmbeddingManager(AbstractEmbeddingManager, HybridQueryMixin):
    BATCH_SIZE = 50  # Number of files to embed in one batch (for memory safety)

    def __init__(self, project_key: str, codebase_dir: Path):
        self.project_key = project_key
        self.codebase_dir = codebase_dir
        self.codebase_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_fn = OpenAIEmbeddings(model="text-embedding-3-small", api_key=config.ai.openai_api_key)

    # ---------------------------------------------------------
    # Public Methods
    # ---------------------------------------------------------
    def index(self, force: bool = False):
        """
        Index the project codebase using configuration include/exclude patterns and paths.
        """
        codebase_cfg = config.embedding.codebase
        base_path = Path(codebase_cfg.path).resolve()

        manifest_path = self.codebase_dir / "manifest.json"
        old_hashes = _load_manifest(manifest_path, force)

        changed_files, files = self._collect_files(
            base_path=base_path,
            include_paths=[Path(p).resolve() for p in getattr(codebase_cfg, "include_paths", [])],
            exclude_paths=[Path(p).resolve() for p in getattr(codebase_cfg, "exclude_paths", [])],
            include_patterns=codebase_cfg.include_patterns,
            exclude_patterns=codebase_cfg.exclude_patterns,
            old_hashes=old_hashes,
            force=force
        )

        # Embed changed/new files
        if changed_files:
            console.print(f"📄 Indexing {len(changed_files)} changed/new files...", style="cyan")
            self._embed_changed_files(changed_files)
        else:
            console.print("✅ No changes detected.", style="green")

        # Save new manifest
        _save_manifest(manifest_path, files, base_path)
        console.print(f"Manifest updated at: {manifest_path}", style="cyan")

    def clean(self):
        _clean_directory(self.codebase_dir, "codebase")

    def stats(self):
        """
        Return statistics for the codebase embeddings.
        """
        manifest_path = self.codebase_dir / "manifest.json"
        if not manifest_path.exists():
            return {"files_indexed": 0}
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        return {"files_indexed": len(manifest.get("files", {}))}

    def query(self, query: str, top_k: int = 5, debug: bool = False) -> List[EmbeddingResult]:
        store = _load_vector_store(self.codebase_dir, self.embedding_fn)
        hits = store.similarity_search_with_score(query, k=top_k * 2)

        results = [
            EmbeddingResult(
                content=doc.page_content,
                source="codebase",
                reference=doc.metadata.get("source", ""),
                similarity=-score  # Convert distance to similarity (higher = better)
            )
            for doc, score in hits
        ]

        # Apply keyword re-ranking
        results = self._rerank_by_keyword(query, results)
        final_results = results[:top_k]

        if debug:
            self._debug_print_results(query, final_results)

        return final_results


    @staticmethod
    def _collect_files(
            base_path: Path,
            include_paths: List[Path],
            exclude_paths: List[Path],
            include_patterns: List[str],
            exclude_patterns: List[str],
            old_hashes: Dict[str, str],
            force: bool
    ) -> Tuple[List[Path], Dict[str, str]]:
        changed_files = []
        new_hashes = {}

        for root, _, filenames in os.walk(base_path):
            root_path = Path(root).resolve()

            for filename in filenames:
                file_path = root_path / filename

                if not _is_included(
                        file_path=file_path,
                        base_path=base_path,
                        include_paths=include_paths,
                        exclude_paths=exclude_paths,
                        include_patterns=include_patterns,
                        exclude_patterns=exclude_patterns
                ):
                    continue

                rel_path = os.path.relpath(file_path, base_path)
                file_hash = _hash_file(file_path)
                new_hashes[rel_path] = file_hash

                if force or old_hashes.get(rel_path) != file_hash:
                    changed_files.append(file_path)

        return changed_files, new_hashes

    def _embed_changed_files(self, changed_files: List[Path]):
        """
        Embed changed files in batches.
        """
        try:
            db = FAISS.load_local(str(self.codebase_dir), self.embedding_fn)
        except Exception:
            db = None

        for i in range(0, len(changed_files), self.BATCH_SIZE):
            batch = changed_files[i:i + self.BATCH_SIZE]
            documents = []
            for path in batch:
                try:
                    loader = TextLoader(path, encoding='utf-8')
                    docs = loader.load()
                    # Add reference to metadata for later display
                    for doc in docs:
                        doc.metadata["source"] = str(path)
                    documents.extend(docs)
                except Exception as e:
                    console.print(f"[yellow]Warning:[/] Could not load file {path}: {e}")

            if not documents:
                continue

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " ", ""]
            )
            chunks = splitter.split_documents(documents)

            if db:
                db.add_documents(chunks)
            else:
                db = FAISS.from_documents(chunks, self.embedding_fn)

        if db:
            db.save_local(str(self.codebase_dir))

def _is_included(
        file_path: Path,
        base_path: Path,
        include_paths: List[Path],
        exclude_paths: List[Path],
        include_patterns: List[str],
        exclude_patterns: List[str]
) -> bool:
    """
    Check if a file should be included based on include/exclude paths and patterns.
    """
    # Exclude entire directory or file
    if any(file_path.is_relative_to(ex_path) for ex_path in exclude_paths):
        return False

    # Restrict to include_paths if defined
    if include_paths and not any(file_path.is_relative_to(inc_path) for inc_path in include_paths):
        return False

    # Match patterns (relative to base)
    rel_path = os.path.relpath(file_path, base_path)
    return _matches_patterns(rel_path, include_patterns, exclude_patterns)


def _matches_patterns(rel_path: str, include_patterns: List[str], exclude_patterns: List[str]) -> bool:
    """
    Check if the relative path matches include/exclude patterns.
    """
    if include_patterns and not any(fnmatch.fnmatch(rel_path, pat) for pat in include_patterns):
        return False
    if exclude_patterns and any(fnmatch.fnmatch(rel_path, pat) for pat in exclude_patterns):
        return False
    return True


def _load_manifest(manifest_path: Path, force: bool) -> Dict[str, str]:
    """
    Loads the manifest file and returns a mapping of file -> hash.
    """
    if manifest_path.exists() and not force:
        with open(manifest_path, "r", encoding="utf-8") as f:
            old_manifest = json.load(f)
        console.print(f"🔄 Found existing manifest: {manifest_path}", style="cyan")
        old_hashes = old_manifest.get("file-hashes", {})
        return old_hashes
    else:
        console.print("🆕 No manifest found or forced indexing. Full re-indexing.", style="cyan")
        return {}


def _save_manifest(manifest_path: Path, hashes: Dict[str, str], base_path: Path):
    """
    Saves the manifest file.
    """
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "file-hashes": hashes,
            "base-path": str(base_path),
            "modified": datetime.now().isoformat()
        }, f, indent=2)
