# REST API Документация

API сервер для управления парсером SteamCharts через HTTP запросы.

## Базовый URL

```
http://your-railway-app.railway.app
```

## Endpoints

### 1. Health Check

**GET** `/health`

Проверка работоспособности сервера.

**Response:**
```json
{
  "status": "ok",
  "parser_running": false
}
```

---

### 2. Запуск парсера

**POST** `/start`

Запускает парсер с файлом app_ids.

**Request:**
- Content-Type: `multipart/form-data`
- Body: файл `file` с app_ids (один ID на строку)

**Пример с curl:**
```bash
curl -X POST http://your-app.railway.app/start \
  -F "file=@app_ids.txt"
```

**Response (200):**
```json
{
  "status": "started",
  "message": "Parser started with 104215 app IDs",
  "file": "app_ids.txt"
}
```

**Response (400):**
```json
{
  "error": "Parser is already running",
  "status": "running"
}
```

---

### 3. Статус парсинга

**GET** `/status`

Получить текущий статус парсинга.

**Response (200):**
```json
{
  "parser_running": true,
  "statistics": {
    "total_apps": 104215,
    "completed": 5000,
    "pending": 99000,
    "errors": 215,
    "ccu_records": 2500000,
    "price_records": 0
  },
  "progress_percent": 5.0
}
```

---

### 4. Остановка парсера

**POST** `/stop`

Останавливает работающий парсер.

**Response (200):**
```json
{
  "status": "stopping",
  "message": "Parser stop signal sent"
}
```

---

### 5. Экспорт данных

**GET** `/export?type=<type>`

Экспортирует результаты парсинга.

**Параметры:**
- `type` (optional): `full`, `ccu`, или `errors` (по умолчанию: `full`)

**Примеры:**
```bash
# Экспорт всех данных
curl http://your-app.railway.app/export?type=full

# Экспорт только CCU данных
curl http://your-app.railway.app/export?type=ccu

# Экспорт только ошибок
curl http://your-app.railway.app/export?type=errors
```

**Response для type=full:**
```json
{
  "status": "exported",
  "files": {
    "ccu": "/download/ccu?timestamp=20251210_120000",
    "errors": "/download/errors?timestamp=20251210_120000"
  },
  "message": "Export completed. Use /download endpoints to get files."
}
```

**Response для type=ccu или errors:**
Возвращает CSV файл напрямую.

---

### 6. Скачивание файлов

**GET** `/download/<file_type>?timestamp=<timestamp>`

Скачивание экспортированных файлов.

**Параметры:**
- `file_type`: `ccu` или `errors`
- `timestamp` (optional): временная метка файла

**Примеры:**
```bash
# Скачать CCU данные
curl -O http://your-app.railway.app/download/ccu?timestamp=20251210_120000

# Скачать ошибки
curl -O http://your-app.railway.app/download/errors?timestamp=20251210_120000
```

---

### 7. Логи

**GET** `/logs?lines=<number>`

Получить последние логи парсера.

**Параметры:**
- `lines` (optional): количество строк (по умолчанию: 100)

**Пример:**
```bash
curl http://your-app.railway.app/logs?lines=50
```

**Response:**
```json
{
  "logs": [
    "2025-12-10 12:00:00 - INFO - Parser started",
    "2025-12-10 12:00:01 - INFO - Loaded 104215 APP IDs"
  ],
  "total_lines": 1000
}
```

---

## Примеры использования

### Полный цикл работы

```bash
# 1. Проверить статус сервера
curl http://your-app.railway.app/health

# 2. Запустить парсер
curl -X POST http://your-app.railway.app/start \
  -F "file=@app_ids.txt"

# 3. Проверить прогресс
curl http://your-app.railway.app/status

# 4. Экспортировать результаты
curl http://your-app.railway.app/export?type=full

# 5. Скачать файлы
curl -O http://your-app.railway.app/download/ccu?timestamp=20251210_120000
curl -O http://your-app.railway.app/download/errors?timestamp=20251210_120000

# 6. Остановить парсер (если нужно)
curl -X POST http://your-app.railway.app/stop
```

### Python пример

```python
import requests

BASE_URL = "http://your-app.railway.app"

# Запуск парсера
with open('app_ids.txt', 'rb') as f:
    response = requests.post(f"{BASE_URL}/start", files={'file': f})
    print(response.json())

# Проверка статуса
response = requests.get(f"{BASE_URL}/status")
status = response.json()
print(f"Progress: {status['progress_percent']}%")
print(f"Completed: {status['statistics']['completed']}")
print(f"Errors: {status['statistics']['errors']}")

# Экспорт данных
response = requests.get(f"{BASE_URL}/export?type=ccu", stream=True)
with open('results.csv', 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

---

## Обработка ошибок

Все endpoints возвращают стандартные HTTP коды:
- `200` - Успешно
- `400` - Ошибка запроса (неверные параметры)
- `404` - Не найдено
- `500` - Внутренняя ошибка сервера

В случае ошибки response содержит:
```json
{
  "error": "Описание ошибки"
}
```


