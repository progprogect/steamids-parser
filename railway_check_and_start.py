#!/usr/bin/env python3
"""
Скрипт для проверки и запуска парсинга на Railway
Использование:
  python3 railway_check_and_start.py [RAILWAY_URL]
  
Или установите переменную окружения:
  export RAILWAY_URL=https://your-app.railway.app
  python3 railway_check_and_start.py
"""
import os
import sys
import json
import time
import requests
from pathlib import Path

def print_colored(text, color='green'):
    """Вывод цветного текста"""
    colors = {
        'green': '\033[0;32m',
        'yellow': '\033[1;33m',
        'red': '\033[0;31m',
        'blue': '\033[0;34m',
        'nc': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['nc']}")

def check_health(url):
    """Проверка health endpoint"""
    try:
        response = requests.get(f"{url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data
        return False, {"error": f"HTTP {response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}

def get_status(url):
    """Получение статуса парсера"""
    try:
        response = requests.get(f"{url}/status", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print_colored(f"Ошибка при получении статуса: {e}", 'red')
        return None

def start_parser(url, app_ids_file):
    """Запуск парсера"""
    if not Path(app_ids_file).exists():
        print_colored(f"❌ Файл {app_ids_file} не найден", 'red')
        return False
    
    try:
        with open(app_ids_file, 'rb') as f:
            files = {'file': (app_ids_file, f, 'text/plain')}
            response = requests.post(f"{url}/start", files=files, timeout=30)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, response.json()
    except Exception as e:
        return False, {"error": str(e)}

def stop_parser(url):
    """Остановка парсера"""
    try:
        response = requests.post(f"{url}/stop", timeout=10)
        if response.status_code == 200:
            return True, response.json()
        return False, response.json()
    except Exception as e:
        return False, {"error": str(e)}

def monitor_progress(url, interval=10):
    """Мониторинг прогресса парсинга"""
    print_colored("\n📊 Мониторинг прогресса (Ctrl+C для выхода)\n", 'blue')
    
    try:
        while True:
            status = get_status(url)
            if status:
                stats = status.get('statistics', {})
                parser_running = status.get('parser_running', False)
                
                if parser_running:
                    total = stats.get('total_apps', 0)
                    completed = stats.get('completed', 0)
                    pending = stats.get('pending', 0)
                    errors = stats.get('errors', 0)
                    ccu_records = stats.get('ccu_records', 0)
                    progress = status.get('progress_percent', 0)
                    
                    print(f"\r{'='*70}")
                    print(f"Обработано:     {completed:>8} / {total:>8} ({progress:>5.1f}%)")
                    print(f"Ожидает:       {pending:>8}")
                    print(f"Ошибок:        {errors:>8}")
                    print(f"CCU записей:   {ccu_records:>8}")
                    print(f"{'='*70}\r", end='', flush=True)
                else:
                    print_colored("\n✅ Парсинг завершен", 'green')
                    break
            
            time.sleep(interval)
    except KeyboardInterrupt:
        print_colored("\n\nМониторинг остановлен", 'yellow')

def main():
    # Получение URL
    railway_url = os.getenv('RAILWAY_URL')
    if len(sys.argv) > 1:
        railway_url = sys.argv[1]
    
    if not railway_url:
        print_colored("❌ URL Railway приложения не указан", 'red')
        print("\nИспользование:")
        print("  python3 railway_check_and_start.py [RAILWAY_URL]")
        print("\nИли установите переменную окружения:")
        print("  export RAILWAY_URL=https://your-app.railway.app")
        sys.exit(1)
    
    # Убираем trailing slash
    railway_url = railway_url.rstrip('/')
    
    print_colored(f"🚀 Проверка Railway приложения: {railway_url}\n", 'blue')
    
    # Проверка health
    print("1. Проверка работоспособности сервера...")
    health_ok, health_data = check_health(railway_url)
    
    if not health_ok:
        print_colored(f"❌ Сервер не отвечает: {health_data.get('error', 'Unknown error')}", 'red')
        sys.exit(1)
    
    print_colored("✅ Сервер работает", 'green')
    print(f"   PostgreSQL: {health_data.get('postgresql', False)}")
    print(f"   БД подключена: {health_data.get('database_connected', False)}")
    print()
    
    # Проверка статуса
    print("2. Проверка текущего статуса парсера...")
    status = get_status(railway_url)
    
    if status:
        parser_running = status.get('parser_running', False)
        stats = status.get('statistics', {})
        
        if parser_running:
            print_colored("⚠️  Парсер уже запущен", 'yellow')
            print(f"   Обработано: {stats.get('completed', 0)} / {stats.get('total_apps', 0)}")
            print()
            
            response = input("Остановить текущий парсинг и запустить заново? (y/N): ")
            if response.lower() == 'y':
                print("Остановка парсера...")
                stop_ok, stop_data = stop_parser(railway_url)
                if stop_ok:
                    print_colored("✅ Парсер остановлен", 'green')
                    time.sleep(2)
                else:
                    print_colored(f"❌ Ошибка при остановке: {stop_data}", 'red')
                    sys.exit(1)
            else:
                print_colored("Парсинг продолжается. Используйте: curl {railway_url}/status", 'yellow')
                monitor_progress(railway_url)
                sys.exit(0)
        else:
            print_colored("✅ Парсер не запущен", 'green')
            if stats.get('total_apps', 0) > 0:
                print(f"   Всего APP IDs в БД: {stats.get('total_apps', 0)}")
                print(f"   Завершено: {stats.get('completed', 0)}")
                print(f"   Ожидает: {stats.get('pending', 0)}")
    print()
    
    # Запуск парсинга
    app_ids_file = Path('app_ids.txt')
    if not app_ids_file.exists():
        print_colored(f"❌ Файл {app_ids_file} не найден", 'red')
        sys.exit(1)
    
    app_count = len([line for line in open(app_ids_file) if line.strip()])
    print(f"3. Запуск парсинга ({app_count} APP IDs)...")
    
    start_ok, start_data = start_parser(railway_url, app_ids_file)
    
    if start_ok:
        print_colored("✅ Парсер запущен успешно!", 'green')
        print(f"\nОтвет сервера:")
        print(json.dumps(start_data, indent=2, ensure_ascii=False))
        print()
        
        # Мониторинг
        response = input("Начать мониторинг прогресса? (Y/n): ")
        if response.lower() != 'n':
            monitor_progress(railway_url)
    else:
        print_colored(f"❌ Ошибка при запуске парсера", 'red')
        print(json.dumps(start_data, indent=2, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main()


