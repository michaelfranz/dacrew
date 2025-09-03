"""CLI for Jira webhook ingestion."""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from .server import app
from .config import JiraIngestConfig

console = Console()


@click.group()
def cli():
    """Jira webhook ingestion CLI."""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8080, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host, port, reload):
    """Start the Jira webhook ingestion server."""
    try:
        console.print("🚀 Starting Jira webhook ingestion server...")
        console.print(f"📡 Host: {host}")
        console.print(f"🔌 Port: {port}")
        console.print(f"🔄 Reload: {reload}")
        
        import uvicorn
        uvicorn.run(
            "dacrew.jira_ingest.server:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        console.print("⏹️  Server stopped by user")
    except Exception as e:
        console.print(f"❌ Server failed: {e}", style="red")
        sys.exit(1)


@cli.command()
def config():
    """Show current configuration."""
    try:
        config = JiraIngestConfig.from_env()
        
        console.print("📋 Jira Ingest Configuration:")
        console.print(f"  Webhook Secret: {'*' * len(config.webhook_secret) if config.webhook_secret else 'Not set'}")
        console.print(f"  Webhook Endpoint: {config.webhook_endpoint}")
        console.print(f"  Host: {config.host}")
        console.print(f"  Port: {config.port}")
        console.print(f"  Log Directory: {config.log_dir}")
        console.print(f"  Redis URL: {config.redis_url}")
        
    except Exception as e:
        console.print(f"❌ Failed to load configuration: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
