"""CLI interface for DaCrew - AI-powered Development Crew"""
import shlex
from pathlib import Path
import typer
from rich.console import Console

from agents import BaseAgent
from config import Config
from jira_client import JiraClient
# Import required managers
from .dacrew_completer import DaCrewCompleter
from .embedding.embedding_manager import EmbeddingManager

# Initialize Typer app and Rich console
app = typer.Typer(
    help="🚀 DaCrew - AI-powered development crew, your team of software development assistants"
)
console = Console()

GLOBAL_EXAMPLE_CONFIG_CONTENT = """
# ~/.dacrew/config.yml
# Global configuration for DaCrew.
# Copy this file to ~/.dacrew/config.yml and update it with your values.

embedding:
  codebase:
    path: "./"
    include_patterns:
      - "src/**/*.java"
      - "src/**/*.py"
    exclude_patterns:
      - "node_modules/**"
      - "build/**"

  issues:
    include_statuses: ["To Do", "In Progress", "Done"]
    exclude_statuses: ["Deleted", "Archived"]

  documents:
    paths:
      - "docs/architecture/"
      - "docs/design-specs/spec.pdf"
    urls:
      - "https://mycompanywiki.com/project-guidelines"
      - "https://developer.mozilla.org/en-US/docs/Web/HTTP"

gen:
  build: "./gradlew build"
  test: "./gradlew test"

git:
  default_branch_prefix: "dacrew/"
  commit_template: "Implementing {ISSUE_ID}: {ISSUE_TITLE}"

jira:
  api_token: "your-api-token"
  url: "https://custom-jira-instance.atlassian.net"
  jira_project_key: "ABC"
  user_id: "john.doe"
  fetch_limit: 500

ai:
  openai_api_key: "your-openai-api-key"
  model: "gpt-4"
  temperature: 0.7
  embeddings_model: "sentence-transformers/all-MiniLM-L6-v2"

crew:
  name: codegen_crew
  description: >
    A sample multi-agent setup for code generation and review.

  agents:
    - name: requirement_agent
      role: Requirement Interpreter
      goal: >
        Analyze the user requirement and create a structured specification.
      knowledge:
        codebase: { enabled: true }
        jira: { enabled: true }
        documents: { enabled: true }
      tools:
        - embedding_retriever
      llm: gpt-4-turbo
      issue_routing:
        Story:
          Draft Requirement:
            name: task_analyze_requirement
            tags: ["architecture", "spec"]

  tools:
    - name: embedding_retriever
      description: >
        Retrieves semantically relevant code and documentation chunks from 
        FAISS/BM25 hybrid embeddings of the codebase.
      type: retrieval
      config:
        retriever: faiss
        reranker: bm25
        top_k: 10

  tasks:
    - name: task_analyze_requirement
      description: >
        Create a technical specification and pseudocode plan for the user request.
      input: user_requirement
      output: code_specification
"""

PROJECT_EXAMPLE_CONFIG_CONTENT = """

# ~/.dacrew/config.yml
# Project-specific configuration for DaCrew.
# Copy this file to ~/.dacrew/config.yml and update it with your values.

embedding:
  codebase:
    path: "./"
    include_patterns:
      - "src/**/*.java"
      - "src/**/*.py"
    exclude_patterns:
      - "node_modules/**"
      - "build/**"

  issues:
    include_statuses: ["To Do", "In Progress", "Done"]
    exclude_statuses: ["Deleted", "Archived"]

  documents:
    paths:
      - "docs/architecture/"
      - "docs/design-specs/spec.pdf"
    urls:
      - "https://mycompanywiki.com/project-guidelines"
      - "https://developer.mozilla.org/en-US/docs/Web/HTTP"

gen:
  build: "./gradlew build"
  test: "./gradlew test"

git:
  default_branch_prefix: "dacrew/"
  commit_template: "Implementing {ISSUE_ID}: {ISSUE_TITLE}"

jira:
  url: "https://custom-jira-instance.atlassian.net"
  jira_project_key: "ABC"
  user_id: "john.doe"
  fetch_limit: 500

ai:
  model: "gpt-4"
  temperature: 0.7
  embeddings_model: "sentence-transformers/all-MiniLM-L6-v2"

crew:
  name: codegen_crew
  description: >
    A sample multi-agent setup for code generation and review.

  agents:
    - name: requirement_agent
      role: Requirement Interpreter
      goal: >
        Analyze the user requirement and create a structured specification.
      knowledge:
        codebase: { enabled: true }
        jira: { enabled: true }
        documents: { enabled: true }
      tools:
        - embedding_retriever
      llm: gpt-4-turbo
      issue_routing:
        Story:
          Draft Requirement:
            name: task_analyze_requirement
            tags: ["architecture", "spec"]

  tools:
    - name: embedding_retriever
      description: >
        Retrieves semantically relevant code and documentation chunks from 
        FAISS/BM25 hybrid embeddings of the codebase.
      type: retrieval
      config:
        retriever: faiss
        reranker: bm25
        top_k: 10

  tasks:
    - name: task_analyze_requirement
      description: >
        Create a technical specification and pseudocode plan for the user request.
      input: user_requirement
      output: code_specification
"""




# ============================================================================
# INIT COMMAND
# ============================================================================
@app.command("init")
def init_project():
    """Initialize DaCrew for the current project and global environment."""
    project_dir = Path.cwd()
    home_dir = Path.home() / ".dacrew"

    home_dir.mkdir(parents=True, exist_ok=True)

    global_example_config = home_dir / "config-example.yml"
    if not global_example_config.exists():
        global_example_config.write_text(GLOBAL_EXAMPLE_CONFIG_CONTENT)
        console.print(f"✅ Created global config example: {global_example_config}", style="green")
        console.print("💡 Copy this to ~/.dacrew/config.yml and customize it.", style="yellow")
    elif not (home_dir / "config.yml").exists():
        console.print("⚠️ Global config ~/.dacrew/config.yml not found.", style="yellow")
        console.print(f"   Copy and edit: {global_example_config}", style="dim")

    project_example_config = project_dir / ".dacrew-example.yml"
    if not project_example_config.exists():
        project_example_config.write_text(PROJECT_EXAMPLE_CONFIG_CONTENT)
        console.print(f"✅ Created project config example: {project_example_config}", style="green")
        console.print("💡 Copy this to .dacrew.yml and customize it.", style="yellow")
    else:
        console.print("⚠️ Project config example already exists (.dacrew-example.yml).", style="yellow")

# ============================================================================
# TEST CONNECTION
# ============================================================================
@app.command("test-connection")
def test_jira_connection():
    """🔗 Test Jira connection"""
    try:
        from .config import Config
        from .jira_client import JiraClient
        console.print("🔗 Testing Jira connection...", style="cyan")
        config = Config.load()

        if not config.jira.url:
            console.print("❌ Jira URL not configured", style="red")
            return
        if not config.jira.user_id:
            console.print("❌ Jira username not configured", style="red")
            return
        if not config.jira.api_token:
            console.print("❌ Jira API token not configured", style="red")
            return

        client = JiraClient(config.jira)
        if client.test_connection():
            console.print("✅ Jira connection successful!", style="green")
            console.print(f"Connected to: {config.jira.url}", style="dim")
        else:
            console.print("❌ Jira connection failed!", style="red")

    except Exception as e:
        console.print(f"❌ Error testing connection: {str(e)}", style="red")

# ============================================================================
# ISSUES COMMAND GROUP
# ============================================================================
agent_app = typer.Typer(help="🤖 Run an agent on a specific JIRA issue")
app.add_typer(agent_app, name="agent")

@agent_app.command("run")
def run_agent(
        issue: str = typer.Option(..., "--issue", "-i", help="JIRA issue ID"),
        config_path: Path = typer.Option(Path.cwd(), "--config-path", help="Path to config root"),
        dry_run: bool = typer.Option(False, "--dry-run", help="Preview agent and task without running")
):
    """Run the appropriate agent and task for the given JIRA issue."""
    try:
        config = Config.load(config_path)
        jira_client = JiraClient(config.jira)
        issue_data = jira_client.get_issue(issue)

        issue_type = issue_data["issue_type"]
        issue_status = issue_data["status"]

        matched = None
        for agent_conf in config.crew.agents:
            routing = agent_conf.issue_routing or {}
            if issue_type in routing:
                if issue_status in routing[issue_type]:
                    matched = (agent_conf.name, routing[issue_type][issue_status])
                    break

        if not matched:
            console.print(f"❌ No agent configured to handle '{issue_type}' in status '{issue_status}'", style="red")
            raise typer.Exit(1)

        agent_name, task_meta = matched
        task_name = task_meta["name"]
        tags = task_meta.get("tags", [])

        if dry_run:
            console.print(f"🔍 [bold]Dry run:[/bold] Issue '{issue}' would be handled by agent '[cyan]{agent_name}[/cyan]' executing task '[green]{task_name}[/green]' with tags {tags}", style="yellow")
            return

        agent = BaseAgent(config=config, agent_name=agent_name)
        agent.run(issue)
        console.print(f"✅ Agent '[cyan]{agent_name}[/cyan]' ran successfully for issue '[bold]{issue}[/bold]'", style="green")

    except Exception as e:
        console.print(f"❌ Error running agent: {str(e)}", style="red")


@agent_app.command("list")
def list_agents():
    """📋 List available agents"""
    try:
        from .config import Config
        config = Config.load()
        if not config.crew or not config.crew.agents:
            console.print("No agents configured", style="yellow")
            return

        for agent in config.crew.agents:
            console.print(f"🤖 {agent.name}: {agent.goal or 'No goal'}")
    except Exception as e:
        console.print(f"❌ Error listing agents: {str(e)}", style="red")


# ============================================================================
# ISSUES COMMAND GROUP
# ============================================================================
issues_app = typer.Typer(help="🎫 Manage Jira issues and tickets")
app.add_typer(issues_app, name="issues")

@issues_app.command("list")
def list_issues(
        project: str = typer.Option(None, "--project", "-p", help="Project key"),
        status: str = typer.Option(None, "--status", "-s", help="Filter by status"),
        assignee: str = typer.Option(None, "--assignee", "-a", help="Filter by assignee"),
        limit: int = typer.Option(10, "--limit", "-l", help="Maximum number of issues to show")
):
    """📋 List Jira issues"""
    try:
        from .config import Config
        from .jira_client import JiraClient

        config = Config.load()
        client = JiraClient(config.jira)

        # Build JQL query
        jql_parts = []

        if project:
            jql_parts.append(f"project = {project}")
        elif isinstance(config.project, dict) and "jira_project_key" in config.project:
            jql_parts.append(f"project = {config.project['jira_project_key']}")

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

        table = Table(title="Jira Issues")
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
        from .jira_client import JiraClient

        config = Config.load()
        client = JiraClient(config.jira)

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
    """✨ Create a new Jira issue"""
    try:
        from .config import Config
        from .jira_client import JiraClient

        config = Config.load()
        client = JiraClient(config.jira)

        # Use default project if not specified
        if not project:
            project = config.project

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
    """🔗 Test Jira connection (issues context)"""
    test_jira_connection()

# ============================================================================
# EMBEDDINGS COMMAND GROUP
# ============================================================================
embeddings_app = typer.Typer(help="🧠 Manage embeddings for code, issues, and docs")
app.add_typer(embeddings_app, name="embeddings")

@embeddings_app.command("index")
def index_embeddings(
        codebase: bool = typer.Option(False, "--codebase", help="Index codebase"),
        issues: bool = typer.Option(False, "--issues", help="Index issues"),
        documents: bool = typer.Option(False, "--documents", help="Index documents"),
        force: bool = typer.Option(False, "--force", "-f", help="Force re-indexing"),
):
    """Create embeddings for specified sources."""
    manager = EmbeddingManager(_get_config().project)
    sources = _get_sources(codebase, issues, documents)
    console.print(f"Indexing sources: {', '.join(sources)}", style="cyan")
    manager.index_sources(sources, force)

@embeddings_app.command("clean")
def clean_embeddings(
        codebase: bool = typer.Option(False, "--codebase", help="Index codebase"),
        issues: bool = typer.Option(False, "--issues", help="Index issues"),
        documents: bool = typer.Option(False, "--documents", help="Index documents"),
        force: bool = typer.Option(False, "--force", "-f", help="Force re-indexing"),
):
    """🧹 Clean up embeddings."""
    manager = EmbeddingManager(_get_config().project)
    if not force:
        confirm = typer.confirm("This action is irreversible. Continue?")
        if not confirm:
            console.print("❌ Cleanup cancelled", style="yellow")
            return

    sources = _get_sources(codebase, issues, documents)
    console.print(f"Cleaning sources: {', '.join(sources)}", style="cyan")
    manager.clean(sources)


@embeddings_app.command("stats")
def embeddings_stats(
        codebase: bool = typer.Option(False, "--codebase", help="Index codebase"),
        issues: bool = typer.Option(False, "--issues", help="Index issues"),
        documents: bool = typer.Option(False, "--documents", help="Index documents")):
    """📊 Show embedding statistics."""
    manager = EmbeddingManager(_get_config().project)
    stats = _get_stats(codebase, issues, documents)
    console.print(f"Embedding stats: {stats}", style="cyan")
    manager.get_stats(stats)

@embeddings_app.command("query")
def query_embeddings(
        query: str,
        codebase: bool = typer.Option(False, "--codebase", help="Index codebase"),
        issues: bool = typer.Option(False, "--issues", help="Index issues"),
        documents: bool = typer.Option(False, "--documents", help="Index documents"),
        top_k: int = typer.Option(5, "--top-k", help="Number of results"),
):
    """🔍 Query embeddings."""
    manager = EmbeddingManager(_get_config().project)
    sources = _get_sources(codebase, issues, documents)
    results = manager.query(query, sources, top_k)
    console.print("Results:", style="cyan")
    for i, result in enumerate(results, start=1):
        console.print("─" * 50, style="dim")
        console.print(f"[{i}] Source: {result.source} | Similarity: {result.similarity:.2f}", style="yellow")
        if result.reference:
            console.print(f"Reference: {result.reference}", style="blue")
        console.print(result.content, style="green")

# ============================================================================
# GEN COMMAND GROUP
# ============================================================================
gen_app = typer.Typer(help="✨ Generate code and artifacts")
app.add_typer(gen_app, name="gen")

# (gen_command logic remains unchanged)

# ============================================================================
# REPL
# ============================================================================
@app.command("repl")
def repl(verbose: bool = typer.Option(False, "--verbose", "-v")):
    from prompt_toolkit import PromptSession
    session = PromptSession(completer=DaCrewCompleter())
    print("Starting REPL session...")
    while True:
        try:
            user_input = session.prompt('>>> ')
            if user_input.lower() in ['exit', 'quit', 'bye']:
                break
            process_command(user_input, verbose)
        except KeyboardInterrupt:
            continue
        except EOFError:
            break


def process_command(command, verbose):
    if verbose:
        print(f"Processing command: {command}")
    if command.startswith('embeddings '):
        embeddings_command(command, verbose)
    elif command.startswith('issues '):
        issues_command(command, verbose)
    elif command.startswith('agent '):
        agent_command(command, verbose)
    else:
        print(f"Unknown command: {command}")


def agent_command(command: str, verbose: bool):
    """
    Handle 'agent' commands within REPL mode by delegating to the Typer app.
    """
    if verbose:
        console.print(f"Handling agent command: {command}", style="dim")

    try:
        # Split the command into arguments (like shell)
        args = shlex.split(command)
        # Remove the leading 'agent'
        args = args[1:]
        console.print(f"🐛 DEBUG: args = {args}", style="magenta")

        if not args:
            console.print("⚠️ No agent subcommand provided. Type 'help agent' for options.", style="yellow")
            return

        # Invoke Typer's agent_app
        agent_app(args)
    except SystemExit:
        # Typer may call sys.exit(), catch it to prevent REPL from exiting
        pass
    except Exception as e:
        console.print(f"❌ Error handling agent command: {str(e)}", style="red")


def embeddings_command(command: str, verbose: bool):
    """
    Handle 'embeddings' commands within REPL mode by delegating to the Typer app.
    """
    if verbose:
        console.print(f"Handling embeddings command: {command}", style="dim")

    try:
        # Split the command into arguments (like shell)
        args = shlex.split(command)
        # Remove the leading 'embeddings'
        args = args[1:]
        if not args:
            console.print("⚠️ No embeddings subcommand provided. Type 'help embeddings' for options.", style="yellow")
            return

        embeddings_app(args)
    except SystemExit:
        # Typer may call sys.exit(), catch it to prevent REPL from exiting
        pass
    except Exception as e:
        console.print(f"❌ Error handling embeddings command: {str(e)}", style="red")


def issues_command(command: str, verbose: bool):
    """
    Handle 'issues' commands within REPL mode by delegating to the Typer app.
    """
    if verbose:
        console.print(f"Handling issues command: {command}", style="dim")

    try:
        # Split the command into arguments (like shell)
        args = shlex.split(command)
        # Remove the leading 'issues'
        args = args[1:]
        if not args:
            console.print("⚠️ No issues subcommand provided. Type 'help issues' for options.", style="yellow")
            return

        # Invoke Typer's issues_app
        issues_app(args)
    except SystemExit:
        # Typer may call sys.exit(), catch it to prevent REPL from exiting
        pass
    except Exception as e:
        console.print(f"❌ Error handling issues command: {str(e)}", style="red")


def _get_sources(codebase, issues, documents):
    sources = []
    if not any([codebase, issues, documents]):
        sources = ["codebase", "issues", "documents"]
    else:
        if codebase:
            sources.append("codebase")
        if issues:
            sources.append("issues")
        if documents:
            sources.append("documents")
    return sources

def _get_stats(codebase, issues, documents):
    stats = []
    if not any([codebase, issues, documents]):
        stats = ["codebase", "issues", "docs"]
    else:
        if codebase:
            stats.append("codebase")
        if issues:
            stats.append("issues")
        if documents:
            stats.append("docs")
    return stats

def _get_config():
    from .config import Config
    try:
        return Config.load()
    except FileNotFoundError:
        console.print("❌ No configuration found.", style="red")
        console.print("💡 Run 'dacrew init' to create initial config files.", style="yellow")
        raise typer.Exit(1)

# ============================================================================
# MAIN
# ============================================================================
def main():
    app()

if __name__ == "__main__":
    main()