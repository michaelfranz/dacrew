"""CLI interface for DaCrew - AI-powered Development Crew"""

import typer
from rich.console import Console
from typing import Optional
from pathlib import Path

# Initialize Typer app and Rich console
app = typer.Typer(
    help="🚀 DaCrew - AI-powered development crew, your team of software development assistants"
)
console = Console()

# ============================================================================
# Test Connection Command (Top-level)
# ============================================================================

@app.command("test-connection")
def test_jira_connection():
    """🔗 Test JIRA connection"""
    try:
        from .config import Config
        from .jira_client import JIRAClient

        console.print("🔗 Testing JIRA connection...", style="cyan")

        config = Config.load()

        # Validate configuration
        if not config.jira.url:
            console.print("❌ JIRA URL not configured", style="red")
            console.print("Please set JIRA_URL in your .env file", style="yellow")
            return

        if not config.jira.username:
            console.print("❌ JIRA username not configured", style="red")
            console.print("Please set JIRA_USERNAME in your .env file", style="yellow")
            return

        if not config.jira.api_token:
            console.print("❌ JIRA API token not configured", style="red")
            console.print("Please set JIRA_API_TOKEN in your .env file", style="yellow")
            return

        # Test connection
        client = JIRAClient(config)

        if client.test_connection():
            console.print("✅ JIRA connection successful!", style="green")
            console.print(f"Connected to: {config.jira.url}", style="dim")
            console.print(f"Username: {config.jira.username}", style="dim")
        else:
            console.print("❌ JIRA connection failed!", style="red")
            console.print("Please check your credentials and try again", style="yellow")

    except Exception as e:
        console.print(f"❌ Error testing connection: {str(e)}", style="red")

# ============================================================================
# Issues Command Group
# ============================================================================

issues_app = typer.Typer(help="🎫 Manage JIRA issues and tickets")
app.add_typer(issues_app, name="issues")

@issues_app.command("list")
def list_issues(
        project: str = typer.Option(None, "--project", "-p", help="Project key"),
        status: str = typer.Option(None, "--status", "-s", help="Filter by status"),
        assignee: str = typer.Option(None, "--assignee", "-a", help="Filter by assignee"),
        limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of issues to show")
):
    """📋 List JIRA issues"""
    try:
        from .config import Config
        from .jira_client import JIRAClient

        config = Config.load()
        client = JIRAClient(config)

        # Build JQL query
        jql_parts = []

        if project:
            jql_parts.append(f"project = {project}")
        elif config.project.default_project_key:
            jql_parts.append(f"project = {config.project.default_project_key}")

        if status:
            jql_parts.append(f"status = '{status}'")

        if assignee:
            jql_parts.append(f"assignee = '{assignee}'")

        jql = " AND ".join(jql_parts) if jql_parts else "order by updated DESC"

        console.print(f"🔍 Searching with JQL: {jql}", style="dim")
        issues = client.search_issues(jql, max_results=limit)

        if not issues:
            console.print("No issues found", style="yellow")
            return

        # Display issues in a table
        from rich.table import Table

        table = Table(title="JIRA Issues")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Summary", style="white")
        table.add_column("Status", style="green")
        table.add_column("Assignee", style="blue")
        table.add_column("Updated", style="magenta")

        for issue in issues:
            table.add_row(
                issue['key'],
                issue['summary'][:50] + "..." if len(issue['summary']) > 50 else issue['summary'],
                issue['status'],
                issue['assignee'],
                issue['updated'][:10]  # Just the date part
            )

        console.print(table)

    except Exception as e:
        console.print(f"❌ Error listing issues: {str(e)}", style="red")

@issues_app.command("show")
def show_issue(issue_key: str):
    """🔍 Show detailed information about a specific issue"""
    try:
        from .config import Config
        from .jira_client import JIRAClient

        config = Config.load()
        client = JIRAClient(config)

        issue = client.get_issue(issue_key)

        if not issue:
            console.print(f"❌ Issue {issue_key} not found", style="red")
            return

        from rich.panel import Panel
        from rich.table import Table

        # Main issue info
        info_table = Table.grid(padding=1)
        info_table.add_column(style="cyan", justify="right")
        info_table.add_column(style="white")

        info_table.add_row("Key:", issue['key'])
        info_table.add_row("Summary:", issue['summary'])
        info_table.add_row("Status:", issue['status'])
        info_table.add_row("Priority:", issue['priority'])
        info_table.add_row("Assignee:", issue['assignee'])
        info_table.add_row("Reporter:", issue['reporter'])
        info_table.add_row("Project:", issue['project'])
        info_table.add_row("Type:", issue['issue_type'])
        info_table.add_row("Created:", issue['created'][:10])
        info_table.add_row("Updated:", issue['updated'][:10])
        info_table.add_row("URL:", issue['url'])

        console.print(Panel(info_table, title=f"Issue {issue_key}", border_style="blue"))

        # Description
        if issue['description']:
            console.print(Panel(issue['description'], title="Description", border_style="green"))

    except Exception as e:
        console.print(f"❌ Error showing issue: {str(e)}", style="red")

@issues_app.command("create")
def create_issue(
        summary: str,
        description: str = typer.Option("", "--description", "-d", help="Issue description"),
        project: str = typer.Option(None, "--project", "-p", help="Project key"),
        issue_type: str = typer.Option("Task", "--type", "-t", help="Issue type"),
        priority: str = typer.Option(None, "--priority", help="Priority"),
        assignee: str = typer.Option(None, "--assignee", "-a", help="Assignee username")
):
    """✨ Create a new JIRA issue"""
    try:
        from .config import Config
        from .jira_client import JIRAClient

        config = Config.load()
        client = JIRAClient(config)

        # Use default project if not specified
        if not project:
            project = config.project.default_project_key

        if not project:
            console.print("❌ No project specified and no default project configured", style="red")
            console.print("Use --project flag or set DEFAULT_PROJECT_KEY in .env", style="yellow")
            return

        # Prepare additional fields
        kwargs = {}
        if priority:
            kwargs['priority'] = {'name': priority}
        if assignee:
            kwargs['assignee'] = {'name': assignee}

        console.print(f"🚀 Creating issue in project {project}...", style="cyan")

        issue = client.create_issue(
            project_key=project,
            summary=summary,
            description=description,
            issue_type=issue_type,
            **kwargs
        )

        if issue:
            console.print(f"✅ Successfully created issue: {issue['key']}", style="green")
            console.print(f"URL: {issue['url']}", style="dim")
        else:
            console.print("❌ Failed to create issue", style="red")

    except Exception as e:
        console.print(f"❌ Error creating issue: {str(e)}", style="red")

@issues_app.command("test-connection")
def test_connection_issues():
    """🔗 Test JIRA connection (issues context)"""
    # Reuse the main test-connection logic
    test_jira_connection()

# ============================================================================
# Codebase Command Group
# ============================================================================

codebase_app = typer.Typer(help="📁 Manage repository codebases")
app.add_typer(codebase_app, name="codebase")

@codebase_app.command("init")
def init_workspace():
    """🚀 Initialize workspace structure"""
    try:
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        workspace_dir = project_root / "workspace"
        repos_dir = workspace_dir / "repos"
        embeddings_dir = workspace_dir / "embeddings"

        console.print("🚀 Initializing workspace structure...", style="cyan")

        # Create directories
        workspace_dir.mkdir(exist_ok=True)
        repos_dir.mkdir(exist_ok=True)
        embeddings_dir.mkdir(exist_ok=True)

        # Create .gitkeep files to track empty directories
        for dir_path in [repos_dir, embeddings_dir]:
            gitkeep = dir_path / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.write_text("# This file ensures the directory is tracked by git\n")

        console.print("✅ Workspace structure initialized!", style="green")
        console.print(f"📁 Workspace root: {workspace_dir}", style="dim")
        console.print(f"📁 Repositories: {repos_dir}", style="dim")
        console.print(f"📁 Embeddings: {embeddings_dir}", style="dim")

        console.print("\n💡 Next steps:", style="bold yellow")
        console.print("1. Clone repositories into workspace/repos/", style="white")
        console.print("   cd workspace/repos && git clone <repo-url>", style="dim")
        console.print("2. Scan repositories: dacrew codebase scan", style="white")
        console.print("3. Index for AI search: dacrew codebase index --repo <name>", style="white")

    except Exception as e:
        console.print(f"❌ Error initializing workspace: {str(e)}", style="red")

@codebase_app.command("add")
def add_repository(
    repo_url: str,
    name: str = typer.Option(None, "--name", "-n", help="Custom name for the repository (note: currently not implemented)"),
    branch: str = typer.Option(None, "--branch", "-b", help="Specific branch to clone"),
    shallow: bool = typer.Option(True, "--shallow/--full", help="Perform shallow clone (default: True)"),
    auto_index: bool = typer.Option(True, "--index/--no-index", help="Automatically create embeddings after adding (default: True)")
):
    """➕ Add a new repository and optionally index it"""
    try:
        # Import required managers
        from .codebase.codebase_manager import SimpleCodebaseManager
        from .embedding.embedding_manager import EmbeddingManager
        
        console.print(f"🚀 Adding repository: {repo_url}", style="cyan")
        
        # Show warning if custom name was specified (not yet supported)
        if name:
            console.print("⚠️ Custom name parameter is not yet supported by the codebase manager", style="yellow")
            console.print("   Repository will use the default name from the URL", style="dim")
        
        # Initialize codebase manager
        codebase_manager = SimpleCodebaseManager()
        
        # Add the repository
        console.print("📥 Cloning repository...", style="yellow")
        
        def progress_callback(message):
            console.print(f"   {message}", style="dim")
        
        try:
            # Call the method with the correct parameters
            repo_path, detected_branch = codebase_manager.add_codebase(
                repo_url=repo_url,
                branch=branch,
                shallow=shallow,
                progress_callback=progress_callback
            )
            
            if not repo_path:
                console.print("❌ Failed to add repository", style="red")
                return
                
            console.print(f"✅ Successfully added repository to: {repo_path}", style="green")
            console.print(f"🌿 Branch: {detected_branch}", style="dim")
            
            # Get repository info to show more details
            repo_info = codebase_manager.get_current_repository_info()
            if repo_info:
                console.print(f"📝 Repository name: {repo_info['repo_name']}", style="dim")
                console.print(f"🆔 Repository ID: {repo_info['repo_id']}", style="dim")
                console.print(f"🎯 Set as current repository", style="green")
            
        except Exception as e:
            console.print(f"❌ Failed to clone repository: {str(e)}", style="red")
            return
        
        # Auto-index if requested
        if auto_index:
            console.print("\n🗂️ Creating embeddings for repository...", style="cyan")
            
            try:
                embedding_manager = EmbeddingManager()
                
                def embedding_progress_callback(message):
                    console.print(f"   {message}", style="dim")
                
                metadata = embedding_manager.create_embedding_for_current_repo(
                    progress_callback=embedding_progress_callback
                )
                
                console.print(f"✅ Embeddings created successfully!", style="green")
                console.print(f"📊 Indexed {metadata.get('total_files', 0)} files into {metadata.get('total_chunks', 0)} chunks", style="dim")
                
            except Exception as e:
                console.print(f"⚠️ Repository added but indexing failed: {str(e)}", style="yellow")
                console.print("💡 You can index later with: dacrew codebase index", style="dim")
        
        # Show next steps
        console.print("\n🎉 Repository setup complete!", style="bold green")
        console.print("\n💡 What you can do next:", style="bold yellow")
        if repo_info:
            console.print("• Scan the repository: dacrew codebase scan --repo " + repo_info['repo_name'], style="white")
        console.print("• Search the code: dacrew codebase search 'your query'", style="white")
        console.print("• List all repos: dacrew codebase list", style="white")
        console.print("• Show current repo: dacrew codebase current", style="white")
        
    except ImportError as e:
        console.print(f"❌ Missing required components: {str(e)}", style="red")
        console.print("💡 Make sure all codebase and embedding modules are properly set up", style="yellow")
    except Exception as e:
        console.print(f"❌ Error adding repository: {str(e)}", style="red")

@codebase_app.command("list")
def list_repositories():
    """📋 List repositories in workspace/repos"""
    try:
        # Get workspace/repos directory
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        repos_dir = project_root / "workspace" / "repos"

        if not repos_dir.exists():
            console.print("📁 workspace/repos directory doesn't exist", style="yellow")
            console.print("💡 It will be created when you run other commands", style="dim")
            return

        repos = [d for d in repos_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

        if not repos:
            console.print("📭 No repositories found in workspace/repos", style="yellow")
            console.print("💡 Clone repositories into this directory:", style="dim")
            console.print(f"   cd {repos_dir}", style="dim")
            console.print("   git clone <repo-url>", style="dim")
            return

        console.print(f"📋 Found {len(repos)} repositories in workspace/repos:", style="cyan")

        from rich.table import Table
        repo_table = Table()
        repo_table.add_column("Repository", style="cyan", no_wrap=True)
        repo_table.add_column("Type", style="green")
        repo_table.add_column("Size", style="magenta", justify="right")
        repo_table.add_column("Last Modified", style="yellow")

        for repo_dir in sorted(repos, key=lambda x: x.name.lower()):
            # Detect repo type
            repo_type = "📁 Directory"
            if (repo_dir / ".git").exists():
                repo_type = "🔄 Git Repository"
            elif (repo_dir / "package.json").exists():
                repo_type = "📦 Node.js Project"
            elif (repo_dir / "requirements.txt").exists() or (repo_dir / "pyproject.toml").exists():
                repo_type = "🐍 Python Project"
            elif (repo_dir / "pom.xml").exists():
                repo_type = "☕ Maven Project"
            elif (repo_dir / "Cargo.toml").exists():
                repo_type = "🦀 Rust Project"
            elif (repo_dir / "go.mod").exists():
                repo_type = "🐹 Go Project"

            # Calculate size
            try:
                size_bytes = sum(f.stat().st_size for f in repo_dir.rglob('*') if f.is_file())
                if size_bytes < 1024*1024:  # < 1MB
                    size_str = f"{size_bytes//1024}KB"
                elif size_bytes < 1024*1024*1024:  # < 1GB
                    size_str = f"{size_bytes//(1024*1024)}MB"
                else:
                    size_str = f"{size_bytes//(1024*1024*1024):.1f}GB"
            except:
                size_str = "Unknown"

            # Get last modified
            try:
                last_modified_timestamp = repo_dir.stat().st_mtime
                from datetime import datetime
                last_modified_date = datetime.fromtimestamp(last_modified_timestamp).strftime('%Y-%m-%d %H:%M')
            except:
                last_modified_date = "Unknown"

            repo_table.add_row(repo_dir.name, repo_type, size_str, last_modified_date)

        console.print(repo_table)
        console.print(f"\n💡 Use: dacrew codebase scan --repo <name> to analyze a specific repository", style="dim")

    except Exception as e:
        console.print(f"❌ Error listing repositories: {str(e)}", style="red")

@codebase_app.command("scan")
def scan_codebase(
        path: str = typer.Option(None, "--path", "-p", help="Path to scan (default: workspace/repos)"),
        repo: str = typer.Option(None, "--repo", "-r", help="Specific repository to scan"),
        exclude: str = typer.Option(".git,node_modules,__pycache__,.pytest_cache,.venv,venv", "--exclude", "-e", help="Comma-separated list of directories to exclude"),
        extensions: str = typer.Option("py,js,ts,java,cpp,c,h,rb,go,rs", "--extensions", "-x", help="Comma-separated list of file extensions to include"),
        output: str = typer.Option(None, "--output", "-o", help="Output file path (optional)")
):
    """🔍 Scan and analyze codebase structure in workspace/repos"""
    import os
    from pathlib import Path
    from rich.table import Table
    from rich.tree import Tree

    try:
        # Determine scan path
        if path:
            scan_path = Path(path).resolve()
        else:
            # Default to workspace/repos from project root
            project_root = Path(__file__).parent.parent  # Go up from src/ to project root
            workspace_dir = project_root / "workspace"
            repos_dir = workspace_dir / "repos"

            # Create workspace structure if it doesn't exist
            if not workspace_dir.exists():
                console.print("📁 Creating workspace directory...", style="cyan")
                workspace_dir.mkdir(exist_ok=True)

            if not repos_dir.exists():
                console.print("📁 Creating repos directory...", style="cyan")
                repos_dir.mkdir(exist_ok=True)

            # Also create embeddings directory
            embeddings_dir = workspace_dir / "embeddings"
            if not embeddings_dir.exists():
                console.print("📁 Creating embeddings directory...", style="cyan")
                embeddings_dir.mkdir(exist_ok=True)

            scan_path = repos_dir

        if not scan_path.exists():
            console.print(f"❌ Path not found: {scan_path}", style="red")
            console.print("💡 Tip: Clone some repositories to workspace/repos first", style="yellow")
            return

        # If specific repo requested, scan that repo
        if repo:
            repo_path = scan_path / repo
            if not repo_path.exists():
                console.print(f"❌ Repository '{repo}' not found in {scan_path}", style="red")

                # List available repos
                available_repos = [d.name for d in scan_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
                if available_repos:
                    console.print(f"📂 Available repositories: {', '.join(available_repos)}", style="cyan")
                return
            scan_path = repo_path

        excluded_dirs = set(exclude.split(','))
        valid_extensions = set(ext.strip('.') for ext in extensions.split(','))

        console.print(f"🔍 Scanning codebase at: {scan_path}", style="cyan")
        console.print(f"📂 Excluding directories: {', '.join(excluded_dirs)}", style="dim")
        console.print(f"📄 Including extensions: {', '.join(valid_extensions)}", style="dim")

        # If scanning repos directory, show repository overview first
        if scan_path.name == "repos" and not repo:
            console.print("\n📋 Repository Overview:", style="bold cyan")
            repos = [d for d in scan_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

            if not repos:
                console.print("📭 No repositories found in workspace/repos", style="yellow")
                console.print("💡 Try: git clone <repo-url> into workspace/repos/", style="dim")
                return

            repo_table = Table()
            repo_table.add_column("Repository", style="cyan")
            repo_table.add_column("Type", style="green")
            repo_table.add_column("Last Modified", style="magenta")

            for repo_dir in sorted(repos):
                # Detect repo type
                repo_type = "Unknown"
                if (repo_dir / ".git").exists():
                    repo_type = "Git Repository"
                elif (repo_dir / "package.json").exists():
                    repo_type = "Node.js Project"
                elif (repo_dir / "requirements.txt").exists() or (repo_dir / "pyproject.toml").exists():
                    repo_type = "Python Project"
                elif (repo_dir / "pom.xml").exists():
                    repo_type = "Maven Project"
                elif (repo_dir / "Cargo.toml").exists():
                    repo_type = "Rust Project"

                # Get last modified
                try:
                    last_modified_timestamp = repo_dir.stat().st_mtime
                    from datetime import datetime
                    last_modified_date = datetime.fromtimestamp(last_modified_timestamp).strftime('%Y-%m-%d')
                except:
                    last_modified_date = "Unknown"

                repo_table.add_row(repo_dir.name, repo_type, last_modified_date)

            console.print(repo_table)
            console.print(f"\n💡 Use --repo <name> to scan a specific repository", style="dim")
            console.print(f"💡 Example: dacrew codebase scan --repo {repos[0].name}", style="dim")
            return

        # Statistics
        stats = {
            'total_files': 0,
            'code_files': 0,
            'total_lines': 0,
            'code_lines': 0,
            'directories': 0,
            'extensions': {},
            'repo_name': scan_path.name if repo else 'Multiple Repositories'
        }

        # File tree for display
        tree = Tree(f"📁 {scan_path.name}")

        def scan_directory(current_path: Path, current_tree: Tree = None, max_depth: int = 3, current_depth: int = 0):
            if current_depth > max_depth:
                return

            try:
                items = list(current_path.iterdir())
                items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

                for item in items:
                    if item.name.startswith('.') and item.name not in ['.env', '.env.example']:
                        continue

                    if item.is_dir():
                        if item.name in excluded_dirs:
                            continue
                        stats['directories'] += 1

                        if current_tree and current_depth < max_depth:
                            dir_node = current_tree.add(f"📁 {item.name}")
                            scan_directory(item, dir_node, max_depth, current_depth + 1)
                        else:
                            scan_directory(item, None, max_depth, current_depth + 1)

                    else:
                        stats['total_files'] += 1
                        file_ext = item.suffix.lstrip('.')

                        if file_ext in valid_extensions:
                            stats['code_files'] += 1
                            stats['extensions'][file_ext] = stats['extensions'].get(file_ext, 0) + 1

                            # Count lines
                            try:
                                with open(item, 'r', encoding='utf-8', errors='ignore') as f:
                                    lines = f.readlines()
                                    total_lines = len(lines)
                                    code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
                                    stats['total_lines'] += total_lines
                                    stats['code_lines'] += code_lines
                            except Exception:
                                pass

                            if current_tree and current_depth < max_depth:
                                file_icon = "🐍" if file_ext == "py" else "📄"
                                current_tree.add(f"{file_icon} {item.name}")

            except PermissionError:
                pass

        scan_directory(scan_path, tree)

        # Display tree (limited depth)
        console.print(tree)
        console.print()

        # Display statistics
        stats_table = Table(title=f"Codebase Statistics - {stats['repo_name']}")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Count", style="white", justify="right")

        stats_table.add_row("Total Files", str(stats['total_files']))
        stats_table.add_row("Code Files", str(stats['code_files']))
        stats_table.add_row("Directories", str(stats['directories']))
        stats_table.add_row("Total Lines", f"{stats['total_lines']:,}")
        stats_table.add_row("Code Lines", f"{stats['code_lines']:,}")

        console.print(stats_table)

        # Extensions breakdown
        if stats['extensions']:
            ext_table = Table(title="File Extensions")
            ext_table.add_column("Extension", style="cyan")
            ext_table.add_column("Files", style="white", justify="right")
            ext_table.add_column("Percentage", style="green", justify="right")

            total_code_files = stats['code_files']
            for ext, count in sorted(stats['extensions'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_code_files) * 100 if total_code_files > 0 else 0
                ext_table.add_row(f".{ext}", str(count), f"{percentage:.1f}%")

            console.print(ext_table)

        # Save to file if requested
        if output:
            output_path = Path(output)
            scan_report = {
                'path': str(scan_path),
                'repository': stats['repo_name'],
                'timestamp': str(Path().resolve()),
                'statistics': stats,
                'scan_parameters': {
                    'excluded_directories': excluded_dirs,
                    'included_extensions': valid_extensions
                }
            }

            import json
            with open(output_path, 'w') as f:
                json.dump(scan_report, f, indent=2, default=str)
            console.print(f"📄 Report saved to: {output_path}", style="green")

    except Exception as e:
        console.print(f"❌ Error scanning codebase: {str(e)}", style="red")

@codebase_app.command("index")
def index_codebase(
        path: str = typer.Option(".", "--path", "-p", help="Path to index"),
        force: bool = typer.Option(False, "--force", "-f", help="Force reindex even if already indexed")
):
    """🗂️ Index codebase for AI analysis"""
    try:
        from .config import Config
        from pathlib import Path

        config = Config.load()
        index_path = Path(path).resolve()

        if not index_path.exists():
            console.print(f"❌ Path not found: {path}", style="red")
            return

        console.print(f"🗂️ Indexing codebase at: {index_path}", style="cyan")

        # Check if vector database exists
        vector_db_path = Path(config.ai.chroma_persist_directory)
        if vector_db_path.exists() and not force:
            console.print("📊 Existing index found", style="yellow")
            console.print("Use --force to reindex", style="dim")
            return

        # Import vector database components
        try:
            from .vector_db.manager import VectorDBManager
            from .embedding.generator import EmbeddingGenerator
        except ImportError:
            console.print("❌ Vector database components not available", style="red")
            console.print("This feature requires additional dependencies", style="yellow")
            return

        console.print("🚀 Starting indexing process...", style="cyan")

        # Initialize components
        embedding_generator = EmbeddingGenerator(config.ai.embeddings_model)
        vector_manager = VectorDBManager(config.ai.chroma_persist_directory)

        # Scan for code files
        code_files = []
        for file_path in index_path.rglob("*.py"):  # Focus on Python files for now
            if not any(excluded in str(file_path) for excluded in ['.git', '__pycache__', '.venv', 'venv']):
                code_files.append(file_path)

        console.print(f"📄 Found {len(code_files)} Python files to index", style="green")

        # Process files with progress
        from rich.progress import Progress, SpinnerColumn, TextColumn

        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
        ) as progress:
            task = progress.add_task("Indexing files...", total=len(code_files))

            indexed_count = 0
            for file_path in code_files:
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    if content.strip():  # Only index non-empty files
                        # Generate embedding
                        embedding = embedding_generator.generate_embedding(content)

                        # Store in vector database
                        vector_manager.add_document(
                            document=content,
                            metadata={
                                'file_path': str(file_path.relative_to(index_path)),
                                'file_name': file_path.name,
                                'file_type': 'python',
                                'indexed_at': str(Path().resolve())
                            },
                            embedding=embedding
                        )
                        indexed_count += 1

                    progress.update(task, advance=1)

                except Exception as e:
                    console.print(f"⚠️ Skipped {file_path.name}: {str(e)}", style="yellow")
                    progress.update(task, advance=1)

        console.print(f"✅ Successfully indexed {indexed_count} files", style="green")
        console.print(f"📊 Vector database saved to: {config.ai.chroma_persist_directory}", style="dim")

    except Exception as e:
        console.print(f"❌ Error indexing codebase: {str(e)}", style="red")


@codebase_app.command("search")
def search_codebase(
        query: str,
        limit: int = typer.Option(5, "--limit", "-l", help="Maximum number of results"),
        threshold: float = typer.Option(0.7, "--threshold", "-t", help="Similarity threshold (0.0-1.0)")
):
    """🔍 Search indexed codebase using AI similarity"""
    try:
        from .config import Config
        from pathlib import Path

        config = Config.load()

        # Check if index exists
        vector_db_path = Path(config.ai.chroma_persist_directory)
        if not vector_db_path.exists():
            console.print("❌ No codebase index found", style="red")
            console.print("Run 'dacrew codebase index' first", style="yellow")
            return

        # Import vector database components
        try:
            from .vector_db.manager import VectorDBManager
            from .embedding.generator import EmbeddingGenerator
        except ImportError:
            console.print("❌ Vector database components not available", style="red")
            return

        console.print(f"🔍 Searching for: '{query}'", style="cyan")

        # Initialize components
        embedding_generator = EmbeddingGenerator(config.ai.embeddings_model)
        vector_manager = VectorDBManager(config.ai.chroma_persist_directory)

        # Generate query embedding
        query_embedding = embedding_generator.generate_embedding(query)

        # Search vector database
        results = vector_manager.search_similar(
            query_embedding=query_embedding,
            limit=limit,
            threshold=threshold
        )

        if not results:
            console.print("No similar code found", style="yellow")
            return

        # Display results
        from rich.panel import Panel
        from rich.syntax import Syntax

        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            content = result.get('document', '')
            similarity = result.get('similarity', 0.0)

            file_path = metadata.get('file_path', 'unknown')
            file_name = metadata.get('file_name', 'unknown')

            # Create syntax highlighted code preview
            code_preview = content[:500] + "..." if len(content) > 500 else content
            syntax = Syntax(code_preview, "python", theme="monokai", line_numbers=True)

            panel_title = f"Result {i}: {file_name} (similarity: {similarity:.2f})"
            panel = Panel(
                syntax,
                title=panel_title,
                subtitle=f"📁 {file_path}",
                border_style="blue"
            )

            console.print(panel)
            console.print()

    except Exception as e:
        console.print(f"❌ Error searching codebase: {str(e)}", style="red")

@codebase_app.command("stats")
def show_codebase_stats():
    """📊 Show codebase indexing statistics"""
    try:
        from .config import Config
        from pathlib import Path

        config = Config.load()
        vector_db_path = Path(config.ai.chroma_persist_directory)

        if not vector_db_path.exists():
            console.print("❌ No codebase index found", style="red")
            console.print("Run 'dacrew codebase index' first", style="yellow")
            return

        # Import vector database components
        try:
            from .vector_db.manager import VectorDBManager
        except ImportError:
            console.print("❌ Vector database components not available", style="red")
            return

        vector_manager = VectorDBManager(config.ai.chroma_persist_directory)
        stats = vector_manager.get_stats()

        # Display statistics
        from rich.table import Table

        stats_table = Table(title="Codebase Index Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white", justify="right")

        stats_table.add_row("Total Documents", str(stats.get('document_count', 0)))
        stats_table.add_row("Database Path", str(vector_db_path))
        stats_table.add_row("Embedding Model", config.ai.embeddings_model)

        console.print(stats_table)

        # Show recent files if available
        recent_files = stats.get('recent_files', [])
        if recent_files:
            files_table = Table(title="Recently Indexed Files")
            files_table.add_column("File", style="cyan")
            files_table.add_column("Type", style="green")

            for file_info in recent_files[:10]:  # Show last 10
                files_table.add_row(file_info.get('name', 'unknown'), file_info.get('type', 'unknown'))

            console.print(files_table)

    except Exception as e:
        console.print(f"❌ Error getting stats: {str(e)}", style="red")

@codebase_app.command("current")
def show_current_repository():
    """🎯 Show current active repository"""
    try:
        from .codebase.codebase_manager import SimpleCodebaseManager
        from .embedding.embedding_manager import EmbeddingManager

        codebase_manager = SimpleCodebaseManager()
        embedding_manager = EmbeddingManager()

        # Get current repository
        repo_info = codebase_manager.get_current_repository_info()

        if not repo_info:
            console.print("📭 No current repository set", style="yellow")
            console.print("💡 Use 'dacrew codebase add <repo-url>' to add a repository", style="dim")
            console.print("💡 Or 'dacrew codebase list' to see available repositories", style="dim")
            return

        # Display current repository info
        from rich.panel import Panel
        from rich.table import Table

        info_table = Table.grid(padding=1)
        info_table.add_column(style="cyan", justify="right")
        info_table.add_column(style="white")

        info_table.add_row("Repository:", repo_info['repo_name'])
        info_table.add_row("ID:", repo_info['repo_id'])
        info_table.add_row("URL:", repo_info.get('repo_url', 'N/A'))
        info_table.add_row("Branch:", repo_info.get('branch', 'N/A'))
        info_table.add_row("Path:", repo_info['actual_path'])
        info_table.add_row("Added:", repo_info.get('cloned_at', 'N/A'))
        info_table.add_row("Exists:", "✅ Yes" if repo_info.get('exists', False) else "❌ No")

        console.print(Panel(info_table, title="🎯 Current Repository", border_style="blue"))

        # Show embedding status
        embedding_status = embedding_manager.get_current_embedding_status()
        if embedding_status.get('exists', False):
            metadata = embedding_status.get('metadata', {})

            embed_table = Table.grid(padding=1)
            embed_table.add_column(style="green", justify="right")
            embed_table.add_column(style="white")

            embed_table.add_row("Status:", metadata.get('indexing_status', 'Unknown'))
            embed_table.add_row("Files:", str(metadata.get('total_files', 0)))
            embed_table.add_row("Chunks:", str(metadata.get('total_chunks', 0)))
            embed_table.add_row("Last Updated:", metadata.get('last_updated', 'N/A')[:10])
            embed_table.add_row("Model:", metadata.get('embedding_model', 'N/A'))

            console.print(Panel(embed_table, title="🗂️ Embedding Status", border_style="green"))
        else:
            console.print(Panel("No embeddings found", title="🗂️ Embedding Status", border_style="yellow"))
            console.print("💡 Create embeddings with: dacrew codebase index", style="dim")

    except ImportError as e:
        console.print(f"❌ Missing required components: {str(e)}", style="red")
    except Exception as e:
        console.print(f"❌ Error getting current repository: {str(e)}", style="red")

@codebase_app.command("switch")
def switch_repository(repo_name: str):
    """🔄 Switch to a different repository"""
    try:
        from .codebase.codebase_manager import SimpleCodebaseManager

        codebase_manager = SimpleCodebaseManager()

        # Find repository by name or ID
        repositories = codebase_manager.list_repositories()
        repo_info = None

        for repo in repositories:
            if repo['repo_name'] == repo_name or repo['repo_id'] == repo_name:
                repo_info = repo
                break

        if not repo_info:
            console.print(f"❌ Repository '{repo_name}' not found", style="red")

            # Show available repositories
            if repositories:
                console.print("\n📋 Available repositories:", style="cyan")
                for repo in repositories:
                    status = "✅" if repo.get('exists', False) else "❌"
                    console.print(f"  • {repo['repo_name']} {status}", style="white")
            return

        # Switch to repository
        success = codebase_manager.set_current_codebase(repo_info['repo_id'])

        if success:
            console.print(f"🔄 Switched to repository: {repo_info['repo_name']}", style="green")
            console.print(f"📁 Path: {repo_info['actual_path']}", style="dim")
        else:
            console.print(f"❌ Failed to switch to repository", style="red")

    except ImportError as e:
        console.print(f"❌ Missing required components: {str(e)}", style="red")
    except Exception as e:
        console.print(f"❌ Error switching repository: {str(e)}", style="red")

@codebase_app.command("remove")
def remove_repository(
        repo_name: str,
        keep_embeddings: bool = typer.Option(False, "--keep-embeddings", help="Keep embeddings when removing repository"),
        confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """🗑️ Remove a repository and optionally its embeddings"""
    try:
        from .codebase.codebase_manager import SimpleCodebaseManager
        from .embedding.embedding_manager import EmbeddingManager

        # Initialize managers
        codebase_manager = SimpleCodebaseManager()
        embedding_manager = EmbeddingManager()

        # Check if repository exists
        repositories = codebase_manager.list_repositories()
        repo_info = None

        for repo in repositories:
            if repo['repo_name'] == repo_name or repo['repo_id'] == repo_name:
                repo_info = repo
                break

        if not repo_info:
            console.print(f"❌ Repository '{repo_name}' not found", style="red")

            # Show available repositories
            if repositories:
                console.print("\n📋 Available repositories:", style="cyan")
                for repo in repositories:
                    console.print(f"  • {repo['repo_name']}", style="white")
            return

        # Confirmation prompt
        if not confirm:
            console.print(f"🗑️ About to remove repository: {repo_info['repo_name']}", style="yellow")
            console.print(f"📁 Path: {repo_info['actual_path']}", style="dim")

            if not keep_embeddings:
                console.print("⚠️ This will also delete associated embeddings", style="red")

            confirm_delete = typer.confirm("Are you sure you want to continue?")
            if not confirm_delete:
                console.print("❌ Operation cancelled", style="yellow")
                return

        repo_id = repo_info['repo_id']

        # Remove embeddings first if requested
        if not keep_embeddings:
            console.print("🗂️ Removing embeddings...", style="cyan")
            if embedding_manager.has_embedding(repo_id):
                success = embedding_manager.delete_embedding(repo_id)
                if success:
                    console.print("✅ Embeddings removed", style="green")
                else:
                    console.print("⚠️ Failed to remove embeddings", style="yellow")
            else:
                console.print("📝 No embeddings found", style="dim")

        # Remove repository
        console.print("📁 Removing repository...", style="cyan")
        success = codebase_manager.remove_codebase(repo_id)

        if success:
            console.print(f"✅ Successfully removed repository: {repo_info['repo_name']}", style="green")
        else:
            console.print(f"❌ Failed to remove repository", style="red")

    except ImportError as e:
        console.print(f"❌ Missing required components: {str(e)}", style="red")
    except Exception as e:
        console.print(f"❌ Error removing repository: {str(e)}", style="red")

# ============================================================================
# Main CLI Entry Point
# ============================================================================

def main():
    """Main CLI entry point"""
    app()

if __name__ == "__main__":
    main()
