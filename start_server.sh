#!/bin/bash
# Скрипт запуска сервера для Railway
# Railway автоматически устанавливает PORT в переменных окружения

PORT=${PORT:-8080}

echo "Starting API server on port $PORT"
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 1 --threads 2 --timeout 120 api_server:app


