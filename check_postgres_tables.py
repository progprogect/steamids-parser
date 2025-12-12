#!/usr/bin/env python3
"""
Проверка структуры таблиц в PostgreSQL
"""
import os
import psycopg2
import urllib.parse as urlparse

def check_tables(database_url: str):
    """Проверить структуру таблиц"""
    result = urlparse.urlparse(database_url)
    
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port or 5432,
        connect_timeout=30
    )
    cursor = conn.cursor()
    
    # Проверяем существующие таблицы
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    tables = cursor.fetchall()
    
    print("📊 Существующие таблицы:")
    for table in tables:
        print(f"   ✅ {table[0]}")
    
    # Проверяем структуру каждой таблицы
    required_tables = ['ccu_history', 'price_history', 'app_status', 'errors']
    
    print("\n🔍 Проверка структуры таблиц:\n")
    
    for table_name in required_tables:
        if (table_name,) in tables:
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            print(f"📋 {table_name}:")
            for col in columns:
                nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
                print(f"   - {col[0]}: {col[1]} {nullable}")
            
            # Проверяем индексы
            cursor.execute(f"""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = '{table_name}'
            """)
            indexes = cursor.fetchall()
            if indexes:
                print(f"   Индексы:")
                for idx in indexes:
                    print(f"   - {idx[0]}")
            print()
        else:
            print(f"❌ Таблица {table_name} не найдена!\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    database_url = os.getenv("DATABASE_URL") or os.getenv("DATABASE_PUBLIC_URL")
    
    if not database_url:
        print("❌ DATABASE_URL не установлен!")
        exit(1)
    
    check_tables(database_url)


