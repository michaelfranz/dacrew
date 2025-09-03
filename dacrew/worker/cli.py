"""CLI for worker processing."""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from .consumer import IssueConsumer
from .config import WorkerConfig

console = Console()


@click.group()
def cli():
    """Worker processing CLI."""
    pass


@cli.command()
@click.option("--redis-url", help="Redis URL (overrides environment variable)")
@click.option("--batch-size", help="Number of messages to process in each batch (overrides environment variable)")
@click.option("--poll-interval", help="Poll interval in milliseconds (overrides environment variable)")
@click.option("--mock-processing", is_flag=True, help="Enable mock processing (overrides environment variable)")
def run(redis_url, batch_size, poll_interval, mock_processing):
    """Run a worker process."""
    try:
        # Load configuration from environment
        config = WorkerConfig.from_env()
        
        # Override with command line arguments if provided
        if redis_url:
            config.redis_url = redis_url
        if batch_size:
            config.batch_size = int(batch_size)
        if poll_interval:
            config.poll_interval_ms = int(poll_interval)
        if mock_processing is not None:
            config.mock_processing = mock_processing
        
        console.print("🚀 Starting worker...")
        console.print(f"🔗 Redis: {config.redis_url}")
        console.print(f"📦 Batch size: {config.batch_size}")
        console.print(f"⏱️  Poll interval: {config.poll_interval_ms}ms")
        console.print(f"🎭 Mock processing: {config.mock_processing}")
        
        # Create and run consumer
        consumer = IssueConsumer(config)
        asyncio.run(consumer.run())
        
    except KeyboardInterrupt:
        console.print("⏹️  Worker stopped by user")
    except Exception as e:
        console.print(f"❌ Worker failed: {e}", style="red")
        sys.exit(1)


@cli.command()
def config():
    """Show current configuration."""
    try:
        config = WorkerConfig.from_env()
        
        console.print("📋 Worker Configuration:")
        console.print(f"  Redis URL: {config.redis_url}")
        console.print(f"  Batch Size: {config.batch_size}")
        console.print(f"  Poll Interval: {config.poll_interval_ms}ms")
        console.print(f"  Mock Processing: {config.mock_processing}")
        console.print(f"  Log Directory: {config.log_dir}")
        console.print(f"  Agent Timeout: {config.agent_timeout}s")
        console.print(f"  Max Retries: {config.max_retries}")
        
    except Exception as e:
        console.print(f"❌ Failed to load configuration: {e}", style="red")
        sys.exit(1)


@cli.command()
@click.option("--num-workers", default=1, help="Number of workers to start")
def run_multiple(num_workers):
    """Run multiple worker processes."""
    try:
        console.print(f"🚀 Starting {num_workers} worker(s)...")
        
        # Create configuration
        config = WorkerConfig.from_env()
        
        # Create and run multiple consumers
        consumers = []
        for i in range(num_workers):
            consumer = IssueConsumer(config)
            consumers.append(consumer)
        
        # Run all consumers concurrently
        tasks = [consumer.run() for consumer in consumers]
        asyncio.run(asyncio.gather(*tasks))
        
    except KeyboardInterrupt:
        console.print("⏹️  Workers stopped by user")
    except Exception as e:
        console.print(f"❌ Workers failed: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
