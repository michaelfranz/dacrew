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
def git_commit_and_push(message: str, branch: str) -> str:
    """Commit changes and push to the remote repository."""


@tool("GitStatus")
def git_status() -> str:
    """Get current git status including modified files."""


@tool("GitDiff")
def git_diff(file_path: str = "") -> str:
    """Show differences in modified files."""