#!/usr/bin/env python3
"""
Скрипт для инициализации PostgreSQL базы данных на Railway
Создает все необходимые таблицы и индексы
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import urllib.parse as urlparse

def init_postgres_database(database_url: str):
    """Инициализировать PostgreSQL базу данных"""
    
    print("🔌 Подключение к PostgreSQL...")
    
    # Парсим URL
    result = urlparse.urlparse(database_url)
    
    try:
        conn = psycopg2.connect(
            database=result.path[1:],  # Remove leading '/'
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port or 5432,
            connect_timeout=30
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("✅ Подключение установлено\n")
        
        # CCU History table
        print("📊 Создание таблицы ccu_history...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ccu_history (
                id SERIAL PRIMARY KEY,
                app_id INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                players INTEGER NOT NULL,
                value_type TEXT DEFAULT 'avg',
                UNIQUE(app_id, datetime, value_type)
            )
        """)
        print("✅ Таблица ccu_history создана")
        
        # Индексы для ccu_history
        print("📇 Создание индексов для ccu_history...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccu_app_datetime ON ccu_history(app_id, datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccu_app ON ccu_history(app_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccu_value_type ON ccu_history(value_type)")
        print("✅ Индексы созданы")
        
        # Price History table
        print("\n💰 Создание таблицы price_history...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY,
                app_id INTEGER NOT NULL,
                datetime TEXT NOT NULL,
                price_final REAL NOT NULL,
                currency_symbol TEXT NOT NULL,
                currency_name TEXT NOT NULL,
                UNIQUE(app_id, datetime, currency_symbol)
            )
        """)
        print("✅ Таблица price_history создана")
        
        # Индексы для price_history
        print("📇 Создание индексов для price_history...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_app_datetime ON price_history(app_id, datetime)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_app ON price_history(app_id)")
        print("✅ Индексы созданы")
        
        # App Status table
        print("\n📋 Создание таблицы app_status...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_status (
                app_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                ccu_processed INTEGER DEFAULT 0,
                price_processed INTEGER DEFAULT 0,
                ccu_error TEXT,
                price_error TEXT,
                last_updated TEXT NOT NULL,
                ccu_url TEXT,
                price_url TEXT
            )
        """)
        print("✅ Таблица app_status создана")
        
        # Индекс для app_status
        print("📇 Создание индекса для app_status...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON app_status(status)")
        print("✅ Индекс создан")
        
        # Errors table
        print("\n❌ Создание таблицы errors...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id SERIAL PRIMARY KEY,
                app_id INTEGER NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                error_traceback TEXT,
                timestamp TEXT NOT NULL,
                url TEXT,
                retry_count INTEGER DEFAULT 0
            )
        """)
        print("✅ Таблица errors создана")
        
        # Индекс для errors
        print("📇 Создание индекса для errors...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_app ON errors(app_id)")
        print("✅ Индекс создан")
        
        # Проверка созданных таблиц
        print("\n🔍 Проверка созданных таблиц...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print("✅ Созданные таблицы:")
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ База данных успешно инициализирована!")
        print("=" * 60)
        
    except psycopg2.Error as e:
        print(f"\n❌ Ошибка при работе с PostgreSQL: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Получаем DATABASE_URL из переменных окружения или аргументов
    database_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
    
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    
    if not database_url:
        print("❌ DATABASE_URL не указан!")
        print("\nИспользование:")
        print("  python3 init_postgres.py <DATABASE_URL>")
        print("или установите переменную окружения DATABASE_URL")
        sys.exit(1)
    
    init_postgres_database(database_url)


