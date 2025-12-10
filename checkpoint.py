"""
Checkpoint manager for tracking parsing progress
"""
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import config
from database import Database

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoint and progress tracking"""
    
    def __init__(self, database: Database):
        self.database = database
        self.checkpoint_file = config.CHECKPOINT_FILE
    
    def initialize_app_ids(self, app_ids: List[int]):
        """Initialize APP IDs in database if not already present"""
        conn = self.database.get_connection()
        use_postgresql = self.database.use_postgresql
        
        # Используем правильный placeholder в зависимости от БД
        param = '%s' if use_postgresql else '?'
        
        initialized = 0
        for app_id in app_ids:
            # Check if app_id already exists
            query = f"SELECT app_id FROM app_status WHERE app_id = {param}"
            cursor = conn.cursor()
            cursor.execute(query, (app_id,))
            if not cursor.fetchone():
                # Insert as pending
                insert_query = f"""INSERT INTO app_status (app_id, status, last_updated) 
                       VALUES ({param}, 'pending', {param})"""
                cursor.execute(insert_query, (app_id, datetime.now().isoformat()))
                initialized += 1
        
        conn.commit()
        logger.info(f"Initialized {initialized} APP IDs in database")
    
    def get_pending_app_ids(self) -> List[int]:
        """Get list of pending APP IDs"""
        conn = self.database.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT app_id FROM app_status WHERE status = 'pending' ORDER BY app_id")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    
    def mark_ccu_done(self, app_id: int, ccu_count: int):
        """Mark CCU as done for app_id"""
        status = 'ccu_done' if ccu_count > 0 else 'ccu_error'
        self.database.update_app_status(
            app_id, 
            status,
            ccu_processed=ccu_count
        )
        logger.debug(f"Marked CCU done for app_id {app_id}: {ccu_count} records")
    
    def mark_price_done(self, app_id: int, price_count: int):
        """Mark Price as done for app_id"""
        # Get current status
        current_status = self.database.get_app_status(app_id)
        ccu_count = current_status.get('ccu_processed', 0) if current_status else 0
        
        if price_count > 0:
            if ccu_count > 0:
                status = 'completed'
            else:
                status = 'price_done'
        else:
            if current_status and current_status.get('status') == 'ccu_done':
                status = 'ccu_error'
            else:
                status = 'price_error'
        
        self.database.update_app_status(
            app_id,
            status,
            price_processed=price_count
        )
        logger.debug(f"Marked Price done for app_id {app_id}: {price_count} records")
    
    def mark_app_completed(self, app_id: int, ccu_count: int, price_count: int):
        """Mark app as fully completed"""
        self.database.update_app_status(
            app_id,
            'completed',
            ccu_processed=ccu_count,
            price_processed=price_count
        )
        logger.debug(f"Marked app_id {app_id} as completed: CCU={ccu_count}, Price={price_count}")
    
    def mark_app_error(self, app_id: int, error_type: str, error_message: str, url: str = None):
        """Mark error for app_id"""
        # Get current status
        current_status = self.database.get_app_status(app_id)
        
        if error_type == 'ccu':
            status = 'ccu_error'
            self.database.update_app_status(
                app_id,
                status,
                ccu_error=error_message,
                ccu_url=url
            )
        elif error_type == 'price':
            if current_status and current_status.get('status') == 'ccu_error':
                status = 'both_error'
            else:
                status = 'price_error'
            self.database.update_app_status(
                app_id,
                status,
                price_error=error_message,
                price_url=url
            )
        else:
            status = 'both_error'
            self.database.update_app_status(
                app_id,
                status,
                ccu_error=error_message if error_type == 'ccu' else None,
                price_error=error_message if error_type == 'price' else None,
                ccu_url=url if error_type == 'ccu' else None,
                price_url=url if error_type == 'price' else None
            )
        
        # Log error to errors table
        self.database.log_error(app_id, error_type, error_message, url)
        logger.warning(f"Marked {error_type} error for app_id {app_id}: {error_message}")
    
    def get_progress(self) -> Dict:
        """Get parsing progress statistics"""
        return self.database.get_statistics()
    
    def save_checkpoint(self):
        """Save checkpoint to JSON file"""
        try:
            stats = self.get_progress()
            checkpoint_data = {
                'timestamp': datetime.now().isoformat(),
                'statistics': stats
            }
            
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            logger.debug("Checkpoint saved")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

