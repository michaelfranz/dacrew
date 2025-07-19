"""Command Line Interface for JIRA AI Assistant"""

from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents import AgentManager
from .config import Config
from .jira_client import JIRAClient
from .utils import build_jql_query
from .vector_db.vector_manager import VectorManager

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
        console.print(f"Vector DB Path: {cfg.ai.chroma_persist_directory}")
    except Exception as e:
        console.print(f"❌ Error loading configuration: {e}", style="bold red")


@app.command()
def test_connection():
    """Test all connections (JIRA, Vector DB, AI Agents)"""
    console.print(Panel.fit("🧪 Testing System Connections", style="bold blue"))
    
    try:
        cfg = Config.load()
        
        # Test JIRA
        console.print("Testing JIRA connection...", style="dim")
        client = JIRAClient(cfg)
        if client.test_connection():
            console.print("✅ JIRA connection successful", style="green")
        else:
            console.print("❌ JIRA connection failed", style="red")
            return
        
        # Test Vector DB
        console.print("Testing Vector Database...", style="dim")
        try:
            vector_manager = VectorManager(cfg)
            stats = vector_manager.get_collection_stats()
            console.print(f"✅ Vector DB initialized ({stats.get('total_issues', 0)} issues)", style="green")
        except Exception as e:
            console.print(f"⚠️ Vector DB not available: {e}", style="yellow")
            vector_manager = None
        
        # Test AI Agents
        console.print("Testing AI Agents...", style="dim")
        manager = AgentManager(cfg, client, vector_manager)
        status = manager.get_agent_status()
        console.print(f"✅ AI Agents initialized ({len(status['available_agents'])} agents)", style="green")
        
        console.print("\n🎉 System is ready!", style="bold green")
        
    except Exception as e:
        console.print(f"❌ System test failed: {e}", style="bold red")


@app.command()
def show_projects():
    """List all accessible JIRA projects"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        
        projects = client.get_projects()
        if projects:
            console.print(Panel.fit("📁 JIRA Projects", style="bold blue"))
            
            table = Table()
            table.add_column("Key", style="cyan", no_wrap=True)
            table.add_column("Name", style="magenta")
            table.add_column("Description", style="dim")
            
            for project in projects:
                desc = project['description']
                if len(desc) > 60:
                    desc = desc[:60] + "..."
                
                table.add_row(
                    project['key'],
                    project['name'],
                    desc
                )
            console.print(table)
        else:
            console.print("No projects found.", style="dim")
            
    except Exception as e:
        console.print(f"❌ Error getting projects: {e}", style="bold red")


@app.command()
def show_metadata(
        project: Optional[str] = typer.Option(None, "--project", "-p", help="Project key")
):
    """Show available issue types, priorities, and other metadata"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)

        console.print(Panel.fit("📊 JIRA Metadata", style="bold blue"))

        # Show issue types
        issue_types = client.get_issue_types(project)
        if issue_types:
            console.print("\n🏷️ Available Issue Types:")
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="dim")

            for it in issue_types:
                table.add_row(
                    it['name'],
                    it['description'][:50] + "..." if len(it['description']) > 50 else it['description']
                )
            console.print(table)

        # Show priorities
        priorities = client.get_priorities()
        if priorities:
            console.print("\n⚡ Available Priorities:")
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="dim")

            for p in priorities:
                table.add_row(
                    p['name'],
                    p['description'][:50] + "..." if len(p['description']) > 50 else p['description']
                )
            console.print(table)

        # Show statuses
        statuses = client.get_statuses()
        if statuses:
            console.print("\n🔄 Available Statuses:")
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Description", style="dim")

            for s in statuses:
                table.add_row(
                    s['name'],
                    s['description'][:50] + "..." if len(s['description']) > 50 else s['description']
                )
            console.print(table)

    except Exception as e:
        console.print(f"❌ Error getting metadata: {e}", style="bold red")


@app.command()
def create_issue(
        summary: str = typer.Argument(..., help="Issue summary"),
        project: str = typer.Option(..., "--project", "-p", help="Project key"),
        issue_type: str = typer.Option("Task", "--type", "-t", help="Issue type"),
        priority: Optional[str] = typer.Option(None, "--priority", help="Priority"),
        assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="Assignee username"),
        description: Optional[str] = typer.Option(None, "--description", "-d", help="Issue description"),
        labels: Optional[List[str]] = typer.Option(None, "--label", "-l", help="Labels (can be used multiple times)"),
        interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode")
):
    """Create a new JIRA issue"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        
        if interactive:
            console.print(Panel.fit("📝 Create New Issue (Interactive)", style="bold blue"))
            
            # Get project if not provided
            if not project:
                projects = client.get_projects()
                if projects:
                    console.print("Available projects:")
                    for p in projects[:10]:  # Show first 10
                        console.print(f"  {p['key']}: {p['name']}")
                project = Prompt.ask("Enter project key")
            
            # Get issue type
            issue_types = client.get_issue_types(project)
            if issue_types:
                console.print("\nAvailable issue types:")
                for it in issue_types:
                    console.print(f"  {it['name']}")
                issue_type = Prompt.ask("Enter issue type", default="Task")
            
            # Get priority
            priorities = client.get_priorities()
            if priorities:
                console.print("\nAvailable priorities:")
                for p in priorities:
                    console.print(f"  {p['name']}")
                priority = Prompt.ask("Enter priority (optional)", default="")
                if not priority:
                    priority = None
            
            # Get other fields
            if not summary:
                summary = Prompt.ask("Enter summary")
            if not description:
                description = Prompt.ask("Enter description (optional)", default="")
                if not description:
                    description = None
            if not assignee:
                assignee = Prompt.ask("Enter assignee (optional)", default="")
                if not assignee:
                    assignee = None
        
        # Prepare issue data
        issue_data = {}
        if priority:
            issue_data['priority'] = {'name': priority}
        if assignee:
            issue_data['assignee'] = {'name': assignee}
        if labels:
            issue_data['labels'] = labels
        
        console.print(f"\n📝 Creating issue in project {project}...")
        
        with console.status("[bold green]Creating issue..."):
            issue = client.create_issue(
                project_key=project,
                summary=summary,
                description=description or "",
                issue_type=issue_type,
                **issue_data
            )
        
        if issue:
            console.print(f"✅ Issue created successfully: {issue['key']}", style="bold green")
            console.print(f"Summary: {issue['summary']}")
            console.print(f"URL: {issue['url']}")
        else:
            console.print("❌ Failed to create issue", style="bold red")
            
    except Exception as e:
        console.print(f"❌ Error creating issue: {e}", style="bold red")


@app.command()
def update_issue(
        issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
        summary: Optional[str] = typer.Option(None, "--summary", "-s", help="New summary"),
        description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
        priority: Optional[str] = typer.Option(None, "--priority", "-p", help="New priority"),
        assignee: Optional[str] = typer.Option(None, "--assignee", "-a", help="New assignee"),
        add_labels: Optional[List[str]] = typer.Option(None, "--add-label", help="Add labels"),
        remove_labels: Optional[List[str]] = typer.Option(None, "--remove-label", help="Remove labels"),
        interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode")
):
    """Update an existing JIRA issue"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        
        if not validate_issue_key(issue_key):
            console.print(f"❌ Invalid issue key format: {issue_key}", style="bold red")
            return
        
        # Get current issue details
        current_issue = client.get_issue(issue_key)
        if not current_issue:
            console.print(f"❌ Issue {issue_key} not found", style="bold red")
            return
        
        if interactive:
            console.print(Panel.fit(f"✏️ Update Issue: {issue_key}", style="bold blue"))
            console.print(f"Current summary: {current_issue['summary']}")
            console.print(f"Current assignee: {current_issue['assignee']}")
            console.print(f"Current priority: {current_issue['priority']}")
            
            if Confirm.ask("\nUpdate summary?"):
                summary = Prompt.ask("Enter new summary", default=current_issue['summary'])
            
            if Confirm.ask("Update assignee?"):
                assignee = Prompt.ask("Enter new assignee", default=current_issue['assignee'])
            
            if Confirm.ask("Update priority?"):
                priorities = client.get_priorities()
                console.print("Available priorities:")
                for p in priorities:
                    console.print(f"  {p['name']}")
                priority = Prompt.ask("Enter new priority", default=current_issue['priority'])
        
        # Build update fields
        fields = {}
        if summary:
            fields['summary'] = summary
        if description:
            fields['description'] = description
        if priority:
            fields['priority'] = {'name': priority}
        if assignee:
            fields['assignee'] = {'name': assignee}
        
        if not fields and not add_labels and not remove_labels:
            console.print("No changes specified", style="yellow")
            return
        
        console.print(f"\n✏️ Updating issue {issue_key}...")
        
        with console.status("[bold green]Updating issue..."):
            success = client.update_issue(issue_key, **fields)
        
        if success:
            console.print(f"✅ Issue {issue_key} updated successfully", style="bold green")
        else:
            console.print(f"❌ Failed to update issue {issue_key}", style="bold red")
            
    except Exception as e:
        console.print(f"❌ Error updating issue: {e}", style="bold red")


@app.command()
def transition_issue(
        issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
        status: Optional[str] = typer.Option(None, "--status", "-s", help="Target status"),
        interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode")
):
    """Transition an issue to a new status"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        
        if not validate_issue_key(issue_key):
            console.print(f"❌ Invalid issue key format: {issue_key}", style="bold red")
            return
        
        # Get available transitions
        transitions = client.get_transitions(issue_key)
        if not transitions:
            console.print(f"❌ No transitions available for {issue_key}", style="bold red")
            return
        
        if interactive or not status:
            console.print(Panel.fit(f"🔄 Transition Issue: {issue_key}", style="bold blue"))
            console.print("Available transitions:")
            
            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("To Status", style="green")
            
            for t in transitions:
                table.add_row(t['id'], t['name'], t['to'])
            
            console.print(table)
            
            if not status:
                transition_id = Prompt.ask("Enter transition ID")
            else:
                # Find transition by status name
                transition_id = None
                for t in transitions:
                    if t['to'].lower() == status.lower():
                        transition_id = t['id']
                        break
                
                if not transition_id:
                    console.print(f"❌ No transition found to status '{status}'", style="bold red")
                    return
        else:
            # Find transition by status name
            transition_id = None
            for t in transitions:
                if t['to'].lower() == status.lower():
                    transition_id = t['id']
                    break
            
            if not transition_id:
                console.print(f"❌ No transition found to status '{status}'", style="bold red")
                console.print("Available transitions:")
                for t in transitions:
                    console.print(f"  {t['name']} -> {t['to']}")
                return
        
        console.print(f"\n🔄 Transitioning issue {issue_key}...")
        
        with console.status("[bold green]Transitioning issue..."):
            success = client.transition_issue(issue_key, transition_id)
        
        if success:
            console.print(f"✅ Issue {issue_key} transitioned successfully", style="bold green")
        else:
            console.print(f"❌ Failed to transition issue {issue_key}", style="bold red")
            
    except Exception as e:
        console.print(f"❌ Error transitioning issue: {e}", style="bold red")


@app.command()
def add_comment(
        issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)"),
        comment: str = typer.Argument(..., help="Comment text"),
        interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode")
):
    """Add a comment to an issue"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        
        if not validate_issue_key(issue_key):
            console.print(f"❌ Invalid issue key format: {issue_key}", style="bold red")
            return
        
        if interactive:
            console.print(Panel.fit(f"💬 Add Comment to: {issue_key}", style="bold blue"))
            comment = Prompt.ask("Enter comment")
        
        console.print(f"\n💬 Adding comment to {issue_key}...")
        
        with console.status("[bold green]Adding comment..."):
            success = client.add_comment(issue_key, comment)
        
        if success:
            console.print(f"✅ Comment added to {issue_key}", style="bold green")
        else:
            console.print(f"❌ Failed to add comment to {issue_key}", style="bold red")
            
    except Exception as e:
        console.print(f"❌ Error adding comment: {e}", style="bold red")


@app.command()
def show_comments(issue_key: str = typer.Argument(..., help="Issue key (e.g., PROJ-123)")):
    """Show all comments for an issue"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        
        if not validate_issue_key(issue_key):
            console.print(f"❌ Invalid issue key format: {issue_key}", style="bold red")
            return
        
        comments = client.get_issue_comments(issue_key)
        
        if comments:
            console.print(Panel.fit(f"💬 Comments for {issue_key}", style="bold blue"))
            
            for i, comment in enumerate(comments, 1):
                console.print(f"\n**Comment #{i}** by **{comment['author']}** ({comment['created']})")
                console.print(f"{comment['body']}")
                console.print("─" * 60)
        else:
            console.print(f"No comments found for {issue_key}", style="dim")
            
    except Exception as e:
        console.print(f"❌ Error getting comments: {e}", style="bold red")


@app.command()
def sync(
        project: Optional[str] = typer.Option(None, "--project", "-p", help="Project key to sync"),
        force_refresh: bool = typer.Option(False, "--force", "-f", help="Force full refresh")
):
    """Sync JIRA issues with vector database"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)
        vector_manager = VectorManager(cfg)

        console.print(Panel.fit("🔄 Syncing Vector Database", style="bold yellow"))

        with console.status("[bold green]Syncing issues..."):
            result = vector_manager.sync_with_jira(
                jira_client=client,
                project_key=project,
                force_refresh=force_refresh
            )

        if result['success']:
            console.print(f"✅ Successfully synced {result.get('added', 0)} issues")

            # Show updated stats
            stats = vector_manager.get_collection_stats()
            console.print(f"📊 Total issues in vector DB: {stats.get('total_issues', 0)}")
        else:
            console.print(f"❌ Sync failed: {result.get('error', 'Unknown error')}")

    except Exception as e:
        console.print(f"❌ Error syncing vector database: {e}", style="bold red")


@app.command()
def semantic_search(
        query: str = typer.Argument(..., help="Search query"),
        max_results: int = typer.Option(10, "--max", "-m", help="Maximum results"),
        project: Optional[str] = typer.Option(None, "--project", "-p", help="Project filter"),
        status: Optional[str] = typer.Option(None, "--status", "-s", help="Status filter")
):
    """Perform semantic search on JIRA issues"""
    try:
        cfg = Config.load()
        vector_manager = VectorManager(cfg)

        console.print(f"🔍 Semantic search: {query}")

        # Prepare filters
        filters = {}
        if project:
            filters['project'] = project
        if status:
            filters['status'] = status

        results = vector_manager.semantic_search(
            query=query,
            n_results=max_results,
            filters=filters
        )

        if results:
            console.print(f"\n📋 Found {len(results)} similar issues:")
            table = Table()
            table.add_column("Key", style="cyan")
            table.add_column("Summary", style="magenta")
            table.add_column("Similarity", style="green")
            table.add_column("Status", style="yellow")

            for result in results:
                metadata = result['metadata']
                similarity = f"{result['similarity_score']:.2f}"

                table.add_row(
                    metadata['issue_key'],
                    metadata['summary'][:50] + "..." if len(metadata['summary']) > 50 else metadata['summary'],
                    similarity,
                    metadata['status']
                )
            console.print(table)
        else:
            console.print("No similar issues found.", style="dim")

    except Exception as e:
        console.print(f"❌ Error performing semantic search: {e}", style="bold red")


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
            console.print(f"**Created:** {issue['created']}")
            console.print(f"**Updated:** {issue['updated']}")
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
def query(
        text: str = typer.Argument(..., help="Natural language query"),
        project: Optional[str] = typer.Option(None, "--project", "-p", help="JIRA project key"),
):
    """Process a natural language query using AI agents"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)

        # Initialize vector manager
        try:
            vector_manager = VectorManager(cfg)
        except Exception as e:
            console.print(f"⚠️ Vector database not available: {e}", style="yellow")
            vector_manager = None

        manager = AgentManager(cfg, client, vector_manager)

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


@app.command()
def version():
    """Show version information"""
    from . import __version__
    console.print(f"🚀 JIRA AI Assistant v{__version__}")
    console.print("AI-powered natural language interface for JIRA")


@app.command()
def bulk_update(
        jql: str = typer.Argument(..., help="JQL query to select issues"),
        field: str = typer.Option(..., "--field", "-f", help="Field to update (assignee, priority, status, etc.)"),
        value: str = typer.Option(..., "--value", "-v", help="New value for the field"),
        dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be changed without making changes")
):
    """Bulk update issues matching a JQL query"""
    try:
        cfg = Config.load()
        client = JIRAClient(cfg)

        console.print(f"🔍 Finding issues with JQL: {jql}")
        issues = client.search_issues(jql, max_results=100)

        if not issues:
            console.print("No issues found matching the query", style="dim")
            return

        console.print(f"📋 Found {len(issues)} issues to update")

        if dry_run:
            console.print("**DRY RUN - No changes will be made**", style="yellow")
            table = Table()
            table.add_column("Key", style="cyan")
            table.add_column("Summary", style="magenta")
            table.add_column("Current", style="red")
            table.add_column("New", style="green")

            for issue in issues:
                current_value = issue.get(field, 'N/A')
                table.add_row(
                    issue['key'],
                    issue['summary'][:40] + "..." if len(issue['summary']) > 40 else issue['summary'],
                    str(current_value),
                    value
                )
            console.print(table)
            console.print(f"\nTo execute these changes, run with --execute flag")
        else:
            if not Confirm.ask(f"Update {len(issues)} issues?"):
                console.print("Cancelled", style="yellow")
                return

            success_count = 0
            failed_count = 0

            with console.status(f"[bold green]Updating {len(issues)} issues..."):
                for issue in issues:
                    try:
                        update_fields = {field: value}
                        if client.update_issue(issue['key'], **update_fields):
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        console.print(f"❌ Failed to update {issue['key']}: {e}")
                        failed_count += 1

            console.print(f"✅ Successfully updated: {success_count}", style="green")
            if failed_count > 0:
                console.print(f"❌ Failed to update: {failed_count}", style="red")

    except Exception as e:
        console.print(f"❌ Error in bulk update: {e}", style="bold red")


if __name__ == "__main__":
    app()