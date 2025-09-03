"""Redis-based message queue for Dacrew work processing.

This module provides a competing consumers architecture where:
- The ingest servers enqueue DacrewWork objects to Redis Streams
- Multiple worker processes can subscribe and process work independently
- Messages are reliably delivered and acknowledged
"""

import json
import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import redis

from .dacrew_work import DacrewWork

logger = logging.getLogger(__name__)

# Retry configuration
QUEUE_RETRY_COUNT = 3


class DacrewWorkQueue:
    """Redis-based queue for Dacrew work processing."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize the queue with Redis connection."""
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.stream_name = "dacrew_work_queue"
        self.group_name = "dacrew_work_consumers"
        self.consumer_name = f"consumer_{os.getpid()}"
        
        # Initialize Redis connection
        self.redis = redis.from_url(self.redis_url, decode_responses=True)
        
        # Ensure consumer group exists
        self._ensure_consumer_group()
    
    def _ensure_consumer_group(self) -> None:
        """Ensure the consumer group exists."""
        try:
            # Try to create the consumer group
            self.redis.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
            logger.info(f"Created consumer group '{self.group_name}' for stream '{self.stream_name}'")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group '{self.group_name}' already exists")
            else:
                logger.error(f"Error creating consumer group: {e}")
                raise
    
    def enqueue_dacrew_work(self, dacrew_work: DacrewWork) -> str:
        """Enqueue a DacrewWork object for processing."""
        for attempt in range(QUEUE_RETRY_COUNT):
            try:
                # Add to Redis stream
                message_id = self.redis.xadd(
                    self.stream_name,
                    {
                        "work_id": dacrew_work.id,
                        "source": dacrew_work.source,
                        "work_data": dacrew_work.model_dump_json(),
                        "created_at": dacrew_work.created_at.isoformat()
                    }
                )
                
                logger.info(f"Enqueued DacrewWork {dacrew_work.id} with message ID {message_id}")
                return message_id
                
            except Exception as e:
                logger.error(f"Failed to enqueue DacrewWork (attempt {attempt + 1}/{QUEUE_RETRY_COUNT}): {e}")
                if attempt == QUEUE_RETRY_COUNT - 1:
                    raise
                # Brief pause before retry
                import time
                time.sleep(0.1 * (attempt + 1))
    
    def get_pending_messages(self, count: int = 10) -> List[Tuple[str, Dict[str, Any]]]:
        """Get pending messages for this consumer."""
        try:
            # Get pending messages for this consumer
            pending = self.redis.xpending_range(
                self.stream_name,
                self.group_name,
                "-", "+", count,
                self.consumer_name
            )
            
            messages = []
            for msg in pending:
                message_id = msg["message_id"]
                # Get the actual message data
                message_data = self.redis.xrange(self.stream_name, message_id, message_id)
                if message_data:
                    messages.append((message_id, message_data[0][1]))
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get pending messages: {e}")
            return []
    
    def read_messages(self, count: int = 10, block_ms: int = 5000) -> List[Tuple[str, Dict[str, Any]]]:
        """Read new messages from the stream."""
        try:
            # Read messages from the stream
            messages = self.redis.xreadgroup(
                self.group_name,
                self.consumer_name,
                {self.stream_name: ">"},
                count=count,
                block=block_ms
            )
            
            if not messages:
                return []
            
            # Extract message data
            result = []
            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    result.append((message_id, message_data))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to read messages: {e}")
            return []
    
    def acknowledge_message(self, message_id: str) -> bool:
        """Acknowledge a processed message."""
        try:
            self.redis.xack(self.stream_name, self.group_name, message_id)
            logger.debug(f"Acknowledged message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False
    
    def claim_orphaned_messages(self, min_idle_time_ms: int = 60000) -> List[Tuple[str, Dict[str, Any]]]:
        """Claim messages that have been idle for too long."""
        try:
            # Get pending messages for all consumers
            pending = self.redis.xpending_range(
                self.stream_name,
                self.group_name,
                "-", "+", 100  # Get up to 100 pending messages
            )
            
            # Filter for orphaned messages
            orphaned_ids = []
            for msg in pending:
                if msg["idle"] > min_idle_time_ms:
                    orphaned_ids.append(msg["message_id"])
            
            if not orphaned_ids:
                return []
            
            # Claim orphaned messages
            claimed = self.redis.xclaim(
                self.stream_name,
                self.group_name,
                self.consumer_name,
                min_idle_time_ms,
                orphaned_ids
            )
            
            # Convert to our format
            messages = []
            for message_id, message_data in claimed:
                messages.append((message_id, message_data))
            
            if messages:
                logger.info(f"Claimed {len(messages)} orphaned messages")
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to claim orphaned messages: {e}")
            return []
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        try:
            # Get stream info
            stream_info = self.redis.xinfo_stream(self.stream_name)
            
            # Get consumer group info
            group_info = self.redis.xinfo_groups(self.stream_name)
            
            # Get pending messages count
            pending = self.redis.xpending(self.stream_name, self.group_name)
            
            return {
                "stream_length": stream_info.get("length", 0),
                "stream_groups": len(group_info),
                "pending_messages": pending.get("pending", 0),
                "consumers": len(pending.get("consumers", [])),
                "last_generated_id": stream_info.get("last-generated-id", "0-0")
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}


# Global queue instance
_queue_instance: Optional[DacrewWorkQueue] = None


def get_queue() -> DacrewWorkQueue:
    """Get the global queue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = DacrewWorkQueue()
    return _queue_instance


def enqueue_dacrew_work(dacrew_work: DacrewWork) -> str:
    """Convenience function to enqueue a DacrewWork object."""
    return get_queue().enqueue_dacrew_work(dacrew_work)
