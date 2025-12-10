"""
Progress tracker and statistics display
"""
import logging
import time
from typing import Dict
from datetime import datetime, timedelta
import config
from checkpoint import CheckpointManager

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks and displays parsing progress"""
    
    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_stats = {}
        self.processed_count = 0
    
    def update_progress(self, app_ids: list = None, status: str = None):
        """Update progress tracking"""
        if app_ids:
            self.processed_count += len(app_ids)
        else:
            self.processed_count += 1
        self.last_update_time = time.time()
    
    def get_current_stats(self) -> Dict:
        """Get current statistics"""
        stats = self.checkpoint_manager.get_progress()
        
        elapsed_time = time.time() - self.start_time
        
        # Calculate speed
        if elapsed_time > 0:
            speed_per_hour = (stats['completed'] / elapsed_time) * 3600
        else:
            speed_per_hour = 0
        
        # Estimate remaining time
        if speed_per_hour > 0 and stats['pending'] > 0:
            remaining_hours = stats['pending'] / speed_per_hour
        else:
            remaining_hours = 0
        
        stats.update({
            'elapsed_time': elapsed_time,
            'speed_per_hour': speed_per_hour,
            'remaining_hours': remaining_hours,
            'processed_count': self.processed_count
        })
        
        return stats
    
    def display_statistics(self, force: bool = False):
        """Display statistics to console"""
        stats = self.get_current_stats()
        
        # Only update if interval passed or forced
        if not force:
            time_since_update = time.time() - self.last_update_time
            if time_since_update < 10:  # Update at least every 10 seconds
                return
        
        self.last_stats = stats
        self.last_update_time = time.time()
        
        # Format elapsed time
        elapsed = timedelta(seconds=int(stats['elapsed_time']))
        remaining = timedelta(hours=int(stats['remaining_hours'])) if stats['remaining_hours'] > 0 else timedelta(0)
        
        # Calculate progress percentage
        if stats['total'] > 0:
            progress_pct = (stats['completed'] / stats['total']) * 100
        else:
            progress_pct = 0
        
        # Display statistics
        print("\n" + "=" * 70)
        print("📊 ПРОГРЕСС ПАРСИНГА")
        print("=" * 70)
        print(f"Обработано:     {stats['completed']:>8} / {stats['total']:>8} ({progress_pct:>5.1f}%)")
        print(f"Ожидает:        {stats['pending']:>8}")
        print(f"Ошибок:         {stats['errors']:>8}")
        print(f"")
        print(f"CCU записей:    {stats['ccu_records']:>8}")
        print(f"Price записей:  {stats['price_records']:>8}")
        print(f"")
        print(f"Скорость:       {stats['speed_per_hour']:>8.0f} APP IDs/час")
        print(f"Прошло времени: {str(elapsed):>20}")
        print(f"Осталось:       {str(remaining):>20}")
        print("=" * 70 + "\n")
        
        logger.info(
            f"Progress: {stats['completed']}/{stats['total']} ({progress_pct:.1f}%), "
            f"Speed: {stats['speed_per_hour']:.0f} APP IDs/hour, "
            f"Errors: {stats['errors']}"
        )
    
    def get_summary(self) -> str:
        """Get summary string"""
        stats = self.get_current_stats()
        elapsed = timedelta(seconds=int(stats['elapsed_time']))
        
        return (
            f"Completed: {stats['completed']}/{stats['total']}, "
            f"Speed: {stats['speed_per_hour']:.0f}/hour, "
            f"Time: {elapsed}, "
            f"Errors: {stats['errors']}"
        )

