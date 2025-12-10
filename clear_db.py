#!/usr/bin/env python3
"""
Скрипт для очистки базы данных перед новым запуском парсера
"""
import shutil
from pathlib import Path
from database import Database
import config

def clear_database():
    """Очистить базу данных"""
    db_path = config.DATABASE_PATH
    backup_path = db_path.with_suffix('.db.backup')
    
    if db_path.exists():
        # Создаем резервную копию
        print(f"📦 Создаю резервную копию: {backup_path}")
        shutil.copy2(db_path, backup_path)
        
        # Удаляем старую БД
        print(f"🗑️  Удаляю старую базу данных: {db_path}")
        db_path.unlink()
    
    # Инициализируем новую БД
    print("🔄 Инициализирую новую базу данных...")
    db = Database()
    db.init_database()
    db.close()
    
    print("✅ База данных очищена и готова к использованию")

if __name__ == "__main__":
    clear_database()

