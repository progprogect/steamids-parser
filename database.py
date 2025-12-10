"""
Database module for SteamDB parser
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import config

logger = logging.getLogger(__name__)


class Database:
    """Database manager for SteamDB parser"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.conn = None
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def init_database(self):
        """Initialize database with all tables and indexes"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # CCU History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ccu_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                players INTEGER NOT NULL,
                UNIQUE(app_id, datetime)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccu_app_datetime ON ccu_history(app_id, datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccu_app ON ccu_history(app_id)")
        
        # Price History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                price_final REAL NOT NULL,
                currency_symbol TEXT NOT NULL,
                currency_name TEXT NOT NULL,
                UNIQUE(app_id, datetime, currency_symbol)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_app_datetime ON price_history(app_id, datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_app ON price_history(app_id)")
        
        # App Status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_status (
                app_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                ccu_processed INTEGER DEFAULT 0,
                price_processed INTEGER DEFAULT 0,
                ccu_error TEXT,
                price_error TEXT,
                last_updated TEXT NOT NULL,
                ccu_url TEXT,
                price_url TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON app_status(status)")
        
        # Errors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                error_traceback TEXT,
                timestamp TEXT NOT NULL,
                url TEXT,
                retry_count INTEGER DEFAULT 0
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_app ON errors(app_id)")
        
        conn.commit()
        logger.info("Database initialized successfully")
    
    def save_ccu_data(self, app_id: int, data_list: List[Dict]):
        """Save CCU data in batch"""
        if not data_list:
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare data for batch insert
            values = [(app_id, item['datetime'], item['players']) for item in data_list]
            
            # Insert in batches
            for i in range(0, len(values), config.DB_BATCH_SIZE):
                batch = values[i:i + config.DB_BATCH_SIZE]
                cursor.executemany(
                    "INSERT OR IGNORE INTO ccu_history (app_id, datetime, players) VALUES (?, ?, ?)",
                    batch
                )
            
            conn.commit()
            logger.debug(f"Saved {len(data_list)} CCU records for app_id {app_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving CCU data for app_id {app_id}: {e}")
            raise
    
    def save_price_data(self, app_id: int, data_list: List[Dict]):
        """Save Price data in batch"""
        if not data_list:
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare data for batch insert
            values = [
                (app_id, item['datetime'], item['price_final'], 
                 item['currency_symbol'], item['currency_name'])
                for item in data_list
            ]
            
            # Insert in batches
            for i in range(0, len(values), config.DB_BATCH_SIZE):
                batch = values[i:i + config.DB_BATCH_SIZE]
                cursor.executemany(
                    """INSERT OR IGNORE INTO price_history 
                       (app_id, datetime, price_final, currency_symbol, currency_name) 
                       VALUES (?, ?, ?, ?, ?)""",
                    batch
                )
            
            conn.commit()
            logger.debug(f"Saved {len(data_list)} Price records for app_id {app_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving Price data for app_id {app_id}: {e}")
            raise
    
    def update_app_status(self, app_id: int, status: str, **kwargs):
        """Update app status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        # Build update query dynamically
        fields = ['status', 'last_updated']
        values = [status, timestamp]
        
        for key, value in kwargs.items():
            if key in ['ccu_processed', 'price_processed', 'ccu_error', 'price_error', 'ccu_url', 'price_url']:
                fields.append(key)
                values.append(value)
        
        # Use INSERT OR REPLACE
        placeholders = ', '.join(['?'] * len(fields))
        cursor.execute(
            f"INSERT OR REPLACE INTO app_status (app_id, {', '.join(fields)}) VALUES (?, {placeholders})",
            [app_id] + values
        )
        
        conn.commit()
    
    def get_app_status(self, app_id: int) -> Optional[Dict]:
        """Get app status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM app_status WHERE app_id = ?", (app_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_statistics(self) -> Dict:
        """Get parsing statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total apps
        cursor.execute("SELECT COUNT(*) FROM app_status")
        total = cursor.fetchone()[0]
        
        # Completed
        cursor.execute("SELECT COUNT(*) FROM app_status WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        
        # Pending
        cursor.execute("SELECT COUNT(*) FROM app_status WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        
        # Errors
        cursor.execute("SELECT COUNT(*) FROM app_status WHERE status LIKE '%error%'")
        errors = cursor.fetchone()[0]
        
        # Total CCU records
        cursor.execute("SELECT COUNT(*) FROM ccu_history")
        ccu_records = cursor.fetchone()[0]
        
        # Total Price records
        cursor.execute("SELECT COUNT(*) FROM price_history")
        price_records = cursor.fetchone()[0]
        
        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'errors': errors,
            'ccu_records': ccu_records,
            'price_records': price_records
        }
    
    def log_error(self, app_id: int, error_type: str, error_message: str, 
                  url: str = None, traceback: str = None):
        """Log error"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute(
            """INSERT INTO errors (app_id, error_type, error_message, error_traceback, timestamp, url)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (app_id, error_type, error_message, traceback, timestamp, url)
        )
        
        conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

