"""Command Line Interface for JIRA AI Assistant"""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents import AgentManager
from .config import Config
from .jira_client import JIRAClient
from .utils import build_jql_query

app = typer.Typer(
    name="jira-ai",
    help="AI-powered natural language interface for JIRA",
    add_completion=False,
)
console = Console()


@app.command()
def hello():
    """Test command to verify the CLI is working"""
    console.print(Panel.fit("🚀 JIRA AI Assistant", style="bold blue"))
    console.print("Hello! The CLI is working correctly.")


@app.command()
def config():
    """Show current configuration"""
    try:
        cfg = Config.load()
        console.print(Panel.fit("⚙️ Configuration", style="bold green"))
        console.print(f"JIRA URL: {cfg.jira.url}")
        console.print(f"JIRA Username: {cfg.jira.username}")
        console.print(f"OpenAI API Key: {'*' * 20 if cfg.ai.openai_api_key else 'Not set'}")
        console.print(f"Default Project: {cfg.project.default_project_key}")
        console.print(f"Embeddings Model: {cfg.ai.embeddings_model}")
    except Exception as e:
        console.print(f"❌ Error loading configuration: {e}", style="bold red")


@app.command()
def test_jira():
    """Test JIRA connection"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)

        if client.test_connection():
            console.print("✅ JIRA connection successful!", style="bold green")

            # Show available projects
            projects = client.get_projects()
            if projects:
                console.print("\n📁 Available Projects:")
                table = Table()
                table.add_column("Key", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Description", style="dim")

                for project in projects[:5]:  # Show first 5 projects
                    table.add_row(
                        project['key'],
                        project['name'],
                        project['description'][:50] + "..." if len(project['description']) > 50 else project['description']
                    )
                console.print(table)
        else:
            console.print("❌ JIRA connection failed!", style="bold red")

    except Exception as e:
        console.print(f"❌ Error testing JIRA connection: {e}", style="bold red")


@app.command()
def test_agents():
    """Test AI agents initialization"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        manager = AgentManager(cfg, client)

        status = manager.get_agent_status()

        console.print(Panel.fit("🤖 AI Agents Status", style="bold blue"))
        console.print(f"✅ Agents initialized: {status['agents_initialized']}")
        console.print(f"✅ Available agents: {', '.join(status['available_agents'])}")
        console.print(f"✅ JIRA connected: {status['jira_connected']}")

    except Exception as e:
        console.print(f"❌ Error testing agents: {e}", style="bold red")


@app.command()
def search(
        query: str = typer.Argument(..., help="JQL query or simple search"),
        project: Optional[str] = typer.Option(None, "--project", "-p", help="Project key"),
        max_results: int = typer.Option(10, "--max", "-m", help="Maximum results")
):
    """Search for JIRA issues"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)

        # If query looks like JQL, use it directly, otherwise build simple search
        if any(keyword in query.lower() for keyword in ['and', 'or', 'order by', '=']):
            jql = query
        else:
            jql = build_jql_query(
                project=project or cfg.project.default_project_key,
                text_search=query
            )

        console.print(f"🔍 Searching with JQL: {jql}")
        issues = client.search_issues(jql, max_results)

        if issues:
            console.print(f"\n📋 Found {len(issues)} issue(s):")
            table = Table()
            table.add_column("Key", style="cyan")
            table.add_column("Summary", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Assignee", style="yellow")

            for issue in issues:
                table.add_row(
                    issue['key'],
                    issue['summary'][:50] + "..." if len(issue['summary']) > 50 else issue['summary'],
                    issue['status'],
                    issue['assignee']
                )
            console.print(table)
        else:
            console.print("No issues found.", style="dim")

    except Exception as e:
        console.print(f"❌ Error searching issues: {e}", style="bold red")


@app.command()
def issue(issue_key: str):
    """Get details of a specific issue"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)

        issue = client.get_issue(issue_key)
        if issue:
            console.print(Panel.fit(f"📋 Issue Details: {issue['key']}", style="bold blue"))

            # Basic info
            console.print(f"**Summary:** {issue['summary']}")
            console.print(f"**Status:** {issue['status']}")
            console.print(f"**Priority:** {issue['priority']}")
            console.print(f"**Assignee:** {issue['assignee']}")
            console.print(f"**Reporter:** {issue['reporter']}")
            console.print(f"**Type:** {issue['issue_type']}")
            console.print(f"**Project:** {issue['project']}")
            console.print(f"**URL:** {issue['url']}")

            if issue['description']:
                console.print(f"\n**Description:**")
                console.print(issue['description'])

            if issue['labels']:
                console.print(f"\n**Labels:** {', '.join(issue['labels'])}")

        else:
            console.print(f"❌ Issue {issue_key} not found", style="bold red")

    except Exception as e:
        console.print(f"❌ Error getting issue details: {e}", style="bold red")


@app.command()
def version():
    """Show version information"""
    from . import __version__
    console.print(f"JIRA AI Assistant v{__version__}")


@app.command()
def query(
        text: str = typer.Argument(..., help="Natural language query"),
        project: Optional[str] = typer.Option(None, "--project", "-p", help="JIRA project key"),
):
    """Process a natural language query using AI agents"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        manager = AgentManager(cfg, client)

        console.print(Panel.fit("🤖 Processing Natural Language Query", style="bold yellow"))
        console.print(f"Query: {text}")
        if project:
            console.print(f"Project: {project}")

        # Process the query using AI agents
        with console.status("[bold green]Processing with AI agents..."):
            result = manager.process_natural_language_query(text, project)

        if result['success']:
            console.print(Panel.fit("✅ Query Result", style="bold green"))
            console.print(result['result'])
        else:
            console.print(Panel.fit("❌ Query Failed", style="bold red"))
            console.print(f"Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        console.print(f"❌ Error processing query: {e}", style="bold red")


if __name__ == "__main__":
    app()