#!/usr/bin/env python3
"""
Скрипт запуска gunicorn для Railway
Читает PORT из переменных окружения
"""
import os
import sys

port = os.getenv('PORT', '8080')

try:
    port_int = int(port)
except ValueError:
    print(f"Error: PORT environment variable '{port}' is not a valid port number", file=sys.stderr)
    sys.exit(1)

print(f"Starting gunicorn on port {port_int}")

# Запускаем gunicorn через subprocess
import subprocess

cmd = [
    'gunicorn',
    '--bind', f'0.0.0.0:{port_int}',
    '--workers', '1',
    '--threads', '2',
    '--timeout', '120',
    'api_server:app'
]

os.execvp('gunicorn', cmd)
