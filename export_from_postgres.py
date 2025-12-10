#!/usr/bin/env python3
"""
Скрипт для экспорта данных из PostgreSQL на Railway
Можно запустить через Railway CLI или как отдельный сервис
"""
import os
import sys
from pathlib import Path
from export_full_results import main as export_main

if __name__ == "__main__":
    # Проверка наличия DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL не установлен!")
        print("Убедитесь, что PostgreSQL сервис подключен в Railway")
        sys.exit(1)
    
    print("✅ DATABASE_URL найден, начинаю экспорт...")
    
    # На Railway можно использовать переменные окружения для пути экспорта
    export_dir = os.getenv("EXPORT_DIR", "/tmp/exports")
    Path(export_dir).mkdir(parents=True, exist_ok=True)
    
    # Изменяем рабочую директорию для экспорта
    original_dir = os.getcwd()
    os.chdir(export_dir)
    
    try:
        export_main()
        print(f"\n✅ Экспорт завершен! Файлы находятся в {export_dir}")
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")
        sys.exit(1)
    finally:
        os.chdir(original_dir)
