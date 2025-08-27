#!/usr/bin/env python3
"""CLI tool for dacrew operations."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .config import AppConfig
from .embeddings import EmbeddingManager
from .service import EvaluationService

console = Console()


@click.group()
@click.option("--config", default="config.yml", help="Configuration file path")
@click.pass_context
def cli(ctx, config):
    """Dacrew CLI tool for managing embeddings and evaluations."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@cli.command()
@click.argument("project_id")
@click.pass_context
def update_embeddings(ctx, project_id):
    """Update embeddings for a specific project."""
    config_path = ctx.obj["config_path"]
    
    try:
        config = AppConfig.load(config_path)
        embedding_manager = EmbeddingManager(config)
        
        console.print(f"🔄 Updating embeddings for project {project_id}...")
        
        # Run the async function
        asyncio.run(embedding_manager.update_project_embeddings(project_id))
        
        console.print(f"✅ Embeddings updated successfully for project {project_id}")
        
    except Exception as e:
        console.print(f"❌ Error updating embeddings: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.pass_context
def list_projects(ctx):
    """List all configured projects."""
    config_path = ctx.obj["config_path"]
    
    try:
        config = AppConfig.load(config_path)
        
        table = Table(title="Configured Projects")
        table.add_column("Project ID", style="cyan")
        table.add_column("Codebase", style="green")
        table.add_column("Documents", style="yellow")
        table.add_column("Agent Mappings", style="magenta")
        
        for project in config.projects:
            has_codebase = "✅" if project.codebase else "❌"
            has_documents = "✅" if project.documents else "❌"
            mappings = ", ".join([
                f"{issue_type}:{status}→{agent}"
                for issue_type, status_map in project.type_status_map.items()
                for status, agent in status_map.items()
            ]) or "None"
            
            table.add_row(
                project.project_id,
                has_codebase,
                has_documents,
                mappings
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Error listing projects: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.argument("project_id")
@click.argument("issue_id")
@click.pass_context
def evaluate_issue(ctx, project_id, issue_id):
    """Evaluate a specific Jira issue."""
    config_path = ctx.obj["config_path"]
    
    try:
        config = AppConfig.load(config_path)
        service = EvaluationService(config)
        
        console.print(f"🔍 Evaluating issue {issue_id} in project {project_id}...")
        
        # Run the async function
        asyncio.run(service.enqueue(project_id, issue_id))
        
        console.print(f"✅ Issue {issue_id} queued for evaluation")
        
    except Exception as e:
        console.print(f"❌ Error evaluating issue: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.argument("project_id")
@click.argument("query")
@click.option("--top-k", default=5, help="Number of results to return")
@click.pass_context
def search_context(ctx, project_id, query, top_k):
    """Search for relevant context in project embeddings."""
    config_path = ctx.obj["config_path"]
    
    try:
        config = AppConfig.load(config_path)
        embedding_manager = EmbeddingManager(config)
        
        console.print(f"🔍 Searching for context in project {project_id}...")
        
        results = embedding_manager.get_relevant_context(project_id, query, top_k=top_k)
        
        if not results:
            console.print("❌ No relevant context found")
            return
        
        table = Table(title=f"Relevant Context for: {query}")
        table.add_column("Source", style="cyan")
        table.add_column("Similarity", style="green")
        table.add_column("Content", style="white")
        
        for result in results:
            content = result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
            table.add_row(
                result["source_type"],
                f"{result['similarity']:.3f}",
                content
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Error searching context: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx):
    """Show the status of all projects and their embeddings."""
    config_path = ctx.obj["config_path"]
    
    try:
        config = AppConfig.load(config_path)
        embedding_manager = EmbeddingManager(config)
        
        table = Table(title="Project Status")
        table.add_column("Project ID", style="cyan")
        table.add_column("Codebase Embeddings", style="green")
        table.add_column("Document Embeddings", style="yellow")
        table.add_column("Last Update", style="magenta")
        
        for project in config.projects:
            project_id = project.project_id
            
            # Check codebase embeddings
            codebase_file = embedding_manager.get_embedding_file(project_id, "codebase")
            codebase_status = "✅" if codebase_file.exists() else "❌"
            
            # Check document embeddings
            documents_file = embedding_manager.get_embedding_file(project_id, "documents")
            documents_status = "✅" if documents_file.exists() else "❌"
            
            # Get last update time
            last_update = "Never"
            if codebase_file.exists():
                metadata_file = embedding_manager.get_metadata_file(project_id, "codebase")
                if metadata_file.exists():
                    import json
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            last_update = metadata.get('last_update', 'Unknown')
                    except:
                        last_update = "Error"
            
            table.add_row(
                project_id,
                codebase_status,
                documents_status,
                last_update
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Error getting status: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
