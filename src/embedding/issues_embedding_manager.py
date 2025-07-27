"""
Internal manager for Jira issues embeddings.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console

from .abstract_embedding_manager import AbstractEmbeddingManager, EmbeddingResult
from .codebase_embedding_manager import config
from .embedding_utils import _clean_directory
from ..jira_client import JiraClient

console = Console()


class IssuesEmbeddingManager(AbstractEmbeddingManager):
    def __init__(self, project_key: str, issues_dir: Path):
        self.project_key = project_key
        self.issues_dir = issues_dir
        self.issues_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_model = "text-embedding-3-small"
        self.embedding_fn = OpenAIEmbeddings(model=self.embedding_model, api_key=config.ai.openai_api_key)

    def index(self, force: bool = False):
        """
        Index the project issues using configuration include/exclude patterns.
        """
        issues_cfg = config.embedding.issues
        manifest_path = self.issues_dir / "manifest.json"
        old_hashes = _load_manifest(manifest_path, force)

        changed_issues, new_hashes = _collect_issues(
            include_statuses=issues_cfg.include_statuses,
            exclude_statuses=issues_cfg.exclude_statuses,
            old_hashes=old_hashes,
            force=force
        )

        # Embed changed/new issues
        if changed_issues:
            console.print(f"📄 Indexing {len(changed_issues)} changed/new issues...", style="cyan")
            _embed_changed_issues(self.issues_dir, changed_issues, self.embedding_model)
        else:
            console.print("✅ No changes detected.", style="green")

        # Save new manifest
        _save_manifest(manifest_path, new_hashes, config.jira.url, config.jira.jira_project_key)
        console.print(f"Manifest updated at: {manifest_path}", style="cyan")

    def clean(self):
        _clean_directory(self.issues_dir, "issues")

    def stats(self):
        """
        Return statistics for the issues embeddings.
        """
        manifest_path = self.issues_dir / "manifest.json"
        if not manifest_path.exists():
            return {"files_indexed": 0}
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        return {"files_indexed": len(manifest.get("files", []))}

    def query(self, query: str, top_k: int = 5, debug: bool = False) -> List[EmbeddingResult]:
        store = self._load_vector_store()
        hits = store.similarity_search_with_score(query, k=top_k * 2)  # fetch more candidates
        results = [
            EmbeddingResult(
                content=doc.page_content,
                source="issues",
                reference=doc.metadata.get("key", ""),
                similarity=-score
            )
            for doc, score in hits
        ]

        # Re-rank results
        results = _rerank_by_keyword(query, results)
        final_results = results[:top_k]

        if debug:
            console.print(f"[DEBUG] Query: {query}", style="cyan")
            for r in final_results:
                console.print(f"[{r.similarity:.3f}] {r.reference} -> {r.content[:120]}...", style="dim")

        return final_results


    def _load_vector_store(self) -> FAISS:
        return FAISS.load_local(
            self.issues_dir.as_posix(),
            self.embedding_fn,
            allow_dangerous_deserialization=True
        )


def _rerank_by_keyword(query: str, results: List[EmbeddingResult], boost: float = 0.2) -> List[EmbeddingResult]:
    """
    Re-rank results by keyword overlap with the query.
    boost: How much to increase the similarity score per keyword match.
    """
    import re
    query_terms = re.findall(r"\w+", query.lower())
    for r in results:
        content_lower = r.content.lower()
        keyword_matches = sum(1 for term in query_terms if term in content_lower)
        r.similarity += keyword_matches * boost
    return sorted(results, key=lambda x: x.similarity, reverse=True)


def _collect_issues(
        include_statuses: Optional[List[str]] = None,
        exclude_statuses: Optional[List[str]] = None,
        old_hashes: Optional[Dict[str, str]] = None,
        force: bool = False
) -> Tuple[List[Dict], Dict[str, str]]:
    if old_hashes is None:
        old_hashes = {}
    if include_statuses is None:
        include_statuses = []
    if exclude_statuses is None:
        exclude_statuses = []

    changed_issues = []

    jira_config = config.jira
    jira_client = JiraClient(jira_config)
    jql = f"project = {jira_config.jira_project_key} order by updated DESC"

    console.print(f"🔍 Searching with JQL: {jql}", style="dim")
    fetched_issues = jira_client.search_issues(jql, max_results=jira_config.fetch_limit)

    new_hashes = {}
    for issue in fetched_issues:
        status = issue.get("status", "")
        if include_statuses and status not in include_statuses:
            continue
        if exclude_statuses and status in exclude_statuses:
            continue

        issue_str = f"{issue['summary']} {issue.get('description', '')} {status}"
        issue_hash = hashlib.sha1(issue_str.encode("utf-8")).hexdigest()

        new_hashes[issue["key"]] = issue_hash

        if force or old_hashes.get(issue["key"]) != issue_hash:
            changed_issues.append(issue)

    return changed_issues, new_hashes


def _embed_changed_issues(issues_dir: Path, changed_issues: List[Dict], embedding_model: str):
    """
    Embed the changed issues and store in FAISS.
    """
    documents = []
    for issue in changed_issues:
        fields = [
            f"Issue {issue['key']} - {issue['summary']}",
            f"Status: {issue['status']}"
        ]
        if issue.get('priority'):
            fields.append(f"Priority: {issue['priority']}")
        if issue.get('assignee'):
            fields.append(f"Assignee: {issue['assignee']}")
        if issue.get('description'):
            fields.append(issue['description'])

        text = "\n\n".join(fields)
        documents.append(Document(page_content=text, metadata={"key": issue["key"]}))

    # Split only if text is long
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = []
    for doc in documents:
        if len(doc.page_content) > 1000:
            chunks.extend(splitter.split_documents([doc]))
        else:
            chunks.append(doc)

    if not chunks:
        console.print("[yellow]No chunks created from issues.[/]")
        return

    embeddings = OpenAIEmbeddings(model=embedding_model, api_key=config.ai.openai_api_key)
    try:
        db = FAISS.load_local(str(issues_dir), embeddings)
        db.add_documents(chunks)
    except Exception:
        db = FAISS.from_documents(chunks, embeddings)

    db.save_local(str(issues_dir))


def _load_manifest(manifest_path: Path, force: bool) -> Dict[str, str]:
    if manifest_path.exists() and not force:
        with open(manifest_path, "r", encoding="utf-8") as f:
            old_manifest = json.load(f)
        console.print(f"🔄 Found existing manifest: {manifest_path}", style="cyan")
        return old_manifest.get("issue-hashes", {})
    else:
        console.print("🆕 No manifest found or forced indexing. Full re-indexing.", style="cyan")
        return {}


def _save_manifest(manifest_path: Path, hashes: Dict[str, str], jira_url: str, jira_project_key: str):
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "issue-hashes": hashes,
            "jira-url": jira_url,
            "jira-project-key": jira_project_key,
            "modified": datetime.now().isoformat()
        }, f, indent=2)