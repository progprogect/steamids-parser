#!/bin/bash
# Скрипт для запуска парсинга на Railway

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Запуск парсинга на Railway${NC}"
echo ""

# Проверка наличия Railway CLI
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI не установлен${NC}"
    echo "Установите: npm i -g @railway/cli"
    exit 1
fi

# Проверка подключения к проекту
if ! railway status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Проект не подключен к Railway${NC}"
    echo "Подключите проект: railway link"
    echo ""
    echo "Или укажите URL приложения напрямую:"
    echo "  export RAILWAY_URL=https://your-app.railway.app"
    echo "  ./railway_start_parsing.sh"
    exit 1
fi

# Получение URL приложения
if [ -z "$RAILWAY_URL" ]; then
    echo "Получение URL приложения..."
    RAILWAY_URL=$(railway domain 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
    
    if [ -z "$RAILWAY_URL" ]; then
        echo -e "${YELLOW}⚠️  Не удалось получить URL автоматически${NC}"
        echo "Укажите URL вручную:"
        echo "  export RAILWAY_URL=https://your-app.railway.app"
        exit 1
    fi
fi

echo -e "${GREEN}✅ URL приложения: $RAILWAY_URL${NC}"
echo ""

# Проверка health endpoint
echo "Проверка работоспособности сервера..."
HEALTH_RESPONSE=$(curl -s "$RAILWAY_URL/health" || echo "ERROR")

if echo "$HEALTH_RESPONSE" | grep -q "error"; then
    echo -e "${RED}❌ Сервер не отвечает${NC}"
    echo "Ответ: $HEALTH_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Сервер работает${NC}"
echo ""

# Проверка статуса парсера
echo "Проверка текущего статуса парсера..."
STATUS_RESPONSE=$(curl -s "$RAILWAY_URL/status")
PARSER_RUNNING=$(echo "$STATUS_RESPONSE" | grep -o '"parser_running":[^,]*' | cut -d: -f2)

if [ "$PARSER_RUNNING" = "true" ]; then
    echo -e "${YELLOW}⚠️  Парсер уже запущен${NC}"
    echo "Текущий статус:"
    echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
    echo ""
    read -p "Остановить текущий парсинг и запустить заново? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Остановка парсера..."
        curl -s -X POST "$RAILWAY_URL/stop" > /dev/null
        sleep 2
    else
        echo "Парсинг продолжается. Используйте: curl $RAILWAY_URL/status"
        exit 0
    fi
fi

# Проверка наличия файла app_ids.txt
if [ ! -f "app_ids.txt" ]; then
    echo -e "${RED}❌ Файл app_ids.txt не найден${NC}"
    exit 1
fi

APP_COUNT=$(wc -l < app_ids.txt | tr -d ' ')
echo -e "${GREEN}✅ Найдено $APP_COUNT APP IDs${NC}"
echo ""

# Запуск парсинга
echo "Запуск парсинга..."
START_RESPONSE=$(curl -s -X POST "$RAILWAY_URL/start" -F "file=@app_ids.txt")

if echo "$START_RESPONSE" | grep -q "error"; then
    echo -e "${RED}❌ Ошибка при запуске парсера${NC}"
    echo "Ответ: $START_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Парсер запущен успешно!${NC}"
echo ""
echo "Ответ сервера:"
echo "$START_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$START_RESPONSE"
echo ""

# Мониторинг прогресса
echo "Мониторинг прогресса (Ctrl+C для выхода)..."
echo ""

while true; do
    STATUS_RESPONSE=$(curl -s "$RAILWAY_URL/status")
    echo "$STATUS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$STATUS_RESPONSE"
    echo ""
    sleep 10
done
