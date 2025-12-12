#!/usr/bin/env python3
"""
Скрипт для проверки прогресса парсинга
"""
from database import Database
import config

def check_progress():
    """Проверить прогресс парсинга"""
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Общая статистика
    cursor.execute("SELECT COUNT(*) FROM app_status")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM app_status WHERE status = 'completed'")
    completed = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM app_status WHERE status IN ('ccu_error', 'price_error', 'both_error')")
    errors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM app_status WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    
    # Статистика по записям CCU
    cursor.execute("SELECT COUNT(*) FROM ccu_history")
    ccu_records = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT app_id) FROM ccu_history")
    apps_with_data = cursor.fetchone()[0]
    
    print("=" * 60)
    print("📊 Статистика парсинга")
    print("=" * 60)
    print(f"Всего APP IDs: {total}")
    print(f"✅ Завершено успешно: {completed}")
    print(f"⏳ В процессе/ожидании: {pending}")
    print(f"❌ Ошибок: {errors}")
    print(f"📈 Записей CCU в БД: {ccu_records:,}")
    print(f"🎮 Игр с данными: {apps_with_data}")
    
    if total > 0:
        progress = ((completed + errors) / total) * 100
        print(f"📊 Прогресс: {progress:.2f}%")
    
    print("=" * 60)
    
    db.close()

if __name__ == "__main__":
    check_progress()



