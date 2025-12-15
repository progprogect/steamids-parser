# Очистка таблицы ccu_history в Railway

## 🚨 Проблема
База данных переполнена из-за большого количества записей в таблице `ccu_history` (~13 млн записей).

## ✅ Решения

### Вариант 1: Через API Endpoint (рекомендуется)

После деплоя изменений выполните:

```bash
curl -X POST https://worker-production-19aa.up.railway.app/database/clear/ccu_history
```

Endpoint автоматически:
- Подключится к базе данных
- Покажет размер и количество записей
- Очистит таблицу `ccu_history`
- Освободит место на диске

### Вариант 2: Через Railway Dashboard (если API недоступен)

1. Откройте ваш проект на [Railway](https://railway.app)
2. Перейдите в **PostgreSQL** сервис
3. Откройте вкладку **Query**
4. Выполните следующий SQL:

```sql
-- Проверка размера перед очисткой
SELECT 
    pg_size_pretty(pg_total_relation_size('ccu_history')) as total_size,
    pg_size_pretty(pg_relation_size('ccu_history')) as table_size,
    (SELECT COUNT(*) FROM ccu_history) as row_count;

-- Очистка таблицы
TRUNCATE TABLE ccu_history RESTART IDENTITY CASCADE;

-- Проверка результата
SELECT 
    pg_size_pretty(pg_total_relation_size('ccu_history')) as total_size_after,
    (SELECT COUNT(*) FROM ccu_history) as row_count_after;
```

### Вариант 3: Через Railway CLI

```bash
# Установите Railway CLI (если еще не установлен)
npm i -g @railway/cli

# Войдите в Railway
railway login

# Подключитесь к проекту
railway link

# Подключитесь к PostgreSQL
railway connect postgres

# Выполните SQL команду
TRUNCATE TABLE ccu_history RESTART IDENTITY CASCADE;
```

### Вариант 4: Прямое подключение через psql

```bash
# Используйте DATABASE_PUBLIC_URL
psql "postgresql://postgres:uOPRuIMnrxqslboMcXBWmIpREfTwsQnh@switchyard.proxy.rlwy.net:58449/railway" -c "TRUNCATE TABLE ccu_history RESTART IDENTITY CASCADE;"
```

## ⚠️ Важно

- `TRUNCATE` быстрее чем `DELETE` и сразу освобождает место на диске
- `RESTART IDENTITY` сбрасывает счетчик ID
- `CASCADE` удаляет связанные данные (если есть внешние ключи)
- После очистки таблица будет пуста, но структура сохранится

## 📊 После очистки

После успешной очистки:
1. Проверьте статус базы данных
2. Увеличьте лимит диска в Railway (если возможно)
3. Перезапустите ITAD парсер - он продолжит с места остановки

## 🔄 Восстановление данных (если нужно)

Если данные были экспортированы ранее, их можно восстановить через:

```bash
# Через API
curl -O https://worker-production-19aa.up.railway.app/export?type=ccu

# Или через Railway CLI
railway run python3 export_from_postgres.py
```

