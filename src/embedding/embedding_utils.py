import hashlib
import shutil
from pathlib import Path

from rich.console import Console

console = Console()

def _clean_directory(directory: Path, name: str):
    if not directory.exists() or not any(directory.iterdir()):
        console.print(f"⚠️ No {name} embeddings found to clean.", style="yellow")
        return

    try:
        shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)  # Recreate the empty directory
        console.print(f"✅ {name.capitalize()} embeddings cleaned successfully.", style="green")
    except Exception as e:
        console.print(f"❌ Failed to clean {name} embeddings: {e}", style="red")

import fnmatch


def _get_files(base_path, include_patterns, exclude_patterns):
    all_files = []
    for root, dirs, files in os.walk(base_path):
        for file in files:
            rel_path = Path(root, file).relative_to(base_path)
            # Include check
            if not any(fnmatch.fnmatch(str(rel_path), pat) for pat in include_patterns):
                continue
            # Exclude check
            if any(fnmatch.fnmatch(str(rel_path), pat) for pat in exclude_patterns):
                continue
            all_files.append(rel_path)
    return all_files


def _hash_file(path: Path) -> str:
    """Generate a hash of the file contents (for incremental updates)."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()
