#!/usr/bin/env python3
"""
Скрипт для очистки таблицы ccu_history из базы данных
"""
import os
import sys
from database import Database
import config

def clear_ccu_history():
    """Очистить таблицу ccu_history"""
    print("🔌 Подключение к базе данных...")
    db = Database()
    
    try:
        # Получаем размер таблицы перед очисткой
        print("📊 Проверка размера таблицы ccu_history...")
        size_before = db.get_table_size('ccu_history')
        print(f"   Размер до очистки: {size_before}")
        
        # Подсчитываем количество записей
        cursor = db._get_cursor()
        cursor.execute("SELECT COUNT(*) FROM ccu_history")
        result = cursor.fetchone()
        if db.use_postgresql:
            # PostgreSQL returns RealDictRow or tuple
            if isinstance(result, dict):
                row_count = result.get('count', 0)
            else:
                row_count = result[0] if result else 0
        else:
            row_count = result[0] if result else 0
        print(f"   Количество записей: {row_count:,}")
        
        # Подтверждение
        if row_count > 0:
            response = input(f"\n⚠️  Вы уверены, что хотите удалить {row_count:,} записей из ccu_history? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Очистка отменена")
                return
        
        # Очищаем таблицу
        print("\n🗑️  Очистка таблицы ccu_history...")
        success = db.clear_ccu_history()
        
        if success:
            print("✅ Таблица очищена успешно")
            
            # Для PostgreSQL TRUNCATE уже освободил место, VACUUM не нужен
            # Для SQLite можно выполнить VACUUM
            if not db.use_postgresql:
                print("🔄 Выполнение VACUUM для освобождения места...")
                cursor.execute("VACUUM")
                db.get_connection().commit()
                print("✅ VACUUM выполнен")
            
            # Проверяем размер после очистки
            print("\n📊 Проверка результата...")
            size_after = db.get_table_size('ccu_history')
            print(f"   Размер после очистки: {size_after}")
            
            # Проверяем количество записей
            cursor.execute("SELECT COUNT(*) FROM ccu_history")
            result = cursor.fetchone()
            if db.use_postgresql:
                if isinstance(result, dict):
                    row_count_after = result.get('count', 0)
                else:
                    row_count_after = result[0] if result else 0
            else:
                row_count_after = result[0] if result else 0
            print(f"   Количество записей после очистки: {row_count_after:,}")
            
            print("\n✅ Готово! Таблица ccu_history очищена.")
        else:
            print("❌ Ошибка при очистке таблицы")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    clear_ccu_history()

