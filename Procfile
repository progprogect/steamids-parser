web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120 api_server:app
worker: python3 parser.py

