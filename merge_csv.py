#!/usr/bin/env python3
"""
Merge multiple CSV files downloaded from SteamDB into a single file.
Format: app_id,datetime,players
"""

import os
import csv
import glob
from pathlib import Path
from datetime import datetime

def merge_csv_files(downloads_dir=None, output_file=None):
    """
    Merge all CSV files from SteamDB downloads into a single file.
    
    Args:
        downloads_dir: Directory containing CSV files (default: Downloads folder)
        output_file: Output file path (default: steamdb_merged_YYYY-MM-DD.csv)
    """
    # Default to Downloads folder
    if downloads_dir is None:
        home = Path.home()
        downloads_dir = home / 'Downloads'
    else:
        downloads_dir = Path(downloads_dir)
    
    if not downloads_dir.exists():
        print(f"❌ Папка {downloads_dir} не существует")
        return
    
    # Find all CSV files (SteamDB usually names them with timestamp or app IDs)
    csv_files = list(downloads_dir.glob('*.csv'))
    
    # Filter SteamDB CSV files (usually contain 'steamdb' or 'charts' in name, or have specific format)
    steamdb_files = []
    for csv_file in csv_files:
        name_lower = csv_file.name.lower()
        # Check if it's a SteamDB file (contains 'steamdb', 'charts', or matches pattern)
        if 'steamdb' in name_lower or 'charts' in name_lower or 'compare' in name_lower:
            steamdb_files.append(csv_file)
        else:
            # Check file content - SteamDB CSV usually has headers like "Time", "Players", or app IDs
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline()
                    # SteamDB CSV typically has headers with "Time" or "Players" or starts with app ID
                    if 'time' in first_line.lower() or 'players' in first_line.lower() or first_line.strip().isdigit():
                        steamdb_files.append(csv_file)
            except:
                pass
    
    if not steamdb_files:
        print(f"⚠️ Не найдено CSV файлов SteamDB в {downloads_dir}")
        print(f"💡 Убедитесь, что файлы скачаны из SteamDB Compare tool")
        return
    
    print(f"📊 Найдено {len(steamdb_files)} CSV файлов SteamDB")
    
    # Default output file
    if output_file is None:
        output_file = downloads_dir / f"steamdb_merged_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    else:
        output_file = Path(output_file)
    
    # Merge files
    merged_data = []
    seen_rows = set()  # To avoid duplicates
    
    for csv_file in steamdb_files:
        print(f"  📄 Обрабатываю: {csv_file.name}")
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                
                if not header:
                    continue
                
                # Parse header to understand format
                # SteamDB CSV format varies:
                # 1. "Time,App1,App2,..." (multiple apps in one file)
                # 2. "Time,Players" (single app)
                # 3. Direct data rows with app_id,datetime,players
                
                # Check if it's already in our format (app_id,datetime,players)
                if len(header) >= 3 and 'app_id' in header[0].lower() and 'datetime' in header[1].lower():
                    # Already in our format
                    for row in reader:
                        if len(row) >= 3:
                            row_key = (row[0], row[1])  # app_id, datetime
                            if row_key not in seen_rows:
                                seen_rows.add(row_key)
                                merged_data.append(row)
                else:
                    # SteamDB format: need to extract app IDs from header or filename
                    app_ids = []
                    
                    # Try to extract app IDs from header (columns after "Time")
                    for i, col in enumerate(header):
                        if i == 0 and ('time' in col.lower() or 'date' in col.lower()):
                            continue
                        # App ID might be in column name or we need to infer from data
                        app_ids.append(i)
                    
                    # If no app IDs found, try to infer from filename or data
                    if not app_ids:
                        # Try to extract from filename (e.g., "charts_364770_364790.csv")
                        import re
                        filename_ids = re.findall(r'\d{4,}', csv_file.name)
                        if filename_ids:
                            app_ids = [int(id) for id in filename_ids]
                    
                    # Parse rows
                    for row in reader:
                        if len(row) < 2:
                            continue
                        
                        timestamp = row[0]
                        # Convert timestamp to our format if needed
                        try:
                            # Try parsing different timestamp formats
                            if 'T' in timestamp or '-' in timestamp:
                                dt = datetime.fromisoformat(timestamp.replace('T', ' '))
                            else:
                                # Unix timestamp
                                dt = datetime.fromtimestamp(int(timestamp))
                            datetime_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            datetime_str = timestamp
                        
                        # Process each app column
                        for i, app_id in enumerate(app_ids):
                            if i + 1 < len(row):
                                players = row[i + 1].strip()
                                if players and players.isdigit():
                                    row_key = (str(app_id), datetime_str)
                                    if row_key not in seen_rows:
                                        seen_rows.add(row_key)
                                        merged_data.append([str(app_id), datetime_str, players])
        except Exception as e:
            print(f"  ⚠️ Ошибка обработки {csv_file.name}: {e}")
            continue
    
    if not merged_data:
        print("⚠️ Не удалось извлечь данные из CSV файлов")
        return
    
    # Sort by app_id, then datetime
    merged_data.sort(key=lambda x: (int(x[0]) if x[0].isdigit() else 0, x[1]))
    
    # Write merged file
    print(f"💾 Сохраняю объединенный файл: {output_file}")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['app_id', 'datetime', 'players'])
        writer.writerows(merged_data)
    
    print(f"✅ Объединено {len(merged_data)} записей из {len(steamdb_files)} файлов")
    print(f"📁 Результат сохранен в: {output_file}")

if __name__ == '__main__':
    import sys
    
    downloads_dir = None
    output_file = None
    
    if len(sys.argv) > 1:
        downloads_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    merge_csv_files(downloads_dir, output_file)

