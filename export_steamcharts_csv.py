#!/usr/bin/env python3
"""
Export SteamCharts CCU data to CSV format
Format: app_id,timestamp,avg_players,peak_players
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
    
    # Fetch all CCU data with value_type
    cursor.execute("""
        SELECT app_id, datetime, players, value_type
        FROM ccu_history
        ORDER BY app_id, datetime, value_type
    """)
    
    # Group data by app_id and datetime
    # Structure: {(app_id, datetime): {'avg': players, 'peak': players}}
    data_dict = defaultdict(lambda: {'avg': None, 'peak': None})
    
    total_rows = 0
    for row in cursor.fetchall():
        app_id = row[0]
        datetime_str = row[1]
        players = row[2]
        value_type = row[3] or 'avg'  # Default to 'avg' for old data
        
        key = (app_id, datetime_str)
        if value_type in ['avg', 'peak']:
            data_dict[key][value_type] = players
            total_rows += 1
    
    logger.info(f"Loaded {total_rows} records from database")
    logger.info(f"Grouped into {len(data_dict)} unique (app_id, datetime) pairs")
    
    # Write to CSV
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(['app_id', 'timestamp', 'avg_players', 'peak_players'])
        
        # Write data rows
        written_rows = 0
        for (app_id, datetime_str), values in sorted(data_dict.items()):
            avg_players = values['avg'] if values['avg'] is not None else ''
            peak_players = values['peak'] if values['peak'] is not None else ''
            
            # Skip rows where both avg and peak are missing
            if avg_players == '' and peak_players == '':
                continue
            
            writer.writerow([app_id, datetime_str, avg_players, peak_players])
            written_rows += 1
    
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

