import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Dict

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


def _hash_file(file_path: Path) -> str:
    """Return SHA1 hash of a file."""
    h = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):  # 64KB chunks
            h.update(chunk)
    return h.hexdigest()


def _hash_file(file_path: Path) -> str:
    """Return SHA1 hash of a file."""
    h = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):  # 64KB chunks
            h.update(chunk)
    return h.hexdigest()


