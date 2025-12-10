# Развертывание парсера на Railway

## Подготовка

1. **Установите Railway CLI** (если еще не установлен):
```bash
npm i -g @railway/cli
```

2. **Войдите в Railway**:
```bash
railway login
```

## Развертывание

### Вариант 1: Через Railway Dashboard (рекомендуется)

1. Зайдите на [railway.app](https://railway.app)
2. Создайте новый проект
3. Подключите ваш GitHub репозиторий или загрузите код
4. Railway автоматически определит Python проект
5. Добавьте переменные окружения (если нужно):
   - `LOG_LEVEL=INFO`
   - `STEAMCHARTS_REQUESTS_PER_SECOND=100`
   - `STEAMCHARTS_MAX_CONCURRENT=80`

### Вариант 2: Через Railway CLI

```bash
# Инициализация проекта
railway init

# Развертывание
railway up

# Просмотр логов
railway logs

# Подключение к сервису
railway shell
```

## Настройка PostgreSQL базы данных

**Рекомендуется использовать PostgreSQL вместо SQLite для лучшей производительности:**

1. В Railway Dashboard → ваш проект → **New** → **Database** → **Add PostgreSQL**
2. Railway автоматически создаст переменную окружения `DATABASE_URL`
3. Парсер автоматически определит PostgreSQL и будет использовать его вместо SQLite

## Настройка переменных окружения

В Railway Dashboard → Variables добавьте (опционально):

```
LOG_LEVEL=INFO
STEAMCHARTS_REQUESTS_PER_SECOND=100
STEAMCHARTS_MAX_CONCURRENT=80
```

**Примечание:** `DATABASE_URL` будет автоматически установлен Railway при создании PostgreSQL сервиса.

## Хранение данных

**Вариант 1: PostgreSQL (рекомендуется)**
- Данные хранятся в PostgreSQL
- Автоматические бэкапы Railway
- Лучшая производительность при параллельных запросах
- Не требует persistent volumes

**Вариант 2: SQLite с persistent volumes**
- В Railway Dashboard → ваш сервис → Settings → Volumes
- Добавьте volume для `/app/data`
- Это сохранит базу данных между перезапусками

## Экспорт данных

### Вариант 1: Экспорт из PostgreSQL через Railway CLI (рекомендуется)

```bash
# Подключитесь к контейнеру
railway shell

# Запустите экспорт (автоматически использует PostgreSQL)
python3 export_from_postgres.py

# Или стандартный экспорт
python3 export_full_results.py

# Файлы будут созданы в /tmp/exports/ или текущей директории
# Скачайте их через Railway Dashboard → Volumes или через CLI
```

### Вариант 2: Прямой SQL экспорт из PostgreSQL

```bash
# Подключитесь к PostgreSQL через Railway CLI
railway connect postgres

# Или используйте psql с DATABASE_URL
railway run psql $DATABASE_URL -c "\COPY (SELECT * FROM ccu_history) TO '/tmp/ccu_data.csv' CSV HEADER"
railway run psql $DATABASE_URL -c "\COPY (SELECT * FROM app_status WHERE status LIKE '%error%') TO '/tmp/errors.csv' CSV HEADER"
```

### Вариант 3: Через Python скрипт с прямым подключением

```bash
railway run python3 << 'EOF'
from database import Database
from export_steamcharts_csv import export_to_csv
from pathlib import Path

db = Database()
export_to_csv(db, Path("/tmp/results.csv"))
print("✅ Экспорт завершен: /tmp/results.csv")
EOF
```

### Вариант 4: Скачивание через Railway Dashboard

1. Запустите экспорт через Railway shell
2. Файлы будут в `/tmp/exports/` или `/app/data/`
3. Используйте Railway Dashboard → Volumes для скачивания

## Мониторинг

- **Логи**: Railway Dashboard → ваш сервис → Logs
- **Метрики**: Railway Dashboard → ваш сервис → Metrics
- **Проверка прогресса**: `railway run python3 check_progress.py`

## Остановка/Перезапуск

```bash
# Остановить сервис
railway service stop

# Запустить сервис
railway service start

# Перезапустить
railway service restart
```

## Рекомендации

1. **Используйте PostgreSQL** вместо SQLite для лучшей производительности в облаке:
   - Добавьте PostgreSQL сервис в Railway
   - Измените `database.py` для использования PostgreSQL

2. **Настройте автоэкспорт**:
   - Добавьте cron job для периодического экспорта
   - Или используйте Railway Cron для запуска экспорта

3. **Мониторинг**:
   - Настройте алерты в Railway
   - Используйте `check_progress.py` для проверки статуса

4. **Оптимизация стоимости**:
   - Railway взимает плату за время работы
   - Рассмотрите возможность запуска парсера периодически, а не постоянно

## Пример команды для периодического запуска

Создайте `run_once.py`:

```python
#!/usr/bin/env python3
"""Запуск парсера один раз с последующим экспортом"""
from parser import SteamDBParser
from export_full_results import main as export_main

parser = SteamDBParser()
parser.run()

# После завершения - экспорт
export_main()
```

Затем используйте Railway Cron для запуска по расписанию.

