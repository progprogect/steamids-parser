# ITAD Price History Parser

## Описание

Модуль для парсинга истории минимальных цен (lowest price history) Steam игр через API IsThereAnyDeal (ITAD).

## Архитектура решения

### Компоненты

1. **`itad_api.py`** - Клиент для работы с ITAD API
   - Управление запросами к API
   - Rate limiting
   - Обработка ошибок

2. **`itad_currency_mapping.py`** - Маппинг валют Steam на регионы ITAD
   - Поддержка всех активных валют Steam (47 валют)
   - Маппинг валют на коды стран ITAD
   - Символы и названия валют

3. **`itad_price_parser.py`** - Основной парсер истории цен
   - Парсинг батчей AppID по валютам
   - Извлечение данных из API ответов
   - Сохранение в CSV формат

4. **`test_itad_parser.py`** - Тестовый скрипт
   - Тестирование на 1-2 AppID
   - Проверка формата данных

## Формат данных

### Входные данные
- Список Steam App IDs (например: `[730, 440]`)

### Выходные данные
CSV файлы с форматом:
```csv
app_id,datetime,price_final,currency_symbol,currency_name
730,2021-07-16 00:00:00,9.99,$,U.S. Dollar
730,2021-09-01 00:00:00,7.49,$,U.S. Dollar
```

### Структура файлов
```
data/itad_price_history/
├── price_history_batch_1_USD.csv
├── price_history_batch_1_EUR.csv
├── price_history_batch_1_GBP.csv
└── ...
```

## Использование

### 1. Установка API ключа

```bash
export ITAD_API_KEY="your_api_key_here"
```

Или добавьте в `config.py`:
```python
ITAD_API_KEY = "your_api_key_here"
```

### 2. Тестирование на малом количестве AppID

```bash
python3 test_itad_parser.py
```

### 3. Парсинг батча AppID

```python
from itad_price_parser import ITADPriceParser

parser = ITADPriceParser()
app_ids = [730, 440, 570]  # Ваши App IDs
stats = parser.parse_price_history(app_ids, batch_number=1)
print(f"Processed: {stats['processed']}, Errors: {stats['errors']}")
```

## Масштабирование на 100k AppID

### Алгоритм работы:

1. **Разбиение на батчи**: 100,000 AppID → 500 батчей по 200 AppID
2. **Обработка по валютам**: Для каждого батча делаем запросы по всем валютам (47 валют)
3. **Сохранение результатов**: Каждый батч × валюта → отдельный CSV файл

### Примерная структура:

```
Батч 1:
  - price_history_batch_1_USD.csv
  - price_history_batch_1_EUR.csv
  - ...
  - price_history_batch_1_BYN.csv

Батч 2:
  - price_history_batch_2_USD.csv
  - ...
```

### Итого файлов:
- 500 батчей × 47 валют = **23,500 CSV файлов**

## API Endpoints

### `/games/historylow/v1` (POST)
Получение истории минимальных цен.

**Формат запроса:**
```json
{
  "game_ids": ["steam/app/730", "steam/app/440"],
  "country": "US",
  "shops": ["steam"]
}
```

### `/games/history/v2` (GET)
Получение полной истории цен (альтернативный эндпоинт).

## Ограничения и рекомендации

1. **Rate Limiting**: ~2 запроса в секунду (настроено в коде)
2. **API Key**: Обязателен для работы API
3. **Батчинг**: Рекомендуется использовать батчи по 200 AppID
4. **Валюты**: Обрабатываются последовательно для каждого батча

## Следующие шаги

1. ✅ Создан модуль для работы с ITAD API
2. ✅ Реализован маппинг валют
3. ✅ Создан парсер истории цен
4. ✅ Реализовано сохранение в CSV
5. ⏳ **Требуется**: Получить API ключ и протестировать на реальных данных
6. ⏳ **После тестирования**: Масштабировать на полный набор AppID

## Примечания

- API ключ можно получить на https://isthereanydeal.com/app/
- Формат данных соответствует требованиям: `app_id, datetime, price_final, currency_symbol, currency_name`
- Поддерживаются все активные валюты Steam из файла `Поддерживаемые валюты.txt`

