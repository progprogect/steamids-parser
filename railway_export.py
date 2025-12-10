#!/usr/bin/env python3
"""
Скрипт для экспорта данных на Railway
Можно запустить через Railway CLI или как отдельный сервис
"""
import os
import sys
from pathlib import Path
from export_full_results import main as export_main

if __name__ == "__main__":
    # На Railway можно использовать переменные окружения для пути экспорта
    export_dir = os.getenv("EXPORT_DIR", "/tmp/exports")
    Path(export_dir).mkdir(parents=True, exist_ok=True)
    
    # Изменяем рабочую директорию для экспорта
    original_dir = os.getcwd()
    os.chdir(export_dir)
    
    try:
        export_main()
    finally:
        os.chdir(original_dir)

