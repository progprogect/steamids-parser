#!/usr/bin/env python3
"""
Export SteamCharts CCU data to CSV format
Format: ID,datetime,players
(only average values are exported)
"""
import csv
import sys
import logging
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict

import config
from database import Database

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def export_to_csv(db: Database, output_file: Path):
    """
    Export CCU data from database to CSV format
    
    Args:
        db: Database instance
        output_file: Path to output CSV file
    """
    logger.info(f"Starting CSV export to {output_file}")
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Fetch only average CCU data (value_type='avg')
    cursor.execute("""
        SELECT app_id, datetime, players
        FROM ccu_history
        WHERE value_type = 'avg' OR value_type IS NULL
        ORDER BY app_id, datetime
    """)
    
    logger.info(f"Loading CCU data from database...")
    
    # Write to CSV
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    written_rows = 0
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header (формат: ID, datetime, players)
        writer.writerow(['ID', 'datetime', 'players'])
        
        # Write data rows
        for row in cursor.fetchall():
            app_id = row[0]
            datetime_str = row[1]
            players = row[2]
            
            writer.writerow([app_id, datetime_str, players])
            written_rows += 1
    
    logger.info(f"Loaded {written_rows} records from database")
    
    logger.info(f"Exported {written_rows} rows to {output_file}")
    logger.info("CSV export completed successfully")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export SteamCharts CCU data to CSV')
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='steamcharts_export.csv',
        help='Output CSV file path (default: steamcharts_export.csv)'
    )
    
    args = parser.parse_args()
    
    output_file = Path(args.output)
    if not output_file.is_absolute():
        output_file = config.BASE_DIR / output_file
    
    try:
        db = Database()
        export_to_csv(db, output_file)
        db.close()
    except Exception as e:
        logger.error(f"Error during export: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

