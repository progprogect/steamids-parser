# 🚀 Быстрый запуск парсинга на Railway

## Вариант 1: Если у вас уже есть URL приложения

Если ваше приложение уже развернуто на Railway и вы знаете URL:

```bash
# Установите URL
export RAILWAY_URL=https://your-app.railway.app

# Запустите парсинг
./railway_start_parsing.sh
```

Или напрямую через curl:

```bash
# Проверка работоспособности
curl https://your-app.railway.app/health

# Запуск парсинга
curl -X POST https://your-app.railway.app/start \
  -F "file=@app_ids.txt

# Проверка статуса
curl https://your-app.railway.app/status
```

---

## Вариант 2: Подключение через Railway CLI

### Шаг 1: Подключите проект

```bash
# Войдите в Railway (если еще не вошли)
railway login

# Подключите проект
railway link
# Выберите ваш проект из списка
```

### Шаг 2: Получите URL приложения

```bash
# Получить домен
railway domain

# Или проверить переменные окружения
railway variables | grep RAILWAY
```

### Шаг 3: Запустите парсинг

```bash
# Используйте скрипт
./railway_start_parsing.sh

# Или вручную через curl (замените URL)
curl -X POST https://your-app.railway.app/start \
  -F "file=@app_ids.txt"
```

---

## Вариант 3: Создание нового проекта на Railway

Если проект еще не создан:

### Через Railway Dashboard (рекомендуется)

1. Зайдите на [railway.app](https://railway.app)
2. Создайте новый проект
3. Подключите GitHub репозиторий: `https://github.com/progprogect/steamids-parser.git`
4. Railway автоматически определит Python проект и запустит API сервер
5. Добавьте PostgreSQL сервис: **New** → **Database** → **Add PostgreSQL**
6. Добавьте переменные окружения (опционально):
   - `LOG_LEVEL=INFO`
   - `STEAMCHARTS_REQUESTS_PER_SECOND=100`
   - `STEAMCHARTS_MAX_CONCURRENT=80`

### Через Railway CLI

```bash
# Инициализация проекта
railway init

# Развертывание
railway up

# Добавление PostgreSQL
# (через Dashboard: New → Database → Add PostgreSQL)

# Подключение проекта
railway link
```

---

## Проверка работоспособности

### 1. Health Check

```bash
curl https://your-app.railway.app/health
```

Ожидаемый ответ:
```json
{
  "status": "ok",
  "parser_running": false,
  "database_connected": true,
  "postgresql": true
}
```

### 2. Проверка статуса

```bash
curl https://your-app.railway.app/status
```

### 3. Проверка логов

```bash
railway logs
```

---

## Запуск парсинга

### Через скрипт (рекомендуется)

```bash
./railway_start_parsing.sh
```

### Вручную через curl

```bash
# Запуск
curl -X POST https://your-app.railway.app/start \
  -F "file=@app_ids.txt"

# Проверка статуса
curl https://your-app.railway.app/status

# Мониторинг (в цикле)
watch -n 10 'curl -s https://your-app.railway.app/status | python3 -m json.tool'
```

---

## Мониторинг прогресса

### Через API

```bash
# Однократная проверка
curl https://your-app.railway.app/status | python3 -m json.tool

# Непрерывный мониторинг
while true; do
  clear
  echo "=== Статус парсинга ==="
  curl -s https://your-app.railway.app/status | python3 -m json.tool
  sleep 10
done
```

### Через Railway CLI

```bash
# Логи в реальном времени
railway logs --follow

# Проверка прогресса через shell
railway shell
python3 check_progress.py
```

---

## Остановка парсинга

```bash
curl -X POST https://your-app.railway.app/stop
```

Парсер корректно остановится и сохранит checkpoint. При следующем запуске продолжит с места остановки.

---

## Экспорт данных

### Через API

```bash
# Экспорт CCU данных
curl -O https://your-app.railway.app/export?type=ccu

# Экспорт ошибок
curl -O https://your-app.railway.app/export?type=errors

# Экспорт всех данных
curl https://your-app.railway.app/export?type=full
```

### Через Railway CLI

```bash
railway shell
python3 export_from_postgres.py
# Файлы будут в /tmp/exports/
```

---

## Решение проблем

### Парсер не запускается

1. Проверьте логи: `railway logs`
2. Проверьте health: `curl https://your-app.railway.app/health`
3. Убедитесь, что PostgreSQL подключен: проверьте переменные окружения `DATABASE_URL`

### Ошибки подключения к БД

```bash
# Проверка переменных окружения
railway variables | grep DATABASE

# Проверка подключения через shell
railway shell
python3 -c "from database import Database; db = Database(); print('OK' if db.use_postgresql else 'SQLite')"
```

### Парсер работает медленно

1. Увеличьте `STEAMCHARTS_MAX_CONCURRENT` в переменных окружения Railway
2. Проверьте логи на наличие ошибок rate limiting
3. Убедитесь, что PostgreSQL имеет достаточно ресурсов

---

## Полезные команды

```bash
# Просмотр всех переменных окружения
railway variables

# Просмотр логов
railway logs --tail 100

# Подключение к shell
railway shell

# Перезапуск сервиса
railway service restart

# Проверка статуса сервиса
railway status
```


