"""Simple codebase management for workspace operations - Git and filesystem only"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import platform
import hashlib

from .exceptions import WorkspaceError, GitCloneError

# ============================================================================
# Cross-Platform Link Management
# ============================================================================

class CrossPlatformLinkManager:
    """Manages symbolic links across different platforms"""

    @staticmethod
    def is_windows():
        """Check if running on Windows"""
        return platform.system().lower() == 'windows'

    def can_create_symlinks(self) -> bool:
        """Check if symbolic links can be created on this system"""
        if not self.is_windows():
            return True  # Unix-like systems generally support symlinks

        try:
            # On Windows, try creating a test symlink to check permissions
            test_dir = Path.cwd() / 'temp_symlink_test'
            test_target = Path.cwd() / 'temp_symlink_target'

            # Create target
            test_target.mkdir(exist_ok=True)

            # Try creating symlink
            test_dir.symlink_to(test_target)

            # Clean up
            test_dir.unlink()
            test_target.rmdir()

            return True
        except (OSError, NotImplementedError):
            return False

    def create_link(self, link_path: Path, target_path: Path) -> str:
        """
        Create a link to target directory
        Returns: 'symlink', 'junction', or 'none'
        """
        try:
            # Remove existing link if it exists
            if link_path.exists() or link_path.is_symlink():
                if link_path.is_dir():
                    if self.is_windows() and link_path.is_symlink():
                        link_path.unlink()
                    else:
                        link_path.unlink()
                else:
                    link_path.unlink()

            if self.is_windows():
                return self._create_windows_link(link_path, target_path)
            else:
                # Unix-like systems: create symbolic link
                link_path.symlink_to(target_path)
                return 'symlink'

        except Exception:
            return 'none'

    def _create_windows_link(self, link_path: Path, target_path: Path) -> str:
        """Create Windows-specific link (junction or symlink)"""
        try:
            # First try symbolic link (requires admin or developer mode)
            link_path.symlink_to(target_path)
            return 'symlink'
        except (OSError, NotImplementedError):
            try:
                # Fallback to junction using mklink
                result = subprocess.run([
                    'cmd', '/c', 'mklink', '/J',
                    str(link_path), str(target_path)
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    return 'junction'
                else:
                    return 'none'
            except:
                return 'none'

# ============================================================================
# Simplified Codebase Manager - Git and filesystem operations only
# ============================================================================

class SimpleCodebaseManager:
    """Manager for repository operations with current selection - No embedding dependencies"""

    def __init__(self):
        self.workspace_root = Path.cwd() / "workspace"
        self.repos_dir = self.workspace_root / "repos"
        self.current_link = self.workspace_root / "current"
        self.info_file = self.workspace_root / "repositories.json"
        self.link_manager = CrossPlatformLinkManager()

        # Ensure workspace directory exists
        self.workspace_root.mkdir(exist_ok=True)
        self.repos_dir.mkdir(exist_ok=True)

    # ============================================================================
    # Repository Information Management
    # ============================================================================

    def has_active_codebase(self) -> bool:
        """Check if there's an active codebase"""
        try:
            if self.current_link.exists():
                target = self._resolve_current_link()
                return target is not None and target.exists()
            return False
        except:
            return False

    def get_repositories_info(self) -> Dict[str, Any]:
        """Get information about all repositories"""
        try:
            if not self.info_file.exists():
                return {"repositories": {}, "current": None}

            with open(self.info_file, 'r') as f:
                return json.load(f)
        except:
            return {"repositories": {}, "current": None}

    def get_current_repository_info(self) -> Optional[Dict[str, Any]]:
        """Get current repository information"""
        repos_info = self.get_repositories_info()
        current_repo = repos_info.get("current")

        if current_repo and current_repo in repos_info["repositories"]:
            return repos_info["repositories"][current_repo].copy()

        return None

    def get_repository_info(self, repo_identifier: str) -> Optional[Dict[str, Any]]:
        """Get specific repository information by ID or name"""
        repos_info = self.get_repositories_info()

        # Find repository by ID or name
        for repo_id, repo_info in repos_info["repositories"].items():
            if repo_id == repo_identifier or repo_info["repo_name"] == repo_identifier:
                return repo_info.copy()

        return None

    def get_codebase_path(self) -> Optional[Path]:
        """Get path to current codebase"""
        # First try the 'current' link
        if self.current_link.exists():
            return self._resolve_current_link()

        # Fallback: get current repo from info file
        current_info = self.get_current_repository_info()
        if current_info:
            actual_path = Path(current_info['actual_path'])
            if actual_path.exists():
                return actual_path

        return None

    def _resolve_current_link(self) -> Optional[Path]:
        """Resolve the current symlink to actual path"""
        try:
            if self.current_link.is_symlink():
                return self.current_link.resolve()
            elif self.current_link.is_dir():
                return self.current_link
        except:
            pass
        return None

    # ============================================================================
    # Repository Management
    # ============================================================================

    def add_codebase(self, repo_url: str, branch: Optional[str] = None,
                     shallow: bool = True,
                     progress_callback: Optional[callable] = None) -> Tuple[Path, str]:
        """
        Add a codebase from git repository
        Returns: (path, detected_branch)
        """
        if not self._is_valid_git_url(repo_url):
            raise ValueError(f"Invalid git URL: {repo_url}")

        # Generate unique repository ID
        repo_id = self._generate_repo_id(repo_url)
        repo_name = self._extract_repo_name(repo_url)
        target_path = self.repos_dir / repo_id

        # Get current repositories info
        repos_info = self.get_repositories_info()

        # Check if this repository already exists
        existing_repo = None
        for rid, info in repos_info["repositories"].items():
            if info["repo_url"] == repo_url:
                existing_repo = rid
                break

        if existing_repo:
            # Repository already exists, just switch to it
            if progress_callback:
                progress_callback("Repository already exists, switching to it...")

            return self._switch_to_existing_repository(existing_repo, repos_info)

        # Clone new repository with branch detection
        if progress_callback:
            progress_callback("Cloning repository...")

        detected_branch = self._clone_with_branch_detection(repo_url, branch, shallow, target_path)

        # Create repository info
        repo_info = {
            'repo_url': repo_url,
            'repo_name': repo_name,
            'repo_id': repo_id,
            'branch': detected_branch,
            'actual_path': str(target_path.absolute()),
            'cloned_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'shallow': shallow,
            'platform': platform.system()
        }

        # Add to repositories info and make current
        repos_info["repositories"][repo_id] = repo_info
        repos_info["current"] = repo_id

        # Create/update 'current' link
        link_status = self.link_manager.create_link(self.current_link, target_path)
        repo_info['symlink_status'] = link_status

        # Save updated repositories info
        repos_info["repositories"][repo_id] = repo_info
        self._save_repositories_info(repos_info)

        if progress_callback:
            progress_callback("Repository cloning completed!")

        return target_path, detected_branch

    def _switch_to_existing_repository(self, repo_id: str, repos_info: Dict[str, Any]) -> Tuple[Path, str]:
        """Switch to an existing repository"""
        repos_info["current"] = repo_id

        # Update current symlink
        existing_path = Path(repos_info["repositories"][repo_id]["actual_path"])
        link_status = self.link_manager.create_link(self.current_link, existing_path)

        # Update symlink status
        repos_info["repositories"][repo_id]["symlink_status"] = link_status
        repos_info["repositories"][repo_id]["last_accessed"] = datetime.now().isoformat()

        self._save_repositories_info(repos_info)

        return existing_path, repos_info["repositories"][repo_id]["branch"]

    def switch_codebase(self, repo_identifier: str) -> bool:
        """Switch to a different repository by repo_id or repo_name"""
        repos_info = self.get_repositories_info()

        # Find repository by ID or name
        target_repo_id = None
        for repo_id, repo_info in repos_info["repositories"].items():
            if repo_id == repo_identifier or repo_info["repo_name"] == repo_identifier:
                target_repo_id = repo_id
                break

        if not target_repo_id:
            raise WorkspaceError(f"Repository '{repo_identifier}' not found")

        # Check if target repository still exists
        target_path = Path(repos_info["repositories"][target_repo_id]["actual_path"])
        if not target_path.exists():
            raise WorkspaceError(f"Repository directory not found: {target_path}")

        # Switch to repository
        self._switch_to_existing_repository(target_repo_id, repos_info)

        return True

    def list_repositories(self) -> List[Dict[str, Any]]:
        """List all available repositories"""
        repos_info = self.get_repositories_info()
        current_repo = repos_info.get("current")

        repositories = []
        for repo_id, repo_info in repos_info["repositories"].items():
            repo_copy = repo_info.copy()
            repo_copy["is_current"] = (repo_id == current_repo)
            repo_copy["exists"] = Path(repo_info["actual_path"]).exists()

            # Calculate repository size
            repo_copy["size_mb"] = self._calculate_repo_size(Path(repo_info["actual_path"]))

            repositories.append(repo_copy)

        return repositories

    def remove_repository(self, repo_identifier: str, delete_files: bool = False) -> bool:
        """Remove a repository from workspace"""
        repos_info = self.get_repositories_info()

        # Find repository
        target_repo_id = None
        for repo_id, repo_info in repos_info["repositories"].items():
            if repo_id == repo_identifier or repo_info["repo_name"] == repo_identifier:
                target_repo_id = repo_id
                break

        if not target_repo_id:
            raise WorkspaceError(f"Repository '{repo_identifier}' not found")

        repo_info = repos_info["repositories"][target_repo_id]

        # If this is the current repository, clear the current link
        if repos_info.get("current") == target_repo_id:
            if self.current_link.exists():
                if self.current_link.is_symlink():
                    self.current_link.unlink()
                elif self.current_link.is_dir():
                    shutil.rmtree(self.current_link)
            repos_info["current"] = None

        # Delete files if requested
        if delete_files:
            repo_path = Path(repo_info["actual_path"])
            if repo_path.exists():
                shutil.rmtree(repo_path)

        # Remove from repositories info
        del repos_info["repositories"][target_repo_id]

        # Save updated info
        self._save_repositories_info(repos_info)

        return True

    def update_codebase(self, progress_callback: Optional[callable] = None) -> bool:
        """Update current codebase (git pull)"""
        current_info = self.get_current_repository_info()
        if not current_info:
            raise WorkspaceError("No active codebase to update")

        codebase_path = Path(current_info['actual_path'])
        if not codebase_path.exists():
            raise WorkspaceError("Codebase directory not found")

        try:
            if progress_callback:
                progress_callback("Updating repository...")

            # Git pull
            result = subprocess.run(
                ["git", "pull", "origin", current_info['branch']],
                cwd=codebase_path,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Update timestamp
                repos_info = self.get_repositories_info()
                current_repo = repos_info.get("current")
                if current_repo:
                    repos_info["repositories"][current_repo]['last_updated'] = datetime.now().isoformat()
                    self._save_repositories_info(repos_info)

                if progress_callback:
                    progress_callback("Repository update completed!")

                return True
            else:
                raise WorkspaceError(f"Git pull failed: {result.stderr}")

        except Exception as e:
            raise WorkspaceError(f"Update failed: {str(e)}")

    # ============================================================================
    # Workspace Management
    # ============================================================================

    def clear_workspace(self):
        """Clear the entire workspace (all repositories)"""
        try:
            # Remove the 'current' link/directory
            if self.current_link.exists():
                if self.current_link.is_symlink():
                    self.current_link.unlink()
                elif self.current_link.is_dir():
                    shutil.rmtree(self.current_link)

            # Remove all repository directories
            if self.repos_dir.exists():
                shutil.rmtree(self.repos_dir)
                self.repos_dir.mkdir(exist_ok=True)

            # Remove repositories info file
            if self.info_file.exists():
                self.info_file.unlink()

        except Exception as e:
            raise WorkspaceError(f"Failed to clear workspace: {str(e)}")

    def cleanup_workspace(self) -> Dict[str, List[str]]:
        """Clean up orphaned files and inconsistencies"""
        cleaned = {
            "missing_repositories": [],
            "orphaned_symlinks": []
        }

        # Check for missing repositories
        repos_info = self.get_repositories_info()
        for repo_id, repo_info in repos_info["repositories"].items():
            repo_path = Path(repo_info["actual_path"])
            if not repo_path.exists():
                cleaned["missing_repositories"].append(repo_id)

        # Check for orphaned current link
        if self.current_link.exists():
            resolved = self._resolve_current_link()
            if not resolved or not resolved.exists():
                cleaned["orphaned_symlinks"].append("current")

        return cleaned

    def get_workspace_status(self) -> Dict[str, Any]:
        """Get comprehensive workspace status"""
        current_info = self.get_current_repository_info()
        repos_info = self.get_repositories_info()

        # Basic status
        if not current_info:
            return {
                'has_codebase': False,
                'total_repositories': len(repos_info["repositories"]),
                'platform': platform.system()
            }

        # Calculate size
        size_mb = 0
        actual_path = Path(current_info['actual_path'])
        if actual_path.exists():
            size_mb = self._calculate_repo_size(actual_path)

        # Check current path
        current_path = "Not accessible"
        if self.current_link.exists():
            current_path = str(self.current_link)

        return {
            'has_codebase': True,
            'repo_name': current_info['repo_name'],
            'repo_url': current_info['repo_url'],
            'branch': current_info['branch'],
            'size_mb': size_mb,
            'cloned_at': current_info['cloned_at'],
            'last_updated': current_info['last_updated'],
            'platform': current_info['platform'],
            'current_path': current_path,
            'actual_path': current_info['actual_path'],
            'symlink_status': current_info.get('symlink_status', 'unknown'),
            'shallow': current_info.get('shallow', False),
            'total_repositories': len(repos_info["repositories"])
        }

    # ============================================================================
    # Utility Methods
    # ============================================================================

    def _save_repositories_info(self, repos_info: Dict[str, Any]):
        """Save repositories information to file"""
        with open(self.info_file, 'w') as f:
            json.dump(repos_info, f, indent=2)

    def _generate_repo_id(self, repo_url: str) -> str:
        """Generate a unique repository ID from URL"""
        # Create a short hash from the URL for uniqueness
        url_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
        repo_name = self._extract_repo_name(repo_url)
        return f"{repo_name}_{url_hash}"

    def _extract_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL"""
        try:
            # Handle different URL formats
            if repo_url.endswith('.git'):
                repo_url = repo_url[:-4]

            # Extract name from various URL formats
            if '/' in repo_url:
                name = repo_url.split('/')[-1]

                # Clean up common prefixes/suffixes
                if name.startswith('git@'):
                    name = name.split(':')[-1]

                return name if name else "repository"

            return "repository"
        except:
            return "repository"

    def _is_valid_git_url(self, url: str) -> bool:
        """Basic validation of git URL"""
        try:
            # Basic patterns for git URLs
            patterns = [
                'https://github.com/',
                'https://gitlab.com/',
                'https://bitbucket.org/',
                'git@github.com:',
                'git@gitlab.com:',
                'git@bitbucket.org:',
                'https://',  # Generic HTTPS
                'git://',    # Git protocol
                'ssh://',    # SSH protocol
            ]

            url_lower = url.lower()
            return any(url_lower.startswith(pattern) for pattern in patterns)

        except:
            return False

    def _calculate_repo_size(self, repo_path: Path) -> float:
        """Calculate repository size in MB"""
        try:
            if not repo_path.exists():
                return 0.0

            size_bytes = sum(
                f.stat().st_size
                for f in repo_path.rglob('*')
                if f.is_file()
            )
            return round(size_bytes / (1024 * 1024), 1)
        except:
            return 0.0

    def _clone_with_branch_detection(self, repo_url: str, branch: Optional[str],
                                     shallow: bool, target_path: Path) -> str:
        """Clone repository with intelligent branch detection"""

        # If branch is specified, only try that branch
        if branch:
            self._clone_repository(repo_url, branch, shallow, target_path)
            return branch

        # Auto-detection: try common branch names in order
        branches_to_try = ['main', 'master', 'develop', 'dev']
        last_error = None

        for branch_name in branches_to_try:
            try:
                self._clone_repository(repo_url, branch_name, shallow, target_path)
                return branch_name  # Success!
            except GitCloneError as e:
                last_error = e
                # Check if this is a "branch not found" error
                if ("Remote branch" in str(e) and "not found" in str(e)) or \
                        ("fatal: Remote branch" in str(e)):
                    # Clean up partial clone attempt
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    continue  # Try next branch
                else:
                    # Different error (network, permissions, etc.), don't retry
                    raise

        # All branches failed - get list of available branches and provide helpful error
        available_branches = self._get_remote_branches(repo_url)

        if available_branches:
            raise GitCloneError(
                f"Could not find any of the default branches {branches_to_try}. "
                f"Available branches: {available_branches}. "
                f"Use --branch to specify the correct branch name."
            )
        else:
            raise GitCloneError(
                f"Could not find any of the default branches {branches_to_try}. "
                f"Use --branch to specify the correct branch name. "
                f"Last error: {last_error}"
            )

    def _get_remote_branches(self, repo_url: str) -> list:
        """Get list of available remote branches (best effort)"""
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--heads", repo_url],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                branches = []
                for line in result.stdout.strip().split('\n'):
                    if line and '\trefs/heads/' in line:
                        branch_name = line.split('\trefs/heads/')[-1]
                        branches.append(branch_name)
                return branches[:10]  # Limit to first 10 branches
        except:
            pass

        return []

    def _clone_repository(self, repo_url: str, branch: str, shallow: bool,
                          target_path: Path):
        """Clone git repository to specific path"""

        # Remove existing directory if it exists
        if target_path.exists():
            shutil.rmtree(target_path)

        try:
            clone_args = ["git", "clone"]

            if shallow:
                clone_args.extend(["--depth", "1"])

            clone_args.extend([
                "--branch", branch,
                repo_url,
                str(target_path)
            ])

            # Set environment to skip large files initially
            env = os.environ.copy()
            env['GIT_LFS_SKIP_SMUDGE'] = '1'

            result = subprocess.run(
                clone_args,
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for large repos
            )

            if result.returncode != 0:
                raise GitCloneError(f"Failed to clone repository: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise GitCloneError("Git clone operation timed out")
        except Exception as e:
            raise GitCloneError(f"Unexpected error during clone: {str(e)}")