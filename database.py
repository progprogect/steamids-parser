"""
Database module for SteamDB parser
Supports both SQLite (local) and PostgreSQL (Railway/cloud)
"""
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import config

# Import config after it's defined
try:
    DATABASE_PUBLIC_URL = config.DATABASE_PUBLIC_URL
except AttributeError:
    DATABASE_PUBLIC_URL = None

logger = logging.getLogger(__name__)

# Try to import PostgreSQL adapter
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False

# Try to import SQLite
try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False


class Database:
    """Database manager for SteamDB parser - supports SQLite and PostgreSQL"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.conn = None
        # Check DATABASE_URL from environment or config
        database_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
        if not database_url and hasattr(config, 'DATABASE_PUBLIC_URL'):
            database_url = config.DATABASE_PUBLIC_URL
        self.database_url = database_url
        self.use_postgresql = (database_url is not None) and POSTGRESQL_AVAILABLE
        
        if self.use_postgresql:
            logger.info("Using PostgreSQL database")
        else:
            logger.info("Using SQLite database")
        
        self.init_database()
    
    def get_connection(self):
        """Get database connection (PostgreSQL or SQLite)"""
        if self.conn is None:
            if self.use_postgresql:
                # Parse DATABASE_URL (format: postgresql://user:password@host:port/database)
                import urllib.parse as urlparse
                result = urlparse.urlparse(self.database_url)
                self.conn = psycopg2.connect(
                    database=result.path[1:],  # Remove leading '/'
                    user=result.username,
                    password=result.password,
                    host=result.hostname,
                    port=result.port or 5432,
                    connect_timeout=30
                )
                self.conn.autocommit = False
            else:
                # SQLite
                if not SQLITE_AVAILABLE:
                    raise RuntimeError("SQLite not available")
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
                self.conn.row_factory = sqlite3.Row
                # Enable WAL mode for better concurrency
                self.conn.execute("PRAGMA journal_mode=WAL")
        return self.conn
    
    def _get_cursor(self):
        """Get cursor with appropriate row factory"""
        conn = self.get_connection()
        if self.use_postgresql:
            return conn.cursor(cursor_factory=RealDictCursor)
        else:
            return conn.cursor()
    
    def _execute(self, query: str, params: Tuple = None):
        """Execute query with database-specific adaptations"""
        cursor = self._get_cursor()
        
        # Adapt SQL for PostgreSQL
        if self.use_postgresql:
            # Replace SQLite-specific syntax
            query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            query = query.replace("INSERT OR IGNORE", "INSERT ON CONFLICT DO NOTHING")
            query = query.replace("INSERT OR REPLACE", "INSERT ON CONFLICT DO UPDATE")
            query = query.replace("CREATE INDEX IF NOT EXISTS", "CREATE INDEX IF NOT EXISTS")
            query = query.replace("CREATE TABLE IF NOT EXISTS", "CREATE TABLE IF NOT EXISTS")
            # Replace ? with %s for PostgreSQL
            if params:
                query = query.replace("?", "%s")
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        return cursor
    
    def init_database(self):
        """Initialize database with all tables and indexes"""
        conn = self.get_connection()
        
        # CCU History table
        if self.use_postgresql:
            # PostgreSQL schema
            self._execute("""
                CREATE TABLE IF NOT EXISTS ccu_history (
                    id SERIAL PRIMARY KEY,
                    app_id INTEGER NOT NULL,
                    datetime TEXT NOT NULL,
                    players INTEGER NOT NULL,
                    value_type TEXT DEFAULT 'avg',
                    UNIQUE(app_id, datetime, value_type)
                )
            """)
            
            # Create indexes
            self._execute("CREATE INDEX IF NOT EXISTS idx_ccu_app_datetime ON ccu_history(app_id, datetime)")
            self._execute("CREATE INDEX IF NOT EXISTS idx_ccu_app ON ccu_history(app_id)")
            self._execute("CREATE INDEX IF NOT EXISTS idx_ccu_value_type ON ccu_history(value_type)")
        else:
            # SQLite schema with migration logic
            cursor = self._get_cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ccu_history'")
            existing_table = cursor.fetchone()
            
            if existing_table and "UNIQUE(app_id, datetime)" in str(existing_table[0]) and "UNIQUE(app_id, datetime, value_type)" not in str(existing_table[0]):
                logger.info("Migrating ccu_history table to new UNIQUE constraint...")
                cursor.execute("""
                    CREATE TABLE ccu_history_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        app_id INTEGER NOT NULL,
                        datetime TEXT NOT NULL,
                        players INTEGER NOT NULL,
                        value_type TEXT DEFAULT 'avg',
                        UNIQUE(app_id, datetime, value_type)
                    )
                """)
                cursor.execute("""
                    INSERT INTO ccu_history_new (app_id, datetime, players, value_type)
                    SELECT app_id, datetime, players, COALESCE(value_type, 'avg') as value_type
                    FROM ccu_history
                """)
                cursor.execute("DROP TABLE ccu_history")
                cursor.execute("ALTER TABLE ccu_history_new RENAME TO ccu_history")
                conn.commit()
                logger.info("Migration completed")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ccu_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_id INTEGER NOT NULL,
                    datetime TEXT NOT NULL,
                    players INTEGER NOT NULL,
                    value_type TEXT DEFAULT 'avg',
                    UNIQUE(app_id, datetime, value_type)
                )
            """)
            
            # Add value_type column if it doesn't exist
            try:
                cursor.execute("ALTER TABLE ccu_history ADD COLUMN value_type TEXT DEFAULT 'avg'")
                cursor.execute("UPDATE ccu_history SET value_type = 'avg' WHERE value_type IS NULL")
                conn.commit()
            except sqlite3.OperationalError:
                try:
                    cursor.execute("UPDATE ccu_history SET value_type = 'avg' WHERE value_type IS NULL")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccu_app_datetime ON ccu_history(app_id, datetime)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccu_app ON ccu_history(app_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccu_value_type ON ccu_history(value_type)")
        
        # Price History table
        if self.use_postgresql:
            self._execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id SERIAL PRIMARY KEY,
                    app_id INTEGER NOT NULL,
                    datetime TEXT NOT NULL,
                    price_final REAL NOT NULL,
                    currency_symbol TEXT NOT NULL,
                    currency_name TEXT NOT NULL,
                    UNIQUE(app_id, datetime, currency_symbol)
                )
            """)
            self._execute("CREATE INDEX IF NOT EXISTS idx_price_app_datetime ON price_history(app_id, datetime)")
            self._execute("CREATE INDEX IF NOT EXISTS idx_price_app ON price_history(app_id)")
        else:
            cursor = self._get_cursor()
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
        if self.use_postgresql:
            self._execute("""
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
            self._execute("CREATE INDEX IF NOT EXISTS idx_status ON app_status(status)")
        else:
            cursor = self._get_cursor()
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
            # SQLite doesn't support ALTER TABLE ADD COLUMN IF NOT EXISTS directly
            # Check if columns exist before adding
            cursor.execute("PRAGMA table_info(app_status)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'itad_currencies_checked' not in columns:
                cursor.execute("ALTER TABLE app_status ADD COLUMN itad_currencies_checked TEXT")
            if 'itad_price_processed' not in columns:
                cursor.execute("ALTER TABLE app_status ADD COLUMN itad_price_processed INTEGER DEFAULT 0")
            if 'itad_error' not in columns:
                cursor.execute("ALTER TABLE app_status ADD COLUMN itad_error TEXT")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON app_status(status)")
        
        # Errors table
        if self.use_postgresql:
            self._execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id SERIAL PRIMARY KEY,
                    app_id INTEGER NOT NULL,
                    error_type TEXT NOT NULL,
                    error_message TEXT,
                    error_traceback TEXT,
                    timestamp TEXT NOT NULL,
                    url TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            self._execute("CREATE INDEX IF NOT EXISTS idx_errors_app ON errors(app_id)")
        else:
            cursor = self._get_cursor()
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
    
    def save_ccu_data(self, app_id: int, data_list: List[Dict], value_type: str = 'avg'):
        """Save CCU data in batch"""
        if not data_list:
            return
        
        conn = self.get_connection()
        cursor = self._get_cursor()
        
        try:
            values = [(app_id, item['datetime'], item['players'], value_type) for item in data_list]
            
            for i in range(0, len(values), config.DB_BATCH_SIZE):
                batch = values[i:i + config.DB_BATCH_SIZE]
                if self.use_postgresql:
                    cursor.executemany(
                        "INSERT INTO ccu_history (app_id, datetime, players, value_type) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        batch
                    )
                else:
                    cursor.executemany(
                        "INSERT OR IGNORE INTO ccu_history (app_id, datetime, players, value_type) VALUES (?, ?, ?, ?)",
                        batch
                    )
            
            conn.commit()
            logger.debug(f"Saved {len(data_list)} CCU records for app_id {app_id} (type: {value_type})")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving CCU data for app_id {app_id}: {e}")
            raise
    
    def save_price_data(self, app_id: int, data_list: List[Dict]):
        """Save Price data in batch"""
        if not data_list:
            return
        
        conn = self.get_connection()
        cursor = self._get_cursor()
        
        try:
            values = [
                (app_id, item['datetime'], item['price_final'], 
                 item['currency_symbol'], item['currency_name'])
                for item in data_list
            ]
            
            for i in range(0, len(values), config.DB_BATCH_SIZE):
                batch = values[i:i + config.DB_BATCH_SIZE]
                if self.use_postgresql:
                    cursor.executemany(
                        """INSERT INTO price_history 
                           (app_id, datetime, price_final, currency_symbol, currency_name) 
                           VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        batch
                    )
                else:
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
    
    def save_price_data_batch(self, records: List[Dict]):
        """
        Save price data records in batch (multiple app_ids)
        
        Args:
            records: List of dicts with keys: app_id, datetime, price_final, currency_symbol, currency_name
        """
        if not records:
            return
        
        conn = self.get_connection()
        cursor = self._get_cursor()
        
        try:
            values = [
                (item['app_id'], item['datetime'], item['price_final'], 
                 item['currency_symbol'], item['currency_name'])
                for item in records
            ]
            
            for i in range(0, len(values), config.DB_BATCH_SIZE):
                batch = values[i:i + config.DB_BATCH_SIZE]
                if self.use_postgresql:
                    cursor.executemany(
                        """INSERT INTO price_history 
                           (app_id, datetime, price_final, currency_symbol, currency_name) 
                           VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                        batch
                    )
                else:
                    cursor.executemany(
                        """INSERT OR IGNORE INTO price_history 
                           (app_id, datetime, price_final, currency_symbol, currency_name) 
                           VALUES (?, ?, ?, ?, ?)""",
                        batch
                    )
            
            conn.commit()
            logger.debug(f"Saved {len(records)} Price records in batch")
        except Exception as e:
            conn.rollback()
            logger.error(f"Error saving Price data batch: {e}")
            raise
    
    def update_app_status(self, app_id: int, status: str, **kwargs):
        """Update app status"""
        conn = self.get_connection()
        cursor = self._get_cursor()
        
        timestamp = datetime.now().isoformat()
        fields = ['status', 'last_updated']
        values = [status, timestamp]
        
        for key, value in kwargs.items():
            if key in ['ccu_processed', 'price_processed', 'ccu_error', 'price_error', 'ccu_url', 'price_url',
                       'itad_currencies_checked', 'itad_price_processed', 'itad_error']:
                fields.append(key)
                values.append(value)
        
        if self.use_postgresql:
            # PostgreSQL: Use INSERT ... ON CONFLICT
            placeholders = ', '.join(['%s'] * len(fields))
            set_clause = ', '.join([f"{f} = EXCLUDED.{f}" for f in fields if f != 'app_id'])
            cursor.execute(
                f"""INSERT INTO app_status (app_id, {', '.join(fields)}) 
                    VALUES (%s, {placeholders})
                    ON CONFLICT (app_id) DO UPDATE SET {set_clause}""",
                [app_id] + values
            )
        else:
            # SQLite: Use INSERT OR REPLACE
            placeholders = ', '.join(['?'] * len(fields))
            cursor.execute(
                f"INSERT OR REPLACE INTO app_status (app_id, {', '.join(fields)}) VALUES (?, {placeholders})",
                [app_id] + values
            )
        
        conn.commit()
    
    def get_app_status(self, app_id: int) -> Optional[Dict]:
        """Get app status"""
        cursor = self._get_cursor()
        
        if self.use_postgresql:
            cursor.execute("SELECT * FROM app_status WHERE app_id = %s", (app_id,))
        else:
            cursor.execute("SELECT * FROM app_status WHERE app_id = ?", (app_id,))
        
        row = cursor.fetchone()
        
        if row:
            if self.use_postgresql:
                return dict(row)
            else:
                return dict(row)
        return None
    
    def get_statistics(self) -> Dict:
        """Get parsing statistics"""
        cursor = self._get_cursor()
        
        param = '%s' if self.use_postgresql else '?'
        
        def get_count(query, params=None):
            """Helper to get count value"""
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            if self.use_postgresql and isinstance(row, dict):
                return list(row.values())[0] if row else 0
            return row[0] if row else 0
        
        total = get_count("SELECT COUNT(*) FROM app_status")
        completed = get_count("SELECT COUNT(*) FROM app_status WHERE status = " + param, ('completed',))
        pending = get_count("SELECT COUNT(*) FROM app_status WHERE status = " + param, ('pending',))
        errors = get_count("SELECT COUNT(*) FROM app_status WHERE status LIKE " + param, ('%error%',))
        ccu_records = get_count("SELECT COUNT(*) FROM ccu_history")
        price_records = get_count("SELECT COUNT(*) FROM price_history")
        
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
        cursor = self._get_cursor()
        timestamp = datetime.now().isoformat()
        
        if self.use_postgresql:
            cursor.execute(
                """INSERT INTO errors (app_id, error_type, error_message, error_traceback, timestamp, url)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (app_id, error_type, error_message, traceback, timestamp, url)
            )
        else:
            cursor.execute(
                """INSERT INTO errors (app_id, error_type, error_message, error_traceback, timestamp, url)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (app_id, error_type, error_message, traceback, timestamp, url)
            )
        
        self.get_connection().commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
