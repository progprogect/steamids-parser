#!/usr/bin/env python3
"""
Скрипт для экспорта ошибок из базы данных в CSV файл
"""
import csv
from pathlib import Path
from database import Database
import config

def export_errors_to_csv(db: Database, output_file: Path):
    """Экспортировать ошибки в CSV файл"""
    conn = db.get_connection()
    
    # Создаем cursor в зависимости от типа БД
    if db.use_postgresql:
        try:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        except ImportError:
            cursor = conn.cursor()
    else:
        cursor = conn.cursor()
    
    # Получаем все записи с ошибками
    cursor.execute("""
        SELECT app_id, status, ccu_error, price_error, ccu_url, price_url, last_updated
        FROM app_status
        WHERE status IN ('ccu_error', 'price_error', 'both_error')
        ORDER BY app_id
    """)
    
    errors = cursor.fetchall()
    
    if not errors:
        print("✅ Нет ошибок для экспорта")
        return 0
    
    # Записываем в CSV
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['app_id', 'status', 'ccu_error', 'price_error', 'ccu_url', 'price_url', 'last_updated'])
        
        for row in errors:
            if db.use_postgresql:
                # PostgreSQL возвращает dict-like объект
                if isinstance(row, dict):
                    writer.writerow([row['app_id'], row['status'], row['ccu_error'], row['price_error'], 
                                   row['ccu_url'], row['price_url'], row['last_updated']])
                else:
                    writer.writerow(row)
            else:
                # SQLite возвращает tuple
                writer.writerow(row)
    
    print(f"✅ Экспортировано {len(errors)} записей с ошибками в {output_file}")
    return len(errors)

if __name__ == "__main__":
    db = Database()
    output_file = Path(__file__).parent / "errors_export.csv"
    export_errors_to_csv(db, output_file)
    db.close()

