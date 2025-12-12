#!/usr/bin/env python3
"""
Тестовый скрипт для проверки API endpoints локально
"""
import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """Тест health check"""
    print("1. Testing /health...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")

def test_status():
    """Тест статуса"""
    print("2. Testing /status...")
    response = requests.get(f"{BASE_URL}/status")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}\n")

def test_start():
    """Тест запуска парсера"""
    print("3. Testing /start...")
    # Создаем тестовый файл
    test_file = "test_app_ids.txt"
    with open(test_file, 'w') as f:
        f.write("730\n440\n570\n")
    
    with open(test_file, 'rb') as f:
        files = {'file': ('app_ids.txt', f, 'text/plain')}
        response = requests.post(f"{BASE_URL}/start", files=files)
    
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")

if __name__ == "__main__":
    print("🧪 Тестирование API endpoints\n")
    print("=" * 50)
    
    try:
        test_health()
        test_status()
        # test_start()  # Раскомментируйте для теста запуска
    except requests.exceptions.ConnectionError:
        print("❌ Не удалось подключиться к серверу")
        print("Запустите сервер: python3 api_server.py")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


