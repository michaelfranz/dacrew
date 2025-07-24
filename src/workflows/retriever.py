# src/workflows/retriever.py
import os
from pathlib import Path
from rich.console import Console

console = Console()

EMBEDDINGS_DIR = Path(__file__).resolve().parents[2] / "workspace" / "embeddings"

def list_available_embeddings() -> list[str]:
    """
    List all embedding sources in workspace/embeddings.
    """
    if not EMBEDDINGS_DIR.exists():
        return []
    return [d.name for d in EMBEDDINGS_DIR.iterdir() if d.is_dir()]

def retrieve_context(issue_info: dict, top_n: int = 5) -> dict:
    """
    Retrieve relevant context from all available embeddings for the given issue.
    This function is currently mocked, but is structured for future integration
    with a vector database (e.g., Chroma, FAISS).
    """
    console.print(f"🔍 Retrieving context for issue [cyan]{issue_info['key']}[/cyan]...")
    console.print(f"📂 Searching embeddings in: {EMBEDDINGS_DIR}")

    embeddings_to_use = os.getenv("GEN_EMBEDDINGS", "codebase,docs,issues").split(",")
    embeddings_to_use = [e.strip() for e in embeddings_to_use if e.strip()]

    available_embeddings = list_available_embeddings()
    context = {}

    for embedding_name in embeddings_to_use:
        if embedding_name not in available_embeddings:
            console.print(f"⚠️ Embedding '{embedding_name}' not found in {EMBEDDINGS_DIR}", style="yellow")
            continue

        embedding_path = EMBEDDINGS_DIR / embedding_name
        console.print(f"📡 Querying embedding: [green]{embedding_name}[/green]")

        # For now, we mock retrieval:
        context[embedding_name] = mock_query_embedding(embedding_path, issue_info, top_n)

    if not context:
        console.print("⚠️ No relevant context found. Proceeding with minimal information.", style="yellow")

    return context

def mock_query_embedding(embedding_path: Path, issue_info: dict, top_n: int) -> list[str]:
    """
    Placeholder for querying an embedding vector store.
    """
    # In future, this will use a vector similarity search
    # (e.g., via FAISS, ChromaDB, or OpenAI's API).
    return [
        f"Mocked relevant snippet {i+1} from {embedding_path.name} for issue '{issue_info['title']}'"
        for i in range(top_n)
    ]