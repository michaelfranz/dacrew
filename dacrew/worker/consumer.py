"""Work consumer for processing queued DacrewWork messages.

This module implements a competing consumer that:
- Subscribes to the DacrewWork queue
- Processes messages asynchronously
- Handles failures gracefully
- Provides monitoring and statistics
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any, Optional
from datetime import datetime

from ..models.queue import DacrewWorkQueue
from ..models import DacrewWork
from ..common import setup_logging
from .config import WorkerConfig

logger = logging.getLogger(__name__)


class IssueConsumer:
    """Consumer for processing DacrewWork messages."""
    
    def __init__(self, config: Optional[WorkerConfig] = None):
        """Initialize the consumer."""
        self.config = config or WorkerConfig.from_env()
        self.queue = DacrewWorkQueue(self.config.redis_url)
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        self.start_time = None
        
        # Setup logging
        setup_logging(self.config.log_dir)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    async def process_message(self, message_id: str, message_data: Dict[str, Any]) -> bool:
        """Process a single DacrewWork message."""
        try:
            # Parse the message
            work_data_json = message_data.get("work_data")
            if not work_data_json:
                logger.error(f"Message {message_id} has no work_data")
                return False
            
            dacrew_work = DacrewWork.model_validate_json(work_data_json)
            logger.info(f"Processing DacrewWork {dacrew_work.id} (message {message_id})")
            
            # Process the DacrewWork (this is where your business logic goes)
            success = await self._process_work(dacrew_work)
            
            if success:
                # Acknowledge the message
                self.queue.acknowledge_message(message_id)
                self.processed_count += 1
                logger.info(f"Successfully processed DacrewWork {dacrew_work.id}")
                return True
            else:
                logger.error(f"Failed to process DacrewWork {dacrew_work.id}")
                self.error_count += 1
                return False
                
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            self.error_count += 1
            return False
    
    async def _process_work(self, dacrew_work: DacrewWork) -> bool:
        """Process a DacrewWork object with business logic."""
        try:
            logger.info(f"Processing DacrewWork from {dacrew_work.source}")
            
            # TODO: Replace this with your actual processing logic
            # For now, we'll use a mock implementation
            await self._mock_process_work(dacrew_work)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in work processing: {e}")
            return False
    
    async def _mock_process_work(self, dacrew_work: DacrewWork) -> None:
        """Mock processing function for testing."""
        logger.info(f"[MOCK] Starting processing for DacrewWork {dacrew_work.id}")
        logger.info(f"[MOCK] Source: {dacrew_work.source}")
        logger.info(f"[MOCK] Created at: {dacrew_work.created_at}")
        
        # Extract information based on source
        if dacrew_work.source == "Jira":
            jira_model = dacrew_work.payload
            if jira_model.issue and jira_model.issue.fields:
                fields = jira_model.issue.fields
                
                # Extract basic issue information
                issue_type = fields.issuetype.name
                status = fields.status.name
                summary = fields.summary
                description = fields.description or "no description"
                priority = fields.priority.name
                assignee = fields.assignee.displayName if fields.assignee else "unassigned"
                
                logger.info(f"[MOCK] Issue Type: {issue_type}")
                logger.info(f"[MOCK] Status: {status}")
                logger.info(f"[MOCK] Priority: {priority}")
                logger.info(f"[MOCK] Assignee: {assignee}")
                logger.info(f"[MOCK] Summary: {summary}")
                logger.info(f"[MOCK] Description length: {len(description)} characters")
                logger.info(f"[MOCK] Webhook Event: {jira_model.webhookEvent}")
                
                # Log changelog information if available
                if jira_model.changelog and jira_model.changelog.items:
                    logger.info(f"[MOCK] Changelog items: {len(jira_model.changelog.items)}")
                    for item in jira_model.changelog.items:
                        logger.info(f"[MOCK] Changed field: {item.field} from '{item.fromString}' to '{item.toString}'")
            else:
                logger.info(f"[MOCK] No issue data available in Jira model")
        
        elif dacrew_work.source == "Github":
            github_model = dacrew_work.payload
            logger.info(f"[MOCK] Repository: {github_model.repository}")
            logger.info(f"[MOCK] Action: {github_model.action}")
            logger.info(f"[MOCK] Sender: {github_model.sender}")
        
        else:
            logger.info(f"[MOCK] Unknown source type: {dacrew_work.source}")
        
        # Simulate processing time (realistic for LLM operations)
        await asyncio.sleep(2.5)  # Simulate 2.5 seconds processing time
        
        # Log what would happen in real processing
        logger.info(f"[MOCK] Would select appropriate agent based on work content")
        logger.info(f"[MOCK] Would evaluate work with context")
        logger.info(f"[MOCK] Would perform agentic tasks")
        logger.info(f"[MOCK] Would update source system if needed")
        
        logger.info(f"[MOCK] Processing completed for DacrewWork {dacrew_work.id}")
    
    async def run(self, batch_size: Optional[int] = None, poll_interval_ms: Optional[int] = None):
        """Run the consumer loop."""
        self.running = True
        self.start_time = datetime.now()
        
        # Use config values or provided parameters
        batch_size = batch_size or self.config.batch_size
        poll_interval_ms = poll_interval_ms or self.config.poll_interval_ms
        
        logger.info(f"Starting work consumer (PID: {os.getpid()})")
        logger.info(f"Batch size: {batch_size}, Poll interval: {poll_interval_ms}ms")
        
        try:
            while self.running:
                try:
                    # Read messages from the queue
                    messages = self.queue.read_messages(count=batch_size, block_ms=poll_interval_ms)
                    
                    if messages:
                        logger.info(f"Processing batch of {len(messages)} messages")
                        
                        # Process messages concurrently
                        tasks = []
                        for message_id, message_data in messages:
                            task = asyncio.create_task(
                                self.process_message(message_id, message_data)
                            )
                            tasks.append(task)
                        
                        # Wait for all tasks to complete
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        # Log results
                        successful = sum(1 for r in results if r is True)
                        failed = len(results) - successful
                        logger.info(f"Batch completed: {successful} successful, {failed} failed")
                    
                    # Periodically claim orphaned messages
                    if self.processed_count % 50 == 0:  # Every 50 messages
                        orphaned = self.queue.claim_orphaned_messages()
                        if orphaned:
                            logger.info(f"Claimed {len(orphaned)} orphaned messages")
                    
                    # Log statistics periodically
                    if self.processed_count % 100 == 0:  # Every 100 messages
                        self._log_statistics()
                        
                except Exception as e:
                    logger.error(f"Error in consumer loop: {e}")
                    await asyncio.sleep(1)  # Brief pause before retrying
        
        finally:
            self._log_final_statistics()
            logger.info("Consumer stopped")
    
    def _log_statistics(self):
        """Log current statistics."""
        if self.start_time:
            uptime = datetime.now() - self.start_time
            rate = self.processed_count / uptime.total_seconds() if uptime.total_seconds() > 0 else 0
            
            logger.info(f"Statistics: {self.processed_count} processed, {self.error_count} errors, "
                       f"{rate:.2f} msg/sec, uptime: {uptime}")
    
    def _log_final_statistics(self):
        """Log final statistics on shutdown."""
        if self.start_time:
            uptime = datetime.now() - self.start_time
            rate = self.processed_count / uptime.total_seconds() if uptime.total_seconds() > 0 else 0
            
            logger.info(f"Final Statistics:")
            logger.info(f"  Total processed: {self.processed_count}")
            logger.info(f"  Total errors: {self.error_count}")
            logger.info(f"  Processing rate: {rate:.2f} msg/sec")
            logger.info(f"  Uptime: {uptime}")
            
            # Get queue stats
            stats = self.queue.get_queue_stats()
            logger.info(f"  Queue stats: {stats}")


async def main():
    """Main entry point for the consumer."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create and run consumer
        config = WorkerConfig.from_env()
        consumer = IssueConsumer(config)
        await consumer.run()
        
    except KeyboardInterrupt:
        logger.info("Consumer interrupted by user")
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
