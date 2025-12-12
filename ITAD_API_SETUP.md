# ITAD API Setup Guide

## Получение API ключа

1. Зарегистрируйтесь на [IsThereAnyDeal](https://isthereanydeal.com/)
2. Перейдите на страницу приложения: https://isthereanydeal.com/app/
3. Получите ваш API ключ
4. Установите ключ одним из способов:

### Способ 1: Переменная окружения (рекомендуется)
```bash
export ITAD_API_KEY="your_api_key_here"
```

### Способ 2: Добавить в config.py
```python
ITAD_API_KEY = "your_api_key_here"
```

## Тестирование

После установки API ключа запустите тест:

```bash
python3 test_itad_parser.py
```

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

**Формат ответа:**
```json
{
  "steam/app/730": [
    {
      "timestamp": "2022-12-27T11:21:08+01:00",
      "deal": {
        "price": {
          "amount": 9.99,
          "currency": "USD"
        },
        "regular": {
          "amount": 39.99,
          "currency": "USD"
        }
      },
      "shop": {
        "id": 61,
        "name": "Steam"
      }
    }
  ]
}
```

### `/games/history/v2` (GET)
Получение полной истории цен.

**Параметры:**
- `game_ids`: Список game IDs через запятую (например: `steam/app/730,steam/app/440`)
- `country`: Код страны (US, EU, GB, UA, и т.д.)
- `shops`: Магазины (steam)

## Ограничения API

- Rate limiting: ~2 запроса в секунду
- Требуется валидный API ключ
- Некоторые эндпоинты могут требовать платной подписки

## Маппинг валют на страны

Валюты Steam маппятся на коды стран ITAD:
- USD → US
- EUR → EU
- GBP → GB
- RUB → RU
- и т.д.

Полный список маппинга в файле `itad_currency_mapping.py`

