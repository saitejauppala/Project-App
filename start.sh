#!/bin/bash

# Production startup script for Render

echo "🚀 Starting EndlessPath Services API..."

# Run database migrations if needed
# alembic upgrade head

# Start the application with gunicorn for production
# Using Uvicorn workers for ASGI support
exec gunicorn app.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --preload