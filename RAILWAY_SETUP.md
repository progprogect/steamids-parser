# Настройка Railway с PostgreSQL

## Шаг 1: Создание проекта на Railway

1. Зайдите на [railway.app](https://railway.app)
2. Создайте новый проект
3. Подключите GitHub репозиторий: `https://github.com/progprogect/steamids-parser.git`

## Шаг 2: Добавление PostgreSQL

1. В вашем проекте Railway нажмите **New** → **Database** → **Add PostgreSQL**
2. Railway автоматически создаст переменную окружения `DATABASE_URL`
3. Также будет доступен `DATABASE_PUBLIC_URL` для внешних подключений

## Шаг 3: Инициализация базы данных

После создания PostgreSQL сервиса, база данных будет автоматически инициализирована при первом запуске парсера через метод `init_database()` в классе `Database`.

**Или вручную через Railway CLI:**

```bash
# Установите Railway CLI
npm i -g @railway/cli

# Войдите в Railway
railway login

# Подключитесь к проекту
railway link

# Установите DATABASE_URL
railway variables

# Запустите инициализацию
railway run python3 init_postgres.py
```

**Или через Railway Dashboard:**

1. Откройте ваш сервис → **Variables**
2. Найдите `DATABASE_URL` или `DATABASE_PUBLIC_URL`
3. Скопируйте значение
4. Запустите локально:
```bash
export DATABASE_URL="postgresql://..."
python3 init_postgres.py
```

## Шаг 4: Проверка структуры БД

После инициализации проверьте структуру:

```bash
railway run python3 check_postgres_tables.py
```

Или используйте `DATABASE_PUBLIC_URL` локально:

```bash
DATABASE_PUBLIC_URL="postgresql://..." python3 check_postgres_tables.py
```

## Шаг 5: Запуск API сервера

Railway автоматически запустит API сервер при деплое. API будет доступен по адресу:
```
https://your-app.railway.app
```

## Использование API

### Запуск парсера

```bash
curl -X POST https://your-app.railway.app/start \
  -F "file=@app_ids.txt"
```

### Проверка статуса

```bash
curl https://your-app.railway.app/status
```

### Экспорт данных

```bash
# Экспорт CCU данных
curl -O https://your-app.railway.app/export?type=ccu

# Экспорт ошибок
curl -O https://your-app.railway.app/export?type=errors
```

## Переменные окружения

Railway автоматически установит:
- `DATABASE_URL` - внутренний URL PostgreSQL (для приложения)
- `DATABASE_PUBLIC_URL` - публичный URL PostgreSQL (для внешних подключений)
- `PORT` - порт для API сервера

Опционально можно установить:
- `LOG_LEVEL=INFO`
- `STEAMCHARTS_REQUESTS_PER_SECOND=100`
- `STEAMCHARTS_MAX_CONCURRENT=80`

## Проверка подключения к БД

Парсер автоматически определит наличие `DATABASE_URL` или `DATABASE_PUBLIC_URL` и будет использовать PostgreSQL вместо SQLite.

Проверить можно через API:
```bash
curl https://your-app.railway.app/status
```

Если в ответе есть данные - значит БД работает корректно.


