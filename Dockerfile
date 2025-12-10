FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data and logs directories
RUN mkdir -p data logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run API server with gunicorn (parser can be started via API)
# Railway will use PORT from environment variable
# Use shell form to allow variable expansion
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 2 --timeout 120 api_server:app

