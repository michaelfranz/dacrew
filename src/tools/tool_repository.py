# tools/tool_registry.py
from tools.git_tools import clone_or_pull_repo, create_git_branch, git_commit_and_push, git_status, git_diff

ALL_TOOLS = {
    "UpdateGitRepo": clone_or_pull_repo,
    "CreateGitBranch": create_git_branch,
    "GitCommitAndPush": git_commit_and_push,
    "GitStatus": git_status,
    "GitDiff": git_diff,
}

def resolve_tools(tool_names: list[str]):
    return [ALL_TOOLS[name] for name in tool_names if name in ALL_TOOLS]
