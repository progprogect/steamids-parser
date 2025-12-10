# Исправление ошибки запуска парсера на Railway

## Проблема

При запуске парсера через API возникала ошибка:
```
'PosixPath' object has no attribute 'translate'
```

## Исправление

Исправлена обработка путей в `api_server.py`:
- Преобразование `Path` объектов в строки для `shutil.copy2`
- Корректная обработка `UPLOAD_FOLDER` как `Path`

## Деплой исправлений на Railway

### Вариант 1: Автоматический деплой (если подключен GitHub)

Если проект подключен к GitHub репозиторию, Railway автоматически задеплоит изменения при push:

```bash
# Проверка изменений
git status

# Добавление изменений
git add api_server.py

# Коммит
git commit -m "Fix: исправлена обработка путей в API сервере"

# Push (автоматический деплой на Railway)
git push
```

### Вариант 2: Ручной деплой через Railway CLI

```bash
# Подключение к проекту (если еще не подключен)
railway link

# Деплой
railway up
```

### Вариант 3: Через Railway Dashboard

1. Зайдите на [railway.app](https://railway.app)
2. Откройте ваш проект
3. Railway автоматически определит изменения и предложит деплой
4. Нажмите **Deploy**

## Проверка после деплоя

После деплоя проверьте работоспособность:

```bash
# Health check
curl https://worker-production-19aa.up.railway.app/health

# Запуск парсинга
python3 railway_check_and_start.py https://worker-production-19aa.up.railway.app
```

## Альтернативное решение (если деплой невозможен)

Если деплой невозможен прямо сейчас, можно временно использовать прямой запуск парсера через Railway shell:

```bash
# Подключение к Railway shell
railway link
railway shell

# Загрузка файла app_ids.txt
# (скопируйте файл через Railway Dashboard → Volumes или через другой метод)

# Запуск парсера напрямую
python3 parser.py
```

Но это менее удобно, чем через API.
