# Gunicorn configuration for Railway
import os
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = 1
threads = 2
timeout = 120
keepalive = 5
worker_class = "sync"


