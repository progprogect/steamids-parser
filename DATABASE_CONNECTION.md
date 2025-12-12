# Подключение к базе данных PostgreSQL

## 🔗 Строка подключения (Connection String)

```
postgresql://postgres:uOPRuIMnrxqslboMcXBWmIpREfTwsQnh@switchyard.proxy.rlwy.net:58449/railway
```

## 📋 Параметры подключения

| Параметр | Значение |
|----------|----------|
| **Host** | `switchyard.proxy.rlwy.net` |
| **Port** | `58449` |
| **Database** | `railway` |
| **User** | `postgres` |
| **Password** | `uOPRuIMnrxqslboMcXBWmIpREfTwsQnh` |

## 🔧 Примеры подключения

### Python (psycopg2)
```python
import psycopg2

conn = psycopg2.connect(
    host="switchyard.proxy.rlwy.net",
    port=58449,
    database="railway",
    user="postgres",
    password="uOPRuIMnrxqslboMcXBWmIpREfTwsQnh"
)
```

### Python (SQLAlchemy)
```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://postgres:uOPRuIMnrxqslboMcXBWmIpREfTwsQnh@switchyard.proxy.rlwy.net:58449/railway"
)
```

### Node.js (pg)
```javascript
const { Client } = require('pg');

const client = new Client({
    host: 'switchyard.proxy.rlwy.net',
    port: 58449,
    database: 'railway',
    user: 'postgres',
    password: 'uOPRuIMnrxqslboMcXBWmIpREfTwsQnh'
});
```

### DBeaver / pgAdmin
- **Host:** `switchyard.proxy.rlwy.net`
- **Port:** `58449`
- **Database:** `railway`
- **Username:** `postgres`
- **Password:** `uOPRuIMnrxqslboMcXBWmIpREfTwsQnh`

## 📊 Структура базы данных

### Таблицы:
- `ccu_history` - история CCU (Concurrent Users) данных
  - `id` (integer, primary key)
  - `app_id` (integer) - ID приложения Steam
  - `datetime` (text) - дата и время в формате `YYYY-MM-DD HH:MM:SS` (может быть NULL)
  - `players` (integer) - количество игроков (может быть NULL)
  - `value_type` (text) - тип значения ('avg' или NULL)

- `app_status` - статус обработки приложений
  - `app_id` (integer, primary key)
  - `status` (text) - статус ('pending', 'ccu_done', 'ccu_error', 'completed')
  - `last_updated` (text) - дата последнего обновления

- `errors` - журнал ошибок парсинга
  - `id` (integer, primary key)
  - `app_id` (integer)
  - `data_type` (text) - тип данных ('ccu' или 'price')
  - `error_message` (text)
  - `url` (text)
  - `timestamp` (text)

- `price_history` - история цен (если используется)
  - Структура аналогична `ccu_history`

## 📈 Статистика

- **Всего записей CCU:** ~13,197,255
- **Уникальных APP IDs:** 104,215
- **APP IDs с данными:** 104,092
- **APP IDs без данных (NULL):** 123

## ⚠️ Важные замечания

1. **Безопасность:** Эта строка подключения содержит пароль в открытом виде. Не публикуйте её в публичных репозиториях.

2. **Ограничения:** Railway может иметь ограничения на количество подключений и время жизни сессий.

3. **Производительность:** При работе с большими объемами данных используйте индексы и ограничивайте выборки.

4. **NULL значения:** В таблице `ccu_history` поля `datetime` и `players` могут быть NULL для APP IDs без данных.

