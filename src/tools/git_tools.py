import os
import subprocess
from crewai.tools import tool

@tool("UpdateGitRepo")
def clone_or_pull_repo(repo_url: str, local_dir: str) -> str:
    """
    Clone a Git repository to a local directory or pull the latest changes if the repo already exists.
    """
    try:
        if os.path.exists(local_dir):
            result = subprocess.run(
                ["git", "-C", local_dir, "pull"],
                capture_output=True,
                text=True,
                check=True
            )
            return f"Pulled latest changes:\n{result.stdout}"
        else:
            result = subprocess.run(
                ["git", "clone", repo_url, local_dir],
                capture_output=True,
                text=True,
                check=True
            )
            return f"Cloned repository:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Git command failed:\n{e.stderr}"


@tool("CreateGitBranch")
def create_git_branch(local_dir: str, base_branch: str, new_branch: str) -> str:
    """
    Create a new Git branch from an existing base branch.
    The repository is assumed to be the current working directory.
    """
    try:
        # Check out the base branch and pull the latest
        subprocess.run(["git", "-C", local_dir, "checkout", base_branch], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", local_dir, "pull", "origin", base_branch], check=True, capture_output=True, text=True)

        # Create and switch to the new branch
        result = subprocess.run(["git", "-C", local_dir, "checkout", "-b", new_branch], check=True, capture_output=True, text=True)

        return f"Created new branch '{new_branch}' from '{base_branch}':\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Git command failed:\n{e.stderr}"
    
    
@tool("GitCommitAndPush")
def git_commit_and_push(message: str, branch: str, local_dir: str = ".") -> str:
    """Commit changes and push to the remote repository."""
    try:
        subprocess.run(["git", "-C", local_dir, "add", "."], check=True, capture_output=True, text=True)
        subprocess.run(["git", "-C", local_dir, "commit", "-m", message], check=True, capture_output=True, text=True)
        result = subprocess.run(
            ["git", "-C", local_dir, "push", "-u", "origin", branch],
            check=True,
            capture_output=True,
            text=True,
        )
        return f"Committed and pushed to {branch}:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Git command failed:\n{e.stderr}"


@tool("GitStatus")
def git_status(local_dir: str = ".") -> str:
    """Get current git status including modified files."""
    try:
        result = subprocess.run(
            ["git", "-C", local_dir, "status", "--short"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Git command failed:\n{e.stderr}"


@tool("GitDiff")
def git_diff(file_path: str = "", local_dir: str = ".") -> str:
    """Show differences in modified files."""
    try:
        cmd = ["git", "-C", local_dir, "diff"]
        if file_path:
            cmd.append(file_path)
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Git command failed:\n{e.stderr}"
