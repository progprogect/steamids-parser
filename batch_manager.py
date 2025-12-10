"""
Batch manager for grouping APP IDs for Compare requests
"""
import logging
from typing import List, Optional
import config

logger = logging.getLogger(__name__)


class BatchManager:
    """Manages batches of APP IDs for Compare requests"""
    
    def __init__(self, app_ids: List[int], batch_size: int = None):
        self.app_ids = app_ids
        self.batch_size = batch_size or config.COMPARE_BATCH_SIZE
        self.batches = self._create_batches()
        self.processed_batches = set()
        self.current_index = 0
    
    def _create_batches(self) -> List[List[int]]:
        """Create batches from APP IDs list"""
        batches = []
        for i in range(0, len(self.app_ids), self.batch_size):
            batch = self.app_ids[i:i + self.batch_size]
            batches.append(batch)
        
        logger.info(f"Created {len(batches)} batches from {len(self.app_ids)} APP IDs")
        return batches
    
    def get_next_batch(self) -> Optional[List[int]]:
        """Get next unprocessed batch"""
        while self.current_index < len(self.batches):
            batch = self.batches[self.current_index]
            batch_key = tuple(batch)
            
            if batch_key not in self.processed_batches:
                self.current_index += 1
                return batch
            
            self.current_index += 1
        
        return None
    
    def mark_batch_processed(self, batch: List[int]):
        """Mark batch as processed"""
        batch_key = tuple(batch)
        self.processed_batches.add(batch_key)
        logger.debug(f"Marked batch with {len(batch)} APP IDs as processed")
    
    def get_pending_batches(self) -> List[List[int]]:
        """Get all pending batches"""
        pending = []
        for i, batch in enumerate(self.batches):
            batch_key = tuple(batch)
            if batch_key not in self.processed_batches:
                pending.append(batch)
        return pending
    
    def has_pending_batches(self) -> bool:
        """Check if there are pending batches"""
        return len(self.get_pending_batches()) > 0
    
    def get_progress(self) -> dict:
        """Get batch processing progress"""
        total = len(self.batches)
        processed = len(self.processed_batches)
        pending = total - processed
        
        return {
            'total_batches': total,
            'processed_batches': processed,
            'pending_batches': pending,
            'progress_percent': (processed / total * 100) if total > 0 else 0
        }

