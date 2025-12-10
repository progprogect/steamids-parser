#!/usr/bin/env python3
"""
Import CCU data from browser extension JSON export into main database
"""
import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

import config
from database import Database

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_datetime(dt_str: str) -> str:
    """Parse datetime string to ISO format"""
    try:
        # Try parsing various formats
        if 'T' in dt_str:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        return dt.isoformat()
    except Exception as e:
        logger.warning(f"Could not parse datetime '{dt_str}': {e}")
        return dt_str


def load_extension_data(json_file: Path) -> Dict[int, List]:
    """Load data from extension JSON export"""
    logger.info(f"Loading data from {json_file}")
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert keys to integers and normalize data format
    result = {}
    for app_id_str, points in data.items():
        app_id = int(app_id_str)
        normalized_points = []
        
        for point in points:
            if isinstance(point, list) and len(point) >= 2:
                dt_str = point[0]
                players = int(point[1])
                normalized_points.append({
                    'datetime': parse_datetime(dt_str),
                    'players': players
                })
        
        if normalized_points:
            result[app_id] = normalized_points
    
    logger.info(f"Loaded data for {len(result)} APP IDs")
    total_points = sum(len(points) for points in result.values())
    logger.info(f"Total data points: {total_points}")
    
    return result


def import_to_database(db: Database, data: Dict[int, List]):
    """Import data into database"""
    logger.info("Importing data to database...")
    
    imported_count = 0
    skipped_count = 0
    
    for app_id, ccu_data in data.items():
        try:
            # Check if data already exists
            existing = db.get_connection().execute(
                "SELECT COUNT(*) as count FROM ccu_history WHERE app_id = ?",
                (app_id,)
            ).fetchone()
            
            if existing['count'] > 0:
                logger.info(f"APP ID {app_id}: {existing['count']} records already exist, skipping...")
                skipped_count += 1
                continue
            
            # Save data
            db.save_ccu_data(app_id, ccu_data)
            imported_count += 1
            
            logger.info(f"✅ Imported {len(ccu_data)} points for APP ID {app_id}")
            
        except Exception as e:
            logger.error(f"❌ Error importing APP ID {app_id}: {e}")
    
    logger.info(f"\n📊 Import Summary:")
    logger.info(f"  ✅ Imported: {imported_count} APP IDs")
    logger.info(f"  ⏭️  Skipped: {skipped_count} APP IDs (already exist)")
    logger.info(f"  📦 Total: {len(data)} APP IDs")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python import_from_extension.py <json_file>")
        print("\nExample:")
        print("  python import_from_extension.py steamdb_data_2025-12-02.json")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    
    if not json_file.exists():
        logger.error(f"File not found: {json_file}")
        sys.exit(1)
    
    # Load data
    data = load_extension_data(json_file)
    
    if not data:
        logger.warning("No data to import")
        sys.exit(0)
    
    # Initialize database
    db = Database()
    
    # Import data
    import_to_database(db, data)
    
    logger.info("✅ Import completed!")


if __name__ == "__main__":
    main()



