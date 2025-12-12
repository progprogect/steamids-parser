#!/usr/bin/env python3
"""
Скрипт для экспорта всех результатов парсинга:
1. Экспорт данных CCU в CSV (app_id,timestamp,avg_players,peak_players)
2. Экспорт ошибок в CSV (app_id,status,ccu_error,price_error)
"""
import csv
from pathlib import Path
from datetime import datetime
from database import Database
from export_steamcharts_csv import export_to_csv
import config

def export_errors_to_csv(db: Database, output_file: Path):
    """Экспортировать ошибки в CSV файл"""
    conn = db.get_connection()
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
            writer.writerow(row)
    
    print(f"✅ Экспортировано {len(errors)} записей с ошибками в {output_file}")
    return len(errors)

def main():
    """Главная функция экспорта"""
    db = Database()
    base_dir = Path(__file__).parent
    
    # Определяем имена файлов с временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_file = base_dir / f"full_results_{timestamp}.csv"
    errors_file = base_dir / f"full_errors_{timestamp}.csv"
    
    print("=" * 60)
    print("📊 Экспорт результатов парсинга")
    print("=" * 60)
    
    # Экспорт данных CCU
    print(f"\n📈 Экспорт данных CCU в {data_file.name}...")
    try:
        export_to_csv(db, data_file)
        print(f"✅ Данные CCU экспортированы: {data_file}")
    except Exception as e:
        print(f"❌ Ошибка при экспорте данных CCU: {e}")
    
    # Экспорт ошибок
    print(f"\n❌ Экспорт ошибок в {errors_file.name}...")
    try:
        error_count = export_errors_to_csv(db, errors_file)
        if error_count > 0:
            print(f"✅ Ошибки экспортированы: {errors_file}")
        else:
            print("ℹ️  Ошибок нет")
    except Exception as e:
        print(f"❌ Ошибка при экспорте ошибок: {e}")
    
    # Статистика
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM app_status")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM app_status WHERE status = 'completed'")
    completed = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM app_status WHERE status IN ('ccu_error', 'price_error', 'both_error')")
    errors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ccu_history")
    ccu_records = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT app_id) FROM ccu_history")
    apps_with_data = cursor.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("📊 Финальная статистика")
    print("=" * 60)
    print(f"Всего APP IDs: {total:,}")
    print(f"✅ Успешно обработано: {completed:,}")
    print(f"❌ Ошибок: {errors:,}")
    print(f"📈 Записей CCU: {ccu_records:,}")
    print(f"🎮 Игр с данными: {apps_with_data:,}")
    
    if total > 0:
        success_rate = ((completed) / total) * 100
        print(f"📊 Успешность: {success_rate:.2f}%")
    
    print("=" * 60)
    
    db.close()

if __name__ == "__main__":
    main()



